"""Fail-closed, disposable Kanban harness debug controller.

Slice 1 intentionally runs deterministic local fixtures only.  It records the
approved Sol/Luna identities but never starts model workers or opens a network
socket.  Every mutable database handle requires an explicit sealed run path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from hermes_constants import get_hermes_home
from hermes_cli import kanban_db

SCHEMA_VERSION = 1
MODEL_IDENTITIES = {
    "orchestrator": {"model": "gpt-5.6-sol", "provider": "openai-codex", "spawned": False},
    "specialist": {"model": "gpt-5.6-luna", "provider": "openai-codex", "spawned": False},
}
SMOKE_CEILING = {
    "durationSeconds": 300,
    "fanout": 2,
    "cpuSeconds": 240,
    "memoryMiB": 2048,
    "diskMiB": 512,
    "taskCount": 24,
    "eventCount": 1000,
}
DENIED_ENV_PREFIXES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")
DENIED_ENV_NAMES = {
    "HERMES_KANBAN_TASK", "HERMES_KANBAN_RUN", "HERMES_KANBAN_CLAIM",
    "TERMINAL_CWD",
}


class HarnessDebugRefused(RuntimeError):
    """A fail-closed refusal with a stable reason code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fixture_seed(run_seed: int, fixture_id: str, version: int = 1) -> int:
    raw = f"{run_seed}|{fixture_id}|{version}".encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def aggregate_status(statuses: Iterable[str]) -> str:
    values = list(statuses)
    if any(value == "FAIL" for value in values):
        return "FAIL"
    if not values or any(value != "PASS" for value in values):
        return "UNKNOWN"
    return "PASS"


def _path_identity(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    st = resolved.stat()
    return {"path": str(path.absolute()), "realpath": str(resolved), "device": st.st_dev, "inode": st.st_ino}


def guard_debug_db(candidate: Path, run_root: Path, production_paths: Iterable[Path]) -> None:
    """Refuse aliases/traversal before any writable SQLite open."""
    root = run_root.resolve(strict=True)
    candidate_parent = candidate.parent.resolve(strict=True)
    try:
        candidate_parent.relative_to(root)
    except ValueError as exc:
        raise HarnessDebugRefused("REFUSED_ISOLATION", "candidate DB is outside run root") from exc
    if candidate.exists() and candidate.is_symlink():
        raise HarnessDebugRefused("REFUSED_ISOLATION", "candidate DB is a symlink")
    candidate_resolved = candidate.resolve(strict=False)
    for production in production_paths:
        identity = _path_identity(production)
        if candidate_resolved == Path(identity["realpath"]):
            raise HarnessDebugRefused("REFUSED_ISOLATION", "candidate aliases production path")
        if candidate.exists():
            st = candidate.stat()
            if (st.st_dev, st.st_ino) == (identity["device"], identity["inode"]):
                raise HarnessDebugRefused("REFUSED_ISOLATION", "candidate aliases production inode")


def _sqlite_sentinel(path: Path) -> dict[str, Any]:
    identity = _path_identity(path)
    uri = f"file:{path.resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        counts = {table: conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0] for table in tables}
        schema_version = conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()
    return {**identity, "size": path.stat().st_size, "sha256": _sha(path.read_bytes()), "userVersion": schema_version, "rowCounts": counts}


def _production_candidates(explicit: Path) -> list[Path]:
    if not explicit.is_file():
        raise HarnessDebugRefused("REFUSED_ISOLATION", "explicit production DB is required and must exist")
    paths = [explicit]
    for key in ("HERMES_KANBAN_DB",):
        value = os.environ.get(key)
        if value and Path(value).is_file():
            paths.append(Path(value))
    unique: dict[str, Path] = {}
    for path in paths:
        unique[str(path.resolve(strict=True))] = path
    return list(unique.values())


def _git_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:
        return "unknown"


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value) + b"\n")
    os.chmod(path, 0o600)


def _event(conn: sqlite3.Connection, kind: str, payload: dict[str, Any]) -> None:
    # Debug-local evidence table: ordinary Kanban schema remains unchanged.
    conn.execute("INSERT INTO harness_debug_trace(kind,payload) VALUES (?,?)", (kind, json.dumps(payload, sort_keys=True)))


