"""N11's existing synthetic integration checks, reused on the current Hermes HEAD.

No provider or live session is contacted. The six original checks remain unchanged.
"""
import json
import shutil

import pytest

from tests.plugins.test_handoff_capsule_acceptance import capsule as capsule


@pytest.mark.parametrize("limit", [0, 1, 30, 200])
def test_clip_includes_notice_in_budget(capsule, limit):
    body = capsule._clip("x" * 1000, limit, "/long/" + "p" * 300)
    assert len(body) <= limit


def test_spill_failure_preserves_original_conversation(capsule, monkeypatch):
    from agent.context_compressor import ContextCompressor
    monkeypatch.setattr(ContextCompressor, "_generate_summary", lambda *a, **k: "## Goal\nSynthetic work")
    def fail_spill(*args):
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(capsule, "_spill", fail_spill)
    engine = capsule.build()
    messages = [
        {"role": role, "content": f"synthetic turn {i} " + "x" * 1000}
        for i in range(20) for role in ("user", "assistant")
    ]
    original = [dict(message) for message in messages]
    returned = engine.compress(messages, current_tokens=100_000, force=True)
    assert returned == original
    assert engine._last_compress_aborted is True
    assert not (capsule._hermes_home() / "handoffs").exists()


def test_real_discovery_and_config_opt_out(capsule, tmp_path):
    from hermes_cli.config import load_config_readonly, set_config_value
    from agent.agent_init import _select_context_engine
    from plugins.context_engine import load_context_engine
    target = tmp_path / "plugins" / "handoff_capsule" / "__init__.py"
    target.parent.mkdir(parents=True)
    shutil.copyfile(capsule.__file__, target)
    set_config_value("context.engine", "handoff_capsule")
    engine = load_context_engine("handoff_capsule")
    assert engine is not None and engine.name == "handoff_capsule"
    selected = _select_context_engine(load_config_readonly())
    assert selected is not None and selected.name == "handoff_capsule"
    assert selected is not engine
    set_config_value("context.engine", "compressor")
    assert load_config_readonly()["context"]["engine"] == "compressor"
    assert _select_context_engine(load_config_readonly()) is None
    set_config_value("context.engine", "handoff_capsule")
    assert _select_context_engine(load_config_readonly()).name == "handoff_capsule"


def test_forced_handoff_keeps_chat_metadata_with_rotation_enabled(capsule, tmp_path, monkeypatch):
    """Offline integration, not model recall or a live gateway delivery proof."""
    from agent.context_compressor import ContextCompressor
    from hermes_cli.config import set_config_value
    from hermes_state import SessionDB
    from run_agent import AIAgent

    set_config_value("compression.in_place", "false")
    monkeypatch.setattr(ContextCompressor, "_generate_summary", lambda *a, **k:
                        "## Goal\nRemember SYNTHETIC-783.\n## Open Asks\nProve continuity.\n")
    with SessionDB(db_path=tmp_path / "synthetic-state.db") as db:
        parent = "synthetic-parent"
        db.create_session(parent, source="telegram", user_id="synthetic-user",
                          session_key="telegram:synthetic-user:synthetic-chat",
                          chat_id="synthetic-chat", chat_type="private")
        agent = AIAgent(api_key="synthetic-test-key", base_url="https://example.invalid/v1",
                        model="test/model", platform="telegram", quiet_mode=True,
                        session_db=db, session_id=parent, skip_context_files=True,
                        skip_memory=True)
        engine = capsule.build()
        engine.bind_session_state(db, parent)
        agent.context_compressor = engine
        assert agent.compression_in_place is False
        messages = [
            {"role": role, "content": f"synthetic turn {i} " + "x" * 1000}
            for i in range(20) for role in ("user", "assistant")
        ]
        returned, _ = agent._compress_context(messages, "synthetic system", approx_tokens=100_000, force=True)
        child = agent.session_id
        assert child != parent
        row = db.get_session(child)
        assert row["parent_session_id"] == parent
        assert row["chat_id"] == "synthetic-chat"
        assert row["session_key"] == "telegram:synthetic-user:synthetic-chat"
        assert any("SYNTHETIC-783" in str(message.get("content")) for message in returned)
        persisted = db.get_messages_as_conversation(child)
        assert any("SYNTHETIC-783" in str(message.get("content")) for message in persisted)
        print(json.dumps({"parent": parent, "child": child, "chat_id": row["chat_id"],
                          "capsule_persisted": True, "summary_source": "synthetic stub"}))
