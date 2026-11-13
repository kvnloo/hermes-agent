"""A killed optional web build must not invalidate a usable CLI install (#154782)."""

import subprocess

import pytest

from hermes_cli import source_build, source_completion


@pytest.fixture
def prepared_install(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    (root / "hermes_cli").mkdir(parents=True)
    (root / "hermes_cli/source_completion.py").touch()
    monkeypatch.setattr("pm.environments.activate_dependencies", lambda _root: None)
    monkeypatch.setattr("hermes_cli._subprocess_compat.expose_pm_git", lambda _root: None)
    monkeypatch.setattr("hermes_cli.venv_sync.publish_launchers", lambda _root: None)
    monkeypatch.setattr("hermes_cli.source_stamp.write_source_stamp",
                        lambda _root: pytest.fail("deferred work must not be stamped"))
    messages = []

    def maintenance(**kwargs):
        messages.append((kwargs["completion_message"], tuple(kwargs["followups"])))
        return True

    monkeypatch.setattr("hermes_cli.update_cmd_maint._run_post_update_maintenance", maintenance)
    return root, messages


def _killed_build(monkeypatch, *products):
    def build(_root, *, desktop, after_dependencies=None):
        raise source_build.ProductBuildError([
            (name, subprocess.CalledProcessError(-9, ["pnpm", "run", "build"]))
            for name in products
        ])

    monkeypatch.setattr(source_build, "build_update_products", build)


def test_installer_defers_killed_web_build_without_stamping(prepared_install, monkeypatch):
    root, messages = prepared_install
    _killed_build(monkeypatch, "web UI build")

    assert source_completion.main(["--source", str(root), "--prepared"]) == 0
    assert len(messages) == 1
    assert messages[0][0].startswith("✓ Hermes CLI installed; web UI build deferred")
    assert [name for name, _ in messages[0][1]] == ["build"]
    assert not (root / "install-stamp.json").exists()

