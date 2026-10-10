"""A CLI→gateway handoff that arrives while context compression is in flight.

The handoff's synthetic turn is an internal event, so the fresh-turn compression gate defers it
instead of refusing it. A deferred turn has not run: the row must stay ``running`` (the CLI keeps
waiting) until the turn has run in the destination chat, and the turn must run as soon as the
compression lock clears — with no inbound message from the user to shake it loose.

Real ``_handoff_watcher`` / ``_process_handoff`` / ``_handle_message``, a real
``BasePlatformAdapter`` over a fake transport and a real ``SessionStore``. Only the compression-lock
read and the agent turn are stubbed.
"""

import asyncio
import contextlib
from unittest.mock import AsyncMock, patch

import pytest

from gateway import run
from gateway.config import GatewayConfig, HomeChannel, Platform, PlatformConfig
from gateway.platforms.base import BasePlatformAdapter, SendResult
from gateway.run import GatewayRunner
from gateway.session import SessionStore

HOME_CHAT = "555900"
CLI_SESSION = "cli-session-0001"
REPLY = "Confirmed: working here now."

_real_sleep = asyncio.sleep


class _Adapter(BasePlatformAdapter):
    """The real base adapter (pending slot, session guard, drain back-off) over a fake transport."""

    def __init__(self, timeline):
        super().__init__(PlatformConfig(enabled=True, token="x"), Platform.TELEGRAM)
        self.sent = []
        self._timeline = timeline

    @property
    def name(self):
        return "telegram"

    async def connect(self, *, is_reconnect=False):
        return True

    async def disconnect(self):
        pass

    async def send(self, chat_id, content, reply_to=None, metadata=None):
        self.sent.append((str(chat_id), content))
        self._timeline.append("sent")
        return SendResult(success=True)

    async def get_chat_info(self, chat_id):
        return {"id": chat_id, "type": "private"}


class _HandoffRows:
    """The one handoff row, with the state machine the watcher drives."""

    def __init__(self, timeline):
        self.state = "pending"
        self.error = None
        self._timeline = timeline

    async def list_pending_handoffs(self):
        if self.state != "pending":
            return []
        return [{"id": CLI_SESSION, "title": "work", "handoff_platform": "telegram"}]

    async def claim_handoff(self, session_id):
        if self.state != "pending":
            return False
        self.state = "running"
        self._timeline.append("claimed")
        return True

    async def complete_handoff(self, session_id):
        self.state = "completed"
        self._timeline.append("completed")

    async def fail_handoff(self, session_id, error):
        self.state, self.error = "failed", error
        self._timeline.append("failed")


class _Gateway:
    def __init__(self, tmp_path):
        self.timeline = []
        self.turns = []
        self.lock_reads = 0
        self.compressing = False
        self.adapter = _Adapter(self.timeline)
        self.rows = _HandoffRows(self.timeline)

        runner = object.__new__(GatewayRunner)
        runner.config = GatewayConfig(platforms={Platform.TELEGRAM: PlatformConfig(enabled=True, token="x")})
        runner.config.platforms[Platform.TELEGRAM].home_channel = HomeChannel(
            platform=Platform.TELEGRAM, chat_id=HOME_CHAT, name="home")
        runner.adapters = {Platform.TELEGRAM: self.adapter}
        runner._pending_messages = {}
        runner._voice_mode = {}
        runner._background_tasks = set()
        runner._draining = False
        runner._restart_requested = False
        runner._restart_task_started = False
        runner._restart_detached = False
        runner._restart_via_service = False
        runner._restart_drain_timeout = 0.0
        runner._stop_task = None
        runner._exit_code = None
        runner._update_runtime_status = AsyncMock()
        runner._is_user_authorized = lambda _source: True
        runner.hooks = AsyncMock()
        runner.session_store = SessionStore(sessions_dir=tmp_path, config=GatewayConfig())
        runner.delivery_router = AsyncMock()
        runner._session_db = self.rows
        runner._running = True
        self.adapter.set_message_handler(runner._handle_message)
        self.runner = runner

    @contextlib.contextmanager
    def running(self, monkeypatch):
        """Stub the agent turn and the compression-lock read; shorten sleeps (the watcher's 5 s
        connect grace, its poll interval and the adapter's re-dispatch back-off) without removing
        the yield they give the loop."""
        gateway = self

        async def _agent_turn(_runner, event, *_args, **_kwargs):
            gateway.turns.append(event.text)
            gateway.timeline.append("turn")
            return REPLY

        async def _compression_in_flight(_runner, _session_key):
            gateway.lock_reads += 1
            return gateway.compressing

        async def _short_sleep(seconds, *args, **kwargs):
            await _real_sleep(min(seconds, 0.01))

        monkeypatch.setattr(run.asyncio, "sleep", _short_sleep)
        with (
            patch.object(GatewayRunner, "_handle_message_with_agent", _agent_turn),
            patch.object(GatewayRunner, "_run_post_turn_hooks", AsyncMock()),
            patch.object(GatewayRunner, "_clear_durable_active_turn", AsyncMock()),
            patch.object(GatewayRunner, "_persist_active_agents", lambda _runner: None),
            patch.object(GatewayRunner, "_session_has_compression_in_flight", _compression_in_flight),
        ):
            yield

    async def stop(self, watcher):
        self.runner._running = False
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait_for(watcher, timeout=10)
        await self.adapter.cancel_background_tasks()


