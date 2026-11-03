"""stats-dashboard plugin: ``/stats`` opens omp's trace dashboard over this profile's Hermes sessions.

``/stats`` exports changed sessions (``exporter``), starts or reuses one ``omp stats`` server on an
isolated config root (``dashboard``) and opens — or, where no browser can be opened, prints — the
Traces page for the current session. ``/stats stop`` stops that server, ``/stats status`` shows it,
``/stats export`` only exports.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any, Optional

from . import dashboard, exporter

logger = logging.getLogger(__name__)

_HELP = """/stats — trace dashboard (omp stats) for this profile's Hermes sessions

  /stats            export changed sessions, start/reuse the dashboard, open this session's trace
  /stats status     show the dashboard URL if it is running
  /stats export     export only (no server)
  /stats stop       stop the dashboard this plugin started
"""

# Surfaces that run on the user's desktop; elsewhere (ACP editors, messaging) the URL is returned.
_BROWSER_PLATFORMS = {"cli", "tui", "gui"}

_export_lock = threading.Lock()
_backlog: Optional[threading.Thread] = None


class _Settings:
    def __init__(self, ctx: Any):
        self._ctx = ctx

    def get(self, key: str, default: Any) -> Any:
        try:
            value = self._ctx.get_config(key, default)
        except Exception:
            return default
        return default if value is None else value


def _hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return Path(get_hermes_home())
    except Exception:
        return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")


def _profile_of(home: Path) -> tuple[Path, str]:
    """``(hermes root, profile name)`` for a profile home (``<root>/profiles/<name>`` or the root)."""
    if home.parent.name == "profiles":
        return home.parent.parent, home.name
    return home, "default"


def _sources(home: Path, all_profiles: bool) -> list[exporter.HermesStateSource]:
    root, profile = _profile_of(home)
    if all_profiles:
        return exporter.hermes_sources(root, profile, all_profiles=True)
    return [exporter.HermesStateSource(home / "state.db", profile)]


def _run_export(sources, out: Path, max_chars: int, only_keys=None) -> exporter.ExportReport:
    with _export_lock:
        try:
            return exporter.export(sources, out, only_keys=only_keys, max_chars=max_chars)
        finally:
            for source in sources:
                source.close()


def _start_backlog(home: Path, all_profiles: bool, out: Path, max_chars: int, host: str, port: int) -> bool:
    """Export every remaining session on a worker thread, then ask the dashboard to re-sync."""
    global _backlog
    if _backlog is not None and _backlog.is_alive():
        return True

    def work() -> None:
        try:
            report = _run_export(_sources(home, all_profiles), out, max_chars)
            logger.info("stats-dashboard backlog export: %s", report.summary())
            dashboard.request_sync(host, port)
        except Exception:
            logger.warning("stats-dashboard backlog export failed", exc_info=True)

    _backlog = threading.Thread(target=work, name="stats-dashboard-export", daemon=True)
    _backlog.start()
    return True


def _open_browser(url: str, platform: Optional[str]) -> bool:
    if (platform or "cli") not in _BROWSER_PLATFORMS:
        return False
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False
    try:
        return bool(webbrowser.open(url, new=2))
    except Exception:
        return False


def _cmd_open(settings: _Settings, args: list[str], session_id: str, platform: Optional[str]) -> str:
    home = _hermes_home()
    root = dashboard.config_root(home)
    out = dashboard.sessions_dir(root)
    host = str(settings.get("host", dashboard.DEFAULT_HOST))
    port = int(settings.get("port", dashboard.DEFAULT_PORT))
    max_chars = int(settings.get("max_chars", exporter.DEFAULT_MAX_CHARS))
    all_profiles = bool(settings.get("all_profiles", False)) or "--all-profiles" in args
    omp = dashboard.find_omp(settings.get("omp", None) or None)
    if omp is None:
        return dashboard.INSTALL_HINT

    lines: list[str] = []
    first_run = not exporter.state_file(out).exists()
    sources = _sources(home, all_profiles)
    key = (f"{_profile_of(home)[1]}:{session_id}" if all_profiles else session_id) if session_id else None
    if first_run and key:
        # A first export of a large state.db takes a while: write this session's tree now and the
        # backlog on a worker thread, so the trace opens without waiting for history.
        refs = [r for s in sources for r in s.scan()]
        report = _run_export(sources, out, max_chars, only_keys=exporter.session_tree_keys(refs, key))
        _start_backlog(home, all_profiles, out, max_chars, host, port)
        lines.append(f"Exported this session ({report.written} files); exporting the other "
                     f"{max(report.scanned - report.written, 0)} sessions in the background.")
    else:
        report = _run_export(sources, out, max_chars)
        lines.append(f"Export: {report.summary()}")

    try:
        state, started = dashboard.ensure_server(root, omp, host=host, port=port)
    except dashboard.DashboardError as exc:
        return "\n".join(lines + [f"Dashboard not started: {exc}"])
    dashboard.request_sync(host, port)

    session_file = report.paths.get(key) if key else None
    url = dashboard.trace_url(host, port, session_file)
    opened = _open_browser(url, platform) if settings.get("open_browser", True) else False
    lines.insert(0, f"{'Opened' if opened else 'Trace dashboard'}: {url}")
    if session_file is None and session_id:
        lines.append("This session is not in state.db yet; showing the overview.")
    lines.append(f"omp stats pid {state.pid} on {host}:{port} ({'started' if started else 'reused'}); "
                 "/stats stop stops it.")
    return "\n".join(lines)


def _cmd_status(settings: _Settings) -> str:
    root = dashboard.config_root(_hermes_home())
    state = dashboard.server_status(root)
    if state is None:
        return "Trace dashboard is not running. /stats starts it."
    return f"Trace dashboard: {dashboard.trace_url(state.host, state.port)} (omp stats pid {state.pid})"


def _cmd_stop() -> str:
    pid = dashboard.stop_server(dashboard.config_root(_hermes_home()))
    return f"Stopped the trace dashboard (pid {pid})." if pid else "No trace dashboard was running."


def _cmd_export(settings: _Settings, args: list[str]) -> str:
    home = _hermes_home()
    out = dashboard.sessions_dir(dashboard.config_root(home))
    all_profiles = bool(settings.get("all_profiles", False)) or "--all-profiles" in args
    max_chars = int(settings.get("max_chars", exporter.DEFAULT_MAX_CHARS))
    return f"Export: {_run_export(_sources(home, all_profiles), out, max_chars).summary()}"


def make_handler(ctx: Any):
    settings = _Settings(ctx)

    def handle(raw_args: str = "", session_id: str = "", platform: Optional[str] = None, **_: Any) -> str:
        args = (raw_args or "").split()
        sub = args[0].lower() if args and not args[0].startswith("--") else ""
        if sub in {"help", "-h"}:
            return _HELP
        if sub == "stop":
            return _cmd_stop()
        if sub == "status":
            return _cmd_status(settings)
        if sub == "export":
            return _cmd_export(settings, args)
        if sub:
            return f"Unknown /stats subcommand: {sub}\n\n{_HELP}"
        return _cmd_open(settings, args, session_id or "", platform)

    return handle


def register(ctx) -> None:
    ctx.register_command("stats", handler=make_handler(ctx),
                         description="Open the trace dashboard (omp stats) for this session",
                         args_hint="[status|export|stop]")
