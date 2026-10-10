"""A CLI→gateway handoff that arrives while context compression is in flight.

The handoff's synthetic turn is an internal event, so the fresh-turn compression gate defers it
instead of refusing it. A deferred turn has not run: the row must stay ``running`` (the CLI keeps
waiting) until the turn has run in the destination chat, and the turn must run as soon as the
compression lock clears — with no inbound message from the user to shake it loose.

A handoff is reported ``completed`` only on positive evidence that its own turn returned. A turn
that was queued and then discarded without running — gateway stop, ``/stop`` or ``/new`` in the
destination chat, a turn that raised, no adapter to run it — ends ``failed`` with a reason.

Real ``_handoff_watcher`` / ``_process_handoff`` / ``_handle_message`` / ``stop``, a real
``BasePlatformAdapter`` over a fake transport and a real ``SessionStore``. Only the compression-lock
read and the agent turn are stubbed.
"""

import asyncio
import contextlib
from unittest.mock import AsyncMock, patch

import pytest

from gateway import run
from gateway.config import GatewayConfig, HomeChannel, Platform, PlatformConfig
from gateway.platforms.base import BasePlatformAdapter, MessageEvent, SendResult
from gateway.run import GatewayRunner
from gateway.session import SessionStore
from tests.gateway.restart_test_helpers import make_restart_runner

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

        # The runner the shutdown tests stop for real, so ``stop()`` runs its production phases.
        runner, _ = make_restart_runner(self.adapter)
        runner.config.platforms[Platform.TELEGRAM].home_channel = HomeChannel(
            platform=Platform.TELEGRAM, chat_id=HOME_CHAT, name="home")
        runner._restart_drain_timeout = 0.0
        runner.session_store = SessionStore(sessions_dir=tmp_path, config=GatewayConfig())
        runner._session_db = self.rows
        self.adapter.set_message_handler(runner._handle_message)
        self.runner = runner
        self.watcher = None

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
            patch.object(GatewayRunner, "_clear_durable_active_turn", AsyncMock()),
            patch.object(GatewayRunner, "_persist_active_agents", lambda _runner: None),
            patch.object(GatewayRunner, "_session_has_compression_in_flight", _compression_in_flight),
            patch("gateway.status.remove_pid_file"),
            patch("gateway.status.publish_runtime_status"),
        ):
            yield

    def start_watcher(self, drain_timeout=0.2):
        """Spawn the watcher the way ``_start_spawn_background_watchers`` does: supervised and
        tracked in ``_background_tasks``, which is where ``stop()`` finds it."""
        self.watcher = self.runner._spawn_supervised(
            lambda: self.runner._handoff_watcher(interval=0.01, drain_timeout=drain_timeout),
            "handoff_watcher",
        )
        return self.watcher

    async def deferred(self):
        """The row is claimed, the gate has turned the turn away, and nothing has run."""
        assert await _until(lambda: "claimed" in self.timeline and self.lock_reads >= 1)
        await _real_sleep(0.3)
        assert self.turns == [] and self.adapter.sent == []
        assert self.rows.state == "running", (
            f"handoff reported {self.rows.state!r} although its turn never started"
        )

    def session_key(self):
        return self.runner._session_key_for_source(self.user_source())

    def user_source(self):
        """The home chat as the adapter sees a private message from it — the handoff's own key."""
        return self.adapter.build_source(chat_id=HOME_CHAT, chat_type="dm", user_id=HOME_CHAT, user_name="u")

    async def user_says(self, text):
        await self.adapter.handle_message(
            MessageEvent(text=text, source=self.user_source(), message_id=f"m-{len(self.timeline)}"))

    async def stop(self, watcher):
        """Test cleanup, not a shutdown under test: watcher first so nothing is cut short."""
        self.runner._running = False
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait_for(watcher, timeout=10)
        await self.adapter.cancel_background_tasks()

    async def production_stop(self):
        """The real ``GatewayRunner.stop()``: adapters are torn down BEFORE the watcher is
        cancelled, and the cancelled watcher then drains its in-flight dispatch."""
        await self.runner.stop()
        await asyncio.wait({self.watcher}, timeout=10)
        assert self.watcher.done()


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
        watcher = gateway.start_watcher()
        try:
            # The watcher claims the row and the gate turns the synthetic turn away at least once. No
            # turn has run and nothing was sent, so the CLI must still be waiting on the row.
            await gateway.deferred()

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


