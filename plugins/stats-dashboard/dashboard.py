"""Run one ``omp stats`` dashboard over the Hermes export, isolated from the user's own omp data.

omp resolves every path (``stats.db``, the sessions dir, logs) from ``PI_CONFIG_DIR`` (relative to
``$HOME``) and ``PI_CODING_AGENT_DIR``, its native addon cache from ``PI_NATIVES_DIR``; with XDG
variables set it may redirect to ``$XDG_*_HOME/omp``. The child therefore gets its own config root under the Hermes profile home and
no XDG/profile variables, so it can never read or write ``~/.omp``.

The server is tracked by a ``server.json`` (pid, port) next to the export: a live pid answering
``/api/status`` is reused, anything else on the port is reported, never killed.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import quote

DEFAULT_PORT = 3858  # omp's own dashboard defaults to 3847
DEFAULT_HOST = "127.0.0.1"
DASHBOARD_HEADER = "x-omp-stats-dashboard"
INSTALL_HINT = ("omp is not installed (the dashboard is omp's `omp stats`). Install it with "
                "`bun install -g @oh-my-pi/pi-coding-agent`, or set "
                "plugins.entries.stats-dashboard.settings.omp to the omp executable.")
_SCRUBBED_ENV = ("XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "OMP_PROFILE", "PI_PROFILE",
                 "PI_CONFIG_DIR", "PI_CODING_AGENT_DIR", "PI_NATIVES_DIR")


class DashboardError(RuntimeError):
    """A dashboard problem the user should read (missing omp, busy port, failed start)."""


def config_root(hermes_home: Path) -> Path:
    """omp config root for this profile's export (holds ``stats.db`` and ``agent/sessions``)."""
    return Path(hermes_home) / "omp-stats"


def sessions_dir(root: Path) -> Path:
    return Path(root) / "agent" / "sessions"


def omp_env(root: Path, base: Optional[dict] = None) -> dict:
    """Environment that pins omp's config root and agent dir to ``root``."""
    env = dict(os.environ if base is None else base)
    for key in _SCRUBBED_ENV:
        env.pop(key, None)
    # omp joins PI_CONFIG_DIR onto $HOME lexically (node path.join), so the relative path is
    # computed lexically too: resolving symlinks on one side only would point somewhere else.
    home = os.path.abspath(env.get("HOME") or str(Path.home()))
    absolute = os.path.abspath(root)
    env["PI_CONFIG_DIR"] = os.path.relpath(absolute, home)
    env["PI_CODING_AGENT_DIR"] = os.path.join(absolute, "agent")
    # The compiled omp extracts its native addon into the natives dir on every launch (~110 MB once).
    env["PI_NATIVES_DIR"] = os.path.join(absolute, "natives")
    return env


def find_omp(configured: Optional[str] = None) -> Optional[str]:
    if configured:
        path = shutil.which(configured) or (configured if Path(configured).is_file() else None)
        return path
    return shutil.which("omp")


def trace_url(host: str, port: int, session_file: Optional[Path] = None) -> str:
    base = f"http://{host}:{port}/"
    if session_file is None:
        return base + "#/overview?range=all"
    return base + f"#/traces?range=all&s={quote(str(session_file), safe='')}"


def _get(url: str, timeout: float = 2.0) -> Optional[tuple[dict, object]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read()
            return dict(resp.headers), json.loads(body or b"null")
    except (urllib.error.URLError, OSError, ValueError):
        return None


def probe(host: str, port: int) -> Optional[dict]:
    """``/api/status`` of an omp dashboard on ``host:port``, or None if nothing omp answers."""
    got = _get(f"http://{host}:{port}/api/status")
    if not got:
        return None
    headers, body = got
    lowered = {k.lower(): v for k, v in headers.items()}
    if DASHBOARD_HEADER not in lowered or not isinstance(body, dict):
        return None
    return body


def request_sync(host: str, port: int) -> bool:
    req = urllib.request.Request(f"http://{host}:{port}/api/sync", method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=5):
            return True
    except (urllib.error.URLError, OSError):
        return False


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # A zombie still answers kill(0); treat it as gone.
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as fh:
            return fh.read().split(") ", 1)[1][:1] != "Z"
    except (OSError, IndexError):
        return True


@dataclass
class ServerState:
    pid: int
    port: int
    host: str
    root: str

    @classmethod
    def read(cls, root: Path) -> Optional[ServerState]:
        try:
            data = json.loads((Path(root) / "server.json").read_text(encoding="utf-8"))
            return cls(int(data["pid"]), int(data["port"]), str(data["host"]), str(data["root"]))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def write(self) -> None:
        path = Path(self.root) / "server.json"
        path.write_text(json.dumps(self.__dict__), encoding="utf-8")


def server_status(root: Path) -> Optional[ServerState]:
    """The tracked server if its pid is alive and it answers as an omp dashboard."""
    state = ServerState.read(root)
    if state and _pid_alive(state.pid) and probe(state.host, state.port) is not None:
        return state
    return None


def ensure_server(root: Path, omp: str, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                  wait_s: float = 30.0) -> tuple[ServerState, bool]:
    """Reuse the tracked dashboard or start one; returns ``(state, started_now)``."""
    root = Path(root)
    state = server_status(root)
    if state and state.port == port and state.host == host:
        return state, False
    if state:
        stop_server(root)
    if probe(host, port) is not None or _port_open(host, port):
        raise DashboardError(
            f"Port {host}:{port} is already in use by another process; set "
            "plugins.entries.stats-dashboard.settings.port to a free port.")
    root.mkdir(parents=True, exist_ok=True)
    sessions_dir(root).mkdir(parents=True, exist_ok=True)
    log_path = root / "server.log"
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(
            [omp, "stats", "--port", str(port), "--host", host],
            cwd=root, env=omp_env(root), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True)
    state = ServerState(proc.pid, port, host, str(root))
    state.write()
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise DashboardError(f"omp stats exited with code {proc.returncode}:\n{_tail(log_path)}")
        if probe(host, port) is not None:
            return state, True
        time.sleep(0.25)
    raise DashboardError(f"omp stats did not answer on {host}:{port} within {wait_s:.0f}s:\n{_tail(log_path)}")


def stop_server(root: Path, wait_s: float = 5.0) -> Optional[int]:
    """Stop the tracked server by its recorded pid (never by name); returns the pid stopped."""
    state = ServerState.read(root)
    if state is None:
        return None
    (Path(root) / "server.json").unlink(missing_ok=True)
    if not _pid_alive(state.pid) or not _is_omp_process(state.pid):
        return None
    os.kill(state.pid, signal.SIGTERM)
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline and _pid_alive(state.pid):
        time.sleep(0.1)
    if _pid_alive(state.pid):
        os.kill(state.pid, signal.SIGKILL)
    return state.pid


def _is_omp_process(pid: int) -> bool:
    """Guard against a recycled pid: the recorded process must still be an ``omp stats``."""
    try:
        argv = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    except OSError:
        return True  # no /proc (macOS): trust the recorded pid
    return b"stats" in argv and any(Path(a.decode(errors="ignore")).name.startswith("omp") for a in argv if a)


def _port_open(host: str, port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _tail(path: Path, lines: int = 15) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""
