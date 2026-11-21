"""Gateway hygiene compactions survive disposal of the compressor (#148931).

A real summary row is the durable commit receipt. An in-memory increment without
a committed row must not become a false lifetime count after a restart.
"""

from types import SimpleNamespace

from agent.context_compressor import ContextCompressor
from gateway.session_usage import tui_usage, usage_stats
from hermes_state import SessionDB


def _restored(db: SessionDB, sid: str) -> ContextCompressor:
    compressor = ContextCompressor(
        model="test/model", quiet_mode=True, config_context_length=8192,
    )
    compressor.bind_session_state(db, sid)
    return compressor


def test_committed_hygiene_count_survives_helper_eviction_and_restart(tmp_path):
    db = SessionDB(db_path=tmp_path / "state.db")
    sid = "gateway-hygiene"
    db.create_session(sid, source="cli")
    for i in range(16):
        db.append_message(sid, "assistant", f"handoff {i}", _compressed_summary=True)
    db.append_message(sid, "assistant", "ordinary reply")

    # The detached hygiene helper has committed 16 compactions.
    helper = _restored(db, sid)
    assert helper.compression_count == 16

    # Eviction discards its in-memory count. A speculative (uncommitted) bump
    # must not be counted by a fresh agent.
    helper.compression_count += 1
    successor = _restored(db, sid)
    assert successor.compression_count == 16
    stats = usage_stats(SimpleNamespace(context_compressor=successor))
    assert stats["compression_count"] == 16
    assert tui_usage(stats)["compressions"] == 16

    # A later committed summary (including a deferred hygiene completion)
    # is visible even after a new process reconstructs its compressor.
    db.append_message(sid, "assistant", "handoff 17", _compressed_summary=True)
    recovered = _restored(db, sid)
    assert recovered.compression_count == 17

    # /new resets accounting; a different session does not inherit 17.
    db.create_session("new-conversation", source="cli")
    recovered.on_session_reset()
    recovered.bind_session_state(db, "new-conversation")
    assert recovered.compression_count == 0
    db.close()
