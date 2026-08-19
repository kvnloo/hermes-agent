from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import threading
import traceback
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
    return policy.create_test_policy_loader(home, fd, {"keel-test": KEY}, production=False, clock=lambda: NOW)


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
        assert not hasattr(policy, "LauncherPolicyState")
        with pytest.raises(TypeError):
            policy.create_startup_policy_loader(home, fd)  # type: ignore[call-arg]
        with pytest.raises(policy.PolicyLoadError, match="launcher_bootstrap_unavailable"):
            policy.create_startup_policy_loader()
        with pytest.raises(policy.PolicyLoadError, match="test_provider_forbidden"):
            policy.create_test_policy_loader(home, fd, {"keel-test": KEY}, production=True, clock=lambda: NOW)
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
        bad_key = policy.create_test_policy_loader(home, fd, {}, production=False, clock=lambda: NOW)
        assert bad_key.reload().validity == "DENY"
        expired = policy.create_test_policy_loader(home, fd, {"keel-test": KEY}, production=False, clock=lambda: NOW + 101)
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
    fixture = policy.create_test_surface_fixture(startup, {
        "create": lambda: (called.append(create_task.__name__)),
        "promote": lambda: (called.append(promote_task.__name__)),
        "claim": lambda: (called.append(claim_task.__name__)),
        "spawn": lambda: (called.append(subprocess.Popen.__name__)),
    }, active=False, production=False)
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


def test_production_boundary_ignores_late_env_and_object_forgery(tmp_path: Path, monkeypatch) -> None:
    home, fd = _fixture(tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv(policy._STARTUP_FD_ENV, str(fd))
    monkeypatch.setattr(policy, "_KeelSecretServiceProvider", policy._TestPolicyKeyProvider)
    try:
        with pytest.raises(policy.PolicyLoadError, match="launcher_bootstrap_unavailable"):
            policy.create_startup_policy_loader()
        assert "LauncherPolicyState" not in policy.__dict__
        assert "_seal_startup_boundary" not in policy.__dict__
    finally:
        os.close(fd)


@pytest.mark.parametrize("name", [policy.TRUST_ROOT_NAME, policy.MANIFEST_NAME])
def test_final_pathname_reopen_rejects_rename_replacement(tmp_path: Path, monkeypatch, name: str) -> None:
    home, fd = _fixture(tmp_path)
    anchor = policy.trust_anchor_path(home)
    real_reopen = policy._reopen_regular
    swapped = False

    def swap_then_reopen(anchor_fd: int, reopened_name: str, identity, digest: str) -> None:
        nonlocal swapped
        if reopened_name == name and not swapped:
            swapped = True
            target = anchor / name
            raw = target.read_bytes()
            target.rename(anchor / f"{name}.detached")
            target.write_bytes(raw)
            os.chmod(target, 0o600)
        real_reopen(anchor_fd, reopened_name, identity, digest)

    monkeypatch.setattr(policy, "_reopen_regular", swap_then_reopen)
    try:
        snapshot = _loader(home, fd).reload()
    finally:
        os.close(fd)
    assert snapshot.validity == "DENY"
    assert snapshot.reason == f"pathname_replaced_{name}"


def test_disposable_gate_executes_real_db_and_popen_surfaces_only_when_active(tmp_path: Path) -> None:
    from hermes_cli import kanban_db as kb

    db_path = kb.init_db(tmp_path / "kanban.db")
    conn = kb.connect(db_path)
    sentinel = tmp_path / "spawned"
    stacks: list[tuple[str, str]] = []
    created: list[str] = []

    def record(name: str) -> None:
        stacks.append((name, "".join(traceback.format_stack())))

    def create() -> str:
        record("create")
        task_id = kb.create_task(conn, title="focused", assignee="worker", initial_status="running")
        created.append(task_id)
        conn.execute("UPDATE tasks SET status = 'todo' WHERE id = ?", (task_id,))
        conn.commit()
        return task_id

    def promote() -> tuple[bool, str | None]:
        record("promote")
        return kb.promote_task(conn, created[0], actor="test")

    def claim():
        record("claim")
        return kb.claim_task(conn, created[0], claimer="test", ttl_seconds=60)

    def spawn() -> int:
        record("spawn")
        proc = subprocess.Popen(
            ["/bin/sh", "-c", f"printf reached > {sentinel}"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        assert proc.wait(timeout=5) == 0
        return proc.pid

    surfaces = {"create": create, "promote": promote, "claim": claim, "spawn": spawn}
    denied = policy.create_test_surface_fixture(
        policy.PolicySnapshot(1, 0, "DENY", "fixture_deny"),
        surfaces, active=False, production=False,
    )
    for name in surfaces:
        with pytest.raises(PermissionError, match=f"denied {name}"):
            denied.invoke(name)
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
    assert not sentinel.exists()
    assert stacks == []

    active = policy.create_test_surface_fixture(
        policy.PolicySnapshot(2, 1, "ACTIVE", "test_only_active"),
        surfaces, active=True, production=False,
    )
    task_id = active.invoke("create")
    assert task_id == created[0]
    assert active.invoke("promote") == (True, None)
    claimed = active.invoke("claim")
    assert claimed is not None and getattr(claimed, "id") == task_id
    assert isinstance(active.invoke("spawn"), int)
    assert sentinel.read_text() == "reached"
    assert [name for name, _ in stacks] == ["create", "promote", "claim", "spawn"]
    assert all("invoke" in stack for _, stack in stacks)
    kinds = [row[0] for row in conn.execute(
        "SELECT kind FROM task_events WHERE task_id = ? ORDER BY id", (task_id,)
    )]
    assert kinds == ["created", "promoted_manual", "claimed"]
    conn.close()


def test_test_surface_fixture_refuses_production() -> None:
    with pytest.raises(policy.PolicyLoadError, match="forbidden_in_production"):
        policy.create_test_surface_fixture(
            policy.PolicySnapshot(0, 0, "DENY", "x"), {},
            active=True, production=True,
        )
