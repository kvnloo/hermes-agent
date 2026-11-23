"""The Feishu comment tools tell the model when an argument was ignored."""

import json
from importlib import import_module
from unittest.mock import Mock

from tools.registry import registry


def test_list_comments_warns_when_whole_document_filter_is_misspelled(monkeypatch):
    import_module("model_tools")  # Discover the actual registered tool.

    name = "feishu_drive_list_comments"
    entry = registry.get_entry(name)
    assert entry is not None
    call = Mock(return_value=(0, "", {"items": []}))
    monkeypatch.setitem(entry.handler.__globals__, "get_client", lambda: object())
    monkeypatch.setitem(entry.handler.__globals__, "lark_call", call)

    result = json.loads(registry.dispatch(name, {"file_token": "example", "is_whol": True}))

    call.assert_called_once()
    assert ("is_whole", "true") not in call.call_args.kwargs["queries"]
    assert result["items"] == []
    assert "is_whol: not a parameter" in result.get("_warning", ""), result

    result = json.loads(registry.dispatch(name, {"file_token": "example", "is_whole": True}))
    assert ("is_whole", "true") in call.call_args.kwargs["queries"]
    assert "_warning" not in result
