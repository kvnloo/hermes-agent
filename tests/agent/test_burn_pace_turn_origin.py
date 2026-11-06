"""Only a human-submitted turn may use the owner's hot subscription rows."""
import asyncio
import json
from contextvars import copy_context
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from agent import burn_pace_gate as gate
from agent.turn_author import human_turn, human_turn_scope
from gateway.config import Platform
from gateway.session import SessionSource
from gateway.session_turn_origin import human_authored_input

MODEL = "claude-opus-5-5"
LANES = {"owner_profiles": ["clean", "ayo"], "anthropic": {"subscription": "claude"}}
ENTRY = SimpleNamespace(label="subscription")
BOT = {"id": "bot:worker", "name": "Worker", "is_bot": True}
HUMAN = {"id": "human", "name": "Kevin", "is_bot": False}


@pytest.fixture
def pace(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_PROFILE_NAME", "clean")
    monkeypatch.setenv("BURN_GATE_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_BURN_GATE_OVERRIDE", raising=False)
    lanes = tmp_path / ".config/burn-gate/pool-lanes.json"
    lanes.parent.mkdir(parents=True)
    lanes.write_text(json.dumps(LANES))
    reading = tmp_path / ".z0int/state/posture/burn-pace.jsonl"
    reading.parent.mkdir(parents=True)
    reading.write_text(json.dumps({"at": datetime.now(UTC).isoformat(), "lanes": {
        "claude": {"weekly_used_pct": 40, "pace_ratio": 2}}}) + "\n")
    monkeypatch.setattr(gate, "_cache", {"at": 0.0, "key": None, "val": None})


def test_missing_turn_origin_is_bulk(pace):
    assert gate.who_for(MODEL, LANES) == gate.BULK
    assert gate.admit("anthropic", [ENTRY], MODEL) == []


@pytest.fixture
def isolated_update_marker(tmp_path, monkeypatch):
    # This worktree's Git directory can live inside the guarded production home.
    from hermes_cli import _early_recovery

    monkeypatch.setattr(_early_recovery, "interrupted_pull_marker", lambda root: tmp_path / "hermes-update-pull")


def _policy(source):
    return SimpleNamespace(source=source, platform=source, kanban_json=None, request_json="{}") if source else None


@pytest.mark.parametrize("kind,profile,expected", [
    ("cli-human", "clean", gate.OWNER),
    ("cli-human", "ayo", gate.OWNER),
    ("native-human", "clean", gate.OWNER),
    ("cli-human", "ossfactory", gate.BULK),
    ("goal", "clean", gate.BULK),
    ("cron", "clean", gate.BULK),
    ("a2a", "clean", gate.BULK),
    ("bot", "clean", gate.BULK),
    ("native-bot", "clean", gate.BULK),
    ("timer", "clean", gate.BULK),
    ("hidden", "clean", gate.BULK),
    ("unattended", "clean", gate.BULK),
    ("kanban", "clean", gate.BULK),
    ("api-human-label", "clean", gate.BULK),
    ("webhook", "clean", gate.BULK),
])
def test_admission_origin_controls_hot_row_routing(pace, monkeypatch, kind, profile, expected):
    monkeypatch.setenv("HERMES_PROFILE_NAME", profile)
    source = SessionSource(platform=Platform.LOCAL, chat_id="chat", user_id="human")
    policy = _policy("cli")
    payload = {"text": "work"}
    if kind in {"native-human", "native-bot", "goal", "webhook"}:
        source.platform = Platform.WEBHOOK if kind == "webhook" else Platform.TELEGRAM
        policy = None
        source.is_bot = kind == "native-bot"
        payload["native_text_v1"] = {"event": {}, "source": {**source.to_dict(), "is_bot": source.is_bot}}
        if kind == "goal":
            from gateway.run_goals import GatewayGoalsMixin
            event = GatewayGoalsMixin._synthetic_prompt_event(source, "continue")
            payload["native_text_v1"]["event"]["inherit_channel_pin"] = event.inherit_channel_pin
    elif kind == "cron":
        policy = _policy("cron")
    elif kind == "a2a":
        policy = _policy("a2a")
    elif kind == "bot":
        payload["cli_turn_v1"] = {"turn_author": BOT}
    elif kind == "timer":
        payload["local_automation_v1"] = {"producer": "loop"}
    elif kind == "hidden":
        payload["display_v1"] = {"kind": "hidden"}
    elif kind == "unattended":
        payload.update(finite=True, unattended=True)
    elif kind == "kanban":
        policy.kanban_json = "{}"
    elif kind == "api-human-label":
        payload["api_turn_v1"] = {"turn_author": HUMAN}
    row = {"request_id": "input", "payload": payload}
    with human_turn_scope(human_authored_input(policy, row, source)):
        assert gate.who_for(MODEL, LANES) == expected
        assert gate.admit("anthropic", [ENTRY], MODEL) == ([ENTRY] if expected == gate.OWNER else [])
    assert human_turn.get() is False


def test_nested_bulk_work_and_exceptions_restore_the_human_scope(pace):
    with human_turn_scope(True):
        inherited = copy_context()

        def background_work():
            with human_turn_scope():
                assert gate.who_for(MODEL, LANES) == gate.BULK
                raise RuntimeError("failed work")

        with pytest.raises(RuntimeError, match="failed work"):
            inherited.run(background_work)
        assert gate.who_for(MODEL, LANES) == gate.OWNER
    assert human_turn.get() is False


@pytest.mark.asyncio
async def test_real_cli_admission_reclassifies_each_submit_and_carries_scope_to_worker(
        pace, tmp_path, monkeypatch, isolated_update_marker):
    from gateway.session_controls import AuthorityConnection
    from tests.gateway.test_surface_admission import _authority

    seen = []

    async def answer(event):
        # Same executor hop as the gateway model runner, reading the actual pacing gate.
        admitted = await asyncio.to_thread(gate.admit, "anthropic", [ENTRY], MODEL)
        seen.append(bool(admitted))
        return "paid" if admitted else "free"

    authority = await _authority(tmp_path, monkeypatch, answer)
    connection = AuthorityConnection(authority, object(), {"user_id": "owner"})
    try:
        await connection.dispatch({"id": 1, "method": "session.resume", "params": {"session_id": "s"}})
        for index, extra in enumerate(({}, {"turn_author": BOT}, {}, {"display_kind": "hidden"}, {})):
            reply = await connection.dispatch({"id": 2, "method": "prompt.submit", "params": {
                "session_id": "s", "submission_id": str(index), "text": "work", **extra}})
            assert reply.get("result", {}).get("status") == "queued", reply
            await authority.sessions["s"].task
            assert human_turn.get() is False
    finally:
        await connection.close()
    assert seen == [True, False, True, False, True]


def test_native_sender_snapshot_wins_over_live_session_source(pace):
    source = SessionSource(platform=Platform.TELEGRAM, chat_id="chat", user_id="human")
    native = {"event": {}, "source": {**source.to_dict(), "is_bot": True}}
    row = {"request_id": "queued-bot", "payload": {"text": "work", "native_text_v1": native}}
    assert human_authored_input(None, row, source) is False
    native["source"]["is_bot"] = False
    source.is_bot = True
    assert human_authored_input(None, row, source) is True
    native["automation"] = {}
    assert human_authored_input(None, row, source) is False
    del native["automation"]
    del native["source"]["is_bot"]
    assert human_authored_input(None, row, source) is False


def test_gateway_passes_origin_to_the_agent_for_this_turn_only(isolated_update_marker):
    from tests.gateway.test_local_viewer_events_submit import _gateway_runner, _run_turn

    with human_turn_scope(True):
        _, agent = _run_turn(_gateway_runner())
        assert agent.calls[0][1]["human_authored"] is True
    _, agent = _run_turn(_gateway_runner())
    assert agent.calls[0][1]["human_authored"] is False


def test_auxiliary_calls_do_not_inherit_owner_pacing(pace):
    from agent.auxiliary_client import _relay_aux_call_scope

    with human_turn_scope(True):
        with _relay_aux_call_scope(("compression",), {}):
            assert gate.who_for(MODEL, LANES) == gate.BULK
        assert gate.who_for(MODEL, LANES) == gate.OWNER
