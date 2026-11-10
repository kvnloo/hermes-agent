"""Pruned skills must get a reload notice even when the todo list is empty (gap left by #86852)."""
from pathlib import Path
from agent.context_compressor import _skill_pruned_marker
from agent.conversation_compression import _PRUNED_SKILL_RELOAD_NOTICE_HEADER
from hermes_state import SessionDB
from tests.agent.test_skill_todo_retention_parity import _build_agent_with_db, _msgs


def _run(tmp_path: Path, todos):
    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session("P", source="cli")
    agent = _build_agent_with_db(db, "P")
    summary = "[CONTEXT COMPACTION] summary\n\n## Pruned Skills\n" + _skill_pruned_marker("demo-skill")
    agent.context_compressor.compress.return_value = [
        {"role": "user", "content": summary},
        {"role": "assistant", "content": "acknowledged"},
        {"role": "user", "content": "tail"},
    ]
    agent._todo_store._items = todos
    compressed, _ = agent._compress_context(_msgs(), "sys", approx_tokens=120_000)
    db.close()
    return "\n".join(str(m.get("content")) for m in compressed)


def test_with_todos_notice_present(tmp_path):
    assert _PRUNED_SKILL_RELOAD_NOTICE_HEADER in _run(tmp_path, [{"id": "a", "content": "do x", "status": "pending"}])


def test_without_todos_notice_present(tmp_path):
    assert _PRUNED_SKILL_RELOAD_NOTICE_HEADER in _run(tmp_path, [])


def test_without_todos_notice_row_is_synthetic_after_db_roundtrip():
    from agent.context_compressor import ContextCompressor
    from agent.conversation_compression import _pruned_skill_reload_notice
    notice = _pruned_skill_reload_notice([{"role": "user", "content": _skill_pruned_marker("demo-skill")}])
    # SessionDB drops message metadata, so classification must key on content alone.
    assert ContextCompressor._is_synthetic_compression_user_turn({"role": "user", "content": notice})


def test_without_todos_repeated_boundaries_single_notice(tmp_path):
    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session("P", source="cli")
    agent = _build_agent_with_db(db, "P")
    agent._todo_store._items = []
    out = None
    for _ in range(2):
        summary = "[CONTEXT COMPACTION] summary\n\n## Pruned Skills\n" + _skill_pruned_marker("demo-skill")
        carried = [dict(m) for m in out[2:]] if out else []  # previous boundary's tail, incl. its notice
        agent.context_compressor.compress.return_value = [
            {"role": "user", "content": summary}, {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "real ask"}, *carried][:3] + carried[1:]
        out, _ = agent._compress_context(_msgs(), "sys", approx_tokens=120_000)
    text = "\n".join(str(m.get("content")) for m in out)
    db.close()
    assert text.count(_PRUNED_SKILL_RELOAD_NOTICE_HEADER) == 1
    assert "real ask" in text
