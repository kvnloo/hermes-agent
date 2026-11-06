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

from . import dashboard, exporter, trace_query

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


# ---------------------------------------------------------------- trace_query / trace_resolve

_TRACE_QUERY_SCHEMA = {
    "name": "trace_query",
    "description": (
        "Ask the /stats trace data (this profile's Hermes sessions, via omp stats) a question. Returns a compact "
        "analysis (summary, tools with p50/p95, longest spans, failures, idle gaps, per-track cost; every row has "
        "its span id) and render.handle, an interactive board of cards over the same data. Show the board by "
        "calling html_render with html=<render.handle> exactly (plus render.title and render.height); never "
        "paste tables the board already shows. Use for: why a session was slow, which tools failed, what "
        "subagents cost, comparing sessions, cost by model, what happened in a session. Pass focus ids or "
        "a ref from an earlier @trace: selection to zoom in."),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The user's question; picks intent, range and layers."},
            "intent": {"type": "string", "enum": list(trace_query.INTENT_IDS),
                       "description": "Override the intent picked from the question."},
            "session": {"type": "string", "description": (
                "current (default, this session), latest / previous (newest other sessions), 'last 2', "
                "or a Hermes session id like 20261102_190234_62cb5b.")},
            "range": {"type": "string", "enum": list(trace_query.RANGES),
                      "description": "Range for dashboard-wide numbers (tools, errors, cost). Default from question."},
            "layers": {"type": "array", "items": {"type": "string", "enum": list(trace_query.LAYERS)},
                       "description": "Card layers: spans, tokens, cost, errors, subagents, transcript."},
            "focus": {"type": "array", "items": {"type": "string"},
                      "description": "Span ids (or tool:<name>) from an earlier result or selection to detail."},
            "focus_range": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2,
                            "description": "[startMs, endMs] epoch window to summarise."},
            "ref": {"type": "string", "description": "An @trace:v0;... reference the user pasted; sets session/focus."},
            "tool": {"type": "string", "description": "Limit the tool rows to this tool."},
            "plan": {"type": "object", "description": "A trace-query.v0 plan (q, intent, scope, layers) instead."},
            "top": {"type": "integer", "description": "Rows per list (3-20, default 8)."},
            "render": {"type": "boolean", "description": "Build the board (default true)."},
        },
    },
}

_TRACE_RESOLVE_SCHEMA = {
    "name": "trace_resolve",
    "description": (
        "Expand an @trace:v0;... reference (what the user copies from a /stats board) or explicit span ids into "
        "details: each span with its journal entry (model, usage, text excerpt, tool args), tool rows, and a "
        "summary of a selected time range. Use when a message carries an @trace: reference that was not "
        "already expanded, or to look closer at ids from trace_query."),
    "parameters": {
        "type": "object",
        "properties": {
            "ref": {"type": "string", "description": "The @trace:v0;s=...;ids=... reference, verbatim."},
            "session": {"type": "string", "description": "Session id when passing ids without a ref."},
            "ids": {"type": "array", "items": {"type": "string"}, "description": "Span ids or tool:<name>."},
            "range": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2},
        },
    },
}


def _template_path(settings: _Settings, home: Path) -> Path:
    configured = settings.get("inline_template", None)
    return Path(configured).expanduser() if configured else dashboard.config_root(home) / "stats-inline.html"


def _renders_dir(home: Path) -> Path:
    return dashboard.config_root(home) / "renders"


def _prepare(settings: _Settings, session_id: str, need_history: bool):
    """Export (this session's tree, or everything changed), start/reuse the dashboard; returns
    ``(StatsApi, SessionIndex)``."""
    home = _hermes_home()
    root = dashboard.config_root(home)
    out = dashboard.sessions_dir(root)
    host = str(settings.get("host", dashboard.DEFAULT_HOST))
    port = int(settings.get("port", dashboard.DEFAULT_PORT))
    max_chars = int(settings.get("max_chars", exporter.DEFAULT_MAX_CHARS))
    all_profiles = bool(settings.get("all_profiles", False))
    omp = dashboard.find_omp(settings.get("omp", None) or None)
    if omp is None:
        raise trace_query.TraceQueryError(dashboard.INSTALL_HINT)
    sources = _sources(home, all_profiles)
    key = (f"{_profile_of(home)[1]}:{session_id}" if all_profiles else session_id) if session_id else None
    first_run = not exporter.state_file(out).exists()
    if key and (first_run or not need_history):
        refs = [r for s in sources for r in s.scan()]
        _run_export(sources, out, max_chars, only_keys=exporter.session_tree_keys(refs, key))
        if first_run:
            _start_backlog(home, all_profiles, out, max_chars, host, port)
    else:
        _run_export(sources, out, max_chars)
    try:
        state, _ = dashboard.ensure_server(root, omp, host=host, port=port)
    except dashboard.DashboardError as exc:
        raise trace_query.TraceQueryError(f"dashboard not started: {exc}") from exc
    dashboard.request_sync(state.host, state.port)
    api = trace_query.StatsApi(state.host, state.port)
    return api, trace_query.SessionIndex.load(out, exporter.state_file(out))


