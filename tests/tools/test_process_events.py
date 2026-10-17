"""Process lifecycle observers work for silent, non-notifying jobs (#529)."""

import threading
from unittest.mock import Mock


def test_silent_start_and_exit_emit_once_without_consuming_notifications(monkeypatch):
    from tools.process_registry import ProcessRegistry, ProcessSession

    registry = ProcessRegistry()
    monkeypatch.setattr(registry, "_write_checkpoint", lambda: None)
    changes = []
    registry.on_change = lambda p: changes.append((p.id, p.exited))
    release = threading.Event()
    proc = ProcessSession("proc_quiet", "quiet build", session_key="owned", notify_on_complete=False)
    registry._track_started(proc, lambda _: release.wait(10), "jobs-fixture-reader")
    try:
        assert changes == [("proc_quiet", False)]
        registry._finish_exited(proc, 0)
        registry._finish_exited(proc, 0)
        assert changes == [("proc_quiet", False), ("proc_quiet", True)]
        assert registry.completion_queue.empty()
        assert proc.id not in registry._completion_consumed
    finally:
        release.set()
        proc._reader_thread.join(10)


def test_observer_failures_cannot_break_output_or_lifecycle(monkeypatch):
    from tools.process_registry import ProcessRegistry, ProcessSession

    registry = ProcessRegistry()
    proc = ProcessSession("proc_fixture", "fixture")
    registry.on_change = Mock(side_effect=RuntimeError("observer failed"))
    registry.on_output = Mock(side_effect=RuntimeError("renderer disconnected"))
    registry._emit_process_changed(proc)
    registry._ingest_output(proc, "real output")
    assert proc.output_buffer == "real output"
    registry.on_change.assert_called_once_with(proc)
    registry.on_output.assert_called_once_with(proc, "real output")
