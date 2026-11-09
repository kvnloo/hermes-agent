"""Plugin directory scans must skip dunder dirs and survive OSError (#86996)."""

from __future__ import annotations

from pathlib import Path

from hermes_cli.plugins import PluginManager


def test_scan_skips_dunder_dirs_and_still_loads_real_plugin(tmp_path: Path):
    root = tmp_path / "plugins"
    demo = root / "demo"
    demo.mkdir(parents=True)
    (demo / "plugin.yaml").write_text("name: demo\nversion: 0.1.0\ndescription: x\n")
    (demo / "__pycache__").mkdir()
    (root / "__pycache__").mkdir()
    (root / "__MACOSX__").mkdir()

    found = PluginManager()._scan_directory(root, "user")

    assert [manifest.name for manifest in found] == ["demo"]


def test_scan_survives_iterdir_oserror(tmp_path: Path, monkeypatch):
    root = tmp_path / "plugins"
    root.mkdir()

    def _boom(_self):
        raise PermissionError("unreadable plugin root")

    monkeypatch.setattr(Path, "iterdir", _boom, raising=False)
    found = PluginManager()._scan_directory(root, "user")
    assert found == []


def test_scan_skips_child_whose_is_dir_raises(tmp_path: Path, monkeypatch):
    root = tmp_path / "plugins"
    demo = root / "demo"
    demo.mkdir(parents=True)
    (demo / "plugin.yaml").write_text("name: demo\nversion: 0.1.0\ndescription: x\n")
    spooky = root / "spooky"
    spooky.mkdir()

    original_is_dir = Path.is_dir

    def _is_dir(self):
        if self.name == "spooky":
            raise PermissionError("stat failed")
        return original_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", _is_dir)
    found = PluginManager()._scan_directory(root, "user")
    assert [manifest.name for manifest in found] == ["demo"]


def test_transaction_staging_skipped_by_both_scanners_but_hermes_manifest_kept(tmp_path: Path):
    """Regression for #147455 and #137974: staging is hidden, not real Hermes manifests."""
    from hermes_cli.plugins_cmd import _scan_level
    from hermes_cli.plugins_discovery import manifest_key, scan_directory

    root = tmp_path / "plugins"

    def add_manifest(*parts: str, name: str) -> None:
        directory = root.joinpath(*parts)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "plugin.yaml").write_text(
            f"name: {name}\nversion: 0.1.0\ndescription: test\n"
        )

    add_manifest("demo", name="demo")
    # Install, update, and remove all stage inside the scanned plugins root.
    for staging in (".install-123", ".update-123", ".demo.remove-123"):
        add_manifest(staging, "plugin", name="demo")
    add_manifest("multi", ".hermes-plugin", name="multi")

    expected = {"demo", "multi/.hermes-plugin"}
    assert {manifest_key(item) for item in scan_directory(root, "user")} == expected

    listed: dict = {}
    _scan_level(root, "user", set(), "", 0, listed)
    assert set(listed) == expected

    # 'hermes plugins doctor <repo>/.hermes-plugin' stages that directory at
    # the root of its temporary plugins directory, not below a parent plugin.
    doctor_root = tmp_path / "doctor"
    manifest_dir = doctor_root / ".hermes-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "plugin.yaml").write_text(
        "name: doctor-demo\nversion: 0.1.0\ndescription: test\n"
    )
    assert [item.name for item in scan_directory(doctor_root, "user")] == ["doctor-demo"]
