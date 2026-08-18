"""Security boundary for disposable, local-only Kanban harness runs.

Gateway activation is deliberately unavailable. Local execution requires an
HMAC-authenticated, single-use operator receipt and only runs isolated smoke
fixtures. All run bytes are sealed and revalidated before report or cleanup.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import hmac
import json
import os
import secrets
import shutil
import socket
import sqlite3
import stat
import subprocess
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from hermes_constants import get_hermes_home
from hermes_cli import kanban_db

SCHEMA_VERSION = 2
POLICY_REVISION = "harness-debug-local-v2"
POLICY_HASH = "sha256:" + hashlib.sha256(POLICY_REVISION.encode()).hexdigest()
SMOKE_CEILING = {"durationSeconds": 300, "fanout": 2, "taskCount": 24, "eventCount": 1000}
MODEL_IDENTITIES = {
    "orchestrator": {"model": "gpt-5.6-sol", "provider": "openai-codex", "spawned": False},
    "specialist": {"model": "gpt-5.6-luna", "provider": "openai-codex", "spawned": False},
}

class HarnessDebugRefused(RuntimeError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")

def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()

def _write(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush(); os.fsync(stream.fileno())

def _write_json(path: Path, value: Any) -> None:
    _write(path, _canonical(value) + b"\n")

_MANIFEST_EXCLUDED = {"manifest.json", "SEALED", ".run.lock", ".cleanup.lock"}

def _canonical_relpath(value: object) -> str:
    """Return the sole accepted spelling of a run-relative POSIX path."""
    if not isinstance(value, str) or not value or value in {".", ".."}:
        raise ValueError("empty or dot path")
    if "\\" in value or value.startswith("/") or "\x00" in value:
        raise ValueError("non-relative POSIX path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("non-canonical component")
    normalized = unicodedata.normalize("NFC", value)
    if normalized != value:
        raise ValueError("non-NFC path")
    return value

def _open_regular_at(root_fd: int, relative: str) -> tuple[int, os.stat_result]:
    """Open a regular file by walking beneath root_fd without following links."""
    relative = _canonical_relpath(relative)
    current = os.dup(root_fd)
    try:
        for component in relative.split("/")[:-1]:
            nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = nxt
        fd = os.open(relative.split("/")[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            os.close(fd)
            raise ValueError("manifest entry is not regular")
        return fd, st
    finally:
        os.close(current)

def _read_regular_at(root_fd: int, relative: str) -> tuple[bytes, os.stat_result]:
    fd, before = _open_regular_at(root_fd, relative)
    try:
        chunks = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mode) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mode
        ):
            raise ValueError("entry identity changed while hashing")
        return b"".join(chunks), after
    finally:
        os.close(fd)

def fixture_seed(run_seed: int, fixture_id: str, version: int = 1) -> int:
    return int.from_bytes(hashlib.sha256(f"{run_seed}|{fixture_id}|{version}".encode()).digest()[:8], "big")

def aggregate_status(statuses: Iterable[str]) -> str:
    values = list(statuses)
    if any(v in {"FAIL", "TAMPERED"} for v in values): return "FAIL"
    if not values or any(v != "PASS" for v in values): return "UNKNOWN"
    return "PASS"

def make_local_receipt(key: bytes, *, production_db: Path, nonce: str, now: int | None = None,
                       seed: int = 0, fanout: int = 2, operator: str = "local-operator") -> dict[str, Any]:
    issued = int(time.time()) if now is None else now
    body = {"schemaVersion": SCHEMA_VERSION, "surface": "cli-local", "operator": operator,
            "nonce": nonce, "mode": "isolated-nondestructive", "suite": "smoke",
            "budget": {"fanout": fanout}, "seed": seed,
            "productionDb": str(production_db.resolve()), "policyRevision": POLICY_REVISION,
            "policyHash": POLICY_HASH, "issuedAt": issued, "expiresAt": issued + 300}
    return {**body, "signature": hmac.new(key, _canonical(body), hashlib.sha256).hexdigest()}

def _verify_receipt(receipt: dict[str, Any], key: bytes, *, production_db: Path, seed: int, fanout: int,
                    consumed: Path, now: int | None = None) -> None:
    now = int(time.time()) if now is None else now
    signature = receipt.get("signature", "")
    body = {k: v for k, v in receipt.items() if k != "signature"}
    expected = hmac.new(key, _canonical(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(signature), expected):
        raise HarnessDebugRefused("REFUSED_AUTHORITY", "forged local operator receipt")
    required = {"surface": "cli-local", "mode": "isolated-nondestructive", "suite": "smoke",
                "productionDb": str(production_db.resolve()), "seed": seed,
                "budget": {"fanout": fanout}, "policyRevision": POLICY_REVISION, "policyHash": POLICY_HASH}
    if any(body.get(k) != v for k, v in required.items()):
        raise HarnessDebugRefused("REFUSED_AUTHORITY", "receipt scope mismatch")
    if not isinstance(body.get("operator"), str) or not body["operator"].strip():
        raise HarnessDebugRefused("REFUSED_AUTHORITY", "operator identity missing")
    if body.get("issuedAt", now + 1) > now or body.get("expiresAt", 0) < now:
        raise HarnessDebugRefused("REFUSED_AUTHORITY", "receipt expired or not yet valid")
    nonce = body.get("nonce")
    if not isinstance(nonce, str) or len(nonce) < 32:
        raise HarnessDebugRefused("REFUSED_AUTHORITY", "invalid nonce")
    consumed.mkdir(parents=True, exist_ok=True, mode=0o700)
    try: _write(consumed / nonce, _sha(_canonical(body)).encode())
    except FileExistsError as exc: raise HarnessDebugRefused("REFUSED_REPLAY", "receipt nonce already consumed") from exc

def _identity(path: Path) -> dict[str, Any]:
    real = path.resolve(strict=True); st = real.stat()
    return {"path": str(path.absolute()), "realpath": str(real), "device": st.st_dev,
            "inode": st.st_ino, "bytes": st.st_size, "sha256": _sha(real.read_bytes())}

def guard_debug_db(candidate: Path, run_root: Path, production_paths: Iterable[Path]) -> None:
    root = run_root.resolve(strict=True)
    parent = candidate.parent.resolve(strict=True)
    try: parent.relative_to(root)
    except ValueError as exc: raise HarnessDebugRefused("REFUSED_ISOLATION", "outside run root") from exc
    # Walk every existing component without following links.
    current = Path(root.anchor)
    for part in candidate.absolute().parts[1:]:
        current /= part
        if current.exists() and current.is_symlink():
            raise HarnessDebugRefused("REFUSED_ISOLATION", "symlink component")
    target = candidate.resolve(strict=False)
    for production in production_paths:
        ident = _identity(production)
        if target == Path(ident["realpath"]): raise HarnessDebugRefused("REFUSED_ISOLATION", "production alias")
        if candidate.exists():
            st = candidate.stat(follow_symlinks=False)
            if (st.st_dev, st.st_ino) == (ident["device"], ident["inode"]):
                raise HarnessDebugRefused("REFUSED_ISOLATION", "production inode alias")

def _git_revision() -> str:
    try: return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception: return "unknown"

def _sentinel(path: Path) -> dict[str, Any]:
    result = _identity(path)
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        result["tasks"] = [tuple(row) for row in conn.execute("SELECT id,status,assignee,current_run_id FROM tasks ORDER BY id")]
        result["events"] = [tuple(row) for row in conn.execute("SELECT id,task_id,kind,run_id FROM task_events ORDER BY id")]
    finally: conn.close()
    return result

def _trace(conn: sqlite3.Connection, task: str) -> list[str]:
    return [row[0] for row in conn.execute("SELECT kind FROM task_events WHERE task_id=? ORDER BY id", (task,))]

def _behavior_fixture(db: Path, seed: int, mutation: bool = False,
                      identity_check=lambda: None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    identity_check()
    kanban_db.init_db(db); conn = kanban_db.connect(db)
    try:
        identity_check()
        parent = kanban_db.create_task(conn, title="parent", assignee="debug-sol", created_by="fixture", initial_status="running")
        identity_check()
        child = kanban_db.create_task(conn, title="child", assignee="debug-luna", created_by="fixture", parents=[parent], initial_status="running")
        # Fixture setup places both records at the dispatch boundary. The actual
        # dependency rejection and all lifecycle transitions below use public
        # Kanban APIs and their persisted events.
        conn.execute("UPDATE tasks SET status='ready', claim_lock=NULL, claim_expires=NULL WHERE id IN (?,?)", (parent, child))
        conn.commit()
        identity_check()
        blocked_claim = kanban_db.claim_task(conn, child, claimer="fixture")
        claimed = kanban_db.claim_task(conn, parent, claimer="fixture")
        run_id = claimed.current_run_id if claimed else None
        review_ok = kanban_db.request_review(conn, parent, summary="fixture", reviewer="reviewer", expected_run_id=run_id)
        reviewed = kanban_db.claim_review_task(conn, parent, claimer="reviewer")
        done = kanban_db.complete_task(conn, parent, summary="approved", expected_run_id=reviewed.current_run_id if reviewed else None)
        identity_check()
        child_status = conn.execute("SELECT status FROM tasks WHERE id=?", (child,)).fetchone()[0]
        if mutation: child_status = "ready" if child_status != "ready" else "todo"
        observed = {"blockedChildClaim": blocked_claim is None, "parentClaimed": claimed is not None,
                    "reviewRequested": bool(review_ok), "reviewClaimed": reviewed is not None,
                    "parentCompleted": bool(done), "childPromoted": child_status == "ready",
                    "eventKinds": _trace(conn, parent)}
        expected = {"blockedChildClaim": True, "parentClaimed": True, "reviewRequested": True,
                    "reviewClaimed": True, "parentCompleted": True, "childPromoted": True}
        failures = [key for key, value in expected.items() if observed.get(key) != value]
        result = {"id": "behavior.lifecycle-dependency.v2", "version": 2,
                  "seed": fixture_seed(seed, "behavior.lifecycle-dependency.v2"),
                  "status": "FAIL" if failures else "PASS", "reasonCodes": failures,
                  "expected": expected, "observed": observed}
        rows = [dict(row) for row in conn.execute("SELECT id,status,assignee,current_run_id FROM tasks ORDER BY id")]
        return result, rows
    finally: conn.close()

def _manifest(root: Path, key: bytes) -> dict[str, Any]:
    entries = []
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        seen: set[str] = set()
        aliases: set[str] = set()
        for path in sorted(root.rglob("*")):
            relative = _canonical_relpath(path.relative_to(root).as_posix())
            if path.name in _MANIFEST_EXCLUDED:
                continue
            if path.is_symlink():
                raise HarnessDebugRefused("TAMPERED", "symlink in run evidence")
            if not path.is_file():
                continue
            alias = unicodedata.normalize("NFC", relative).casefold()
            if relative in seen or alias in aliases:
                raise HarnessDebugRefused("TAMPERED", "duplicate or ambiguous manifest path")
            seen.add(relative); aliases.add(alias)
            data, st = _read_regular_at(root_fd, relative)
            entries.append({"path": relative, "bytes": len(data), "sha256": _sha(data),
                            "device": st.st_dev, "inode": st.st_ino, "mode": stat.S_IMODE(st.st_mode)})
    finally:
        os.close(root_fd)
    base = {"schemaVersion": SCHEMA_VERSION, "algorithm": "sha256", "entries": entries}
    manifest_hash = _sha(_canonical(base))
    return {**base, "manifestHash": manifest_hash,
            "authTag": hmac.new(key, manifest_hash.encode(), hashlib.sha256).hexdigest()}

def _verify(root: Path, key: bytes) -> dict[str, Any]:
    root_fd = -1
    try:
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        manifest_data, _ = _read_regular_at(root_fd, "manifest.json")
        seal_data, _ = _read_regular_at(root_fd, "SEALED")
        manifest = json.loads(manifest_data)
        base = {k: manifest[k] for k in ("schemaVersion", "algorithm", "entries")}
        if _sha(_canonical(base)) != manifest.get("manifestHash"): raise ValueError("manifest hash")
        expected_tag = hmac.new(key, manifest["manifestHash"].encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(str(manifest.get("authTag", "")), expected_tag): raise ValueError("manifest authentication")
        if seal_data.decode().strip() != manifest["manifestHash"]: raise ValueError("seal")
        expected_paths: set[str] = set(); aliases: set[str] = set()
        for entry in manifest["entries"]:
            relative = _canonical_relpath(entry.get("path"))
            alias = unicodedata.normalize("NFC", relative).casefold()
            if relative in expected_paths or alias in aliases: raise ValueError("duplicate or ambiguous path")
            expected_paths.add(relative); aliases.add(alias)
        actual_paths = {_canonical_relpath(p.relative_to(root).as_posix()) for p in root.rglob("*")
                        if p.is_file() and not p.is_symlink() and p.name not in _MANIFEST_EXCLUDED}
        if expected_paths != actual_paths: raise ValueError("entry set")
        for entry in manifest["entries"]:
            data, st = _read_regular_at(root_fd, entry["path"])
            if len(data) != entry["bytes"] or _sha(data) != entry["sha256"]: raise ValueError(entry["path"])
            if (st.st_dev, st.st_ino, stat.S_IMODE(st.st_mode)) != (entry["device"], entry["inode"], entry["mode"]):
                raise ValueError(f"identity changed: {entry['path']}")
        os.close(root_fd)
        return manifest
    except Exception as exc:
        try:
            if root_fd >= 0: os.close(root_fd)
        except Exception: pass
        raise HarnessDebugRefused("TAMPERED", f"sealed run verification failed: {exc}") from exc

def render_markdown(report: dict[str, Any]) -> str:
    return f"# {report['overallStatus']} / {report['suite']} / {report['runId']}\n\n- Production unchanged: **{str(report['productionSentinel']['equal']).lower()}**\n- Real Sol/Luna spawned: **false**\n"

@dataclass
class HarnessDebugController:
    root: Path
    @classmethod
    def default(cls): return cls(get_hermes_home() / "kanban" / "debug-runs")

    def _key_path(self, run_id: str) -> Path:
        return self.root / ".manifest-keys" / run_id

    def _manifest_key(self, run_id: str) -> bytes:
        path = self._key_path(run_id)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                st = os.fstat(fd)
                if not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600:
                    raise HarnessDebugRefused("TAMPERED", "manifest key protection changed")
                return os.read(fd, 33)
            finally:
                os.close(fd)
        except OSError as exc:
            raise HarnessDebugRefused("TAMPERED", "manifest key unavailable") from exc

    @staticmethod
    def _create_pinned_db(board_fd: int, board_path: Path, name: str) -> tuple[int, Path, tuple[int, int]]:
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=board_fd)
        st = os.fstat(fd)
        return fd, board_path / name, (st.st_dev, st.st_ino)

    def start_smoke(self, *, production_db: Path, receipt: dict[str, Any], authority_key: bytes,
                    seed: int = 0, fanout: int = 2) -> dict[str, Any]:
        if not production_db.is_file(): raise HarnessDebugRefused("REFUSED_ISOLATION", "production DB required")
        if not 1 <= fanout <= 2: raise HarnessDebugRefused("REFUSED_BUDGET", "fanout outside smoke ceiling")
        if self.root.is_symlink(): raise HarnessDebugRefused("REFUSED_ISOLATION", "debug root is a symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = self.root / ".create.lock"
        with open(lock_path, "a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            _verify_receipt(receipt, authority_key, production_db=production_db, seed=seed, fanout=fanout,
                            consumed=self.root / ".consumed")
            before = _sentinel(production_db)
            run_id = "hd_" + secrets.token_hex(12); run = self.root / run_id
            os.mkdir(run, 0o700); os.mkdir(run / "board", 0o700); os.mkdir(run / "evidence", 0o700)
            key_dir = self.root / ".manifest-keys"
            key_dir.mkdir(mode=0o700, exist_ok=True)
            _write(self._key_path(run_id), secrets.token_bytes(32))
        board_dir_fd = os.open(run / "board", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        green_fd = red_fd = -1
        try:
            green_fd, board, green_identity = self._create_pinned_db(board_dir_fd, run / "board", "green.db")
            red_fd, red, red_identity = self._create_pinned_db(board_dir_fd, run / "board", "red.db")
            production_identity = _identity(production_db)
            if green_identity == (production_identity["device"], production_identity["inode"]) or red_identity == (production_identity["device"], production_identity["inode"]):
                raise HarnessDebugRefused("REFUSED_ISOLATION", "production inode alias")
            def check(fd: int, name: str, expected: tuple[int, int]) -> None:
                fst = os.fstat(fd)
                lst = os.stat(name, dir_fd=board_dir_fd, follow_symlinks=False)
                if not stat.S_ISREG(lst.st_mode) or (fst.st_dev, fst.st_ino) != expected or (lst.st_dev, lst.st_ino) != expected:
                    raise HarnessDebugRefused("REFUSED_ISOLATION", f"debug DB identity changed: {name}")
            red_result, red_rows = _behavior_fixture(red, seed, mutation=True,
                                                       identity_check=lambda: check(red_fd, "red.db", red_identity))
            green_result, green_rows = _behavior_fixture(board, seed, mutation=False,
                                                           identity_check=lambda: check(green_fd, "green.db", green_identity))
            check(red_fd, "red.db", red_identity); check(green_fd, "green.db", green_identity)
        finally:
            if green_fd >= 0: os.close(green_fd)
            if red_fd >= 0: os.close(red_fd)
            os.close(board_dir_fd)
        after = _sentinel(production_db)
        envelope = {"schemaVersion": SCHEMA_VERSION, "runId": run_id, "receipt": receipt,
                    "suite": "smoke", "seed": seed, "budget": {**SMOKE_CEILING, "fanout": fanout},
                    "policyRevision": POLICY_REVISION, "policyHash": POLICY_HASH,
                    "codeRevision": _git_revision(), "fixtureVersion": 2, "oracleVersion": 2,
                    "productionSnapshotHash": _sha(_canonical(before)), "networkPolicy": "deny"}
        marker = {"runId": run_id, "nonce": receipt["nonce"], "createdAt": int(time.time())}
        report = {"schemaVersion": SCHEMA_VERSION, "runId": run_id, "suite": "smoke",
                  "overallStatus": aggregate_status([green_result["status"], "PASS" if red_result["status"] == "FAIL" else "FAIL"]),
                  "fixtures": [green_result], "mutationPairs": [{"oracle": "lifecycle-independent-v2",
                  "red": red_result, "green": green_result}], "productionSentinel": {"before": before, "after": after, "equal": before == after},
                  "modelIdentities": MODEL_IDENTITIES, "budgets": {"observed": {"agentWorkers": 0}},
                  "security": {"gatewayEnabled": False, "networkDenied": True, "secretCanaryObserved": False},
                  "envelopeHash": _sha(_canonical(envelope)), "cleanup": {"status": "retained"}}
        if not report["productionSentinel"]["equal"]: report["overallStatus"] = "FAIL"
        _write_json(run / "RUN_MARKER.json", marker); _write_json(run / "envelope.json", envelope)
        _write_json(run / "evidence" / "red-trace.json", red_rows); _write_json(run / "evidence" / "green-trace.json", green_rows)
        _write_json(run / "report.json", report); _write(run / "report.md", render_markdown(report).encode())
        manifest_key = self._manifest_key(run_id)
        manifest = _manifest(run, manifest_key); _write_json(run / "manifest.json", manifest); _write(run / "SEALED", (manifest["manifestHash"] + "\n").encode())
        _verify(run, manifest_key)
        return report

    def _run(self, run_id: str) -> Path:
        if not run_id.startswith("hd_") or any(c in run_id for c in "/\\"):
            raise HarnessDebugRefused("REFUSED_ISOLATION", "invalid run ID")
        run = self.root / run_id
        if not run.is_dir() or run.is_symlink(): raise HarnessDebugRefused("REFUSED_ISOLATION", "run missing")
        return run
    def report(self, run_id: str) -> dict[str, Any]:
        run = self._run(run_id); _verify(run, self._manifest_key(run_id)); return json.loads((run / "report.json").read_text())
    def status(self, run_id: str | None = None) -> dict[str, Any]:
        roots = [self._run(run_id)] if run_id else ([p for p in self.root.glob("hd_*") if p.is_dir() and not p.is_symlink()] if self.root.exists() else [])
        result=[]
        for root in roots:
            try: report=self.report(root.name); result.append({"runId":root.name,"state":"SEALED","overallStatus":report["overallStatus"]})
            except HarnessDebugRefused: result.append({"runId":root.name,"state":"TAMPERED","overallStatus":"FAIL"})
        return {"runs":result}
    def stop(self, run_id: str) -> dict[str, Any]: self.report(run_id); return {"runId":run_id,"status":"already-sealed","ownedPidsStopped":[]}
    def cleanup(self, run_id: str) -> dict[str, Any]:
        run=self._run(run_id)
        with open(run / ".cleanup.lock", "a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX); manifest=_verify(run, self._manifest_key(run_id))
            return {"runId":run_id,"status":"RETAINED_SEALED","sealedHash":manifest["manifestHash"],"idempotent":True}

def build_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    debug=parser.add_subparsers(dest="orchestration_command").add_parser("debug"); actions=debug.add_subparsers(dest="debug_command",required=True)
    start=actions.add_parser("start"); start.add_argument("suite",choices=["smoke"]); start.add_argument("--production-db",type=Path,required=True); start.add_argument("--receipt",type=Path,required=True); start.add_argument("--authority-key",type=Path,required=True); start.add_argument("--seed",type=int,default=0); start.add_argument("--fanout",type=int,default=2)
    status=actions.add_parser("status"); status.add_argument("--run"); status.add_argument("--json",action="store_true")
    stop=actions.add_parser("stop"); stop.add_argument("run_id")
    report=actions.add_parser("report"); report.add_argument("run_id"); report.add_argument("--format",choices=["json","markdown"],default="json")
    cleanup=actions.add_parser("cleanup"); cleanup.add_argument("run_id")
    return parser

def run_command(args: argparse.Namespace, controller: HarnessDebugController | None=None) -> str:
    controller=controller or HarnessDebugController.default(); action=args.debug_command
    if action=="start":
        key=args.authority_key.read_bytes()
        if len(key)<32 or (args.authority_key.stat().st_mode & 0o077): raise HarnessDebugRefused("REFUSED_AUTHORITY","authority key must be >=32 bytes and mode 0600")
        result=controller.start_smoke(production_db=args.production_db,receipt=json.loads(args.receipt.read_text()),authority_key=key,seed=args.seed,fanout=args.fanout)
    elif action=="status": result=controller.status(args.run)
    elif action=="stop": result=controller.stop(args.run_id)
    elif action=="report":
        result=controller.report(args.run_id)
        if args.format=="markdown": return render_markdown(result)
    elif action=="cleanup": result=controller.cleanup(args.run_id)
    else: raise HarnessDebugRefused("REFUSED_SUITE","unknown action")
    return json.dumps(result,indent=2,sort_keys=True)

def run_argv(argv:list[str],controller:HarnessDebugController|None=None)->str:
    parser=argparse.ArgumentParser(prog="orchestration"); build_parser(parser); return run_command(parser.parse_args(argv),controller)