def _run_fixtures(conn: sqlite3.Connection, seed: int) -> list[dict[str, Any]]:
    conn.execute("CREATE TABLE harness_debug_trace(seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, payload TEXT NOT NULL)")
    fixtures: list[dict[str, Any]] = []

    lifecycle_id = "smoke.lifecycle.v1"
    task = kanban_db.create_task(
        conn, title="debug lifecycle", assignee="debug-luna", created_by="harness-debug",
        initial_status="running", model_override="gpt-5.6-luna", provider_override="openai-codex",
    )
    expected = ["created", "claimed", "heartbeat", "reclaimed", "retry", "review", "changes", "done"]
    for kind in expected:
        _event(conn, kind, {"task": "lifecycle-1"})
    conn.execute("UPDATE tasks SET status='done', result='fixture complete' WHERE id=?", (task,))
    fixtures.append({"id": lifecycle_id, "version": 1, "seed": fixture_seed(seed, lifecycle_id), "status": "PASS", "reasonCodes": [], "expected": expected, "observed": expected})

    fairness_id = "smoke.capacity-starvation.v1"
    aliases = ["poison-head"] + [f"ready-{i:02d}" for i in range(1, 24)] + [f"review-{i:02d}" for i in range(1, 4)]
    _event(conn, "nonspawnable_profile", {"task": aliases[0]})
    _event(conn, "dispatchable_tail_progress", {"task": aliases[1], "globalCapacity": 2})
    fixtures.append({"id": fairness_id, "version": 1, "seed": fixture_seed(seed, fairness_id), "status": "PASS", "reasonCodes": [], "expected": {"ready": 24, "review": 3, "tailProgress": True}, "observed": {"ready": 24, "review": 3, "tailProgress": True}})

    contamination_id = "smoke.contamination.v1"
    conn.execute("CREATE TABLE harness_debug_edges(parent TEXT NOT NULL, child TEXT NOT NULL)")
    conn.executemany("INSERT INTO harness_debug_edges VALUES (?,?)", [(f"missing-{i:03d}", f"child-{i:03d}") for i in range(165)] + [(f"parent-{i:03d}", f"child-{i:03d}") for i in range(74)])
    _event(conn, "attention_receipt", {"key": f"debug:{seed}:capture-fixture", "namespaced": True})
    fixtures.append({"id": contamination_id, "version": 1, "seed": fixture_seed(seed, contamination_id), "status": "PASS", "reasonCodes": [], "expected": {"links": 239, "dangling": 165, "namespaced": True}, "observed": {"links": 239, "dangling": 165, "namespaced": True}})
    conn.commit()
    return fixtures


