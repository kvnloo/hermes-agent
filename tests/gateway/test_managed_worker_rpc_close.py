"""A managed worker closes its owner connection when ``execute`` ends, after the store, on success and on
a start failure; a failing close never replaces the turn's own outcome."""
import threading
from types import SimpleNamespace

import pytest

from tests.gateway.test_managed_turn_contract import assignment


def _execute(tmp_path, monkeypatch, events, *, start_error=None, close_error=None,
             agent_class=None, on_result=None):
    from agent import managed_worker as worker

    class RPC:
        def __init__(self, home): pass
        def __call__(self, method, **params): return {'owner_epoch': 1}
        def close(self):
            events.append('rpc.close')
            if close_error is not None:
                raise close_error

    class Agent:
        def __init__(self, **kwargs):
            if start_error is not None:
                raise start_error
            self.session_prompt_tokens = self.session_completion_tokens = 0
        def run_conversation(self, text, **kwargs):
            return {'final_response': 'ok', 'completed': True}

    class Store:
        def __init__(self, *args): pass
        def get_messages_as_conversation(self, sid): return []
        def flush_token_counts(self): pass
        def finish(self): events.append('store.finish')
        def close(self): events.append('store.close')

    class Controls:
        def __init__(self, *args):
            self.stopped, self.finish = threading.Event(), threading.Event()
            self.finish.set()
        def approval(self, data): pass
        def clarify(self, questions): pass

    frame, _ = assignment(tmp_path, monkeypatch)
    monkeypatch.setattr(worker, 'bind_worker_policy', lambda frame: None)
    monkeypatch.setattr(worker, 'discover_profile_mcp', lambda policy: None)
    monkeypatch.setattr(worker, 'retire_agent', lambda agent: None)
    monkeypatch.setattr(worker, 'WorkerControls', Controls)
    monkeypatch.setattr('agent.runtime_session_store.WorkerRPC', RPC)
    monkeypatch.setattr('agent.runtime_session_store.RuntimeSessionStore', Store)
    monkeypatch.setattr('tools.process_registry.process_registry.recover_from_checkpoint', lambda: None)
    monkeypatch.setattr('run_agent.AIAgent', agent_class or Agent)
    monkeypatch.setattr('agent.title_generator.wait_for_title_upgrades', lambda: None)
    def send(kind, **payload):
        events.append(kind)
        if kind == 'result' and on_result is not None:
            on_result()

    worker.execute(frame, SimpleNamespace(send=send))


def test_execute_closes_the_rpc_after_the_store_on_success(tmp_path, monkeypatch):
    events = []
    _execute(tmp_path, monkeypatch, events)
    assert events[-3:] == ['finished', 'store.close', 'rpc.close']


def test_execute_closes_the_rpc_after_the_store_on_a_start_failure(tmp_path, monkeypatch):
    events = []
    with pytest.raises(RuntimeError, match='construct_failed'):
        _execute(tmp_path, monkeypatch, events, start_error=RuntimeError('construct_failed'))
    assert events == ['store.close', 'rpc.close']


@pytest.mark.parametrize('start_error', [None, RuntimeError('construct_failed')])
def test_a_failing_rpc_close_never_masks_the_turns_outcome(tmp_path, monkeypatch, start_error):
    events = []
    if start_error is None:
        _execute(tmp_path, monkeypatch, events, close_error=OSError('close'))
        assert events[-3:] == ['finished', 'store.close', 'rpc.close']
    else:
        with pytest.raises(RuntimeError, match='construct_failed'):
            _execute(tmp_path, monkeypatch, events, start_error=start_error, close_error=OSError('close'))
        assert events[-1] == 'rpc.close'



def test_finished_managed_turn_releases_kernel_wal_writer_before_result(tmp_path, monkeypatch):
    """Regression for #149837: a parked managed worker must not starve other writers."""
    import json
    import sqlite3
    from unittest.mock import patch

    from tools.code_execution_tool import execute_code
    from tools.code_kernel import shutdown_all_kernels

    # The test owns this local Python cell; approval policy is not the behavior under test.
    # Keep the real persistent kernel and WAL writer so lifecycle cleanup is exercised.
    monkeypatch.setattr("tools.approval.check_execute_code_guard",
                        lambda *args, **kwargs: {"approved": True})

    monkeypatch.setenv("TERMINAL_ENV", "local")
    board = tmp_path / "board.db"
    with sqlite3.connect(board) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE events (value INTEGER)")

    class Agent:
        def __init__(self, **kwargs):
            self.session_prompt_tokens = self.session_completion_tokens = 0

        def run_conversation(self, text, **kwargs):
            code = chr(10).join((
                "import sqlite3",
                f"conn = sqlite3.connect({str(board)!r})",
                "conn.execute('BEGIN IMMEDIATE')",
                "conn.execute('INSERT INTO events VALUES (1)')",
            ))
            with patch("tools.code_execution_tool._load_config",
                       return_value={"mode": "strict", "timeout": 20}):
                result = json.loads(execute_code(code, task_id="managed-kernel-wal"))
            assert result["status"] == "success", result
            return {"final_response": "ok", "completed": True}

    def independent_writer():
        # Invoked at the owner's first result frame, before its finish control.
        # On base the idle kernel still owns BEGIN IMMEDIATE and this raises
        # sqlite3.OperationalError: database is locked.
        with sqlite3.connect(board, timeout=0.1) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO events VALUES (2)")

    try:
        events = []
        _execute(tmp_path, monkeypatch, events, agent_class=Agent,
                 on_result=independent_writer)
        assert "result" in events
        with sqlite3.connect(board) as db:
            assert db.execute("SELECT value FROM events").fetchall() == [(2,)]
    finally:
        shutdown_all_kernels()
