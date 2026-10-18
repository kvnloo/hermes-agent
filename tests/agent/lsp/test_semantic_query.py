"""Semantic producers exercise real framed subprocess traffic, never fabricated server success (#577)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent.lsp.manager import LSPService
from agent.lsp.query import query_sync
from agent.lsp.servers import custom_servers
from tui_gateway.contracts.lsp import LspQueryResult


@pytest.fixture
def service(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    path = tmp_path / "a.py"
    path.write_text("class Outer: pass\n")
    services = []

    def create(script="semantic"):
        servers = custom_servers({"mock-semantic": {"extensions": [".py"],
            "command": [sys.executable, str(Path(__file__).with_name("_mock_lsp_server.py"))]}})
        svc = LSPService(enabled=True, wait_mode="document", wait_timeout=3, install_strategy="off", idle_timeout=0,
                         extra_servers=servers, trusted_workspaces=[str(tmp_path)],
                         env_overrides={"mock-semantic": {"MOCK_LSP_SCRIPT": script, "MOCK_LSP_QUERY_LOG": str(tmp_path / "queries.jsonl")}})
        services.append(svc)
        return svc, str(path)
    yield create
    for svc in services:
        svc.shutdown()


def query(service, operation, **kwargs):
    svc, path = service
    result = query_sync(svc, operation, path, **kwargs)
    LspQueryResult.model_validate(result)
    return result["lsp_result"]


def test_cross_file_references_keep_complete_ranges(service, tmp_path):
    result = query(service(), "references", line=2, col=3)
    assert result["kind"] == "references"
    assert [Path(row["path"]).name for row in result["locations"]] == ["a.py", "b.py"]
    assert result["locations"][0]["range"] == {"start": {"line": 2, "col": 3}, "end": {"line": 4, "col": 5}}
    assert result["server"] == "mock-semantic"
    assert result["position_encoding"] == "utf-16"
    sent = json.loads((tmp_path / "queries.jsonl").read_text().splitlines()[0])
    assert sent["method"] == "textDocument/references"
    assert sent["params"]["position"] == {"line": 1, "character": 2}
    assert sent["params"]["context"] == {"includeDeclaration": True}


def test_nested_symbols_have_stable_semantic_ids(service):
    svc = service()
    first = query(svc, "symbols")["symbols"]
    second = query(svc, "symbols")["symbols"]
    assert first == second
    assert first[0]["children"][0]["name"] == "child"
    assert first[0]["id"] != first[0]["children"][0]["id"]


def test_hover_keeps_markdown_and_range(service):
    result = query(service(), "hover")
    assert result["kind"] == "hover"
    assert result["contents"] == [{"format": "markdown", "text": "**actual mock-server protocol reply**", "language": None}]
    assert result["range"]["start"] == {"line": 2, "col": 3}


@pytest.mark.parametrize("operation", ["references", "symbols", "hover"])
def test_null_is_checked_empty_not_server_failure(service, operation):
    result = query(service("semantic_empty"), operation)
    assert result["kind"] == operation
    assert result[{"references": "locations", "symbols": "symbols", "hover": "contents"}[operation]] == []


@pytest.mark.parametrize("script,kind", [("clean", "unavailable"), ("semantic_error", "error"), ("semantic_bad", "error"), ("crash", "unavailable")])
def test_no_semantic_success_for_unsupported_failed_or_malformed_servers(service, script, kind):
    result = query(service(script), "references")
    assert result["kind"] == kind
    assert result["operation"] == "references"
    assert result["message"]
    assert "locations" not in result


def test_disabled_service_is_unavailable():
    assert query_sync(None, "symbols", "/project/a.py")["lsp_result"]["kind"] == "unavailable"
