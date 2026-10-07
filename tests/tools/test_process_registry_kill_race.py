"""Regression tests for the live ``completion_queue`` payload when the reader
thread wins the kill race.

Companion to ``test_process_registry.py::TestKillProcess``: the durable-receipt
re-stamp (commit 0724a6a0) was followed by a live-queue re-stamp so the CLI/TUI
drain surfaces (``drain_notifications`` → ``format_process_notification``) read
``killed``/``kill_all`` instead of the reader's stale ``exited`` snapshot.
"""

import os
import queue
import signal
import subprocess
import threading
import time

import pytest
from unittest.mock import patch

from tools.process_registry import ProcessRegistry
from tests.tools.test_process_registry import _make_session


@pytest.fixture()
def registry():
    """Create a fresh ProcessRegistry."""
    return ProcessRegistry()


@pytest.fixture(autouse=True)
def _reset_systemd_scope_cache():
    """Reset the cached ``systemd-run --user --scope`` availability flag
    before each test so a probe run on a real systemd host (where
    ``INVOCATION_ID`` is set) doesn't leak into tests that mock
    ``subprocess.Popen``. Mirrors ``test_process_registry.py``."""
    import tools.process_registry as _pr

    original = _pr._SYSTEMD_SCOPE_AVAILABLE
    _pr._SYSTEMD_SCOPE_AVAILABLE = False
    yield
    _pr._SYSTEMD_SCOPE_AVAILABLE = original


