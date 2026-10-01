"""F05 clause probe (factory-only; copied into an arm worktree as tests/agent/test_zz_chs_clause_probe.py).

For one hook name (sidecar JSON next to this file: {"hook", "filter_boundary", "out"}; run_tests.sh
runs pytest under ``env -i`` so environment variables do not reach it) it drives real local compactions through AIAgent + SessionDB +
ContextCompressor (only the summary LLM call, and the SessionDB write in the failure scenarios, are
replaced) and records, per scenario, the order of summary / durable commit / hook events and each
contract clause, into the JSONL file named by "out". It asserts nothing about the arm: every
scenario "passes"; the JSON is the measurement.
"""

import json
import os
from unittest.mock import patch

import pytest

from hermes_cli import plugins as plugins_mod
from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest

_CFG = json.loads(open(os.path.splitext(__file__)[0] + ".json", encoding="utf-8").read())
HOOK = _CFG.get("hook", "on_compression_complete")
BOUNDARY_FILTER = bool(_CFG.get("filter_boundary"))
OUT = _CFG.get("out", "")
SUMMARY = "COMPACTION-OBSERVER-SENTINEL summary of the dropped turns"
APPROX_TOKENS = 75_000
ORIGINAL = "original-session"


@pytest.fixture
def plugin_ctx(monkeypatch):
    manager = PluginManager()
    manager._discovered = True
    monkeypatch.setattr(plugins_mod, "_plugin_manager", manager)
    monkeypatch.setattr(plugins_mod, "_plugin_managers_by_home", {})
    return PluginContext(PluginManifest(name="chs-probe", source="user"), manager)


def _agent(tmp_path, *, in_place):
    from hermes_state import SessionDB
    from run_agent import AIAgent

    tmp_path.mkdir(parents=True, exist_ok=True)
    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session(ORIGINAL, source="cli")
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
        agent = AIAgent(
            api_key="test-key", base_url="https://openrouter.ai/api/v1", model="test/model",
            quiet_mode=True, session_db=db, session_id=ORIGINAL, skip_context_files=True, skip_memory=True,
        )
    agent.compression_in_place = in_place
    agent._compression_feasibility_checked = True
    agent.context_compressor.tail_token_budget = 10
    return agent, db


def _history():
    msgs = [{"role": "system", "content": "system prompt"}]
    for i in range(10):
        msgs.append({"role": "user", "content": f"user message {i} " + "detail " * 40})
        msgs.append({"role": "assistant", "content": f"assistant reply {i} " + "detail " * 40})
    return msgs


def _durable(db, sid):
    try:
        return any(SUMMARY in str(m.get("content") or "") for m in db.get_messages(sid or ""))
    except Exception:
        return False


def _shape(messages):
    return json.dumps([(m.get("role"), m.get("content")) for m in messages or []], default=str)


def _run(tmp_path, *, in_place, deferred=False, summary=SUMMARY, fail_commit=None, finalize=None,
         subscribe=None):
    from agent.conversation_compression import finalize_context_engine_compression_notification

    agent, db = _agent(tmp_path, in_place=in_place)
    order, fired = [], []

    def fake_summary(*_a, **_k):
        order.append("summary")
        return summary

    def wrap(name):
        original = getattr(db, name)

        def _w(*a, **k):
            order.append(f"{name}:start")
            if fail_commit == name:
                order.append(f"{name}:raised")
                raise RuntimeError("synthetic SessionDB failure")
            out = original(*a, **k)
            order.append(f"{name}:end")
            return out
        return _w

    if subscribe is not None:
        def boom(**_kwargs):
            raise RuntimeError("observer exploded")

        def record(**kwargs):
            if BOUNDARY_FILTER and kwargs.get("boundary_reason") != "compression":
                return None
            order.append("hook")
            fired.append({
                "keys": sorted(k for k in kwargs if k not in ("conversation_history", "messages", "state")),
                "payload_session_id_is_live": kwargs.get("session_id") == agent.session_id,
                "durable_by_payload_sid": _durable(db, kwargs.get("session_id")),
                "durable_by_live_sid": _durable(db, agent.session_id),
                "session_id": kwargs.get("session_id"), "old_session_id": kwargs.get("old_session_id"),
                "in_place": kwargs.get("in_place"), "tokens_before": kwargs.get("tokens_before"),
                "tokens_after": kwargs.get("tokens_after"),
            })
            return {"action": "block", "message": "observers cannot veto"}

        subscribe.register_hook(HOOK, boom)
        subscribe.register_hook(HOOK, record)

    raised = None
    with patch.object(agent.context_compressor, "_generate_summary", side_effect=fake_summary), \
            patch.object(db, "archive_and_compact", side_effect=wrap("archive_and_compact")), \
            patch.object(db, "publish_compression_child", side_effect=wrap("publish_compression_child")):
        try:
            compressed, prompt = agent._compress_context(
                _history(), "system prompt", approx_tokens=APPROX_TOKENS, force=deferred,
                defer_context_engine_notification=deferred,
            )
        except Exception as exc:  # noqa: BLE001 - measured, not asserted
            raised, compressed, prompt = repr(exc), None, None
    fires_before_finalize = len(fired)
    if finalize is not None:
        order.append(f"finalize:{finalize}")
        finalize_context_engine_compression_notification(agent, committed=finalize)
        if finalize is False:
            finalize_context_engine_compression_notification(agent, committed=True)
    return {
        "order": order, "fired": fired, "fires": len(fired), "fires_before_finalize": fires_before_finalize,
        "raised": raised, "shape": _shape(compressed), "prompt": prompt,
        "committed": _durable(db, agent.session_id), "live_sid_changed": agent.session_id != ORIGINAL,
    }


SCENARIOS = {
    "rotated": dict(in_place=False),
    "in_place": dict(in_place=True),
    "manual_deferred": dict(in_place=True, deferred=True, finalize=True),
    "summary_failed": dict(in_place=True, summary=None),
    "commit_failed_in_place": dict(in_place=True, fail_commit="archive_and_compact"),
    "commit_failed_rotated": dict(in_place=False, fail_commit="publish_compression_child"),
    "manual_discarded": dict(in_place=True, deferred=True, finalize=False),
}
EXPECT_FIRE = {"rotated", "in_place", "manual_deferred"}


@pytest.mark.parametrize("scenario", list(SCENARIOS))
def test_probe(tmp_path, plugin_ctx, scenario):
    spec = SCENARIOS[scenario]
    base = _run(tmp_path / "base", **spec)
    obs = _run(tmp_path / "obs", subscribe=plugin_ctx, **spec)
    row = {
        "hook": HOOK, "scenario": scenario, "expect_fire": scenario in EXPECT_FIRE,
        "fires": obs["fires"], "fires_before_finalize": obs["fires_before_finalize"], "order": obs["order"],
        "baseline_committed": base["committed"], "observed_committed": obs["committed"],
        "output_identical": obs["shape"] == base["shape"] and obs["prompt"] == base["prompt"],
        "raised": obs["raised"], "events": obs["fired"],
    }
    if OUT:
        with open(OUT, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
