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
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXACT_COMMIT = "27a452edfa475de1b7ec72f09ac481bbb0190164"
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
    expected_assets = {rel: hashlib.sha256(git_blob(EXACT_COMMIT, rel)).hexdigest() for rel in ASSETS}
    metadata = {"url": url, "pid": proc.pid, "home": str(home), "db": env["HERMES_KANBAN_DB"], "log": str(log_path), "commit": EXACT_COMMIT, "assets": expected_assets, "canonical_sentinel_before": sentinel_before, "start_command": "python tests/kanban_hold_harness/start.py"}
    ready = False
    for _ in range(1200):
        if proc.poll() is not None:
            log.close()
            shutil.rmtree(home, ignore_errors=True)
            raise SystemExit(f"dashboard exited {proc.returncode}; inspect {log_path}")
        try:
            with urllib.request.urlopen(url, timeout=.5) as response:
                body = response.read()
            if len(body) < 256 or b"</html>" not in body.lower():
                raise OSError("incomplete readiness body")
            for rel, expected in expected_assets.items():
                plugin_path = rel.removeprefix("plugins/kanban/dashboard/")
                asset_url = urllib.parse.urljoin(url, f"/dashboard-plugins/kanban/{plugin_path}")
                with urllib.request.urlopen(asset_url, timeout=.5) as response:
                    actual = hashlib.sha256(response.read()).hexdigest()
                if actual != expected:
                    raise OSError(f"served asset hash mismatch {rel}")
            ready = True
            break
        except (OSError, urllib.error.URLError):
            time.sleep(.05)
    if not ready:
        proc.terminate()
        proc.wait(8)
        log.close()
        shutil.rmtree(home, ignore_errors=True)
        raise SystemExit("dashboard readiness timeout")
    live_path = ROOT / "tests/kanban_hold_harness/live.json"
    live_tmp = live_path.with_suffix(".json.tmp")
    live_tmp.write_text(json.dumps(metadata, indent=2) + "\n")
    os.replace(live_tmp, live_path)
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