def _json(data: Any) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)


def make_trace_query(ctx: Any):
    settings = _Settings(ctx)

    def handle(args: dict, session_id: str = "", **_: Any) -> str:
        try:
            q = trace_query.Query.from_args(args)
            need_history = q.session != "current" or q.intent in ("compare_sessions",)
            api, index = _prepare(settings, session_id or "", need_history)
            home = _hermes_home()
            template = _template_path(settings, home)
            return _json(trace_query.run_query(q, api, index, session_id or "", _renders_dir(home),
                                               template if settings.get("render", True) else None))
        except trace_query.TraceQueryError as exc:
            return _json({"error": str(exc)})

    return handle


def make_trace_resolve(ctx: Any):
    settings = _Settings(ctx)

    def handle(args: dict, session_id: str = "", **_: Any) -> str:
        try:
            if args.get("ref"):
                ref = trace_query.parse_ref(str(args["ref"]))
            else:
                ref = trace_query.parse_ref("@trace:" + ";".join(
                    ["v0", f"s={args.get('session') or session_id}", "k=ids",
                     "ids=" + ",".join(str(i) for i in args.get("ids") or [])]
                    + ([f"r={int(args['range'][0])}-{int(args['range'][1])}"] if args.get("range") else [])))
            api, index = _prepare(settings, session_id or "", ref["s"] != session_id)
            return _json(trace_query.resolve(api, index, ref))
        except (trace_query.TraceQueryError, ValueError, TypeError) as exc:
            return _json({"error": str(exc)})

    return handle


def make_render_hook(ctx: Any):
    """``pre_tool_call``: an ``html_render``/``html_preview`` call whose ``html`` is a ``trace-render:``
    handle gets the board's document instead. Never raises (pre_tool_call hooks fail closed)."""

    def hook(tool_name: str = "", args: Optional[dict] = None, **_: Any) -> Optional[dict]:
        try:
            if not isinstance(args, dict) or not trace_query.is_html_tool(tool_name):
                return None
            html = trace_query.read_render(_renders_dir(_hermes_home()), args.get("html"))
            if html is None:
                if isinstance(args.get("html"), str) and args["html"].strip().startswith(trace_query.RENDER_PREFIX):
                    return {"action": "block", "message": "That trace-render handle has expired; run trace_query again."}
                return None
            return {"action": "modify", "args": {"html": html}}
        except Exception:
            logger.debug("stats-dashboard render hook failed", exc_info=True)
            return None

    return hook


def _context_reference_provider(ctx: Any):
    """``@trace:v0;...`` in a prompt expands to the selection's details before the model reads it."""
    try:
        from agent.context_references import ContextCompletionItem, ContextReferenceProvider
    except Exception:  # an older core without plugin context references
        return None
    settings = _Settings(ctx)

    class TraceReferences(ContextReferenceProvider):
        prefix = "trace"
        description = "a selection copied from a /stats trace board"

        async def autocomplete(self, query: str, *, limit: int = 10) -> list:
            return [ContextCompletionItem(text="@trace:v0;s=", meta="paste a /stats board selection")][:limit]

        async def expand(self, target: str) -> Optional[str]:
            import asyncio

            def run() -> Optional[str]:
                try:
                    ref = trace_query.parse_ref("@trace:" + target)
                    api, index = _prepare(settings, "", True)
                    return trace_query.describe(trace_query.resolve(api, index, ref))
                except trace_query.TraceQueryError as exc:
                    return f"[@trace reference not expanded: {exc}]"

            return await asyncio.to_thread(run)

    return TraceReferences()


def register(ctx) -> None:
    ctx.register_command("stats", handler=make_handler(ctx),
                         description="Open the trace dashboard (omp stats) for this session",
                         args_hint="[status|export|stop]")
    ctx.register_tool(name="trace_query", toolset="stats-dashboard", schema=_TRACE_QUERY_SCHEMA,
                      handler=make_trace_query(ctx), description=_TRACE_QUERY_SCHEMA["description"], emoji="📈")
    ctx.register_tool(name="trace_resolve", toolset="stats-dashboard", schema=_TRACE_RESOLVE_SCHEMA,
                      handler=make_trace_resolve(ctx), description=_TRACE_RESOLVE_SCHEMA["description"], emoji="🔎")
    ctx.register_hook("pre_tool_call", make_render_hook(ctx))
    provider = _context_reference_provider(ctx)
    if provider is not None:
        try:
            ctx.register_context_reference(provider)
        except Exception:
            logger.debug("stats-dashboard: @trace references unavailable", exc_info=True)
    skill = Path(__file__).parent / "skills" / "trace-query" / "SKILL.md"
    if skill.exists() and hasattr(ctx, "register_skill"):
        ctx.register_skill("trace-query", skill, description="Answer trace and usage questions with trace_query "
                                                             "boards and @trace selections")
