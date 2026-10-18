"""Durable side threads, exact ownership and cancellation (#578), without an LLM call."""
import contextlib
import copy
from types import SimpleNamespace

import pytest

from hermes_state import SessionDB
from tui_gateway import server
from tui_gateway.btw_workers import workers


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    db = SessionDB(db_path=tmp_path / "state.db")
    transport = SimpleNamespace(write=lambda frame: True)
    history = [{"role": "user", "content": "Main"}, {"role": "assistant", "content": "Untouched"}]
    owner = {"session_key": "conversation", "transport": transport, "history": copy.deepcopy(history),
             "profile_home": str(tmp_path), "cwd": str(tmp_path), "agent": None}
    monkeypatch.setattr(server, "_sessions", {"live": owner})
    monkeypatch.setattr(server, "_session_db", lambda session: contextlib.nullcontext(db))
    jobs, events = [], []
    monkeypatch.setattr(server, "_start_session_work", lambda run, **kw: jobs.append(run) or True)
    monkeypatch.setattr(server, "_emit", lambda *args: events.append(args))

    def rpc(method, via=transport, **params):
        token = server.bind_transport(via)
        try:
            return server.handle_request({"id": 1, "method": method, "params": {"session_id": "live", **params}})
        finally:
            server.reset_transport(token)

    yield rpc, db, jobs, events, owner, history
    workers.clear()
    db.close()


def test_completed_threads_resume_followups_without_mutating_main(runtime, monkeypatch):
    rpc, db, jobs, events, owner, original = runtime
    seen = []

    def answer(question, snapshot, **kwargs):
        seen.append((question, snapshot))
        kwargs["stream_callback"]("Actual ")
        kwargs["stream_callback"]("answer")
        return "Actual answer"
    monkeypatch.setattr("agent.side_question.answer_side_question", answer)
    admitted = rpc("btw.submit", text="First question")["result"]
    thread_id = admitted["thread"]["id"]
    assert admitted["thread"]["turns"][0]["state"] == "running"
    jobs.pop(0)()
    first = rpc("btw.list")["result"]["threads"][0]
    assert first["id"] == thread_id
    assert first["turns"][0]["answer"] == "Actual answer"
    assert [event[2]["thread"]["turns"][0]["answer"] for event in events] == ["Actual ", "Actual answer", "Actual answer"]
    assert first["turns"][0]["state"] == "answered"
    # The transport can remint its live id while durable conversation ownership remains.
    owner["history"] = copy.deepcopy(original)
    followup = rpc("btw.submit", thread_id=thread_id, text="Follow-up")["result"]
    assert followup["turn_id"] != admitted["turn_id"]
    jobs.pop(0)()
    resumed = rpc("btw.list")["result"]["threads"][0]
    assert len(resumed["turns"]) == 2
    assert "First question" in seen[-1][0] and "Actual answer" in seen[-1][0]
    assert owner["history"] == original == seen[-1][1]
    assert db.get_messages("conversation") == []


def test_exact_session_and_transport_ownership_for_list_submit_cancel(runtime):
    rpc, _, _, _, owner, _ = runtime
    result = rpc("btw.submit", text="Owned")["result"]
    params = {"thread_id": result["thread"]["id"], "turn_id": result["turn_id"]}
    foreign = SimpleNamespace(write=lambda frame: True)
    for method, args in (("btw.list", {}), ("btw.submit", {"text": "bad"}), ("btw.cancel", params)):
        assert rpc(method, via=foreign, **args)["error"]["code"] == 4001
    owner["session_key"] = "different-conversation"
    assert rpc("btw.list")["result"]["threads"] == []
    assert "error" in rpc("btw.submit", text="foreign followup", thread_id=params["thread_id"])
    assert "error" in rpc("btw.cancel", **params)


def test_cancel_readback_fences_late_streams_and_completion(runtime, monkeypatch):
    rpc, _, jobs, _, _, _ = runtime
    result = rpc("btw.submit", text="Stop")["result"]
    ids = {"thread_id": result["thread"]["id"], "turn_id": result["turn_id"]}
    cancelled = rpc("btw.cancel", **ids)["result"]["thread"]
    assert cancelled["turns"][0]["state"] == "cancelled"

    def answer(*args, **kwargs):
        assert kwargs["cancelled"]()
        kwargs["stream_callback"]("Late content must not win")
        return "Late final must not win"
    monkeypatch.setattr("agent.side_question.answer_side_question", answer)
    jobs.pop(0)()
    turn = rpc("btw.list")["result"]["threads"][0]["turns"][0]
    assert turn["state"] == "cancelled"
    assert turn["answer"] == ""
    assert "error" in rpc("btw.cancel", thread_id=ids["thread_id"], turn_id="wrong-turn")


def test_errors_retiring_and_interrupted_backend_are_explicit_and_can_be_followed_up(runtime, monkeypatch):
    rpc, _, jobs, _, _, _ = runtime
    failed = rpc("btw.submit", text="Fails")["result"]
    monkeypatch.setattr("agent.side_question.answer_side_question", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("offline")))
    jobs.pop(0)()
    turn = rpc("btw.list")["result"]["threads"][0]["turns"][0]
    assert (turn["state"], turn["error"]) == ("error", "offline")
    followup = rpc("btw.submit", text="Try again", thread_id=failed["thread"]["id"])["result"]
    assert "error" in rpc("btw.submit", text="Duplicate", thread_id=failed["thread"]["id"])
    workers.pop(followup["turn_id"])
    interrupted = rpc("btw.list")["result"]["threads"][0]["turns"][-1]
    assert interrupted["state"] == "cancelled" and "stopped" in interrupted["error"]
    monkeypatch.setattr(server, "_start_session_work", lambda *a, **kw: None)
    retiring = rpc("btw.submit", text="Retiring")["result"]["thread"]["turns"][0]
    assert retiring["state"] == "error" and "retiring" in retiring["error"]


def test_stream_delivery_follows_resumed_conversation_without_crossing_profile(runtime, monkeypatch):
    rpc, _, jobs, events, owner, _ = runtime
    rpc("btw.submit", text="Resume while running")
    resumed = {**owner, "history": list(owner["history"])}
    foreign = {**owner, "profile_home": owner["profile_home"] + "-other"}
    monkeypatch.setattr(server, "_sessions", {"resumed": resumed, "foreign": foreign})
    monkeypatch.setattr("agent.side_question.answer_side_question", lambda *a, **kw: kw["stream_callback"]("Delta") or "Done")
    jobs.pop(0)()
    assert events and all(event[1] == "resumed" for event in events)
    assert rpc("btw.list", session_id="resumed")["result"]["threads"][0]["turns"][0]["answer"] == "Done"


def test_two_profile_databases_and_arbitrary_session_ids_do_not_share_history(runtime, tmp_path, monkeypatch):
    rpc, first, _, _, owner, _ = runtime
    rpc("btw.submit", text="First profile")
    second = SessionDB(db_path=tmp_path / "second.db")
    try:
        monkeypatch.setattr(server, "_session_db", lambda session: contextlib.nullcontext(second))
        assert rpc("btw.list")["result"]["threads"] == []
        rpc("btw.submit", text="Second profile")
        assert len(rpc("btw.list")["result"]["threads"]) == 1
        monkeypatch.setattr(server, "_session_db", lambda session: contextlib.nullcontext(first))
        owner["session_key"] = 'conversation":"suffix'
        assert rpc("btw.list")["result"]["threads"] == []
        assert len(first.list_meta_prefix('btw:"conversation":')) == 1
    finally:
        second.close()
