#!/usr/bin/env python3
"""Start an exact-asset, loopback-only disposable dashboard for browser review."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys

import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HARNESS = Path(__file__).resolve().parent
EXACT_COMMIT = "27a452edfa475de1b7ec72f09ac481bbb0190164"
ASSETS = ("plugins/kanban/dashboard/dist/index.js", "plugins/kanban/dashboard/dist/style.css")


class GracefulStop(Exception):
    """Operator requested teardown after readiness."""


def sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def prepare_source(source: Path) -> None:
    """Build a light runtime view without copying caches or the whole repository.

    Python/runtime dependencies come from the invoking checkout and interpreter;
    the reviewed product assets alone are materialized byte-for-byte from the
    pinned product commit. This keeps a clean checkout reproducible even when
    the repository contains multi-gigabyte historical fixtures.
    """
    source.mkdir()
    for entry in ROOT.iterdir():
        if entry.name in {".git", ".venv", ".tmp-tests", "venv", "node_modules", "plugins", "tests"}:
            continue
        (source / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    plugins = source / "plugins"
    plugins.mkdir()
    for entry in (ROOT / "plugins").iterdir():
        if entry.name == "kanban":
            continue
        (plugins / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    kanban = plugins / "kanban"
    kanban.mkdir()
    # The dashboard plugin's Python and manifest stay on the repo-supported
    # runtime; only the reviewed browser product is pinned to EXACT_COMMIT.
    for entry in (ROOT / "plugins" / "kanban").iterdir():
        if entry.name == "dashboard":
            continue
        destination = kanban / entry.name
        if entry.is_dir():
            shutil.copytree(entry, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(entry, destination)
    dist = kanban / "dashboard" / "dist"
    dist.mkdir(parents=True)
    for rel in ASSETS:
        (dist / Path(rel).name).write_bytes(git_blob(EXACT_COMMIT, rel))

    # Dashboard discovery intentionally prefers HERMES_HOME plugins. Seed that
    # supported user-plugin surface so bundled assets from the invoking
    # checkout cannot shadow the pinned review product.
    user_dashboard = source.parent / "plugins" / "kanban" / "dashboard"
    shutil.copytree(
        ROOT / "plugins" / "kanban" / "dashboard", user_dashboard,
        ignore=shutil.ignore_patterns("dist", "node_modules", "src", "*.map"),
    )
    user_dist = user_dashboard / "dist"
    user_dist.mkdir()
    for rel in ASSETS:
        (user_dist / Path(rel).name).write_bytes(git_blob(EXACT_COMMIT, rel))


def port_state(port: int) -> dict[str, Any]:
    check = {"host": "127.0.0.1", "port": port, "connectable": False}
    with socket.socket() as sock:
        sock.settimeout(0.15)
        check["connectable"] = sock.connect_ex(("127.0.0.1", port)) == 0
    return check


def process_tree(pid: int | None) -> dict[str, Any]:
    if pid is None:
        return {"root_pid": None, "ps": []}
    completed = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,pgid=,stat=,args="], capture_output=True, text=True, check=False
    )
    rows = [line.strip() for line in completed.stdout.splitlines()]
    descendants = {pid}
    selected: list[str] = []
    changed = True
    while changed:
        changed = False
        for row in rows:
            fields = row.split(None, 4)
            if len(fields) < 4:
                continue
            row_pid, parent = int(fields[0]), int(fields[1])
            if parent in descendants and row_pid not in descendants:
                descendants.add(row_pid)
                changed = True
    for row in rows:
        fields = row.split(None, 4)
        if fields and int(fields[0]) in descendants:
            selected.append(row)
    return {"root_pid": pid, "ps": selected}


def terminate_group(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=8)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-home", action="store_true", help="always preserve the evidence home")
    parser.add_argument("--cleanup-on-exit", action="store_true", help="explicitly remove home after a successful startup")
    parser.add_argument("--home", type=Path, help="requested evidence home (must not already exist)")
    parser.add_argument("--readiness-timeout", type=float, default=120.0, help="total startup bound in seconds")
    parser.add_argument("--progress-seconds", type=float, default=5.0, help="startup heartbeat cadence")
    parser.add_argument("--exit-after-ready", action="store_true", help="stop immediately after publishing live.json")
    parser.add_argument("--backend-command", help=argparse.SUPPRESS)  # deterministic failure injection for tests
    args = parser.parse_args(argv)
    if args.readiness_timeout <= 0 or args.progress_seconds <= 0:
        parser.error("timeouts must be positive")

    live_path = HARNESS / "live.json"
    live_path.unlink(missing_ok=True)  # a prior run can never masquerade as this run
    canonical = Path(os.environ.get("HERMES_KANBAN_DB", Path.home() / ".hermes/kanban.db"))
    sentinel_before = {
        "path": str(canonical), "sha256": sha(canonical),
        "size": canonical.stat().st_size if canonical.exists() else None,
    }
    if args.home:
        home = args.home.resolve()
        home.mkdir(parents=True, exist_ok=False)
    else:
        home = Path(tempfile.mkdtemp(prefix="hermes-hold-drag-"))
    source = home / "exact-source"
    stdout_path = home / "dashboard.stdout.log"
    stderr_path = home / "dashboard.stderr.log"
    failure_path = home / "failure.json"
    phase = "export"
    command: list[str] = []
    proc: subprocess.Popen[bytes] | None = None
    port = 0
    expected_assets: dict[str, str] = {}
    success = False
    failure: BaseException | None = None

    def request_stop(_signum: int, _frame: object) -> None:
        raise GracefulStop()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    try:
        prepare_source(source)
        expected_assets = {rel: hashlib.sha256(git_blob(EXACT_COMMIT, rel)).hexdigest() for rel in ASSETS}

        phase = "runtime-check"
        check = subprocess.run(
            [sys.executable, "-c", "import fastapi, uvicorn, yaml, websockets"],
            cwd=source, capture_output=True, text=True, check=False,
        )
        if check.returncode:
            raise RuntimeError(f"runtime dependency check failed ({check.returncode}): {check.stderr.strip()}")

        env = os.environ.copy()
        env.update({
            "HERMES_HOME": str(home), "HERMES_KANBAN_BOARD": "hold-drag-review",
            "HERMES_KANBAN_DB": str(home / "kanban" / "boards" / "hold-drag-review" / "kanban.db"),
            "PYTHONPATH": str(source),
        })
        phase = "seed"
        subprocess.run([sys.executable, str(HARNESS / "seed.py")], cwd=source, env=env, check=True)
        # User dashboard plugins are intentionally opt-in. The pinned kanban
        # copy above is the sole capability enabled in this disposable home.
        (home / "config.yaml").write_text(
            "plugins:\n  enabled:\n    - kanban\n", encoding="utf-8"
        )

        phase = "port-reservation"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = int(sock.getsockname()[1])
        command = (
            args.backend_command.split() if args.backend_command else
            [sys.executable, "-m", "hermes_cli.main", "dashboard", "--host", "127.0.0.1",
             "--port", str(port), "--no-open", "--skip-build", "--isolated"]
        )
        phase = "backend-start"
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            proc = subprocess.Popen(
                command, cwd=source, env=env, stdout=stdout, stderr=stderr, start_new_session=True
            )

        url = f"http://127.0.0.1:{port}/kanban"
        deadline = time.monotonic() + args.readiness_timeout
        next_progress = time.monotonic()
        last_status = "backend-start"
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"dashboard exited before readiness with status {proc.returncode}")
            now = time.monotonic()
            if now >= next_progress:
                print(f"hold-harness phase={last_status} elapsed={args.readiness_timeout - max(0, deadline-now):.1f}s port={port}", flush=True)
                next_progress = now + args.progress_seconds
            try:
                last_status = "http"
                with urllib.request.urlopen(url, timeout=min(1.0, max(.1, deadline - now))) as response:
                    body = response.read()
                if len(body) < 256 or b"</html>" not in body.lower():
                    raise OSError("incomplete readiness body")
                last_status = "assets"
                for rel, expected in expected_assets.items():
                    plugin_path = rel.removeprefix("plugins/kanban/dashboard/")
                    asset_url = urllib.parse.urljoin(url, f"/dashboard-plugins/kanban/{plugin_path}")
                    with urllib.request.urlopen(asset_url, timeout=1.0) as response:
                        payload = response.read()
                    if hashlib.sha256(payload).hexdigest() != expected:
                        raise OSError(f"served asset hash mismatch {rel}")
                break
            except (OSError, urllib.error.URLError, TimeoutError):
                time.sleep(.1)
        else:
            phase = last_status
            raise TimeoutError(f"dashboard readiness timeout after {args.readiness_timeout:.1f}s in {last_status}")

        phase = "publish-live"
        metadata = {
            "url": url, "port": port, "pid": proc.pid, "home": str(home), "db": env["HERMES_KANBAN_DB"],
            "stdout": str(stdout_path), "stderr": str(stderr_path), "commit": EXACT_COMMIT,
            "assets": expected_assets, "canonical_sentinel_before": sentinel_before,
            "start_command": "python tests/kanban_hold_harness/start.py", "readiness_timeout": args.readiness_timeout,
        }
        atomic_json(live_path, metadata)
        print(json.dumps(metadata, indent=2), flush=True)
        success = True
        if not args.exit_after_ready:
            phase = "matrix-wait"
            while proc.poll() is None:
                time.sleep(1)
            raise RuntimeError(f"dashboard exited unexpectedly with status {proc.returncode}")
        return 0
    except GracefulStop:
        if not success:
            failure = RuntimeError("stop requested before readiness")
            atomic_json(failure_path, {
                "phase": phase, "error": str(failure), "command": command,
                "exit_status": proc.poll() if proc else None,
                "stdout": str(stdout_path), "stderr": str(stderr_path),
                "process_tree": process_tree(proc.pid if proc else None),
                "port_checks": [port_state(port)] if port else [],
                "asset_expectations": expected_assets, "home": str(home), "live_json": str(live_path),
            })
            live_path.unlink(missing_ok=True)
            return 1
        return 0
    except BaseException as exc:
        failure = exc
        tree = process_tree(proc.pid if proc else None)
        terminate_group(proc)
        record = {
            "phase": phase, "error": f"{type(exc).__name__}: {exc}", "command": command,
            "exit_status": proc.poll() if proc else None, "stdout": str(stdout_path), "stderr": str(stderr_path),
            "process_tree": tree, "port_checks": [port_state(port)] if port else [],
            "asset_expectations": expected_assets, "home": str(home), "live_json": str(live_path),
        }
        atomic_json(failure_path, record)
        live_path.unlink(missing_ok=True)
        print(f"hold-harness failed; evidence preserved at {failure_path}", file=sys.stderr, flush=True)
        return 1
    finally:
        terminate_group(proc)
        after = {
            "path": str(canonical), "sha256": sha(canonical),
            "size": canonical.stat().st_size if canonical.exists() else None,
        }
        if after != sentinel_before:
            print("CANONICAL SENTINEL CHANGED " + json.dumps({"before": sentinel_before, "after": after}), file=sys.stderr)
        # Failure evidence is immutable for this run. Success cleanup is only
        # allowed explicitly, or after matrix.js writes the run-bound marker.
        marker = home / "matrix-success.json"
        matrix_succeeded = marker.is_file() and success
        if failure is None and not args.keep_home and (args.cleanup_on_exit or matrix_succeeded):
            shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
