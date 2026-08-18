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
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXACT_COMMIT = "dc6f0284831c4ef656ececbcc75acdf7c960ff9d"
ASSETS = ("plugins/kanban/dashboard/dist/index.js", "plugins/kanban/dashboard/dist/style.css")


def sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-home", action="store_true")
    args = parser.parse_args()
    canonical = Path(os.environ.get("HERMES_KANBAN_DB", Path.home() / ".hermes/kanban.db"))
    sentinel_before = {"path": str(canonical), "sha256": sha(canonical), "size": canonical.stat().st_size if canonical.exists() else None}
    home = Path(tempfile.mkdtemp(prefix="hermes-hold-drag-"))
    source = home / "exact-source"
    source.mkdir()
    archive = home / "exact-source.tar"
    with archive.open("wb") as stream:
        subprocess.run(["git", "archive", EXACT_COMMIT], cwd=ROOT, stdout=stream, check=True)
    with tarfile.open(archive) as bundle:
        bundle.extractall(source, filter="data")
    # Reuse installed dependencies without mutating the archived source tree.
    (source / "node_modules").symlink_to(ROOT / "node_modules", target_is_directory=True)
    env = os.environ.copy()
    env.update({"HERMES_HOME": str(home), "HERMES_KANBAN_BOARD": "hold-drag-review", "HERMES_KANBAN_DB": str(home / "kanban" / "boards" / "hold-drag-review" / "kanban.db"), "PYTHONPATH": str(source)})
    subprocess.run([sys.executable, str(Path(__file__).with_name("seed.py"))], cwd=source, env=env, check=True)

    # Ask the OS for a fresh loopback port; the close-to-bind interval is local and bounded.
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    log_path = home / "dashboard.log"
    log = log_path.open("wb")
    command = [sys.executable, "-m", "hermes_cli.main", "dashboard", "--host", "127.0.0.1", "--port", str(port), "--no-open", "--skip-build", "--isolated"]
    proc = subprocess.Popen(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/kanban"
    metadata = {"url": url, "pid": proc.pid, "home": str(home), "db": env["HERMES_KANBAN_DB"], "log": str(log_path), "commit": EXACT_COMMIT, "assets": {rel: hashlib.sha256(git_blob(EXACT_COMMIT, rel)).hexdigest() for rel in ASSETS}, "canonical_sentinel_before": sentinel_before, "start_command": "python tests/kanban_hold_harness/start.py"}
    (ROOT / "tests/kanban_hold_harness/live.json").write_text(json.dumps(metadata, indent=2) + "\n")
    for _ in range(1200):
        if proc.poll() is not None:
            log.close()
            raise SystemExit(f"dashboard exited {proc.returncode}; inspect {log_path}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=.1):
                break
        except OSError:
            time.sleep(.05)
    else:
        proc.terminate()
        raise SystemExit("dashboard readiness timeout")
    print(json.dumps(metadata, indent=2), flush=True)

    def stop(*_args: object) -> None:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(8)
            except subprocess.TimeoutExpired: proc.kill()
        log.close()
        after = {"path": str(canonical), "sha256": sha(canonical), "size": canonical.stat().st_size if canonical.exists() else None}
        if after != sentinel_before:
            print("CANONICAL SENTINEL CHANGED", json.dumps({"before": sentinel_before, "after": after}), file=sys.stderr)
        if not args.keep_home:
            shutil.rmtree(home, ignore_errors=True)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while proc.poll() is None:
        time.sleep(1)
    stop()


if __name__ == "__main__":
    main()
