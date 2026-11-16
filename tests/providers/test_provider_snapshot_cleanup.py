"""Read-only native provider snapshots should be removable without touching the installed tree.

Regression for NousResearch/hermes-agent#156560.
"""

from __future__ import annotations

import shutil
import stat

import pytest

from providers import plugin_reload


def _mode(path):
    return stat.S_IMODE(path.stat().st_mode)


@pytest.mark.platforms("posix")
@pytest.mark.parametrize("copy_fails", [False, True])
def test_readonly_source_leaves_no_owned_snapshot_or_partial_copy(tmp_path, monkeypatch, copy_fails):
    source = tmp_path / "installed" / "demo"
    package = source / "package"
    package.mkdir(parents=True)
    code = package / "client.py"
    code.write_text("VERSION = 'original'\n", encoding="utf-8")
    (source / "plugin.yaml").write_text("name: demo\nkind: model-provider\n", encoding="utf-8")

    outside = tmp_path / "outside"
    outside.mkdir()
    external_file = outside / "retained.py"
    external_file.write_text("VALUE = 1\n", encoding="utf-8")
    (source / "linked").symlink_to(outside, target_is_directory=True)

    folders = (source, package, outside)
    files = (code, source / "plugin.yaml", external_file)
    for path in folders:
        path.chmod(0o555)
    for path in files:
        path.chmod(0o444)
    originals = {path: _mode(path) for path in (*folders, *files)}

    callbacks = []
    monkeypatch.setattr(plugin_reload, "_snapshot_root", None)
    monkeypatch.setattr(plugin_reload.atexit, "register", lambda *args: callbacks.append(args))
    try:
        if copy_fails:
            real_copytree = shutil.copytree

            def interrupted_copy(src, dst, *args, **kwargs):
                result = real_copytree(src, dst, *args, **kwargs)
                if src == source:
                    raise OSError("interrupted provider staging")
                return result

            monkeypatch.setattr(plugin_reload.shutil, "copytree", interrupted_copy)
            with pytest.raises(OSError, match="interrupted provider staging"):
                plugin_reload._snapshot(source, "demo_version")
        else:
            frozen = plugin_reload._snapshot(source, "demo_version")
            assert frozen.is_dir()
            assert _mode(frozen) == 0o555  # serving snapshots keep source modes
            assert (frozen / "linked" / "retained.py").exists()

        root = plugin_reload._snapshot_root
        assert root is not None
        if copy_fails:
            assert not list((root / "demo_version").glob(".copy-*"))
        assert len(callbacks) == 1
        cleanup, *args = callbacks[0]
        cleanup(*args)  # invoke the real normal-exit callback
        assert not root.exists()
        assert {path: _mode(path) for path in originals} == originals
        assert (source / "linked").is_symlink()
        assert code.read_text(encoding="utf-8") == "VERSION = 'original'\n"
    finally:
        # Let pytest remove the source fixture even if an assertion fails.
        for path in folders:
            path.chmod(0o755)
        for path in files:
            path.chmod(0o644)