def _assert_failed_without_a_turn(gateway):
    assert "completed" not in gateway.timeline, (
        f"handoff reported completed with no turn: timeline={gateway.timeline}"
    )
    assert gateway.turns == []
    assert gateway.adapter.sent == []
    assert gateway.rows.state == "failed", gateway.rows.state
    assert gateway.rows.error


@pytest.mark.asyncio
async def test_gateway_stop_in_production_order_fails_the_deferred_handoff(tmp_path, monkeypatch):
    """``stop()`` tears the adapters down (clearing their queues) before it cancels the watcher,
    whose ``finally`` then waits for the in-flight dispatch. The discarded turn must not read as a
    turn that ran: the row is failed with the reason, so the CLI stops waiting at once."""
    gateway = _Gateway(tmp_path)
    gateway.compressing = True
    with gateway.running(monkeypatch):
        gateway.start_watcher(drain_timeout=2.0)
        await gateway.deferred()
        await gateway.production_stop()

    assert "completed" not in gateway.timeline, f"completed with no turn: timeline={gateway.timeline}"
    assert gateway.turns == []
    assert REPLY not in [content for _chat, content in gateway.adapter.sent]
    assert gateway.rows.state == "failed", gateway.rows.state
    assert "gateway stopped" in gateway.rows.error
    assert gateway.adapter._pending_messages == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["/stop", "/new"])
async def test_stop_or_new_in_the_chat_while_deferred_does_not_complete_the_handoff_early(
    tmp_path, monkeypatch, command
):
    """The user's own ``/stop`` (nothing is running) or unconfirmed ``/new`` in the destination chat
    cancels the task that was re-dispatching the queued turn. The adapter keeps the queued event
    and re-dispatches it, so the row stays ``running`` until that turn has really run."""
    gateway = _Gateway(tmp_path)
    gateway.compressing = True
    with gateway.running(monkeypatch):
        watcher = gateway.start_watcher()
        try:
            await gateway.deferred()
            await gateway.user_says(command)
            await _real_sleep(0.3)
            assert gateway.turns == []
            assert gateway.rows.state == "running", (
                f"{command} made the handoff {gateway.rows.state!r} with no turn: {gateway.rows.error}"
            )
            gateway.compressing = False
            assert await _until(lambda: gateway.rows.state != "running")
        finally:
            await gateway.stop(watcher)

    assert gateway.rows.state == "completed", gateway.rows.error
    assert len(gateway.turns) == 1 and gateway.turns[0].startswith("[Session was just handed off from CLI")
    assert gateway.timeline.index("turn") < gateway.timeline.index("completed")
    assert gateway.adapter.sent[-1] == (HOME_CHAT, REPLY)


@pytest.mark.asyncio
async def test_queue_cleared_while_deferred_fails_the_handoff(tmp_path, monkeypatch):
    """The adapter's own discard (what a reset or an adapter replacement does to a session): the
    owner task is cancelled and the pending slot emptied, so the turn can never run."""
    gateway = _Gateway(tmp_path)
    gateway.compressing = True
    with gateway.running(monkeypatch):
        watcher = gateway.start_watcher()
        try:
            await gateway.deferred()
            await gateway.adapter.cancel_session_processing(gateway.session_key())
            assert await _until(lambda: gateway.rows.state != "running")
            # Compression clearing afterwards must not resurrect the discarded turn.
            gateway.compressing = False
            await _real_sleep(0.3)
        finally:
            await gateway.stop(watcher)

    _assert_failed_without_a_turn(gateway)
    assert "did not run" in gateway.rows.error


