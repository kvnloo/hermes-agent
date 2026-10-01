"""Behaviour contract for the plugin observer at the local compaction boundary (#64231, #118382).

A plugin subscribed to ``on_compression_complete`` hears about a local compaction exactly once,
after the compacted transcript is durable in state.db, with the old and new session ids. By then
the attempt has released its commit fence and the session's compression lease, so a slow plugin
cannot make an interrupt wait behind it (the #118120 hazard) or hold up the next compaction. It
hears nothing about an attempt that did not commit (a failed summary under
``compression.abort_on_summary_failure: true``, the commit site's would-grow refusal, a SessionDB
write failure, a manual compress its host discards), and a subscriber can neither break nor change
the compaction. Real ``AIAgent``, ``SessionDB``, ``ContextCompressor`` and
``CompressionCommitFence``; only the summary LLM call (and, for the commit failure, the SessionDB
write) is replaced, and agent init's model-metadata lookups are stubbed so the test makes no
network request.
"""

import json
import os
from unittest.mock import patch

import pytest

from agent.conversation_compression import (
    CompressionCommitFence, finalize_context_engine_compression_notification,
)
from hermes_cli import plugins as plugins_mod
from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest

HOOK = "on_compression_complete"
SUMMARY = "COMPACTION-OBSERVER-SENTINEL summary of the dropped turns"
APPROX_TOKENS = 75_000


@pytest.fixture
def plugin_ctx(monkeypatch):
    manager = PluginManager()
    manager._discovered = True
    monkeypatch.setattr(plugins_mod, "_plugin_manager", manager)
    monkeypatch.setattr(plugins_mod, "_plugin_managers_by_home", {})
    return PluginContext(PluginManifest(name="compaction-observer", source="user"), manager)


def _agent(tmp_path, *, in_place):
    from hermes_state import SessionDB
    from run_agent import AIAgent

    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session("original-session", source="cli")
    # Pinned window and a stubbed OpenRouter metadata prewarm thread: init makes no network request.
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}), \
            patch("agent.context_compressor.get_model_context_length", return_value=256_000), \
            patch("agent.agent_init.fetch_model_metadata", return_value={}):
        agent = AIAgent(
            api_key="test-key", base_url="https://openrouter.ai/api/v1", model="test/model",
            quiet_mode=True, session_db=db, session_id="original-session",
            skip_context_files=True, skip_memory=True,
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


def _compress(agent, *, deferred=False, summary=SUMMARY, fence=None):
    with patch.object(agent.context_compressor, "_generate_summary", return_value=summary):
        return agent._compress_context(
            _history(), "system prompt", approx_tokens=APPROX_TOKENS, force=deferred,
            defer_context_engine_notification=deferred, commit_fence=fence,
        )


def _durable_summary(db, session_id):
    return any(SUMMARY in str(m.get("content") or "") for m in db.get_messages(session_id or ""))


def _subscribe(plugin_ctx, db, fired, fence=None):
    def boom(**_kwargs):
        raise RuntimeError("observer exploded")

    def record(**kwargs):
        fired.append({
            **kwargs,
            "durable": _durable_summary(db, kwargs.get("session_id")),
            # What an interrupt waits on (hard_interrupt blocks while a commit is in flight) and what
            # the session's next compaction waits on (the durable lease, taken on the old id).
            "fence_in_flight": fence is not None and fence.commit_in_flight,
            "lease_holder": db.get_compression_lock_holder(kwargs.get("old_session_id") or ""),
        })
        return {"action": "block", "message": "observers cannot veto"}

    plugin_ctx.register_hook(HOOK, boom)
    plugin_ctx.register_hook(HOOK, record)


def _shape(messages):
    return json.dumps([(m.get("role"), m.get("content")) for m in messages], default=str)


@pytest.mark.parametrize("mode", ["rotated", "in_place", "manual_deferred"])
def test_observer_fires_once_after_the_durable_commit(tmp_path, plugin_ctx, mode):
    in_place = mode != "rotated"
    deferred = mode == "manual_deferred"
    baseline, baseline_prompt = _compress(
        _agent(tmp_path / "baseline", in_place=in_place)[0], deferred=deferred, fence=CompressionCommitFence(),
    )

    agent, db = _agent(tmp_path / "observed", in_place=in_place)
    fence = CompressionCommitFence()
    fired = []
    _subscribe(plugin_ctx, db, fired, fence)
    compressed, prompt = _compress(agent, deferred=deferred, fence=fence)
    if deferred:
        assert fired == [], "a deferred manual compaction must wait for the host's own commit"
        finalize_context_engine_compression_notification(agent, committed=True)

    assert len(fired) == 1, f"{HOOK} fired {len(fired)} times"
    event = fired[0]
    assert event["durable"], "observer ran before the compacted transcript was durable"
    assert not event["fence_in_flight"], "observer ran inside the commit fence, so an interrupt waits behind it"
    assert event["lease_holder"] is None, "observer ran while the session's compression lease was held"
    assert event["session_id"] == agent.session_id
    assert event["old_session_id"] == "original-session"
    assert event["in_place"] is in_place and (agent.session_id == "original-session") is in_place
    assert isinstance(event["tokens_after"], int) and 0 < event["tokens_after"] < event["tokens_before"]
    # Fail-open and observer-only: a raising subscriber and a directive-shaped return change nothing.
    assert _shape(compressed) == _shape(baseline)
    assert prompt == baseline_prompt


@pytest.mark.parametrize(
    "failure", ["summary_aborted", "would_grow_refused", "commit_failed", "manual_discarded"],
)
def test_observer_is_silent_when_nothing_commits(tmp_path, plugin_ctx, failure):
    agent, db = _agent(tmp_path, in_place=True)
    fired = []
    _subscribe(plugin_ctx, db, fired)
    rows_before = db.get_messages(agent.session_id)
    compressor = agent.context_compressor

    if failure == "summary_aborted":
        compressor.abort_on_summary_failure = True  # compression.abort_on_summary_failure: true
        _compress(agent, summary=None)
        assert compressor._last_compress_aborted, "scenario precondition: the failed summary aborted"
    elif failure == "would_grow_refused":
        # Default config: the fallback summary replaces the failed one, but on this small window it
        # would grow the transcript, so the commit site refuses it.
        _compress(agent, summary=None)
        assert compressor._last_compress_refused_would_grow, "scenario precondition: would-grow refusal"
    elif failure == "commit_failed":
        with patch.object(db, "archive_and_compact", side_effect=RuntimeError("disk full")):
            _compress(agent)
    else:
        _compress(agent, deferred=True)
        finalize_context_engine_compression_notification(agent, committed=False)
        finalize_context_engine_compression_notification(agent, committed=True)
        assert _durable_summary(db, agent.session_id), "the manual attempt itself must have compacted"

    if failure != "manual_discarded":
        assert agent.session_id == "original-session" and db.get_messages(agent.session_id) == rows_before, (
            "scenario precondition: state.db unchanged, nothing committed"
        )
    assert fired == [], f"{HOOK} fired for a compaction its host never committed: {fired!r}"
