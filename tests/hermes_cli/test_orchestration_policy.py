from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

from hermes_cli import orchestration_policy as policy


KEY = b"test-only-key"


def _write_fixture(root: Path, *, active: bool = False) -> tuple[Path, dict, dict]:
    root.mkdir(mode=0o700, exist_ok=True)
    config_home = root / "config"
    config_home.mkdir(mode=0o700)
    anchor = policy.install_anchor(config_home)
    signed = {
        "generation_id": "generation-7",
        "governance_content_sha256": "a" * 64,
        "key_id": "captain-test",
        "policy_version": "6",
    }
    manifest = {**signed, "mac": policy.manifest_mac(signed, KEY)}
    manifest_raw = json.dumps(manifest, sort_keys=True).encode()
    trust = {
        "governance_content_sha256": signed["governance_content_sha256"],
        "key_id": signed["key_id"],
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "policy_version": signed["policy_version"],
    }
    (anchor / policy.MANIFEST_NAME).write_bytes(manifest_raw)
    (anchor / policy.TRUST_ROOT_NAME).write_text(json.dumps(trust), encoding="utf-8")
    os.chmod(anchor / policy.MANIFEST_NAME, 0o600)
    os.chmod(anchor / policy.TRUST_ROOT_NAME, 0o600)
    if active:
        (anchor / policy.ACTIVE_RECEIPT_NAME).write_text("not-authority", encoding="utf-8")
        os.chmod(anchor / policy.ACTIVE_RECEIPT_NAME, 0o600)
    return config_home, trust, manifest


def _provider() -> policy.TestPolicyKeyProvider:
    return policy.TestPolicyKeyProvider({"captain-test": KEY})


def test_valid_governance_is_frozen_and_active_path_does_not_activate(tmp_path: Path) -> None:
    config_home, _, _ = _write_fixture(tmp_path, active=True)
    snapshot = policy.load_policy_snapshot(config_home, _provider())
    assert snapshot.validity == "FROZEN"
    assert snapshot.reason == "activation_receipt_unsupported"
    assert snapshot.generation_id == "generation-7"
    assert snapshot.anchor_identity is not None
    assert not snapshot.focused


def test_environment_and_worker_path_injection_are_ignored(tmp_path: Path, monkeypatch) -> None:
    config_home, _, _ = _write_fixture(tmp_path)
    evil = tmp_path / "evil"
    evil.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(evil))
    monkeypatch.setenv("HERMES_ORCHESTRATION_POLICY", str(evil))
    assert policy.trust_anchor_path(config_home).is_relative_to(config_home)
    assert policy.load_policy_snapshot(config_home, _provider()).generation_id == "generation-7"


def test_missing_root_and_unavailable_key_deny(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert policy.load_policy_snapshot(missing, _provider()).validity == "DENY"
    config_home, _, _ = _write_fixture(tmp_path / "fixture")
    snapshot = policy.load_policy_snapshot(config_home, policy.UnavailablePolicyKeyProvider())
    assert (snapshot.validity, snapshot.reason) == ("DENY", "key_unavailable")


def test_symlink_and_permissions_deny(tmp_path: Path) -> None:
    config_home, _, _ = _write_fixture(tmp_path / "symlink")
    anchor = policy.trust_anchor_path(config_home)
    manifest = anchor / policy.MANIFEST_NAME
    target = anchor / "target.json"
    manifest.rename(target)
    manifest.symlink_to(target)
    assert policy.load_policy_snapshot(config_home, _provider()).validity == "DENY"

    config_home2, _, _ = _write_fixture(tmp_path / "permissions")
    os.chmod(policy.trust_anchor_path(config_home2), 0o777)
    snapshot = policy.load_policy_snapshot(config_home2, _provider())
    assert (snapshot.validity, snapshot.reason) == ("DENY", "insecure_anchor")


def test_owner_predicate_rejects_foreign_uid() -> None:
    class Foreign:
        st_mode = stat.S_IFDIR | 0o700
        st_uid = os.getuid() + 1

    assert not policy._secure_dir(Foreign())  # type: ignore[arg-type]


def test_manifest_hash_pin_and_mac_mismatch_deny(tmp_path: Path) -> None:
    config_home, trust, manifest = _write_fixture(tmp_path / "hash")
    anchor = policy.trust_anchor_path(config_home)
    trust["manifest_sha256"] = "0" * 64
    (anchor / policy.TRUST_ROOT_NAME).write_text(json.dumps(trust), encoding="utf-8")
    assert policy.load_policy_snapshot(config_home, _provider()).reason == "manifest_hash_mismatch"

    config_home2, trust2, manifest2 = _write_fixture(tmp_path / "mac")
    anchor2 = policy.trust_anchor_path(config_home2)
    manifest2["mac"] = "0" * 64
    raw = json.dumps(manifest2, sort_keys=True).encode()
    trust2["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    (anchor2 / policy.MANIFEST_NAME).write_bytes(raw)
    (anchor2 / policy.TRUST_ROOT_NAME).write_text(json.dumps(trust2), encoding="utf-8")
    assert policy.load_policy_snapshot(config_home2, _provider()).reason == "mac_mismatch"


def test_pinned_governance_hash_mismatch_denies(tmp_path: Path) -> None:
    config_home, trust, manifest = _write_fixture(tmp_path)
    anchor = policy.trust_anchor_path(config_home)
    trust["governance_content_sha256"] = "b" * 64
    (anchor / policy.TRUST_ROOT_NAME).write_text(json.dumps(trust), encoding="utf-8")
    assert policy.load_policy_snapshot(config_home, _provider()).reason == "pinned_governance_content_sha256_mismatch"


def test_restart_reload_and_failed_reload_replace_with_deny(tmp_path: Path) -> None:
    config_home, _, _ = _write_fixture(tmp_path)
    first = policy.StartupPolicyLoader(config_home, _provider())
    second = policy.StartupPolicyLoader(config_home, _provider())
    assert first.reload().generation_id == second.reload().generation_id == "generation-7"
    (policy.trust_anchor_path(config_home) / policy.MANIFEST_NAME).unlink()
    failed = first.reload()
    assert failed.validity == "DENY"
    assert first.snapshot == failed


def test_reload_rejects_replaced_anchor_identity(tmp_path: Path) -> None:
    config_home, _, _ = _write_fixture(tmp_path)
    loader = policy.StartupPolicyLoader(config_home, _provider())
    assert loader.reload().validity == "FROZEN"
    anchor = policy.trust_anchor_path(config_home)
    anchor.rename(anchor.with_name("orchestration-policy.old"))
    replacement_root = tmp_path / "replacement"
    replacement_home, _, _ = _write_fixture(replacement_root)
    policy.trust_anchor_path(replacement_home).rename(anchor)
    snapshot = loader.reload()
    assert (snapshot.validity, snapshot.reason) == ("DENY", "anchor_identity_changed")


def test_concurrent_document_change_denies(tmp_path: Path, monkeypatch) -> None:
    config_home, _, _ = _write_fixture(tmp_path)
    real_fstat = policy.os.fstat
    calls = 0

    def changing_fstat(fd: int):
        nonlocal calls
        calls += 1
        value = real_fstat(fd)
        if calls == 7:
            fields = list(value)
            fields[8] += 1  # st_mtime as a portable fallback for st_mtime_ns
            return os.stat_result(fields)
        return value

    monkeypatch.setattr(policy.os, "fstat", changing_fstat)
    snapshot = policy.load_policy_snapshot(config_home, _provider())
    assert snapshot.validity == "DENY"
    assert snapshot.reason.startswith("concurrent_swap_")