"""Eval companions follow the real lifecycle + durable metadata without rewriting stdout."""
import copy
import json

from tui_gateway import server
from tui_gateway.eval_display import eval_metadata


def companion():
    return {"version": 1, "cells": [{"id": "cell", "code": "print(1)", "status": "done", "output": "1\n",
                                     "views": [{"id": "view", "kind": "json", "start": 0, "printed": "1\n"}]}]}


def test_real_gateway_prepares_persists_and_emits_same_companion(monkeypatch):
    raw = json.dumps({"status": "success", "output": "1\n", "eval_display": companion(), "eval_revision": 2})
    emitted = []
    monkeypatch.setattr(server, "_emit_tool_lifecycle", lambda *args: emitted.append(args[-1]))
    monkeypatch.setattr(server, "_tool_progress_enabled", lambda sid: True)
    monkeypatch.setattr(server, "_session_verbose", lambda sid: False)
    server._sessions["eval"] = {}
    try:
        metadata = server._prepare_tool_result_metadata("eval", "call", "execute_code", {}, raw)
        frozen = copy.deepcopy(metadata)
        server._on_tool_complete("eval", "call", "execute_code", {}, raw)
        assert emitted[0]["eval_display"] == metadata["tool_result_metadata"]["eval_display"]
        assert emitted[0]["eval_revision"] == 2
        assert emitted[0]["result"]["output"] == "1\n"
        assert metadata == frozen
        assert json.loads(raw)["output"] == "1\n"
    finally:
        server._sessions.pop("eval", None)


def test_optional_invalid_and_large_companions_fail_open_to_literal_output():
    assert eval_metadata('{"output":"no metadata"}') == {}
    assert eval_metadata(json.dumps({"eval_display": {"version": 99, "cells": []}})) == {}
    huge = companion()
    huge["cells"][0]["code"] = "x" * 100_000
    result = eval_metadata({"eval_display": huge})
    assert len(json.dumps(result)) < 40_000


def test_real_progress_dispatch_is_typed_and_does_not_depend_on_verbose(monkeypatch):
    emitted = []
    monkeypatch.setattr(server, "_emit", lambda *args: emitted.append(args))
    update = {"tool_id": "call", "revision": 1, "cell": companion()["cells"][0]}
    server._on_tool_progress("sid", "eval.update", "execute_code", eval_update=update)
    assert emitted[0][0:2] == ("eval.update", "sid")
    assert emitted[0][2]["cell"]["id"] == "cell"
    server._on_tool_progress("sid", "eval.update", "execute_code", eval_update={"tool_id": "bad"})
    assert len(emitted) == 1
