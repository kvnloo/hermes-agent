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


# The with-todos case is covered by test_skill_todo_retention_parity.py::test_reload_instruction_travels_with_todo_snapshot.
def test_without_todos_notice_present(tmp_path):
    text = _run(tmp_path, [])
    assert _PRUNED_SKILL_RELOAD_NOTICE_HEADER in text
    assert "skill_view(name='demo-skill')" in text.split(_PRUNED_SKILL_RELOAD_NOTICE_HEADER, 1)[1]
    assert "task list above" not in text  # no todo list crossed this boundary; don't claim one did


def test_without_todos_notice_row_is_synthetic_after_db_roundtrip():
    from agent.context_compressor import ContextCompressor
    from agent.conversation_compression import _pruned_skill_reload_notice
    notice = _pruned_skill_reload_notice([{"role": "user", "content": _skill_pruned_marker("demo-skill")}], with_todos=False)
    # SessionDB drops message metadata, so classification must key on content alone.
    assert ContextCompressor._is_synthetic_compression_user_turn({"role": "user", "content": notice})
    # The memory-prefetch ask scan (turn_context) consults only the scaffolding classifier.
    from agent.conversation_compression_scaffolding import is_user_role_scaffolding
    assert is_user_role_scaffolding({"role": "user", "content": notice})


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


def test_without_todos_stale_notice_in_earlier_user_row_is_stripped(tmp_path):
    from agent.conversation_compression import _pruned_skill_reload_notice
    old = _pruned_skill_reload_notice([{"role": "user", "content": _skill_pruned_marker("demo-skill")}], with_todos=False)
    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session("P", source="cli")
    agent = _build_agent_with_db(db, "P")
    agent._todo_store._items = []
    summary = "[CONTEXT COMPACTION] summary\n\n## Pruned Skills\n" + _skill_pruned_marker("demo-skill")
    agent.context_compressor.compress.return_value = [
        {"role": "user", "content": summary}, {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "earlier ask\n\n" + old}, {"role": "assistant", "content": "done"},
        {"role": "user", "content": "tail"},
    ]
    out, _ = agent._compress_context(_msgs(), "sys", approx_tokens=120_000)
    db.close()
    text = "\n".join(str(m.get("content")) for m in out)
    assert text.count(_PRUNED_SKILL_RELOAD_NOTICE_HEADER) == 1
    assert "earlier ask" in text


def _one_boundary(tmp_path, rows, todos):
    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session("P", source="cli")
    agent = _build_agent_with_db(db, "P")
    agent._todo_store._items = todos
    agent.context_compressor.compress.return_value = rows
    out, _ = agent._compress_context(_msgs(), "sys", approx_tokens=120_000)
    db.close()
    return "\n".join(str(m.get("content")) for m in out)


def _lone_notice():
    from agent.conversation_compression import _pruned_skill_reload_notice
    return _pruned_skill_reload_notice([{"role": "user", "content": _skill_pruned_marker("demo-skill")}], with_todos=False)


def test_user_text_merged_after_a_lone_notice_survives_the_next_strip(tmp_path):
    # A consecutive-user merge can land the next real turn on a notice-only row (#137652 shape).
    summary = "[CONTEXT COMPACTION] summary\n\n## Pruned Skills\n" + _skill_pruned_marker("demo-skill")
    text = _one_boundary(tmp_path, [
        {"role": "user", "content": summary}, {"role": "assistant", "content": "ok"},
        {"role": "user", "content": _lone_notice() + "\n\nlater ask"}, {"role": "assistant", "content": "done"},
        {"role": "user", "content": "tail"},
    ], [])
    assert "later ask" in text
    assert text.count(_PRUNED_SKILL_RELOAD_NOTICE_HEADER) == 1


def test_lone_notice_then_todos_single_notice(tmp_path):
    summary = "[CONTEXT COMPACTION] summary\n\n## Pruned Skills\n" + _skill_pruned_marker("demo-skill")
    text = _one_boundary(tmp_path, [
        {"role": "user", "content": summary}, {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "earlier ask\n\n" + _lone_notice()}, {"role": "assistant", "content": "done"},
        {"role": "user", "content": "tail"},
    ], [{"id": "1", "content": "do x", "status": "pending"}])
    assert text.count(_PRUNED_SKILL_RELOAD_NOTICE_HEADER) == 1
    assert "earlier ask" in text
