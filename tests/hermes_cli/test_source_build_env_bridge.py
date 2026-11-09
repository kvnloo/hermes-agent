"""Electron download settings in the active profile reach desktop build children.

Regression for NousResearch/hermes-agent#151909 (reported by lhby2004).
The profile .env also holds credentials, which must not be exported to npm scripts.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

import pm
from pm.package import Runner


@pytest.fixture
def profile(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    for key in ("ELECTRON_MIRROR", "ELECTRON_BUILDER_BINARIES_MIRROR", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    for key in list(os.environ):
        if key.upper().startswith("NPM_CONFIG_"):
            monkeypatch.delenv(key)
    monkeypatch.setattr(pm, "ensure", lambda name, *, base_env, **_: Runner(name, dict(base_env)))
    (home / ".env").write_text(
        "ELECTRON_MIRROR=https://profile.invalid/electron/\n"
        "ELECTRON_BUILDER_BINARIES_MIRROR=https://profile.invalid/binaries/\n"
        "OPENAI_API_KEY=do-not-leak-to-npm\n", encoding="utf-8")
    return home


def test_profile_electron_mirrors_reach_desktop_build_subprocess(profile):
    from hermes_cli.source_build import source_build_env

    env = source_build_env()
    keys = ("ELECTRON_MIRROR", "ELECTRON_BUILDER_BINARIES_MIRROR", "OPENAI_API_KEY")
    output = subprocess.check_output(
        [sys.executable, "-c",
         "import json, os, sys; print(json.dumps([os.getenv(k) for k in sys.argv[1:]]))",
         *keys], env=env, text=True)
    assert json.loads(output) == [
        "https://profile.invalid/electron/", "https://profile.invalid/binaries/", None]
    assert "OPENAI_API_KEY" not in env  # the secret scope must not leak into install scripts


def test_shell_and_base_overrides_win_over_profile(profile, monkeypatch):
    from hermes_cli.source_build import source_build_env

    monkeypatch.setenv("ELECTRON_MIRROR", "https://shell.invalid/")
    env = source_build_env({"ELECTRON_BUILDER_BINARIES_MIRROR": "https://base.invalid/"})

    assert env["ELECTRON_MIRROR"] == "https://shell.invalid/"
    assert env["ELECTRON_BUILDER_BINARIES_MIRROR"] == "https://base.invalid/"


def test_npmrc_mirrors_win_over_profile(profile):
    from hermes_cli.source_build import source_build_env

    (profile / "npmrc").write_text(
        "electron-mirror=https://npmrc.invalid/electron/\n"
        "electron-builder-binaries-mirror=https://npmrc.invalid/binaries/\n",
        encoding="utf-8")
    env = source_build_env()

    assert env["npm_config_electron_mirror"] == "https://npmrc.invalid/electron/"
    assert env["npm_config_electron_builder_binaries_mirror"] == "https://npmrc.invalid/binaries/"
    assert "ELECTRON_MIRROR" not in env
    assert "ELECTRON_BUILDER_BINARIES_MIRROR" not in env
