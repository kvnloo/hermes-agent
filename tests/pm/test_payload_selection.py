"""Regression for #136015: an unrecorded payload must survive the first PM generation.

A gateway lazily installing Telegram replaces the Docker image venv; the MCP SDK
already present in that venv must remain part of the selected dependency graph.
"""

from __future__ import annotations

import os
import sys

import pytest

from pm import paths
from pm.install import _target_selection
from pm.packages import Venv


@pytest.mark.parametrize(("fact", "expected"), [
    ({}, ["all", "computer-use", "telegram"]),
    ({"extras": []}, ["all", "computer-use", "telegram"]),
    ({"extras": ["firecrawl"]}, ["firecrawl", "telegram"]),
])
def test_first_gateway_generation_keeps_payload_mcp(tmp_path, monkeypatch, fact, expected):
    root = tmp_path / "docker-payload"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "payload"\nversion = "0.1"\n'
        '[project.optional-dependencies]\nall = []\ncomputer-use = []\n'
        'telegram = []\nfirecrawl = []\n',
        encoding="utf-8",
    )
    # Real legacy_selection inspects the payload venv, without importing it.
    # The computer-use extra has an mcp anchor and carries the MCP SDK.
    if os.name == "nt":
        site = root / "venv" / "Lib" / "site-packages"
    else:
        site = root / "venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    (site / "mcp").mkdir(parents=True)

    monkeypatch.setattr(paths, "repo_root", lambda: root)
    monkeypatch.setattr(Venv, "expected_stamp", lambda self, extras, **inputs: "fixture-stamp")

    enabled, _, _ = _target_selection(
        Venv(root),
        fact,
        extras=["telegram"],
        inputs={"plugin_dirs": []},
        repair=False,
        shipped=None,
        frozen=None,
    )
    assert enabled == expected
