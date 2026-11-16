"""The installer-manifest read exemption must not allow writes into the real home.

Regression for NousResearch/hermes-agent#156011.
"""
from __future__ import annotations

import os

import pytest

from tests import home_io_guard


def test_payload_manifest_probe_is_read_only(tmp_path, monkeypatch):
    """A checkout's parent manifest can be inspected but never changed by a test."""
    protected = tmp_path / "protected"
    protected.mkdir()
    manifest = protected / "manifest.json"
    manifest.write_text('{"source": "operator"}', encoding="utf-8")

    # Model an install whose checkout is immediately beneath the guarded home.
    # On the PR merge base this whitelist does not exist: its read must be red.
    monkeypatch.setattr(
        home_io_guard,
        "_PAYLOAD_MANIFEST_STRS",
        (os.path.normcase(os.path.realpath(manifest)),),
        raising=False,
    )
    guard = home_io_guard.HomeIOGuard(lambda: [protected])
    guard.check(manifest)  # bootstrap read remains allowed
    guard.check(manifest, metadata=True)  # is_file() remains allowed

    # Without the review fix the PR exempts BOTH operations, including writes.
    with pytest.raises(AssertionError, match="REAL hermes home"):
        guard.check(manifest, destructive=True)
    with pytest.raises(AssertionError, match="REAL hermes home"):
        guard.check(manifest, metadata=True, destructive=True)
    assert manifest.read_text(encoding="utf-8") == '{"source": "operator"}'
