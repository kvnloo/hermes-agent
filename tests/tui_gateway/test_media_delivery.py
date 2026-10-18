"""Bounded, session-owned image delivery for SDK blobs (#582)."""
import base64
import json
from types import SimpleNamespace

import pytest

from tui_gateway import server
from tui_gateway.media_delivery import MAX_IMAGE_BYTES

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVmQAAAAASUVORK5CYII=")


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    transport = SimpleNamespace(write=lambda frame: True)
    path = tmp_path / "image.jpg"  # deliberately not PNG's extension
    path.write_bytes(PNG)
    record = {"session_key": "owned", "transport": transport, "profile_home": str(tmp_path),
              "cwd": str(tmp_path), "history": [], "attached_images": [str(path)]}
    monkeypatch.setattr(server, "_sessions", {"owned": record})
    monkeypatch.setattr(server, "_bound_terminal_backend", lambda home: "local")

    def call(via=transport, **params):
        token = server.bind_transport(via)
        try:
            return server.handle_request({"id": 1, "method": "media.image", "params": {
                "session_id": "owned", "path": str(path), **params}})
        finally:
            server.reset_transport(token)
    return call, record, path


def test_staged_image_bytes_and_magic_mime_without_agent_or_file_mutation(runtime):
    call, record, path = runtime
    before = dict(record)
    response = call()
    assert "error" not in response, response
    assert response["result"] == {"content_base64": base64.b64encode(PNG).decode(),
                                   "mime": "image/png", "bytes": len(PNG)}
    assert record == before
    assert path.read_bytes() == PNG


def test_foreign_transport_unknown_session_and_detached_image_are_rejected(runtime):
    call, record, _ = runtime
    assert call(via=SimpleNamespace(write=lambda frame: True))["error"]["code"] == 4001
    assert call(session_id="missing")["error"]["code"] == 4001
    record["attached_images"] = []
    assert call()["error"]["code"] == 4016


@pytest.mark.parametrize("path", [12, "", "x" * 4097, None])
def test_invalid_known_params_are_rejected_before_file_reads(runtime, path):
    call, _, _ = runtime
    assert call(path=path)["error"]["code"] == 4000


def test_resume_reuses_durable_path_refs_and_does_not_require_a_new_handle(runtime):
    call, record, path = runtime
    from agent.context_references import format_reference_value
    record["attached_images"] = []
    record["history"] = [{"role": "user", "content": [
        {"type": "text", "text": f"Caption\n@image:{format_reference_value(str(path))}"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(PNG).decode()}}]}]
    assert call()["result"]["mime"] == "image/png"
    path.unlink()
    assert call()["error"]["code"] == 4016


def test_only_exact_completed_tool_call_path_is_authorized(runtime):
    call, record, path = runtime
    record["attached_images"] = []
    record["history"] = [
        {"role": "assistant", "tool_calls": [{"id": "read-1", "function": {
            "name": "read_file", "arguments": json.dumps({"path": path.name})}}]},
        {"role": "tool", "tool_call_id": "read-1", "content": json.dumps({"is_image": True})}]
    assert call(tool_call_id="read-1")["result"]["bytes"] == len(PNG)
    assert call(tool_call_id="other")["error"]["code"] == 4016
    assert call(tool_call_id="read-1", path=str(path.parent / "other.png"))["error"]["code"] == 4016
    record["history"][-1]["content"] = json.dumps({"error": "permission denied"})
    assert call(tool_call_id="read-1")["error"]["code"] == 4016


def test_compute_host_paths_cannot_read_same_named_gateway_file(runtime, monkeypatch):
    call, record, path = runtime
    record["history"] = [{"role": "tool", "tool_call_id": "read-1", "name": "read_file",
                          "args": {"path": str(path)}, "content": {"is_image": True}}]
    monkeypatch.setattr(server, "_bound_terminal_backend", lambda home: "ssh")
    assert "Compute-host" in call(tool_call_id="read-1")["error"]["message"]
    # The user's staged bytes still belong to the gateway, not the compute host.
    assert call()["result"]["bytes"] == len(PNG)


def test_oversized_unsupported_and_symlink_files_are_rejected(runtime, tmp_path):
    call, _, path = runtime
    with path.open("wb") as file:
        file.truncate(MAX_IMAGE_BYTES + 1)
    assert call()["error"]["code"] == 4016
    path.write_bytes(b"not an image")
    assert call()["error"]["code"] == 4016
    path.unlink()
    target = tmp_path / "target.png"
    target.write_bytes(PNG)
    path.symlink_to(target)
    assert call()["error"]["code"] == 4016


def test_permission_failure_is_reported_not_hidden(runtime, monkeypatch):
    call, _, _ = runtime
    from tui_gateway import media_delivery
    monkeypatch.setattr(media_delivery.os, "open", lambda *args: (_ for _ in ()).throw(PermissionError("denied")))
    assert "denied" in call()["error"]["message"]
