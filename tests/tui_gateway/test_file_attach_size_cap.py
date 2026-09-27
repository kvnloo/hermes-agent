"""file.attach stages client bytes with the same 25 MB cap as the sibling attach paths."""
import base64
import sys
import types
from pathlib import Path

import pytest

import tui_gateway.prompt_attachments as pa


@pytest.fixture
def bound(tmp_path, monkeypatch):
    """Rebind the server-provided globals the staging function expects."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    home = tmp_path / "home"
    monkeypatch.setattr(pa, "Path", Path, raising=False)
    monkeypatch.setattr(pa, "_session_cwd", lambda session: str(workspace), raising=False)
    monkeypatch.setattr(
        pa, "_session_home_dir",
        lambda session, kind: home / kind, raising=False)
    # The raw_path branch imports helpers from cli (too heavy here); stub them.
    cli = types.ModuleType("cli")
    cli._detect_file_drop = lambda raw: None
    cli._split_path_input = lambda raw: (raw, "")
    cli._resolve_attachment_path = lambda token: token
    monkeypatch.setitem(sys.modules, "cli", cli)
    return {"workspace": workspace, "home": home, "session": {}}


def _data_url(nbytes: int) -> str:
    return "data:application/octet-stream;base64," + base64.b64encode(b"x" * nbytes).decode()


def test_data_url_over_cap_rejected(bound):
    """40 MB data_url (past the 25 MB image cap and near the 50 MB PDF cap) fails loudly."""
    with pytest.raises(ValueError, match="too large"):
        pa._stage_session_file_attachment(
            bound["session"], raw_path="", data_url=_data_url(40 * 1024 * 1024), name="big.bin")
    assert not (bound["home"] / "attachments").exists()


def test_gateway_path_over_cap_rejected(bound):
    """A 40 MB gateway-visible file outside the workspace is not copied in."""
    big = bound["workspace"].parent / "outside.bin"
    big.write_bytes(b"y" * (40 * 1024 * 1024))
    with pytest.raises(ValueError, match="too large"):
        pa._stage_session_file_attachment(
            bound["session"], raw_path=str(big), data_url="", name="")
    assert not (bound["home"] / "attachments").exists()


def test_small_file_attach_still_works(bound):
    """Files under the cap keep staging into attachments/."""
    target, uploaded = pa._stage_session_file_attachment(
        bound["session"], raw_path="", data_url=_data_url(1024), name="small.bin")
    assert uploaded is True
    assert target.read_bytes() == b"x" * 1024
