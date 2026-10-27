"""LOCAL PROBE, NOT FOR COMMIT. Read-and-probe only: what happens to a CLI->gateway handoff whose
synthetic internal turn hits the fresh-turn compression gate?

The probe asserts only setup facts; everything else is printed as OBSERVED lines (run with -s).
"""

import asyncio
import contextlib
import types
from unittest.mock import AsyncMock, patch

import pytest

from gateway import run
from gateway.config import GatewayConfig, HomeChannel, Platform, PlatformConfig
from gateway.platforms.base import BasePlatformAdapter, SendResult
from gateway.platforms.event import MessageEvent, MessageType
from gateway.run import GatewayRunner
from gateway.session import SessionSource, SessionStore

HOME_CHAT = "555900"


class _Adapter(BasePlatformAdapter):
    """A real BasePlatformAdapter (real pending slot, guards and drain) over a fake transport."""

    def __init__(self):
        super().__init__(PlatformConfig(enabled=True, token="x"), Platform.TELEGRAM)
        self.sent = []

    @property
    def name(self):
        return "telegram"

    async def connect(self, *, is_reconnect=False):
        return True

    async def disconnect(self):
        pass

    async def send(self, chat_id, content, reply_to=None, metadata=None):
        self.sent.append(content)
        return SendResult(success=True)

    async def get_chat_info(self, chat_id):
        return {"id": chat_id, "type": "private"}


def _runner(tmp_path):
    adapter = _Adapter()
    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(platforms={Platform.TELEGRAM: PlatformConfig(enabled=True, token="x")})
    runner.config.platforms[Platform.TELEGRAM].home_channel = HomeChannel(
        platform=Platform.TELEGRAM, chat_id=HOME_CHAT, name="home")
    runner.adapters = {Platform.TELEGRAM: adapter}
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
    adapter.set_message_handler(runner._handle_message)
    return runner, adapter


class _DB:
    """Records what the real watcher does with the row."""

    def __init__(self):
        self.state = "pending"
        self.calls = []

    async def list_pending_handoffs(self):
        return [{"id": "cli-session-0001", "title": "work", "handoff_platform": "telegram"}] \
            if self.state == "pending" else []

    async def claim_handoff(self, sid):
        if self.state != "pending":
            return False
        self.state = "running"
        self.calls.append(("claim", sid))
        return True

    async def complete_handoff(self, sid):
        self.state = "completed"
        self.calls.append(("complete", sid))

    async def fail_handoff(self, sid, err):
        self.state = "failed"
        self.calls.append(("fail", sid, err))


@contextlib.contextmanager
def _world(compressing):
    """Stub only the agent turn and the compression-lock read; ``compressing`` is a mutable flag."""
    turns = []

    async def _cold(self, event, *a, **k):
        turns.append(event.text[:40])
        return "COLD_PATH_REPLY"

    async def _in_flight(self, _key):
        return compressing["on"]

    with (
        patch.object(GatewayRunner, "_handle_message_with_agent", _cold),
        patch.object(GatewayRunner, "_run_post_turn_hooks", AsyncMock()),
        patch.object(GatewayRunner, "_clear_durable_active_turn", AsyncMock()),
        patch.object(GatewayRunner, "_persist_active_agents", lambda self: None),
        patch.object(GatewayRunner, "_session_has_compression_in_flight", _in_flight),
    ):
        yield turns


async def _run_watcher_once(runner, db, monkeypatch):
    """Drive the REAL ``_handoff_watcher`` for a couple of ticks against the real ``_process_handoff``."""
    monkeypatch.setattr(run, "_handoff_watch_scopes", lambda _r: [(None, None)])
    real_sleep = asyncio.sleep

    async def _yield_sleep(_s):
        await real_sleep(0)

    monkeypatch.setattr(run.asyncio, "sleep", _yield_sleep)
    states = iter([True] * 4)

    class _Running:
        def __bool__(_self):
            return next(states, False)

    fake = types.SimpleNamespace(_session_db=db, _running=_Running(), _process_handoff=runner._process_handoff)
    await asyncio.wait_for(GatewayRunner._handoff_watcher(fake, interval=0.0, drain_timeout=2.0), timeout=20)
    monkeypatch.setattr(run.asyncio, "sleep", real_sleep)
    for _ in range(20):
        await real_sleep(0)


async def _settle(adapter, seconds=3.0):
    """Let every adapter-owned task finish, up to ``seconds`` of real time."""
    loop = asyncio.get_running_loop()
    end = loop.time() + seconds
    while loop.time() < end:
        await asyncio.sleep(0.05)
        if not [t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()]:
            break


@pytest.mark.asyncio
@pytest.mark.parametrize("compression", [False, True], ids=["control-no-compression", "compression-in-flight"])
async def test_probe_handoff_during_compression(tmp_path, monkeypatch, compression, capsys):
    runner, adapter = _runner(tmp_path)
    db = _DB()
    compressing = {"on": compression}
    out = []
    with _world(compressing) as turns:
        await _run_watcher_once(runner, db, monkeypatch)
        out.append(f"watcher db calls            : {db.calls}")
        out.append(f"handoff row state           : {db.state}")
        out.append(f"agent turns started         : {turns!r}")
        out.append(f"adapter.sent                : {adapter.sent!r}")
        parked = {k: (v.text[:32], v.internal) for k, v in adapter._pending_messages.items()}
        out.append(f"adapter._pending_messages   : {parked}")
        out.append(f"adapter._active_sessions    : {list(adapter._active_sessions)}")
        out.append(f"adapter._session_tasks      : {list(getattr(adapter, '_session_tasks', {}))}")

        # Compression finishes. Does anything deliver the parked event on its own?
        compressing["on"] = False
        await _settle(adapter, seconds=3.0)
        await asyncio.sleep(2.0)
        out.append(f"[+~3s, lock clear] turns    : {turns!r}")
        out.append(f"[+~3s, lock clear] pending  : {list(adapter._pending_messages)}")

        # The user's next real message in the home chat, through the adapter's real inbound path.
        user = MessageEvent(
            text="hello from the phone", message_type=MessageType.TEXT,
            source=SessionSource(platform=Platform.TELEGRAM, chat_id=HOME_CHAT, chat_type="dm",
                                 user_id=HOME_CHAT),
        )
        await adapter.handle_message(user)
        await _settle(adapter, seconds=5.0)
        out.append(f"[after user msg] turns      : {turns!r}")
        out.append(f"[after user msg] sent       : {adapter.sent!r}")
        out.append(f"[after user msg] pending    : {list(adapter._pending_messages)}")
        out.append(f"[after user msg] row state  : {db.state}")
    with capsys.disabled():
        print(f"\n=== OBSERVED ({'compression in flight' if compression else 'control'}) ===")
        for line in out:
            print("  " + line)
    assert ("claim", "cli-session-0001") in db.calls  # setup fact only: the watcher did dispatch the row
