"""Regression for #156226: skills audit must persist lock and scan-cache evidence."""

from io import StringIO

from rich.console import Console

from hermes_cli.skills_hub import do_audit
from tools import skills_hub


def test_audit_persists_verdict_and_cache(tmp_path, monkeypatch):
    skills_dir = tmp_path / "skills"
    skill = skills_dir / "sample"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: sample\ndescription: an example\n---\nUse this skill for documentation.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skills_hub, "SKILLS_DIR", skills_dir)
    monkeypatch.setattr(skills_hub, "HUB_DIR", skills_dir / ".hub")
    lock = skills_hub.HubLockFile()
    lock.record_install(
        "sample", "clawhub", "publisher/sample", "community", "backfilled",
        "sha256:original", "sample", ["SKILL.md"], metadata={"owner": "original"},
    )
    original = lock.get_installed("sample")
    sink = Console(file=StringIO(), force_terminal=False, color_system=None)

    do_audit("sample", console=sink)

    scanned = lock.get_installed("sample")
    assert scanned["scan_verdict"] == "safe"
    assert scanned["scanned_at"]
    assert scanned["scan_provenance"]["scanned_at"] == scanned["scanned_at"]
    assert scanned["scan_provenance"]["scanner_version"]
    assert "fresh" not in scanned["scan_provenance"]
    for field in ("installed_at", "updated_at", "content_hash", "install_path", "metadata"):
        assert scanned[field] == original[field]
    assert len(list((skills_dir / ".hub" / "scan-cache").glob("*.json"))) == 1

    first_lock_bytes = lock.path.read_bytes()
    do_audit("sample", console=sink)
    assert lock.path.read_bytes() == first_lock_bytes
