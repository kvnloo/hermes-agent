"""Regression for #154793: network outages must not become Kanban quota walls."""

import socket
import time

import httpx
import openai

from agent import turn_recovery
from agent.error_classifier import classify_api_error
from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc
from hermes_cli import kanban_db_dispatch as kbd
from hermes_cli.turn_exit import turn_exit_code


def _http_error(status, message):
    response = httpx.Response(status, request=httpx.Request("POST", "https://proxy.example.test/v1"))
    if status == 429:
        return openai.RateLimitError(message, response=response, body=None)
    return openai.InternalServerError(message, response=response, body=None)


def test_network_and_quota_worker_exits_remain_distinct():
    # One test proves all transports and their non-network controls: RED fails
    # on an observable rc=75 rather than on importing a newly added symbol.
    cases = [
        (socket.gaierror(-4, "DNS server misbehaving"), "timeout", 76),
        (httpx.ConnectError("All connection attempts failed"), "timeout", 76),
        (_http_error(500, "Connection error."), "server_error", 76),
        (_http_error(500, "Internal server error"), "server_error", 75),
        (_http_error(429, "Rate limit exceeded"), "rate_limit", 75),
    ]
    for error, reason, exit_code in cases:
        classified = classify_api_error(error)
        assert classified.reason.value == reason
        result = {
            "failed": True, "failure_reason": classified.reason.value,
            "failure_network": bool(classified.error_context.get("transport")),
        }
        code = turn_exit_code(result, kanban_worker=True)
        assert code == exit_code  # 76 on an outage, 75 on an actual provider wall.
        assert kbd._exit_code_kind(code)[0] == ("network" if code == 76 else "rate_limited")
        assert turn_recovery._network_transport_failure(classified) == (code == 76)


def test_network_exit_requeues_without_spending_card_budget(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(kb, "_pid_alive", lambda _pid: False)
    kb.init_db()

    with kbc.connect() as conn:
        tid = kb.create_task(conn, title="outage requeue", assignee="default")
        host = kb._claimer_id().split(":", 1)[0]
        assert kb.claim_task(conn, tid, claimer=f"{host}:worker") is not None
        pid = 70093
        # A historical claim uses the real/default crash grace period.
        conn.execute("UPDATE tasks SET worker_pid=?, started_at=? WHERE id=?",
                     (pid, int(time.time()) - 3600, tid))
        conn.commit()
        kbd._record_worker_exit(pid, kb.KANBAN_NETWORK_ERROR_EXIT_CODE << 8)

        assert tid not in kbd.detect_crashed_workers(conn)
        assert tid in kbd.detect_crashed_workers._last_network
        task = kb.get_task(conn, tid)
        assert task.status == "ready"
        assert task.consecutive_failures == 0
        assert "quota" not in (task.last_failure_error or "")
        outcome = conn.execute("SELECT outcome FROM task_runs WHERE task_id=?",
                               (tid,)).fetchone()["outcome"]
        assert outcome == "network"
        assert kbd.check_respawn_guard(conn, tid) == "infrastructure_cooldown"
