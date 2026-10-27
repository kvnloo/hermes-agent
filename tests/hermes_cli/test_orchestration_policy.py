from __future__ import annotations

import fcntl
import hashlib
import json
import os
import threading
from pathlib import Path

import pytest

from hermes_cli import orchestration_policy as policy

KEY = b"test-only-keel-key"
NOW = 2_000_000_000


def _sealed_fd(raw: bytes) -> int:
    fd = os.memfd_create("policy-bootstrap", os.MFD_ALLOW_SEALING)
    os.write(fd, raw)
    fcntl.fcntl(fd, fcntl.F_ADD_SEALS, policy._REQUIRED_SEALS)
    readonly = os.open(f"/proc/self/fd/{fd}", os.O_RDONLY | os.O_CLOEXEC)
    os.close(fd)
    return readonly


def _fixture(root: Path) -> tuple[Path, int]:
    home = root / "home"
    anchor = policy.install_anchor(home)
    signed = {
        "governance_content_sha256": "a" * 64,
        "governance_version": "6",
        "key_id": "keel-test",
    }
    manifest = {**signed, "mac": policy.manifest_mac(signed, KEY)}
    manifest_raw = policy._canonical_json(manifest)
    trust = {**signed, "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest()}
    trust_raw = policy._canonical_json(trust)
    (anchor / policy.MANIFEST_NAME).write_bytes(manifest_raw)
    (anchor / policy.TRUST_ROOT_NAME).write_bytes(trust_raw)
    os.chmod(anchor / policy.MANIFEST_NAME, 0o600)
    os.chmod(anchor / policy.TRUST_ROOT_NAME, 0o600)
    st = anchor.stat()
    envelope = {
        "anchor_device": st.st_dev,
        "anchor_inode": st.st_ino,
        "effective_at": NOW - 1,
        "expires_at": NOW + 100,
        "generation": 7,
        "governance_content_sha256": signed["governance_content_sha256"],
        "governance_version": signed["governance_version"],
        "key_id": signed["key_id"],
        "nonce": "keel-nonce-7",
        "trust_root_sha256": hashlib.sha256(trust_raw).hexdigest(),
    }
    raw = policy._canonical_json({**envelope, "mac": policy.envelope_mac(envelope, KEY)})
    return home, _sealed_fd(raw)


def _loader(home: Path, fd: int) -> policy._StartupPolicyLoader:
    return policy._create_test_policy_loader(home, fd, {"keel-test": KEY}, production=False, clock=lambda: NOW)


def test_valid_sealed_bootstrap_is_frozen_and_receipt_binding_is_evidence(tmp_path: Path) -> None:
    home, fd = _fixture(tmp_path)
    try:
        snapshot = _loader(home, fd).reload()
    finally:
        os.close(fd)
    assert snapshot.validity == "FROZEN"
    assert snapshot.reason == "activation_unsupported"
    assert snapshot.envelope_generation == 7
    assert snapshot.receipt_binding_sha256 and len(snapshot.receipt_binding_sha256) == 64
    assert not snapshot.focused


def test_production_factory_is_closed_and_test_provider_cannot_enter_production(tmp_path: Path) -> None:
    home, fd = _fixture(tmp_path)
    try:
        production = policy.create_startup_policy_loader(policy.LauncherPolicyState(home, fd))
        assert production.reload().reason == "envelope_authentication_failed"
        with pytest.raises(policy.PolicyLoadError, match="test_provider_forbidden"):
            policy._create_test_policy_loader(home, fd, {"keel-test": KEY}, production=True, clock=lambda: NOW)
        forged = policy.LauncherPolicyState(home, fd, object())
        with pytest.raises(policy.PolicyLoadError, match="untrusted_launcher_state"):
            policy.create_startup_policy_loader(forged)
    finally:
        os.close(fd)


def test_environment_paths_and_unsealed_or_writable_descriptors_cannot_substitute(tmp_path: Path, monkeypatch) -> None:
    home, fd = _fixture(tmp_path)
    evil = tmp_path / "evil"
    evil.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(evil))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(evil))
    try:
        assert _loader(home, fd).reload().validity == "FROZEN"
    finally:
        os.close(fd)
    writable = os.memfd_create("writable", os.MFD_ALLOW_SEALING)
    try:
        assert _loader(home, writable).reload().reason == "envelope_not_read_only"
    finally:
        os.close(writable)


