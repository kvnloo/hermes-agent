"""Inactive, sealed trust bootstrap for focused orchestration policy.

Nothing in this module activates focused mode or changes the live dispatcher.  The
production entry point accepts launcher-owned state only; policy paths, key
providers, and envelope contents are not caller-selectable.
"""
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import stat
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Mapping, Protocol

ANCHOR_COMPONENTS = ("hermes", "orchestration-policy")
TRUST_ROOT_NAME = "trust-root.json"
MANIFEST_NAME = "active-source-manifest.json"
ACTIVE_RECEIPT_NAME = "ACTIVE"
_MAX_DOCUMENT_BYTES = 1024 * 1024
_REQUIRED_SEALS = (
    getattr(fcntl, "F_SEAL_SEAL", 0)
    | getattr(fcntl, "F_SEAL_SHRINK", 0)
    | getattr(fcntl, "F_SEAL_GROW", 0)
    | getattr(fcntl, "F_SEAL_WRITE", 0)
)
_STARTUP_FD_ENV = "HERMES_POLICY_ENVELOPE_FD"


class PolicyLoadError(RuntimeError):
    pass


class _PolicyKeyProvider(Protocol):
    def get_key(self, key_id: str) -> bytes | None: ...


class _KeelSecretServiceProvider:
    """Closed production provider seam; deliberately unavailable until Keel ships."""

    def get_key(self, key_id: str) -> None:
        return None


class _TestPolicyKeyProvider:
    def __init__(self, keys: Mapping[str, bytes]):
        self._keys = dict(keys)

    def get_key(self, key_id: str) -> bytes | None:
        value = self._keys.get(key_id)
        return bytes(value) if value is not None else None


@dataclass(frozen=True)
class FileIdentity:
    device: int
    inode: int
    owner_uid: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int
    link_count: int


@dataclass(frozen=True)
class PolicyBootstrapEnvelope:
    anchor_device: int
    anchor_inode: int
    trust_root_sha256: str
    governance_content_sha256: str
    governance_version: str
    key_id: str
    nonce: str
    generation: int
    effective_at: int
    expires_at: int
    mac: str


@dataclass(frozen=True)
class PolicySnapshot:
    reload_generation: int
    envelope_generation: int
    validity: str
    reason: str
    anchor_device: int | None = None
    anchor_inode: int | None = None
    governance_version: str | None = None
    governance_content_sha256: str | None = None
    receipt_binding_sha256: str | None = None

    @property
    def focused(self) -> bool:
        return False


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def envelope_mac(document_without_mac: Mapping[str, object], key: bytes) -> str:
    return hmac.new(key, _canonical_json(document_without_mac), hashlib.sha256).hexdigest()


def manifest_mac(document_without_mac: Mapping[str, object], key: bytes) -> str:
    return envelope_mac(document_without_mac, key)


def trust_anchor_path(hermes_home: Path) -> Path:
    return Path(hermes_home).joinpath(*ANCHOR_COMPONENTS)


def install_anchor(hermes_home: Path) -> Path:
    """Test/ceremony helper only; loading never creates or mutates the anchor."""
    current = Path(hermes_home)
    current.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(current, 0o700)
    for component in ANCHOR_COMPONENTS:
        current = current / component
        current.mkdir(mode=0o700, exist_ok=True)
        os.chmod(current, 0o700)
    return current


def _identity(st: os.stat_result) -> FileIdentity:
    return FileIdentity(st.st_dev, st.st_ino, st.st_uid, stat.S_IMODE(st.st_mode), st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_nlink)


def _secure_dir(st: os.stat_result) -> bool:
    return stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o700


def _open_chain(home: Path) -> tuple[list[int], list[FileIdentity]]:
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fds: list[int] = []
    try:
        fd = os.open(home, flags)
        fds.append(fd)
        for component in ANCHOR_COMPONENTS:
            fd = os.open(component, flags, dir_fd=fd)
            fds.append(fd)
        identities = []
        for fd in fds:
            st = os.fstat(fd)
            if not _secure_dir(st):
                raise PolicyLoadError("insecure_anchor_component")
            identities.append(_identity(st))
        return fds, identities
    except Exception:
        for fd in reversed(fds):
            os.close(fd)
        raise


def _same_open_chain(home: Path, expected: list[FileIdentity]) -> bool:
    fds, identities = _open_chain(home)
    try:
        return identities == expected
    finally:
        for fd in reversed(fds):
            os.close(fd)