async def _until(predicate, timeout=10.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            return False
        await _real_sleep(0.01)
    return True


@pytest.mark.asyncio
async def test_handoff_waits_for_compression_and_runs_without_a_user_message(tmp_path, monkeypatch):
    gateway = _Gateway(tmp_path)
    gateway.compressing = True
    with gateway.running(monkeypatch):
        watcher = asyncio.create_task(gateway.runner._handoff_watcher(interval=0.01, drain_timeout=0.2))
        try:
            # The watcher claims the row and the gate turns the synthetic turn away at least once.
            assert await _until(lambda: "claimed" in gateway.timeline and gateway.lock_reads >= 1)
            await _real_sleep(0.3)

            # No turn has run and nothing was sent, so the CLI must still be waiting on the row.
            assert gateway.turns == []
            assert gateway.adapter.sent == []
            assert gateway.rows.state == "running", (
                f"handoff reported {gateway.rows.state!r} although its turn never started"
            )

            # Compression commits. Nobody sends anything; the deferred turn must start by itself.
            gateway.compressing = False
            assert await _until(lambda: gateway.rows.state != "running"), (
                f"deferred handoff turn never ran after compression cleared: timeline={gateway.timeline}"
            )
        finally:
            await gateway.stop(watcher)

    assert gateway.rows.state == "completed", gateway.rows.error
    assert len(gateway.turns) == 1 and gateway.turns[0].startswith("[Session was just handed off from CLI")
    assert gateway.adapter.sent == [(HOME_CHAT, REPLY)]
    # The row is completed only after the turn ran and its confirmation went out.
    assert gateway.timeline == ["claimed", "turn", "sent", "completed"]
    # Nothing is left behind to run a second time on the user's next message.
    assert gateway.adapter._pending_messages == {}
    assert gateway.adapter._active_sessions == {}


@pytest.mark.asyncio
async def test_gateway_stop_while_handoff_is_deferred_does_not_report_it_completed(tmp_path, monkeypatch):
    """Compression never clears before shutdown: the row stays ``running`` for the next start's
    stale-handoff reclaim to fail, exactly like any other handoff a stop cut short."""
    gateway = _Gateway(tmp_path)
    gateway.compressing = True
    with gateway.running(monkeypatch):
        watcher = asyncio.create_task(gateway.runner._handoff_watcher(interval=0.01, drain_timeout=0.2))
        try:
            assert await _until(lambda: "claimed" in gateway.timeline and gateway.lock_reads >= 1)
            await _real_sleep(0.3)
        finally:
            await gateway.stop(watcher)

    assert gateway.turns == []
    assert gateway.adapter.sent == []
    assert gateway.rows.state == "running"


@pytest.mark.asyncio
async def test_handoff_without_compression_runs_at_once(tmp_path, monkeypatch):
    gateway = _Gateway(tmp_path)
    with gateway.running(monkeypatch):
        watcher = asyncio.create_task(gateway.runner._handoff_watcher(interval=0.01, drain_timeout=0.2))
        try:
            assert await _until(lambda: gateway.rows.state != "pending" and gateway.rows.state != "running")
        finally:
            await gateway.stop(watcher)

    assert gateway.rows.state == "completed", gateway.rows.error
    assert gateway.adapter.sent == [(HOME_CHAT, REPLY)]
    assert gateway.timeline == ["claimed", "turn", "sent", "completed"]
