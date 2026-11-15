"""An empty ``web_search`` query is refused before any backend is called."""
import json

import pytest

import tools.web_tools
from tools.registry import registry

assert tools.web_tools.web_search_tool  # importing registers web_search


@pytest.mark.parametrize("args", [{"query": ""}, {"query": "   "}])
def test_empty_query_is_refused_without_calling_a_provider(args, monkeypatch):
    def _no_provider(*_a, **_k):
        raise AssertionError("an empty query must not reach a search provider")

    monkeypatch.setattr("tools.web_tools._memoized_search", _no_provider)
    debug_calls = []
    monkeypatch.setattr(tools.web_tools._debug, "log_call", lambda name, data: debug_calls.append((name, dict(data))))
    monkeypatch.setattr(tools.web_tools._debug, "save", lambda: None)
    result = json.loads(registry.dispatch("web_search", args))
    assert result["success"] is False
    assert "non-empty 'query'" in result["error"]
    assert len(debug_calls) == 1
    assert debug_calls[0][0] == "web_search_tool"
    assert debug_calls[0][1]["error"] == result["error"]