class TestKillProcessLiveQueue:
    def test_kill_live_queue_rewritten_when_reader_finalises_first(self, registry):
        """The companion surface to ``test_kill_receipt_rewritten_when_reader_finalises_first``:
        the durable receipt fix must extend to the LIVE ``completion_queue`` payload.

        ``kill_all`` defaults to ``consume_output=False`` precisely so the
        autonomous completion notification is *delivered*. The reader thread can
        finalise a ``notify_on_complete=True`` session during ``kill_process``'s
        SIGKILL grace window: its ``_move_to_finished`` enqueues a stale
        ``completion_reason="exited"`` event *before* the kill path stamps the
        session ``killed``. The kill path's own ``_move_to_finished`` then
        returns False (the reader already moved it), so it can't enqueue a
        corrected one itself. The durable receipt was re-saved by 0724a6a0; the
        live queue payload is corrected here so the CLI/TUI drain surfaces see
        the kill attribution rather than the reader's plain-exit snapshot.
        """
        s = _make_session(sid="proc_kill_race_live", command="sleep 999")
        s.pid = 424244
        s.detached = True
        s.notify_on_complete = True  # the kill_all default shape (background, notify=True)
        registry._running[s.id] = s

        def reader_wins_during_signal(pid, start=None):
            # The reader observes the SIGTERMed exit (real-code -15 for SIGTERM)
            # while the signal path is still inside its grace window.
            registry._finish_exited(s, -15)

        saved = []

        def record_save(session):
            saved.append(
                (session.completion_reason, session.termination_source, session.exit_code)
            )

        try:
            host_guard = patch.object(ProcessRegistry, "_host_pid_is_ours", return_value=True)
            term_patch = patch.object(
                ProcessRegistry, "_terminate_host_pid", side_effect=reader_wins_during_signal,
            )
            saver = patch(
                "tools.process_registry.save_completed_result", side_effect=record_save
            )
            with host_guard, term_patch, saver:
                result = registry.kill_process(
                    s.id, source="kill_all", consume_output=False,
                )

            # Caller's result, live session and durable receipt all carry the
            # kill attribution — pre-existing guarantees, no regression.
            assert result["status"] == "killed"
            assert result["completion_reason"] == "killed"
            assert result["termination_source"] == "kill_all"
            assert s.completion_reason == "killed"
            assert s.termination_source == "kill_all"
            assert saved[0] == ("exited", "", -15)        # reader's first save
            assert saved[-1] == ("killed", "kill_all", -15)  # kill's re-stamp

            # Regression assertion: the LIVE completion_queue payload also carries
            # the kill signature, not the reader's stale plain-exit view.
            queued = list(registry.completion_queue.queue)
            assert len(queued) == 1
            assert queued[0]["completion_reason"] == "killed"
            assert queued[0]["termination_source"] == "kill_all"
            assert queued[0]["exit_code"] == -15
        finally:
            registry._running.pop(s.id, None)
            registry._finished.pop(s.id, None)

    def test_kill_live_queue_text_uses_kill_attribution_when_reader_finalises_first(self, registry):
        """End-to-end on the CLI/TUI drain path: ``drain_notifications`` returns
        ``format_process_notification`` text that says ``terminated by kill_all``,
        not ``exited``, when the reader raced the kill. This is the user-visible
        message the bug report asserts is misdelivered."""
        s = _make_session(sid="proc_kill_race_text", command="sleep 999")
        s.pid = 424245
        s.detached = True
        s.notify_on_complete = True
        s.session_key = "t1"  # routing: drain_notifications uses _owns_event → session_key match
        registry._running[s.id] = s

        def reader_wins_during_signal(pid, start=None):
            registry._finish_exited(s, -15)

        try:
            host_guard = patch.object(ProcessRegistry, "_host_pid_is_ours", return_value=True)
            term_patch = patch.object(
                ProcessRegistry, "_terminate_host_pid", side_effect=reader_wins_during_signal,
            )
            saver = patch("tools.process_registry.save_completed_result", lambda session: None)
            with host_guard, term_patch, saver:
                registry.kill_process(s.id, source="kill_all", consume_output=False)

            # The originating session's next drain delivers exactly the queued
            # event. CLI's _drain_process_notifications feeds owns_event that
            # resolves to the current session_id; emulate with session_key.
            drained = registry.drain_notifications(session_key="t1")
            assert len(drained) == 1, f"expected one notification, got {drained}"
            _evt, text = drained[0]
            assert "terminated by kill_all" in text
            assert "exited" not in text, (
                "stale 'exited' labeling leaked through to the agent-visible text: " + text
            )
        finally:
            registry._running.pop(s.id, None)
            registry._finished.pop(s.id, None)

    def test_replace_stale_completion_notification_preserves_other_events(self, registry):
        """``_replace_stale_completion_notification`` must SWAP only this
        session's stale ``exited`` event and preserve every other event in the
        queue verbatim: foreign sessions' completions, watch_match events, and
        async-delegation completions. The keep-list is what keeps it from
        dropping other sessions' autonomous notifications."""
        target = _make_session(sid="proc_swap_target", command="sleep 999")
        target.notify_on_complete = True
        target.completion_reason = "killed"
        target.termination_source = "kill_all"
        target.exit_code = -15
        target.exited = True

        foreign_completion = _make_session(sid="proc_swap_foreign", command="echo hi")
        foreign_completion.notify_on_complete = True
        foreign_completion.completion_reason = "exited"
        foreign_completion.exit_code = 0
        foreign_completion.exited = True
        registry.completion_queue.put({
            "type": "completion", "session_id": foreign_completion.id,
            "session_key": "foreign", "task_id": "t2",
            "owner_task_id": "t2", "command": "echo hi",
            "completion_reason": "exited", "termination_source": "", "exit_code": 0,
            "output": "hi", "started_at": 0,
        })
        # A foreign watch_match event — must pass through untouched.
        registry.completion_queue.put({
            "type": "watch_match", "session_id": "proc_other_watch",
            "pattern": "READY", "output": "READY=1",
        })
        # The stale 'exited' event the reader enqueued for the target session.
        registry.completion_queue.put({
            "type": "completion", "session_id": target.id,
            "session_key": "t1", "task_id": "t1",
            "owner_task_id": "t1", "command": "sleep 999",
            "completion_reason": "exited", "termination_source": "", "exit_code": -15,
            "output": "partial", "started_at": 0,
        })
        # A foreign async-delegation result — must pass through untouched.
        registry.completion_queue.put({
            "type": "async_delegation", "session_id": "sa-other",
            "summary": "did stuff",
        })

        registry._replace_stale_completion_notification(target)

        queued = list(registry.completion_queue.queue)
        # 4 input events; one stale 'exited' dropped, one corrected 'killed' appended.
        assert len(queued) == 4

        # The corrected target event is the LAST element (drop + append order).
        assert queued[-1]["type"] == "completion"
        assert queued[-1]["session_id"] == target.id
        assert queued[-1]["completion_reason"] == "killed"
        assert queued[-1]["termination_source"] == "kill_all"
        assert queued[-1]["exit_code"] == -15

        # Foreign completion preserved verbatim.
        foreign_kept = [e for e in queued if e.get("session_id") == foreign_completion.id]
        assert len(foreign_kept) == 1
        assert foreign_kept[0]["completion_reason"] == "exited"
        # Watch_match preserved verbatim.
        watch_kept = [e for e in queued if e.get("type") == "watch_match"]
        assert len(watch_kept) == 1
        assert watch_kept[0]["pattern"] == "READY"
        # async_delegation preserved verbatim.
        deleg_kept = [e for e in queued if e.get("type") == "async_delegation"]
        assert len(deleg_kept) == 1
        assert deleg_kept[0]["session_id"] == "sa-other"
        # No stale 'exited' event for the target remains.
        stale = [e for e in queued
                 if e.get("session_id") == target.id and e.get("completion_reason") == "exited"]
        assert stale == []

    def test_kill_live_queue_when_kill_wins_race_uses_kill_stamp(self, registry):
        """Complement to the reader-wins test: if the kill path's stamping runs
        *before* the reader finalises, the reader's ``_move_to_finished`` is
        the FIRST mover (``was_running=True``) and enqueues the corrected
        ``killed`` payload directly. The fix must not double-enqueue or leave a
        duplicate stale event in this case."""
        s = _make_session(sid="proc_kill_wins", command="sleep 999")
        s.pid = 424246
        s.detached = True
        s.notify_on_complete = True
        registry._running[s.id] = s

        # The reader finalises AFTER the signal path returns — i.e. the kill
        # stamps the session before the reader observes the exit. The kill path's
        # _move_to_finished is the first mover (was_running=True) and enqueues the
        # 'killed' payload itself.
        def kill_wins_then_reader_finalises(pid, start=None):
            # Stamp the session BEFORE the reader finalises: this is the post-fix
            # invariant — by the time _move_to_finished enqueues, completion_reason
            # is already 'killed' on the session.
            s.completion_reason = "killed"
            s.termination_source = "kill_all"
            s.exit_code = -15
            s.exited = True

        try:
            host_guard = patch.object(ProcessRegistry, "_host_pid_is_ours", return_value=True)
            term_patch = patch.object(
                ProcessRegistry, "_terminate_host_pid",
                side_effect=kill_wins_then_reader_finalises,
            )
            saver = patch("tools.process_registry.save_completed_result", lambda session: None)
            with host_guard, term_patch, saver:
                registry.kill_process(
                    s.id, source="kill_all", consume_output=False,
                )

            queued = list(registry.completion_queue.queue)
            # Exactly one notification; it carries the kill stamp.
            assert len(queued) == 1
            assert queued[0]["completion_reason"] == "killed"
            assert queued[0]["termination_source"] == "kill_all"
            assert queued[0]["exit_code"] == -15
        finally:
            registry._running.pop(s.id, None)
            registry._finished.pop(s.id, None)

    def test_kill_live_queue_rewritten_redacts_secret(self, registry, monkeypatch):
        """The swapped event must respect the same redaction policy as the
        normal enqueue path: secrets in the session's ``output_buffer`` and
        ``command`` are masked on the corrected ``killed`` payload too.
        Regression for the fix routing the enqueue through
        ``_enqueue_completion_notification`` (which calls
        ``_redact_process_result``) rather than a hand-rolled dict."""
        import agent.redact as _r
        monkeypatch.setattr(_r, "_REDACT_ENABLED", True)

        s = _make_session(sid="proc_redact_race", command="env")
        s.pid = 424247
        s.detached = True
        s.notify_on_complete = True
        s.output_buffer = "OPENAI_API_KEY=sk-proj-secret123\nHOME=/home/u"
        registry._running[s.id] = s

        def reader_wins_during_signal(pid, start=None):
            registry._finish_exited(s, -15)

        try:
            host_guard = patch.object(ProcessRegistry, "_host_pid_is_ours", return_value=True)
            term_patch = patch.object(
                ProcessRegistry, "_terminate_host_pid", side_effect=reader_wins_during_signal,
            )
            saver = patch("tools.process_registry.save_completed_result", lambda session: None)
            with host_guard, term_patch, saver:
                registry.kill_process(s.id, source="kill_all", consume_output=False)

            queued = list(registry.completion_queue.queue)
            assert len(queued) == 1
            assert queued[0]["completion_reason"] == "killed"
            assert "sk-proj-secret123" not in queued[0]["output"], (
                "secret leaked into the corrected (post-swap) notification payload"
            )
        finally:
            registry._running.pop(s.id, None)
            registry._finished.pop(s.id, None)

    @pytest.mark.platforms("posix")
    def test_kill_live_queue_rewritten_real_popen(self, registry):
        """Real reader thread + real ``kill_all``: the queued completion_event
        must read ``completion_reason="killed"``, ``termination_source="kill_all"``.

        Exercises the actual SIGTERM-grace-window race (process tree
        termination → reader observes EOF → reader finalises) — the bug report's
        real-Popen repro fired the stale ``exited`` payload in 25 of 30 trials
        against current code; after the fix it must always read ``killed``.
        """
        proc = subprocess.Popen(
            ["sh", "-c", "sleep 30"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
        s = _make_session(sid="proc_real_kill_race", command="sleep 30")
        s.process = proc
        s.pid = proc.pid
        s.notify_on_complete = True
        s.task_id = "t1"
        s.session_key = "t1"
        registry._running[s.id] = s

        done = threading.Event()

        def _run():
            registry._reader_loop(s)
            done.set()

        reader = threading.Thread(target=_run, daemon=True)
        reader.start()
        try:
            registry.kill_all(task_id="t1", source="kill_all", consume_output=False)

            # Wait for the reader to finalise AND for the kill path to swap the
            # stale event (if the reader won the race). 5s is ample: SIGTERM
            # graced-processes die in <<1s on POSIX.
            deadline = time.monotonic() + 8.0
            queued = []
            while time.monotonic() < deadline:
                try:
                    e = registry.completion_queue.get_nowait()
                except queue.Empty:
                    if done.is_set() and registry.completion_queue.empty():
                        break
                    time.sleep(0.02)
                    continue
                if e.get("type") == "completion" and e.get("session_id") == s.id:
                    queued.append(e)
                else:
                    # Keep any other event (none expected here) for hygiene.
                    registry.completion_queue.put(e)
            assert done.wait(timeout=2.0), "reader thread never finalised"
            assert queued, "reader never enqueued a completion in time"
            assert queued[0]["completion_reason"] == "killed", (
                f"expected 'killed', got {queued[0]['completion_reason']!r} "
                f"(termination_source={queued[0].get('termination_source')!r})"
            )
            assert queued[0]["termination_source"] == "kill_all"
            assert queued[0]["exit_code"] == -15
        finally:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