def _open_final_pair(
    anchor_fd: int,
    expected: Mapping[str, tuple[FileIdentity, str]],
    order: tuple[str, str],
) -> list[int]:
    """Open the whole named set before validating any member of the set.

    The returned descriptors are authority-bearing pins and remain owned by the
    caller until snapshot publication has completed.
    """
    opened: dict[str, tuple[bytes, FileIdentity, int]] = {}
    try:
        for name in order:
            opened[name] = _read_regular(anchor_fd, name)
        # Both names are now pinned.  Validate bytes, complete descriptor stats,
        # and the two current no-follow directory entries as one pair phase.
        for name in (TRUST_ROOT_NAME, MANIFEST_NAME):
            raw, identity, fd = opened[name]
            wanted_identity, wanted_digest = expected[name]
            if identity != wanted_identity:
                raise PolicyLoadError(f"pathname_replaced_{name}")
            if hashlib.sha256(raw).hexdigest() != wanted_digest:
                raise PolicyLoadError(f"pathname_content_changed_{name}")
            if _identity(os.fstat(fd)) != wanted_identity:
                raise PolicyLoadError(f"pathname_changed_{name}")
        for name in (TRUST_ROOT_NAME, MANIFEST_NAME):
            entry = os.stat(name, dir_fd=anchor_fd, follow_symlinks=False)
            if _identity(entry) != expected[name][0]:
                raise PolicyLoadError(f"directory_entry_changed_{name}")
        # Revisit both open descriptors after both directory entries were read.
        for name in (TRUST_ROOT_NAME, MANIFEST_NAME):
            if _identity(os.fstat(opened[name][2])) != expected[name][0]:
                raise PolicyLoadError(f"pair_changed_{name}")
        return [opened[TRUST_ROOT_NAME][2], opened[MANIFEST_NAME][2]]
    except Exception:
        for _, _, fd in opened.values():
            os.close(fd)
        raise


def _read_regular(anchor_fd: int, name: str) -> tuple[bytes, FileIdentity, int]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(name, flags, dir_fd=anchor_fd)
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or stat.S_IMODE(before.st_mode) != 0o600:
        os.close(fd)
        raise PolicyLoadError(f"invalid_{name}")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        total += len(chunk)
        if total > _MAX_DOCUMENT_BYTES:
            os.close(fd)
            raise PolicyLoadError(f"oversize_{name}")
        chunks.append(chunk)
    after = os.fstat(fd)
    if _identity(before) != _identity(after) or total != after.st_size:
        os.close(fd)
        raise PolicyLoadError(f"concurrent_change_{name}")
    return b"".join(chunks), _identity(after), fd


def _read_sealed_envelope(fd: int) -> bytes:
    if fd < 3:
        raise PolicyLoadError("invalid_envelope_descriptor")
    access = fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE
    if access != os.O_RDONLY:
        raise PolicyLoadError("envelope_not_read_only")
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_size > _MAX_DOCUMENT_BYTES:
        raise PolicyLoadError("invalid_envelope_descriptor")
    try:
        seals = fcntl.fcntl(fd, fcntl.F_GET_SEALS)
    except OSError as exc:
        raise PolicyLoadError("envelope_not_sealed") from exc
    if _REQUIRED_SEALS and seals & _REQUIRED_SEALS != _REQUIRED_SEALS:
        raise PolicyLoadError("envelope_not_sealed")
    before = _identity(st)
    raw = os.pread(fd, st.st_size + 1, 0)
    if len(raw) != st.st_size or _identity(os.fstat(fd)) != before:
        raise PolicyLoadError("envelope_changed")
    return raw


