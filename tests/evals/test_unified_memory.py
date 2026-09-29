"""Hermes lane contracts for kvnloo/z0evals#56 (no live model in CI)."""
import importlib
import json
from pathlib import Path
from types import SimpleNamespace


def test_real_resolver_adapter_hook_cache_and_failure_contracts(tmp_path, request, monkeypatch):
    root = request.config.getoption("--z0int-root")
    if not root:
        pytest.skip("Pass --z0int-root to exercise the pinned real z0int dependency")
    from evals.unified_memory.bridge import PacketBridge, load_adapter
    from agent.turn_context import _collect_pre_llm_call_context
    from hermes_cli.plugins import PluginContext, PluginManifest, PluginManager
    from hermes_cli import plugins
    manager = PluginManager()
    monkeypatch.setattr(plugins, "_plugin_manager", manager)
    monkeypatch.setattr(plugins, "_plugin_managers_by_home", {})
    path = tmp_path / "source.txt"
    path.write_text("current = alpha")
    bridge = PacketBridge(Path(root), tmp_path)
    bridge.question = {"id": "test-only", "prompt": "What is current?", "sources": [
        {"source_id": "public:unit", "path": str(path)}
    ]}
    adapter = load_adapter(Path(root), bridge)
    adapter.register(PluginContext(PluginManifest(name="z0-study", source="user"), manager))
    agent = SimpleNamespace(session_id="test-s", model="not-called", platform="test")

    def turn(trace, session="test-s"):
        agent.session_id = session
        return _collect_pre_llm_call_context(agent, effective_task_id="task", turn_id=trace,
            original_user_message="What is current?", messages=[], conversation_history=[])

    first = turn("t1")
    cold = dict(bridge.last)
    assert "alpha" in first and cold["cache_state"] == "miss"
    assert cold["packet"]["evidence"][0]["source_id"] == "public:unit"
    assert cold["packet"]["evidence"][0]["source_version"].startswith("sha256:")
    assert turn("t1") == ""
    assert bridge.last["replayed"] is True
    warm_text = turn("t2")
    assert warm_text == first and bridge.last["cache_state"] == "fresh"
    assert bridge.last["raw_source_reads"] < cold["raw_source_reads"]
    # The hidden verification oracle must not affect retrieval or cache identity.
    bridge.question["verification"] = {"answer": "not model-visible"}
    assert turn("t2b") == first and bridge.last["cache_state"] == "fresh"
    # Same-size replacement and preserved mtime must still invalidate content.
    import os
    timestamp = path.stat().st_mtime_ns
    path.write_text("current = bravo")
    os.utime(path, ns=(timestamp, timestamp))
    changed = turn("t3")
    assert "bravo" in changed and "alpha" not in changed
    assert bridge.last["cache_state"] == "miss"
    assert bridge.last["packet"]["evidence"][0]["source_version"] != cold["packet"]["evidence"][0]["source_version"]
    path.unlink()
    missing = turn("t4")
    assert "unresolved_gaps" in missing and bridge.last["packet"]["evidence"] == []
    assert bridge.last["packet"]["unresolved_gaps"]
    assert turn("t5") == missing and bridge.last["cache_state"] == "miss"
    path.write_text("current = alpha")
    assert "alpha" in turn("t6", "other-session")
    assert bridge.last["cache_state"] == "miss"
    # Unavailable integration must leave native Hermes usable, not inject an answer.
    monkeypatch.setattr(bridge, "resolve", lambda **kw: (_ for _ in ()).throw(OSError("offline")))
    bridge.cache.clear()
    assert turn("t7") == ""
    assert bridge.last["error"] == "OSError"

import pytest


def test_verification_requires_model_delivery_citations_and_oracle():
    from evals.unified_memory.study import verify_answer
    question = {"expected_evidence": ["public:unit"], "verification": {
        "answer": "alpha", "citations": ["public:unit"], "abstained": False}}
    packet = {"evidence": [{"source_id": "public:unit", "source_version": "sha256:" + "a" * 64,
                           "excerpt": "current = alpha", "locator": "source.txt", "trust_class": "code"}],
              "unresolved_gaps": []}
    answer = json.dumps(question["verification"])
    assert verify_answer(question, packet, answer, injected=True, model_completed=True)["answer_supported"]
    for kwargs in ({"injected": False, "model_completed": True}, {"injected": True, "model_completed": False}):
        assert not verify_answer(question, packet, answer, **kwargs)["verified"]
    assert not verify_answer(question, packet, answer.replace("alpha", "bravo"),
                             injected=True, model_completed=True)["verified"]
    assert not verify_answer(question, packet, answer.replace("public:unit", "forged"),
                             injected=True, model_completed=True)["verified"]
    assert not verify_answer(question, {**packet, "unresolved_gaps": ["missing source"]}, answer,
                             injected=True, model_completed=True)["verified"]
    abstention = {"answer": "", "citations": [], "abstained": True}
    question = {"expected_evidence": [], "verification": abstention}
    result = verify_answer(question, {"evidence": [], "unresolved_gaps": ["removed source"]},
                           json.dumps(abstention), injected=True, model_completed=True)
    assert result == {"verified": True, "answer_supported": False, "abstained": True}


def test_public_smoke_revision_changes_source_not_question_identity(tmp_path):
    from evals.unified_memory.run import smoke_question, revise_smoke_question
    first = smoke_question(tmp_path)
    before = Path(first["sources"][0]["path"]).read_bytes()
    revised = revise_smoke_question(first)
    after = Path(revised["sources"][0]["path"]).read_bytes()
    assert before != after
    assert revised["id"] == first["id"]
    assert revised["prompt"] == first["prompt"]
    assert revised["sources"][0]["source_id"] == first["sources"][0]["source_id"]
    assert revised["verification"]["answer"] != first["verification"]["answer"]
    assert json.loads(after)["title"] == revised["verification"]["answer"]
    assert first["id"] not in importlib.import_module("evals.unified_memory.study").QUESTION_IDS


def test_cli_rejects_scaffold_before_resolving_credentials(tmp_path):
    import subprocess
    import sys
    scaffold = tmp_path / "families.json"
    scaffold.write_text('{"questions":[{"id":"exact-identifier"}]}')
    out = tmp_path / "proof"
    result = subprocess.run([sys.executable, "-m", "evals.unified_memory.run",
        "--questions", str(scaffold), "--out", str(out)], capture_output=True, text=True)
    assert result.returncode == 2
    blocker = json.loads((out / "blocker.json").read_text())
    assert blocker["model_called"] is False
    assert "frozen DSH" in blocker["reason"]
    assert not (out / "receipts.jsonl").exists()


def test_family_scaffold_is_not_a_frozen_dsh_cohort():
    study = importlib.import_module("evals.unified_memory.study")
    scaffold = {"schema": "z0eval.unified_memory_questions.v0", "questions": [
        {"id": name, "kind": "exact", "expected": "supported"}
        for name in study.QUESTION_IDS
    ]}
    with pytest.raises(ValueError, match="frozen DSH"):
        study.validate_frozen_bundle(scaffold)
    assert study.validate_frozen_bundle({
        "origin": {"harness": "dsh", "revision": "a" * 40, "locator": "local:fixture"},
        "questions": [
            {"id": name, "prompt": "Test question", "sources": [
                {"source_id": "public:test", "path": "test.txt", "sha256": "b" * 64}
            ], "expected_evidence": ["public:test"],
             "verification": {"answer": "supported", "citations": ["public:test"], "abstained": False}}
            for name in study.QUESTION_IDS
        ],
    })
