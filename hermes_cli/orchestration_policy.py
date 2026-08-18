"""Inactive, descriptor-bound trust bootstrap for focused orchestration policy.

This module deliberately does not gate the dispatcher and cannot activate focused
mode.  A trusted startup owner passes an already-authoritative config-home path;
worker environment and task input are never consulted.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import stat
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

ANCHOR_COMPONENTS = ("hermes", "orchestration-policy")
TRUST_ROOT_NAME = "trust-root.json"
MANIFEST_NAME = "active-source-manifest.json"
ACTIVE_RECEIPT_NAME = "ACTIVE"
_MAX_DOCUMENT_BYTES = 1024 * 1024


class PolicyKeyProvider(Protocol):
    """Retrieves a MAC key from an authenticated OS secret service."""

    def get_key(self, key_id: str) -> bytes | None: ...


class UnavailablePolicyKeyProvider:
    """Production-safe default until a Secret Service/Keel adapter is installed."""

    def get_key(self, key_id: str) -> None:
        return None


class TestPolicyKeyProvider:
    """Explicit in-memory provider for tests; never reads environment or files."""

    __test__ = False

    def __init__(self, keys: Mapping[str, bytes]):
        self._keys = dict(keys)

    def get_key(self, key_id: str) -> bytes | None:
        value = self._keys.get(key_id)
        return bytes(value) if value is not None else None


@dataclass(frozen=True)
class AnchorIdentity:
    device: int
    inode: int
    owner_uid: int


@dataclass(frozen=True)
class PolicySnapshot:
    generation_id: str
    validity: str
    anchor_identity: AnchorIdentity | None
    reason: str
    policy_version: str | None = None
    governance_content_sha256: str | None = None

    @property
    def focused(self) -> bool:
        """Focused mode is impossible in the bootstrap-only implementation."""
        return False


class PolicyLoadError(RuntimeError):
    pass


def trust_anchor_path(authoritative_config_home: Path) -> Path:
    """Derive the fixed anchor without reading XDG_CONFIG_HOME or task input."""
    return Path(authoritative_config_home).joinpath(*ANCHOR_COMPONENTS)


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def manifest_mac(document_without_mac: Mapping[str, object], key: bytes) -> str:
    return hmac.new(key, _canonical_json(document_without_mac), hashlib.sha256).hexdigest()


def install_anchor(authoritative_config_home: Path) -> Path:
    """Create the dedicated anchor for a future local Captain ceremony.

    This is never called by loading or dispatch.  Callers must be a local,
    authenticated installer and must supply the authoritative config-home.
    """
    base = Path(authoritative_config_home)
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    current = base
    for component in ANCHOR_COMPONENTS:
        current = current / component
        current.mkdir(mode=0o700, exist_ok=True)
        os.chmod(current, 0o700)
    return current


def _secure_dir(st: os.stat_result) -> bool:
    return stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid() and not (st.st_mode & 0o022)


def _open_anchor(config_home: Path) -> tuple[int, AnchorIdentity]:
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(config_home, flags)
    try:
        st = os.fstat(fd)
        if not _secure_dir(st):
            raise PolicyLoadError("insecure_config_home")
        for component in ANCHOR_COMPONENTS:
            child = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = child
            st = os.fstat(fd)
            if not _secure_dir(st):
                raise PolicyLoadError("insecure_anchor")
        return fd, AnchorIdentity(st.st_dev, st.st_ino, st.st_uid)
    except Exception:
        os.close(fd)
        raise


def _read_regular(fd: int, name: str, required_mode: int) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    child = os.open(name, flags, dir_fd=fd)
    try:
        before = os.fstat(child)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise PolicyLoadError(f"invalid_{name}")
        if stat.S_IMODE(before.st_mode) != required_mode:
            raise PolicyLoadError(f"permissions_{name}")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(child, 65536)
            if not chunk:
                break
            size += len(chunk)
            if size > _MAX_DOCUMENT_BYTES:
                raise PolicyLoadError(f"oversize_{name}")
            chunks.append(chunk)
        after = os.fstat(child)
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if identity_before != identity_after:
            raise PolicyLoadError(f"concurrent_swap_{name}")
        return b"".join(chunks), after
    finally:
        os.close(child)


def _object(raw: bytes, name: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyLoadError(f"invalid_json_{name}") from exc
    if not isinstance(value, dict):
        raise PolicyLoadError(f"invalid_shape_{name}")
    return value


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_policy_snapshot(authoritative_config_home: Path, key_provider: PolicyKeyProvider) -> PolicySnapshot:
    """Load one immutable validation snapshot; every failure is FROZEN/DENY."""
    anchor_fd = -1
    identity: AnchorIdentity | None = None
    try:
        anchor_fd, identity = _open_anchor(Path(authoritative_config_home))
        trust_raw, _ = _read_regular(anchor_fd, TRUST_ROOT_NAME, 0o600)
        manifest_raw, _ = _read_regular(anchor_fd, MANIFEST_NAME, 0o600)
        trust = _object(trust_raw, "trust_root")
        manifest = _object(manifest_raw, "manifest")
        required_root = {"policy_version", "key_id", "governance_content_sha256", "manifest_sha256"}
        required_manifest = {"policy_version", "key_id", "generation_id", "governance_content_sha256", "mac"}
        if not required_root.issubset(trust) or not required_manifest.issubset(manifest):
            raise PolicyLoadError("missing_fields")
        if not hmac.compare_digest(str(trust["manifest_sha256"]), _sha256(manifest_raw)):
            raise PolicyLoadError("manifest_hash_mismatch")
        for field in ("policy_version", "key_id", "governance_content_sha256"):
            if trust[field] != manifest[field]:
                raise PolicyLoadError(f"pinned_{field}_mismatch")
        key = key_provider.get_key(str(trust["key_id"]))
        if not key:
            raise PolicyLoadError("key_unavailable")
        signed = dict(manifest)
        supplied_mac = str(signed.pop("mac"))
        if not hmac.compare_digest(supplied_mac, manifest_mac(signed, key)):
            raise PolicyLoadError("mac_mismatch")
        # Bootstrap v1 intentionally has no receipt parser. Presence cannot grant
        # authority; even a planted ACTIVE file remains inactive.
        return PolicySnapshot(
            generation_id=str(manifest["generation_id"]), validity="FROZEN",
            anchor_identity=identity, reason="activation_receipt_unsupported",
            policy_version=str(manifest["policy_version"]),
            governance_content_sha256=str(manifest["governance_content_sha256"]),
        )
    except (OSError, PolicyLoadError, TypeError, ValueError) as exc:
        reason = exc.args[0] if isinstance(exc, PolicyLoadError) and exc.args else "anchor_unavailable"
        return PolicySnapshot("none", "DENY", identity, str(reason))
    finally:
        if anchor_fd >= 0:
            os.close(anchor_fd)


class StartupPolicyLoader:
    """Single-owner loader with atomic, fail-closed snapshot replacement."""

    def __init__(self, authoritative_config_home: Path, key_provider: PolicyKeyProvider):
        self._config_home = Path(authoritative_config_home)
        self._key_provider = key_provider
        self._lock = threading.Lock()
        self._snapshot = PolicySnapshot("none", "DENY", None, "not_loaded")
        self._anchor_identity: AnchorIdentity | None = None

    @property
    def snapshot(self) -> PolicySnapshot:
        with self._lock:
            return self._snapshot

    def reload(self) -> PolicySnapshot:
        candidate = load_policy_snapshot(self._config_home, self._key_provider)
        with self._lock:
            if candidate.anchor_identity is not None:
                if self._anchor_identity is None:
                    self._anchor_identity = candidate.anchor_identity
                elif candidate.anchor_identity != self._anchor_identity:
                    candidate = PolicySnapshot(
                        "none", "DENY", candidate.anchor_identity,
                        "anchor_identity_changed",
                    )
            self._snapshot = candidate
            return candidate