@pytest.mark.asyncio
async def test_deferred_turn_that_raises_fails_the_handoff(tmp_path, monkeypatch):
    gateway = _Gateway(tmp_path)
    gateway.compressing = True
    attempts = []

    async def _boom(_runner, event, *_args, **_kwargs):
        attempts.append(event.text)
        raise RuntimeError("model exploded")

    with gateway.running(monkeypatch), patch.object(GatewayRunner, "_handle_message_with_agent", _boom):
        watcher = gateway.start_watcher()
        try:
            await gateway.deferred()
            gateway.compressing = False
            assert await _until(lambda: gateway.rows.state != "running")
        finally:
            await gateway.stop(watcher)

    assert len(attempts) == 1
    assert "completed" not in gateway.timeline
    assert gateway.rows.state == "failed", gateway.rows.state
    assert "did not run" in gateway.rows.error


@pytest.mark.asyncio
async def test_no_delivery_adapter_while_compressing_fails_the_handoff(tmp_path, monkeypatch):
    """With nothing to park the event in, the gate drops it and returns the same empty reply a
    streamed turn does. No turn ran, so that is not a success."""
    gateway = _Gateway(tmp_path)
    gateway.compressing = True
    with gateway.running(monkeypatch), patch.object(GatewayRunner, "_delivery_adapter_for", lambda *_a: None):
        watcher = gateway.start_watcher()
        try:
            assert await _until(lambda: gateway.rows.state not in ("pending", "running"))
        finally:
            await gateway.stop(watcher)

    _assert_failed_without_a_turn(gateway)
    assert "adapter" in gateway.rows.error


@pytest.mark.asyncio
async def test_user_message_while_deferred_does_not_lose_or_repeat_the_handoff(tmp_path, monkeypatch):
    gateway = _Gateway(tmp_path)
    gateway.compressing = True
    with gateway.running(monkeypatch):
        watcher = gateway.start_watcher()
        try:
            await gateway.deferred()
            await gateway.user_says("hello from the phone")
            await _real_sleep(0.3)
            assert gateway.rows.state == "running"
            gateway.compressing = False
            assert await _until(lambda: gateway.rows.state != "running")
            await _real_sleep(0.3)
        finally:
            await gateway.stop(watcher)

    handoff_turns = [turn for turn in gateway.turns if turn.startswith("[Session was just handed off from CLI")]
    assert len(handoff_turns) == 1
    assert gateway.rows.state == "completed", gateway.rows.error
    assert gateway.timeline.index("turn") < gateway.timeline.index("completed")


@pytest.mark.asyncio
async def test_handoff_without_compression_runs_at_once(tmp_path, monkeypatch):
    gateway = _Gateway(tmp_path)
    with gateway.running(monkeypatch):
        watcher = gateway.start_watcher()
        try:
            assert await _until(lambda: gateway.rows.state != "pending" and gateway.rows.state != "running")
        finally:
            await gateway.stop(watcher)

    assert gateway.rows.state == "completed", gateway.rows.error
    assert gateway.adapter.sent == [(HOME_CHAT, REPLY)]
    assert gateway.timeline == ["claimed", "turn", "sent", "completed"]


@pytest.mark.asyncio
async def test_streamed_handoff_without_compression_still_completes(tmp_path, monkeypatch):
    """A turn that streamed its own reply returns nothing to send. That empty reply is still a turn
    that ran, and must keep completing the handoff."""
    gateway = _Gateway(tmp_path)

    async def _streamed_turn(_runner, event, *_args, **_kwargs):
        gateway.turns.append(event.text)
        gateway.timeline.append("turn")
        await gateway.adapter.send(HOME_CHAT, REPLY)
        return None

    with gateway.running(monkeypatch), patch.object(GatewayRunner, "_handle_message_with_agent", _streamed_turn):
        watcher = gateway.start_watcher()
        try:
            assert await _until(lambda: gateway.rows.state not in ("pending", "running"))
        finally:
            await gateway.stop(watcher)

    assert gateway.rows.state == "completed", gateway.rows.error
    assert gateway.timeline == ["claimed", "turn", "sent", "completed"]
