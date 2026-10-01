"""The observer spool belongs to the active Hermes profile.

Regression: when the profile's ``plugin-data`` directory could not be created, rows were
written under ``~/.hermes`` (the default profile) instead of being dropped.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "lab" / "z0_hermes_observer" / "__init__.py"


def _load():
    spec = importlib.util.spec_from_file_location("z0_hermes_observer_storage_scope_plugin", PLUGIN)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_spool_lands_in_the_active_profiles_plugin_data_dir(tmp_path, monkeypatch):
    from plugins.plugin_storage import plugin_data_dir

    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "profile"))
    monkeypatch.delenv("Z0INT_HERMES_EVENT_PATH", raising=False)
    module = _load()

    module.observe("post_api_request", session_id="s", turn_id="t")

    spool = plugin_data_dir(module.PLUGIN_ID) / "events.jsonl"
    assert spool.parent == tmp_path / "profile" / "plugin-data" / "z0-hermes-observer"
    assert [json.loads(line)["event"] for line in spool.read_text(encoding="utf-8-sig").splitlines()] == ["post_api_request"]


def test_unwritable_profile_storage_never_spills_into_the_default_profile(tmp_path, monkeypatch):
    default_home = tmp_path / "default-home"
    default_home.mkdir()
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "plugin-data").write_text("a file where the spool directory should be", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: default_home)
    monkeypatch.setenv("HERMES_HOME", str(profile))
    monkeypatch.delenv("Z0INT_HERMES_EVENT_PATH", raising=False)
    module = _load()

    assert module.observe("post_api_request", session_id="s", turn_id="t") is None

    assert not (default_home / ".hermes").exists()