def _object(raw: bytes, name: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyLoadError(f"invalid_json_{name}") from exc
    if not isinstance(value, dict):
        raise PolicyLoadError(f"invalid_shape_{name}")
    return value


def _parse_envelope(raw: bytes, provider: _PolicyKeyProvider, now: int) -> PolicyBootstrapEnvelope:
    value = _object(raw, "envelope")
    fields = {"anchor_device", "anchor_inode", "trust_root_sha256", "governance_content_sha256", "governance_version", "key_id", "nonce", "generation", "effective_at", "expires_at", "mac"}
    if set(value) != fields:
        raise PolicyLoadError("invalid_envelope_fields")
    supplied = str(value.pop("mac"))
    key = provider.get_key(str(value["key_id"]))
    if not key or not hmac.compare_digest(supplied, envelope_mac(value, key)):
        raise PolicyLoadError("envelope_authentication_failed")
    envelope = PolicyBootstrapEnvelope(**value, mac=supplied)  # type: ignore[arg-type]
    if envelope.generation < 1 or not envelope.nonce:
        raise PolicyLoadError("invalid_envelope_generation")
    if now < envelope.effective_at or now >= envelope.expires_at:
        raise PolicyLoadError("envelope_outside_validity")
    return envelope


def _receipt_binding(envelope: PolicyBootstrapEnvelope, manifest_sha256: str) -> str:
    """Consume the approved K3 tuple; this is binding evidence, not authority."""
    return hashlib.sha256(_canonical_json({
        "anchor_device": envelope.anchor_device,
        "anchor_inode": envelope.anchor_inode,
        "generation": envelope.generation,
        "governance_content_sha256": envelope.governance_content_sha256,
        "governance_version": envelope.governance_version,
        "manifest_sha256": manifest_sha256,
        "nonce": envelope.nonce,
        "trust_root_sha256": envelope.trust_root_sha256,
    })).hexdigest()


def _load_candidate(home: Path, envelope_fd: int, provider: _PolicyKeyProvider, now: int) -> tuple[PolicySnapshot, list[int]]:
    fds: list[int] = []
    document_fds: list[int] = []
    try:
        envelope = _parse_envelope(_read_sealed_envelope(envelope_fd), provider, now)
        fds, chain = _open_chain(home)
        anchor = chain[-1]
        if (anchor.device, anchor.inode) != (envelope.anchor_device, envelope.anchor_inode):
            raise PolicyLoadError("anchor_pin_mismatch")
        trust_raw, trust_identity, trust_fd = _read_regular(fds[-1], TRUST_ROOT_NAME)
        manifest_raw, manifest_identity, manifest_fd = _read_regular(fds[-1], MANIFEST_NAME)
        document_fds.extend((trust_fd, manifest_fd))
        if hashlib.sha256(trust_raw).hexdigest() != envelope.trust_root_sha256:
            raise PolicyLoadError("trust_root_hash_mismatch")
        trust = _object(trust_raw, "trust_root")
        manifest = _object(manifest_raw, "manifest")
        manifest_hash = hashlib.sha256(manifest_raw).hexdigest()
        required = {"governance_content_sha256", "governance_version", "manifest_sha256", "key_id"}
        if not required.issubset(trust):
            raise PolicyLoadError("invalid_trust_root")
        if str(trust["manifest_sha256"]) != manifest_hash:
            raise PolicyLoadError("manifest_hash_mismatch")
        for field in ("governance_content_sha256", "governance_version", "key_id"):
            if str(trust[field]) != str(getattr(envelope, field)):
                raise PolicyLoadError(f"envelope_{field}_mismatch")
        signed = dict(manifest)
        supplied = str(signed.pop("mac", ""))
        key = provider.get_key(envelope.key_id)
        if not key or not hmac.compare_digest(supplied, manifest_mac(signed, key)):
            raise PolicyLoadError("manifest_authentication_failed")
        if str(signed.get("governance_content_sha256")) != envelope.governance_content_sha256 or str(signed.get("governance_version")) != envelope.governance_version:
            raise PolicyLoadError("manifest_governance_mismatch")
        # Revalidate every original descriptor, then resolve and reread both
        # final pathnames from the anchor immediately before publication.
        if _identity(os.fstat(trust_fd)) != trust_identity or _identity(os.fstat(manifest_fd)) != manifest_identity:
            raise PolicyLoadError("document_changed_before_publish")
        expected = {
            TRUST_ROOT_NAME: (trust_identity, hashlib.sha256(trust_raw).hexdigest()),
            MANIFEST_NAME: (manifest_identity, manifest_hash),
        }
        # Opposing open orders close both inter-document windows.  The first
        # pair remains pinned while the second pair and final component checks
        # run; every descriptor survives until the caller commits the snapshot.
        document_fds.extend(_open_final_pair(fds[-1], expected, (TRUST_ROOT_NAME, MANIFEST_NAME)))
        document_fds.extend(_open_final_pair(fds[-1], expected, (MANIFEST_NAME, TRUST_ROOT_NAME)))
        if [_identity(os.fstat(fd)) for fd in fds] != chain or not _same_open_chain(home, chain):
            raise PolicyLoadError("anchor_changed_before_publish")
        snapshot = PolicySnapshot(0, envelope.generation, "FROZEN", "activation_unsupported", anchor.device, anchor.inode, envelope.governance_version, envelope.governance_content_sha256, _receipt_binding(envelope, manifest_hash))
        pinned = document_fds
        document_fds = []
        return snapshot, pinned
    finally:
        for fd in reversed(document_fds):
            os.close(fd)
        for fd in reversed(fds):
            os.close(fd)


class _StartupPolicyLoader:
    def __init__(self, home: Path, envelope_fd: int, provider: _PolicyKeyProvider, *, clock: Callable[[], int] = lambda: int(time.time())):
        self._home = Path(home)
        self._envelope_fd = envelope_fd
        self._provider = provider
        self._clock = clock
        self._lock = threading.Lock()
        self._next_generation = 0
        self._published_generation = 0
        self._snapshot = PolicySnapshot(0, 0, "DENY", "not_loaded")

    @property
    def snapshot(self) -> PolicySnapshot:
        with self._lock:
            return self._snapshot

    def reload(self, *, after_validate: Callable[[], None] | None = None) -> PolicySnapshot:
        with self._lock:
            self._next_generation += 1
            generation = self._next_generation
            pinned: list[int] = []
            try:
                candidate, pinned = _load_candidate(self._home, self._envelope_fd, self._provider, self._clock())
            except (OSError, PolicyLoadError, TypeError, ValueError) as exc:
                reason = exc.args[0] if isinstance(exc, PolicyLoadError) and exc.args else "bootstrap_unavailable"
                candidate = PolicySnapshot(generation, 0, "DENY", str(reason))
            else:
                candidate = replace(candidate, reload_generation=generation)
            try:
                if after_validate:
                    after_validate()
                self._published_generation = generation
                self._snapshot = candidate
                return candidate
            finally:
                for fd in reversed(pinned):
                    os.close(fd)


def _seal_startup_boundary() -> Callable[[], _StartupPolicyLoader]:
    """Capture launcher facts once and return a zero-input boundary."""
    raw_home = os.environ.get("HERMES_HOME")
    raw_fd = os.environ.get(_STARTUP_FD_ENV)
    home = Path(raw_home).resolve() if raw_home else None
    provider = _KeelSecretServiceProvider()
    try:
        envelope_fd = int(raw_fd) if raw_fd is not None else -1
    except ValueError:
        envelope_fd = -1

    def create() -> _StartupPolicyLoader:
        if home is None or envelope_fd < 3:
            raise PolicyLoadError("launcher_bootstrap_unavailable")
        return _StartupPolicyLoader(home, envelope_fd, provider)

    return create


_create_from_sealed_startup = _seal_startup_boundary()
del _seal_startup_boundary


def create_startup_policy_loader() -> _StartupPolicyLoader:
    """Create from the launcher's immutable startup capture only."""
    return _create_from_sealed_startup()


def create_test_policy_loader(home: Path, envelope_fd: int, keys: Mapping[str, bytes], *, production: bool, clock: Callable[[], int]) -> _StartupPolicyLoader:
    if production:
        raise PolicyLoadError("test_provider_forbidden_in_production")
    return _StartupPolicyLoader(home, envelope_fd, _TestPolicyKeyProvider(keys), clock=clock)


class _FocusedPolicyFixture:
    """Disposable adapter over real create/promote/claim/spawn callables.

    It captures one startup snapshot.  Production never constructs this fixture;
    it exists to prove all four mutation surfaces use the same immutable decision.
    """

    def __init__(self, snapshot: PolicySnapshot, surfaces: Mapping[str, Callable[[], object]], *, active: bool):
        self._snapshot = snapshot
        self._surfaces = dict(surfaces)
        self._active = active

    @property
    def startup_snapshot(self) -> PolicySnapshot:
        return self._snapshot

    def invoke(self, surface: str) -> object:
        if surface not in {"create", "promote", "claim", "spawn"}:
            raise ValueError("unknown policy surface")
        if not self._active:
            raise PermissionError(f"focused policy denied {surface}: {self._snapshot.reason}")
        return self._surfaces[surface]()


def create_test_surface_fixture(
    snapshot: PolicySnapshot,
    surfaces: Mapping[str, Callable[[], object]],
    *,
    active: bool,
    production: bool,
) -> _FocusedPolicyFixture:
    """Build the disposable proof harness; it cannot enter production."""
    if production:
        raise PolicyLoadError("test_surface_fixture_forbidden_in_production")
    return _FocusedPolicyFixture(snapshot, surfaces, active=active)