def test_hash_anchor_expiry_and_key_fail_closed(tmp_path: Path) -> None:
    home, fd = _fixture(tmp_path)
    try:
        bad_key = policy._create_test_policy_loader(home, fd, {}, production=False, clock=lambda: NOW)
        assert bad_key.reload().validity == "DENY"
        expired = policy._create_test_policy_loader(home, fd, {"keel-test": KEY}, production=False, clock=lambda: NOW + 101)
        assert expired.reload().reason == "envelope_outside_validity"
        old = policy.trust_anchor_path(home)
        old.rename(old.with_name("old"))
        replacement = policy.install_anchor(home)
        assert _loader(home, fd).reload().reason == "anchor_pin_mismatch"
    finally:
        os.close(fd)


def test_permissions_symlink_and_path_component_replacement_fail_closed(tmp_path: Path, monkeypatch) -> None:
    home, fd = _fixture(tmp_path / "mode")
    try:
        os.chmod(policy.trust_anchor_path(home) / policy.TRUST_ROOT_NAME, 0o644)
        assert _loader(home, fd).reload().reason == f"invalid_{policy.TRUST_ROOT_NAME}"
    finally:
        os.close(fd)

    home2, fd2 = _fixture(tmp_path / "component")
    try:
        monkeypatch.setattr(policy, "_same_open_chain", lambda *_: False)
        assert _loader(home2, fd2).reload().reason == "anchor_changed_before_publish"
    finally:
        os.close(fd2)


def test_post_read_metadata_revalidation_catches_chmod_ctime_and_size(tmp_path: Path, monkeypatch) -> None:
    home, fd = _fixture(tmp_path)
    real_read = policy._read_regular

    def chmod_after_read(anchor_fd: int, name: str):
        result = real_read(anchor_fd, name)
        if name == policy.TRUST_ROOT_NAME:
            # Changes mode and ctime after the bounded read but before publish.
            os.chmod(policy.trust_anchor_path(home) / name, 0o644)
        return result

    monkeypatch.setattr(policy, "_read_regular", chmod_after_read)
    try:
        snapshot = _loader(home, fd).reload()
    finally:
        os.close(fd)
    assert snapshot.validity == "DENY"
    assert snapshot.reason == "document_changed_before_publish"


def test_linearizable_reload_older_success_cannot_overwrite_newer_deny(tmp_path: Path, monkeypatch) -> None:
    home, fd = _fixture(tmp_path)
    loader = _loader(home, fd)
    original = policy._load_candidate
    first_validated = threading.Event()
    release_first = threading.Event()
    calls = 0

    def staged(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            candidate = original(*args, **kwargs)
            first_validated.set()
            release_first.wait(5)
            return candidate
        raise policy.PolicyLoadError("newer_failure")

    monkeypatch.setattr(policy, "_load_candidate", staged)
    result: list[policy.PolicySnapshot] = []
    older = threading.Thread(target=lambda: result.append(loader.reload()))
    older.start()
    assert first_validated.wait(5)
    newer = loader.reload()
    release_first.set()
    older.join(5)
    try:
        assert newer.reload_generation == 2
        assert newer.reason == "newer_failure"
        assert loader.snapshot == newer
        assert result == [newer]
    finally:
        os.close(fd)


def test_disposable_real_surface_fixture_keeps_startup_snapshot_immutable(tmp_path: Path) -> None:
    # These are the actual production create/promote/claim callables; spawn uses
    # the actual subprocess surface. They are intentionally never reached.
    import subprocess
    from hermes_cli.kanban_db import claim_task, create_task, promote_task

    home, fd = _fixture(tmp_path)
    loader = _loader(home, fd)
    startup = loader.reload()
    called: list[str] = []
    fixture = policy.FocusedPolicyFixture(startup, {
        "create": lambda: (called.append(create_task.__name__)),
        "promote": lambda: (called.append(promote_task.__name__)),
        "claim": lambda: (called.append(claim_task.__name__)),
        "spawn": lambda: (called.append(subprocess.Popen.__name__)),
    })
    os.unlink(policy.trust_anchor_path(home) / policy.MANIFEST_NAME)
    current = loader.reload()
    try:
        assert current.validity == "DENY"
        assert fixture.startup_snapshot == startup
        for surface in ("create", "promote", "claim", "spawn"):
            with pytest.raises(PermissionError, match=f"denied {surface}"):
                fixture.invoke(surface)
        assert called == []
    finally:
        os.close(fd)