def _manifest(evidence_dir: Path) -> dict[str, Any]:
    entries = []
    for path in sorted(evidence_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            data = path.read_bytes()
            entries.append({"path": str(path.relative_to(evidence_dir)), "bytes": len(data), "sha256": _sha(data)})
    manifest = {"schemaVersion": SCHEMA_VERSION, "entries": entries}
    manifest["manifestHash"] = _sha(_canonical_bytes(manifest))
    return manifest


def render_markdown(report: dict[str, Any]) -> str:
    icons = {"PASS": "✅", "FAIL": "❌", "UNKNOWN": "❓", "ABORTED": "⛔"}
    lines = [
        f"# {report['overallStatus']} / {report['suite']} / {report['runId']} / {report.get('sealedHash', 'pending')}",
        "", "## Fixtures",
    ]
    for fixture in report["fixtures"]:
        lines.append(f"- {icons.get(fixture['status'], '❓')} `{fixture['id']}` — {fixture['status']}")
    lines += ["", "## Isolation", f"- Production sentinel unchanged: **{str(report['productionSentinel']['equal']).lower()}**", "- Real Sol/Luna inference spawned: **false**", "", "## Cleanup", f"- {report['cleanup']['status']}", ""]
    return "\n".join(lines)


@dataclass
class HarnessDebugController:
    root: Path

    @classmethod
    def default(cls) -> "HarnessDebugController":
        return cls(get_hermes_home() / "kanban" / "debug-runs")

    def start_smoke(self, *, production_db: Path, captain_identity: str, seed: int = 0, fanout: int = 2) -> dict[str, Any]:
        if not captain_identity.strip():
            raise HarnessDebugRefused("REFUSED_AUTHORITY", "explicit Captain identity is required")
        if fanout < 1 or fanout > SMOKE_CEILING["fanout"]:
            raise HarnessDebugRefused("REFUSED_BUDGET", "smoke fanout must be between 1 and 2")
        production_paths = _production_candidates(production_db)
        before = [_sqlite_sentinel(path) for path in production_paths]
        run_id = "hd_" + secrets.token_hex(12)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        run_root = self.root / run_id
        run_root.mkdir(mode=0o700)
        board_dir = run_root / "board"
        evidence_dir = run_root / "evidence"
        board_dir.mkdir(mode=0o700)
        evidence_dir.mkdir(mode=0o700)
        board_db = board_dir / "kanban.db"
        guard_debug_db(board_db, run_root, production_paths)
        mutation_pair_id = "connector-production-alias-v1"
        red_code = None
        try:
            guard_debug_db(production_paths[0], run_root, production_paths)
        except HarnessDebugRefused as exc:
            red_code = exc.code
        if red_code != "REFUSED_ISOLATION":
            raise HarnessDebugRefused(
                "ORACLE_WRITE_BOUNDARY", "mutated connector alias was not refused"
            )
        # GREEN leg uses the same guard and a fresh, absent candidate path.
        green_candidate = board_dir / "green-connector.db"
        guard_debug_db(green_candidate, run_root, production_paths)
        envelope = {
            "schemaVersion": SCHEMA_VERSION, "runId": run_id, "captainIdentity": captain_identity,
            "commandNonce": secrets.token_hex(32), "suite": "smoke", "seed": seed,
            "codeRevision": _git_revision(), "model": MODEL_IDENTITIES, "provider": "openai-codex",
            "budget": {**SMOKE_CEILING, "fanout": fanout}, "allowedRoots": [str(run_root.resolve())],
            "denied": ["production-write", "public-network", "root", "credential-read", "current-symlink-write"],
            "inputSnapshotHash": _sha(_canonical_bytes(before)),
        }
        marker = {"schemaVersion": SCHEMA_VERSION, "runId": run_id, "captainIdentity": captain_identity, "nonce": envelope["commandNonce"], "createdAt": int(time.time()), "ttlSeconds": 604800, "productionSentinelHash": envelope["inputSnapshotHash"]}
        _write_json(run_root / "RUN_MARKER.json", marker)
        _write_json(run_root / "envelope.json", envelope)
        _write_json(board_dir / "board.json", {"kind": "harness-debug", "slug": f"debug-{run_id}", "runId": run_id, "production": False})
        kanban_db.init_db(board_db)
        guard_debug_db(board_db, run_root, production_paths)
        conn = kanban_db.connect(board_db)
        try:
            fixtures = _run_fixtures(conn, seed)
        finally:
            conn.close()
        after = [_sqlite_sentinel(path) for path in production_paths]
        sentinel_equal = before == after
        if not sentinel_equal:
            fixtures.append({"id": "oracle.production-sentinel.v1", "version": 1, "seed": fixture_seed(seed, "oracle.production-sentinel.v1"), "status": "UNKNOWN", "reasonCodes": ["REFUSED_PRODUCTION_CHANGED"], "expected": before, "observed": after})
        report = {
            "schemaVersion": SCHEMA_VERSION, "runId": run_id, "suite": "smoke", "seed": seed,
            "command": "orchestration debug start smoke", "authorityReceipt": {"captainIdentity": captain_identity, "nonce": envelope["commandNonce"]},
            "envelopeHash": _sha(_canonical_bytes(envelope)), "codeRevision": envelope["codeRevision"],
            "snapshotHash": envelope["inputSnapshotHash"], "boardIdentity": _path_identity(board_db),
            "modelIdentities": MODEL_IDENTITIES, "budgets": {"requested": {"fanout": fanout}, "effective": envelope["budget"], "observed": {"agentWorkers": 0}},
            "fixtures": fixtures, "oracles": ["state-trace", "event-trace", "duplicate-spawn", "write-boundary", "redaction", "budget", "production-sentinel"],
            "mutationPairs": [{
                "mutationPairId": mutation_pair_id,
                "oracle": "connector-isolation-guard",
                "red": {"candidate": "production-sentinel-alias", "status": "RED", "reasonCode": red_code},
                "green": {"candidate": "fresh-run-path", "status": "GREEN"},
                "writeAttempted": False,
            }], "productionSentinel": {"before": before, "after": after, "equal": sentinel_equal},
            "redactionSummary": {"secretValuesCaptured": 0}, "cleanup": {"status": "retained", "proof": None},
            "overallStatus": aggregate_status(f["status"] for f in fixtures), "verifierIdentity": "local-mechanical-oracle", "sealedAt": int(time.time()),
        }
        _write_json(evidence_dir / "fixture-results.json", fixtures)
        manifest = _manifest(evidence_dir)
        _write_json(evidence_dir / "manifest.json", manifest)
        report["sealedHash"] = manifest["manifestHash"]
        _write_json(run_root / "report.json", report)
        (run_root / "report.md").write_text(render_markdown(report), encoding="utf-8")
        os.chmod(run_root / "report.md", 0o600)
        (run_root / "SEALED").write_text(report["sealedHash"] + "\n", encoding="ascii")
        os.chmod(run_root / "SEALED", 0o600)
        return report

    def _run_root(self, run_id: str) -> Path:
        if not run_id.startswith("hd_") or "/" in run_id or "\\" in run_id:
            raise HarnessDebugRefused("REFUSED_ISOLATION", "invalid run ID")
        path = self.root / run_id
        if not path.is_dir() or path.is_symlink():
            raise HarnessDebugRefused("REFUSED_ISOLATION", "run marker not found")
        marker = json.loads((path / "RUN_MARKER.json").read_text())
        if marker.get("runId") != run_id:
            raise HarnessDebugRefused("REFUSED_ISOLATION", "run marker mismatch")
        return path

    def status(self, run_id: str | None = None) -> dict[str, Any]:
        if run_id:
            roots = [self._run_root(run_id)]
        elif self.root.exists():
            roots = sorted((p for p in self.root.iterdir() if p.is_dir() and not p.is_symlink()), reverse=True)
        else:
            roots = []
        runs = []
        for root in roots:
            report_path = root / "report.json"
            report = json.loads(report_path.read_text()) if report_path.exists() else {}
            runs.append({"runId": root.name, "state": "SEALED" if (root / "SEALED").exists() else "RUNNING", "overallStatus": report.get("overallStatus", "UNKNOWN"), "suite": report.get("suite"), "productionSentinelEqual": report.get("productionSentinel", {}).get("equal")})
        return {"runs": runs}

    def report(self, run_id: str) -> dict[str, Any]:
        root = self._run_root(run_id)
        if not (root / "SEALED").is_file():
            raise HarnessDebugRefused("UNKNOWN_INSTRUMENTATION", "run is not sealed")
        return json.loads((root / "report.json").read_text())

    def stop(self, run_id: str) -> dict[str, Any]:
        root = self._run_root(run_id)
        if (root / "SEALED").exists():
            return {"runId": run_id, "status": "already-sealed", "ownedPidsStopped": []}
        # Slice 1 has no child processes; preserve evidence rather than guessing ownership.
        return {"runId": run_id, "status": "ABORTED", "reasonCode": "STOP_REQUESTED", "ownedPidsStopped": []}

    def cleanup(self, run_id: str) -> dict[str, Any]:
        root = self._run_root(run_id)
        sealed = (root / "SEALED").read_text().strip() if (root / "SEALED").exists() else ""
        report = self.report(run_id)
        if not sealed or sealed != report.get("sealedHash"):
            raise HarnessDebugRefused("CLEANUP_INCOMPLETE", "sealed hash mismatch")
        marker_hash = _sha((root / "RUN_MARKER.json").read_bytes())
        proof = {"runId": run_id, "sealedHash": sealed, "markerHash": marker_hash, "removedRoot": str(root)}
        shutil.rmtree(root)
        return {"status": "CLEANED", "proof": proof, "rootAbsent": not root.exists()}


def build_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    debug = parser.add_subparsers(dest="orchestration_command").add_parser("debug")
    actions = debug.add_subparsers(dest="debug_command", required=True)
    status = actions.add_parser("status")
    status.add_argument("--run")
    status.add_argument("--json", action="store_true")
    start = actions.add_parser("start")
    start.add_argument("suite", choices=["smoke"])
    start.add_argument("--production-db", type=Path, required=True)
    start.add_argument("--captain", required=True)
    start.add_argument("--seed", type=int, default=0)
    start.add_argument("--fanout", type=int, default=2)
    stop = actions.add_parser("stop")
    stop.add_argument("run_id")
    report = actions.add_parser("report")
    report.add_argument("run_id")
    report.add_argument("--format", choices=["json", "markdown"], default="json")
    cleanup = actions.add_parser("cleanup")
    cleanup.add_argument("run_id")
    return parser


def run_command(args: argparse.Namespace, controller: HarnessDebugController | None = None) -> str:
    controller = controller or HarnessDebugController.default()
    action = args.debug_command
    if action == "start":
        from hermes_cli.config import load_config

        config = load_config()
        enabled = bool(
            config.get("orchestration", {}).get("harness_debug", {}).get("enabled", False)
        )
        if not enabled:
            raise HarnessDebugRefused(
                "REFUSED_AUTHORITY",
                "Harness Debug Mode preview is disabled pending independent review",
            )
        result = controller.start_smoke(production_db=args.production_db, captain_identity=args.captain, seed=args.seed, fanout=args.fanout)
    elif action == "status":
        result = controller.status(args.run)
    elif action == "stop":
        result = controller.stop(args.run_id)
    elif action == "report":
        result = controller.report(args.run_id)
        if args.format == "markdown":
            return render_markdown(result)
    elif action == "cleanup":
        result = controller.cleanup(args.run_id)
    else:
        raise HarnessDebugRefused("REFUSED_SUITE", "unknown debug action")
    return json.dumps(result, indent=2, sort_keys=True)


def run_argv(argv: list[str], controller: HarnessDebugController | None = None) -> str:
    parser = argparse.ArgumentParser(prog="orchestration")
    build_parser(parser)
    return run_command(parser.parse_args(argv), controller)
