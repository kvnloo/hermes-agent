"""Structured diagnostics survive real write/replace/V4A operations (#523)."""
from unittest.mock import MagicMock, patch

import pytest

from agent.lsp.manager import LSPService
from agent.lsp.reporter import MAX_PER_FILE, structured_for_file
from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations


def diagnostic(severity=1):
    return {"severity": severity, "range": {"start": {"line": 1, "character": 2}},
            "message": "Unknown <name>\nsecond line\x00"}


@pytest.mark.parametrize("operation", ["write", "replace", "v4a"])
def test_structured_diagnostics_survive_file_operations(tmp_path, operation):
    target = tmp_path / "x.py"
    target.write_text("x = 1\n")
    fops = ShellFileOperations(LocalEnvironment(cwd=str(tmp_path)))
    service = MagicMock()
    service.enabled_for.return_value = True
    service.get_diagnostics_sync.return_value = [diagnostic(), diagnostic(2)]
    with patch.object(fops, "_lsp_service", return_value=service):
        if operation == "write":
            result = fops.write_file(str(target), "x = 2\n")
        elif operation == "replace":
            result = fops.patch_replace(str(target), "x = 1", "x = 2")
        else:
            result = fops.patch_v4a(f"*** Begin Patch\n*** Update File: {target}\n@@\n-x = 1\n+x = 2\n*** End Patch")
    payload = result.to_dict()
    assert target.read_text() == "x = 2\n"
    assert "ERROR [2:3]" in payload["lsp_diagnostics"]
    assert "WARN" not in payload["lsp_diagnostics"]  # legacy severity policy stays unchanged
    data = payload["lsp_diagnostics_data"]
    assert data == [{"path": str(target), "status": "ok", "omitted": 0, "diagnostics": [
        {"severity": "error", "line": 2, "col": 3, "message": "Unknown <name> second line"},
        {"severity": "warn", "line": 2, "col": 3, "message": "Unknown <name> second line"},
    ]}]
    service.get_diagnostics_sync.assert_called_once()


def test_v4a_aggregates_structured_results_from_two_files(tmp_path):
    fops = ShellFileOperations(LocalEnvironment(cwd=str(tmp_path)))
    paths = [tmp_path / "a.py", tmp_path / "b.py"]
    for path in paths:
        path.write_text("x = 1\n")
    service = MagicMock()
    service.enabled_for.return_value = True
    service.get_diagnostics_sync.return_value = [diagnostic(2)]
    changes = "\n".join(f"*** Update File: {path}\n@@\n-x = 1\n+x = 2" for path in paths)
    with patch.object(fops, "_lsp_service", return_value=service):
        result = fops.patch_v4a(f"*** Begin Patch\n{changes}\n*** End Patch")
    assert result.success
    assert [entry["path"] for entry in result.to_dict()["lsp_diagnostics_data"]] == list(map(str, paths))
    assert service.get_diagnostics_sync.call_count == 2


def test_failed_service_is_not_a_diagnostic_error(tmp_path):
    fops = ShellFileOperations(LocalEnvironment(cwd=str(tmp_path)))
    target = tmp_path / "x.py"
    service = MagicMock()
    service.enabled_for.return_value = True
    service.get_diagnostics_sync.side_effect = RuntimeError("server failed")
    with patch.object(fops, "_lsp_service", return_value=service):
        result = fops.write_file(str(target), "x = 2\n")
    assert result.error is None
    assert result.lsp_diagnostics is None
    assert result.lsp_diagnostics_data == [{"path": str(target), "status": "unavailable",
                                           "message": "LSP unavailable: language server failed to return diagnostics"}]


def test_prewrite_broken_server_surfaces_as_unavailable(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n")
    monkeypatch.chdir(tmp_path)
    service = LSPService(enabled=True, wait_mode="document", wait_timeout=1.0, install_strategy="manual")
    fops = ShellFileOperations(LocalEnvironment(cwd=str(tmp_path)))
    try:
        service._mark_broken_for_file(str(target), RuntimeError("snapshot failed"))
        with patch.object(fops, "_lsp_service", return_value=service):
            result = fops.write_file(str(target), "x = 2\n")
        assert result.error is None
        assert result.lsp_diagnostics_data is not None
        assert result.lsp_diagnostics_data[0]["status"] == "unavailable"
        assert "marked broken" in result.lsp_diagnostics_data[0]["message"]
    finally:
        service.shutdown()


def test_structured_payload_is_bounded_and_records_omissions():
    data = structured_for_file("x.py", [diagnostic()] * (MAX_PER_FILE + 3), failures=[])
    assert len(data["diagnostics"]) == MAX_PER_FILE
    assert data["omitted"] == 3


@pytest.mark.parametrize("raises", [False, True])
def test_service_distinguishes_no_verdict_from_checked_clean(tmp_path, monkeypatch, raises):
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n")
    monkeypatch.chdir(tmp_path)
    service = LSPService(enabled=True, wait_mode="document", wait_timeout=1.0, install_strategy="manual")

    async def no_verdict(*args, **kwargs):
        if raises:
            raise RuntimeError("fixture server failure")
        return None

    try:
        failures = []
        with patch.object(service, "_open_and_wait_async", no_verdict):
            assert service.get_diagnostics_sync(str(target), failures=failures) == []
        assert len(failures) == 1
        assert failures[0].startswith("LSP unavailable:")
    finally:
        service.shutdown()
