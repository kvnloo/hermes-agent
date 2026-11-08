"""Pre-bootstrap release date identity regression for #135217."""

import json
from datetime import UTC, datetime

import hermes_cli
from hermes_cli import version_info


def test_nix_install_root_stamp_used_when_identity_unavailable(tmp_path, monkeypatch):
    """An unavailable PM resolver must not hide the sealed install's stamp."""
    stamp = {
        "commit": "e" * 40,
        "baseVersion": "0.21.6",
        "source": "nix",
        "distribution": "nix",
        "updateMechanism": "external",
        "commitDate": int(datetime(2026, 10, 8, tzinfo=UTC).timestamp()),
    }
    (tmp_path / "install-stamp.json").write_text(json.dumps(stamp), encoding="utf-8")
    monkeypatch.setenv("HERMES_INSTALL_ROOT", str(tmp_path))

    def unavailable():
        raise ModuleNotFoundError("No module named 'pm'", name="pm")

    monkeypatch.setattr(version_info, "get_version_info", unavailable)

    assert hermes_cli.__release_date__ == "2026.10.8"
