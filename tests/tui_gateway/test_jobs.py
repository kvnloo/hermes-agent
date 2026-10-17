"""Jobs sheet RPC ownership, bounded output, and control contracts (#529)."""

import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def jobs_runtime(tmp_path, monkeypatch):
    from tui_gateway import server
    from tools import delegate_tool_registry, process_registry as processes
    from tools.process_registry import ProcessSession

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    transport = SimpleNamespace(write=lambda frame: True)
    owner = {"session_key": "owned-key", "transport": transport, "profile_home": tmp_path}
    monkeypatch.setattr(server, "_sessions", {"owned": owner})
    owned = ProcessSession("proc_owned", "build", session_key="owned-key", started_at=123,
                           output_buffer="one\ntwo\nthree\n")
    foreign = ProcessSession("proc_foreign", "private build", session_key="foreign-key")
    unknown = ProcessSession("proc_unscoped", "unscoped", session_key="")
    procs = {p.id: p for p in (owned, foreign, unknown)}
    registry = SimpleNamespace(
        list_sessions=lambda **kwargs: [{"session_id": p.id} for p in procs.values()],
        get=procs.get, kill_process=Mock(return_value={"status": "killed"}))
    monkeypatch.setattr(processes, "process_registry", registry)
    transcript = tmp_path / "child.jsonl"
    transcript.write_text("first\nsecond\nthird\n")
    child = SimpleNamespace(_live_transcript_path=transcript)
    records = {
        "child": {"subagent_id": "child", "owner_session_id": "owned", "owner_session_record": owner,
                  "owner_transport": transport, "agent": child, "goal": "Read files", "status": "running"},
        "foreign-child": {"subagent_id": "foreign-child", "owner_session_id": "foreign",
                          "owner_session_record": {}, "owner_transport": transport, "goal": "Private goal"},
    }
    monkeypatch.setattr(delegate_tool_registry, "_active_subagents", records)
    monkeypatch.setattr(delegate_tool_registry, "_active_subagents_lock", threading.Lock())

    def call(method, *, via=transport, **params):
        token = server.bind_transport(via)
        try:
            return server.handle_request({"id": 1, "method": method,
                                          "params": {"session_id": "owned", **params}})
        finally:
            server.reset_transport(token)

    return call, registry, owner, procs, child


def test_list_only_callers_processes_and_subagents(jobs_runtime):
    call, _, owner, _, _ = jobs_runtime
    result = call("jobs.list")["result"]
    assert [(j["id"], j["kind"], j["owner_session_id"]) for j in result["jobs"]] == [
        ("proc_owned", "process", "owned"), ("child", "subagent", "owned")]
    assert result["jobs"][0]["started"] == 123
    owner["session_key"] = ""
    assert [j["id"] for j in call("jobs.list")["result"]["jobs"]] == ["child"]


@pytest.mark.parametrize("job_id", ["proc_foreign", "foreign-child", "proc_", "missing"])
def test_foreign_and_nonexact_ids_cannot_be_read_or_cancelled(jobs_runtime, job_id):
    call, registry, _, _, _ = jobs_runtime
    assert "error" in call("jobs.cancel", job_id=job_id)
    assert "error" in call("jobs.tail", job_id=job_id)
    registry.kill_process.assert_not_called()


def test_transport_authority_required_for_every_rpc(jobs_runtime):
    call, registry, _, _, _ = jobs_runtime
    foreign_transport = SimpleNamespace(write=lambda frame: True)
    for method in ("jobs.list", "jobs.tail", "jobs.cancel"):
        params = {} if method == "jobs.list" else {"job_id": "proc_owned"}
        assert "error" in call(method, via=foreign_transport, **params)
    registry.kill_process.assert_not_called()


@pytest.mark.parametrize("job_id, expected", [("proc_owned", "two\nthree"), ("child", "second\nthird")])
def test_tail_returns_last_n_lines_without_consuming_output(jobs_runtime, job_id, expected):
    call, _, _, _, _ = jobs_runtime
    assert call("jobs.tail", job_id=job_id, lines=2)["result"] == {
        "job_id": job_id, "text": expected, "available": True, "truncated": True}
    assert "error" in call("jobs.tail", job_id=job_id, lines=501)


def test_cancel_uses_exact_owned_id_and_preserves_completion_notifications(jobs_runtime):
    call, registry, _, procs, _ = jobs_runtime
    assert call("jobs.cancel", job_id="proc_owned")["result"]["accepted"]
    registry.kill_process.assert_called_once_with("proc_owned", source="jobs.cancel", consume_output=False)
    procs["proc_owned"].exited = True
    assert not call("jobs.cancel", job_id="proc_owned")["result"]["accepted"]
    assert registry.kill_process.call_count == 1


def test_cancel_reports_survivors_instead_of_claiming_success(jobs_runtime):
    call, registry, _, _, _ = jobs_runtime
    registry.kill_process.return_value = {"status": "error", "error": "Job still running"}
    assert call("jobs.cancel", job_id="proc_owned")["error"]["message"] == "Job still running"


def test_lifecycle_event_is_routed_only_to_the_owning_session(jobs_runtime, monkeypatch):
    from tui_gateway import server

    _, registry, _, procs, _ = jobs_runtime
    emit = Mock()
    monkeypatch.setattr(server, "_emit", emit)
    monkeypatch.setattr(server, "_desktop_ui_wired", True)
    server._wire_desktop_sinks()
    registry.on_change(procs["proc_owned"])
    registry.on_change(procs["proc_foreign"])
    registry.on_change(procs["proc_unscoped"])
    emit.assert_called_once_with("jobs.changed", "owned", {"job_id": "proc_owned"})


def test_jobs_dispatch_preserves_transport_authority_in_the_worker(jobs_runtime):
    import queue
    from tui_gateway import server

    _, _, owner, _, _ = jobs_runtime
    responses = queue.Queue()
    transport = SimpleNamespace(write=lambda frame: responses.put(frame))
    owner["transport"] = transport
    result = server.dispatch({"id": "worker", "method": "jobs.list", "params": {"session_id": "owned"}}, transport=transport)
    assert result is None
    assert [j["id"] for j in responses.get(timeout=10)["result"]["jobs"]] == ["proc_owned", "child"]


def test_subagent_cancel_reuses_live_object_authority(jobs_runtime, monkeypatch):
    import agent.interrupt_compat

    call, _, _, _, child = jobs_runtime
    interrupt = Mock(return_value=True)
    monkeypatch.setattr(agent.interrupt_compat, "request_hard_interrupt", interrupt)
    assert call("jobs.cancel", job_id="child")["result"]["accepted"]
    assert interrupt.call_args.args[0] is child
