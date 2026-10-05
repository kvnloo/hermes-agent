"""Backend RPC/worker completion boundary requested in #129391 (not renderer coverage)."""

import copy
import threading
from types import SimpleNamespace

import pytest

from agent import side_question
from tui_gateway import server


@pytest.mark.parametrize("outcome", ["empty", "error"])
def test_registered_btw_completes_with_correlated_terminal_event(tmp_path, monkeypatch, outcome):
    home = tmp_path / "profile"
    home.mkdir()
    (home / "config.yaml").write_text("terminal:\n  backend: local\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(server, "_hermes_home", home)
    sid, question = "btw-consumer-session", "What is the current task?"
    history = [{"role": "user", "content": "ordinary foreground task"}]
    original_history = copy.deepcopy(history)
    parent = SimpleNamespace(_session_messages=history)
    session = {"agent": parent, "history": history, "profile_home": str(home), "cwd": str(tmp_path)}
    monkeypatch.setitem(server._sessions, sid, session)
    entered, release, completed = threading.Event(), threading.Event(), threading.Event()
    threads, frames = [], []

    def answer(text, snapshot, *, parent_agent, main_runtime):
        threads.append(threading.current_thread())
        entered.set()
        assert release.wait(5), "test did not release answer boundary"
        assert text == question
        assert snapshot == original_history and snapshot is not history
        assert parent_agent is parent
        if outcome == "error":
            raise RuntimeError("synthetic answer failure")
        return ""

    def capture(frame):
        frames.append(frame)
        completed.set()
        return True

    monkeypatch.setattr(side_question, "answer_side_question", answer)
    monkeypatch.setattr(server, "write_json", capture)
    try:
        response = server._methods["prompt.btw"](73, {"session_id": sid, "text": question})
        assert response["id"] == 73 and "error" not in response
        task_id = response["result"]["task_id"]
        assert entered.wait(5), "real side worker did not enter answer boundary"
        assert threads[0] is not threading.current_thread()
        assert not completed.is_set()
        release.set()
        assert completed.wait(5), "accepted side question had no terminal event"
    finally:
        release.set()
        for worker in threads:
            worker.join(5)
            assert not worker.is_alive(), "side worker leaked after completion"

    assert len(frames) == 1
    assert frames[0]["params"]["session_id"] == sid
    assert frames[0]["params"]["type"] == "btw.complete"
    payload = frames[0]["params"]["payload"]
    assert payload == {
        "task_id": task_id, "question": question,
        "text": "" if outcome == "empty" else "error: synthetic answer failure",
    }
    assert history == original_history
    assert parent._session_messages is history
