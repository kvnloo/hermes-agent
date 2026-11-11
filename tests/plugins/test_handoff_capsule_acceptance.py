"""N11 acceptance checks against an isolated copy of the deployed scratch engine.

No provider, account, gateway, or live profile is used. Supply the private plugin
as .n11-proof/handoff_capsule.py. These are not live same-chat/model-recall proof.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

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
    assert result is None or len(result) <= capsule.CAPSULE_TOKENS * capsule._CHARS_PER_TOKEN
