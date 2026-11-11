"""N11 acceptance checks against an isolated copy of the deployed scratch engine.

No provider, account, gateway, or live profile is used. Supply the private plugin
as .n11-proof/handoff_capsule.py. These are not live same-chat/model-recall proof.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil

import pytest


@pytest.fixture
def capsule(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    source = Path(__file__).parents[2] / ".n11-proof/handoff_capsule.py"
    spec = importlib.util.spec_from_file_location("n11_capsule_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_hermes_home", lambda: tmp_path)
    monkeypatch.setattr(module, "_config", lambda: {})
    return module


def test_capsule_preserves_open_work_and_private_spill(capsule, tmp_path):
    full = "## Goal\nFinish N11.\n## Open Asks\nKeep ASK-783 open.\n## Next\nRun the acceptance proof.\n"
    body = capsule.build_capsule(full, "synthetic-session")
    assert "ASK-783" in body
    assert "Finish N11" in body
    spill = tmp_path / "handoffs/synthetic-session.md"
    assert spill.read_text().strip() == full.strip()
    assert spill.stat().st_mode & 0o777 == 0o600
    assert str(spill) in body


def test_capsule_obeys_even_its_own_character_budget(capsule):
    full = "\n\n".join(
        f"## {name}\n" + ("X" * 80 + "\n") * 400
        for name, _limit in capsule.CAPSULE_SECTIONS
    ) + "\n\n## Context Recovery\n" + ("Y" * 80 + "\n") * 100
    body = capsule.build_capsule(full, "synthetic-long-summary")
    framed = capsule.HANDOFF_PREFIX + "\n" + body
    measured = len(framed)
    limit = capsule.CAPSULE_TOKENS * capsule._CHARS_PER_TOKEN
    print(json.dumps({"framed_characters": measured, "character_budget": limit}))
    assert measured <= limit, "The clipping notice itself must fit inside the budget"


def test_host_adapts_legacy_engine_signature(capsule):
    from agent.conversation_compression import _supported_compression_kwargs
    engine = capsule.build()
    messages = [{"role": "user", "content": "tiny synthetic transcript"}]
    kwargs = _supported_compression_kwargs(
        engine.compress, current_tokens=10, focus_topic=None,
        force=True, memory_context="", bypass_cooldown=True,
    )
    assert engine.compress(messages, **kwargs) == messages


def test_opt_out_status_and_opt_in_dispatch(capsule, monkeypatch):
    selected = []
    monkeypatch.setattr(capsule, "_set_engine", selected.append)
    assert "compressor" in capsule.autohandoff_command("off")
    assert "handoff_capsule" in capsule.autohandoff_command("on")
    assert selected == ["compressor", "handoff_capsule"]
    assert "capsule cap 4000" in capsule.autohandoff_command("status")


def test_successful_summary_is_capped_and_spilled(capsule, monkeypatch, tmp_path):
    from agent.context_compressor import ContextCompressor
    full = "## Goal\nRemember SYNTHETIC-783.\n## Open Asks\nProve same-chat continuity.\n"
    monkeypatch.setattr(ContextCompressor, "_generate_summary", lambda *a, **k: full)
    engine = capsule.build()
    engine._session_id = "synthetic-summary"
    result = engine._generate_summary([])
    assert result.startswith(capsule.HANDOFF_PREFIX)
    assert "SYNTHETIC-783" in result
    assert (tmp_path / "handoffs/synthetic-summary.md").is_file()


def test_spill_failure_does_not_return_an_oversized_capsule(capsule, monkeypatch):
    from agent.context_compressor import ContextCompressor
    full = "## Goal\n" + "oversized synthetic summary " * 2000
    monkeypatch.setattr(ContextCompressor, "_generate_summary", lambda *a, **k: full)
    def fail_spill(*args):
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(capsule, "_spill", fail_spill)
    result = capsule.build()._generate_summary([])
    assert result is None, "A failed spill must not silently lose handoff details"


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


def test_real_discovery_and_config_opt_out(capsule, tmp_path, monkeypatch):
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
