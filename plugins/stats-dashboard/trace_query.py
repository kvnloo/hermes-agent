"""``trace_query`` / ``trace_resolve``: the model pulls a bounded slice of the ``/stats`` data.

``trace_query`` runs a question (or a ``trace-query.v0`` plan) against the live omp-stats API of the
``/stats`` server and returns two things:

* an **analysis** for the model: summary, top tools with p50/p95, longest spans, failures, idle gaps
  and per-track cost, every row carrying the span/track id it came from. It stays a few KB however
  large the trace is (``ANALYSIS_BUDGET``), with truncation said out loud;
* a **render handle** (``trace-render:<hex>``): a self-contained HTML board of interactive ephemeral-ui
  cards over the exact data slice, written under ``<omp root>/renders``. The model passes the handle as
  ``html`` to the client's ``html_render`` tool and the plugin's ``pre_tool_call`` hook swaps in the
  document, so the model never re-emits hundreds of KB of HTML.

What the user selects in a board comes back as a compact reference, ``@trace:v0;s=<session>;k=<kind>;
ids=<id,...>;r=<t0>-<t1>;l=<layers>``. Hermes expands ``@trace:`` references in a prompt through the
plugin's context-reference provider; ``trace_resolve`` expands one on request (span entries via
``/api/session/entry``, range summaries) for surfaces that do not.

Everything here is stdlib and side-effect free except :class:`StatsApi` (HTTP to the local dashboard)
and :func:`write_render` (one file per board).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Optional
from urllib.parse import quote

ANALYSIS_BUDGET = 6_000          # bytes of analysis JSON the model reads
SLICE_BUDGET = 300_000           # bytes of data embedded in one board
HTML_LIMIT = 500_000             # T3's html_render takes at most 512,000 characters
TEMPLATE_TOKEN = "__EUI_SLICE__"
RENDER_PREFIX = "trace-render:"
RENDER_RE = re.compile(r"^\s*trace-render:([0-9a-f]{16})\s*$")
REF_PREFIX = "@trace:"
REF_RE = re.compile(r"@trace:(v0;[^\s`'\"]+)")
LAYERS = ("spans", "tokens", "cost", "errors", "subagents", "transcript")
RANGES = ("1h", "24h", "7d", "30d", "90d", "all")
_ID_RE = re.compile(r"^[\w.:\-@]{1,200}$")

# Question -> intent, the same rules as the kit's "Ask the trace" (src/js/ask.js), first match wins.
INTENTS: list[tuple[str, re.Pattern, tuple[str, ...]]] = [
    ("compare_sessions", re.compile(r"\bcompare\b|\bvs\.?\b|versus|differ|side.by.side|last two|two sessions", re.IGNORECASE),
     ("spans", "tokens", "cost", "errors", "subagents")),
    ("explain_slowness", re.compile(r"slow|(?:took|take|takes|taking) (?:so |this |that )?long|latency|bottleneck|stuck|waiting|idle|how long|\bgaps?\b", re.IGNORECASE),
     ("spans", "tokens", "errors", "subagents")),
    ("subagent_cost", re.compile(r"sub.?agents?|child (?:agents?|tracks?)|scouts?|delegat", re.IGNORECASE),
     ("spans", "tokens", "cost", "subagents")),
    ("tool_failures", re.compile(r"tools?\b.*(?:fail|error|broke)|(?:fail|error)\w*.*\btools?\b|which tools?", re.IGNORECASE),
     ("spans", "errors")),
    ("errors", re.compile(r"error|fail|broke|wrong|crash|exception|retry", re.IGNORECASE), ("spans", "errors", "transcript")),
    ("frustration", re.compile(r"frustrat|annoy|angry|mood|sentiment|upset", re.IGNORECASE), ()),
    ("cost_breakdown", re.compile(r"cost|spend|spent|money|price|\$|expensive|bill|budget|models?\b|providers?|tokens?", re.IGNORECASE),
     ("cost", "tokens", "errors")),
    ("walkthrough", re.compile(r"what happened|transcript|walk me|steps|timeline|trace", re.IGNORECASE),
     ("spans", "subagents", "transcript")),
]
OVERVIEW_LAYERS = ("spans", "tokens", "cost", "subagents")
INTENT_IDS = tuple(i for i, _, _ in INTENTS) + ("session_overview",)
RANGE_INTENTS = {"cost_breakdown", "frustration"}


class TraceQueryError(RuntimeError):
    """Something the model should read and act on (bad session, dashboard down, bad ref)."""


def classify(question: str) -> tuple[str, list[str]]:
    for intent, pattern, layers in INTENTS:
        if pattern.search(question or ""):
            return intent, list(layers)
    return "session_overview", list(OVERVIEW_LAYERS)


def default_layers(intent: str) -> list[str]:
    for name, _, layers in INTENTS:
        if name == intent:
            return list(layers) or ["spans"]
    return list(OVERVIEW_LAYERS)


def range_for(question: str, intent: str) -> str:
    q = question or ""
    if re.search(r"today|24 ?h|last day|yesterday", q, re.IGNORECASE):
        return "24h"
    if re.search(r"month|30 ?d", q, re.IGNORECASE):
        return "30d"
    if re.search(r"week|7 ?d", q, re.IGNORECASE):
        return "7d"
    return "30d" if intent == "errors" else "7d"


# ---------------------------------------------------------------- API client

class StatsApi:
    """GET JSON from the omp-stats dashboard (paths exactly as ``server.ts`` ``handleApi`` serves them)."""

    def __init__(self, host: str, port: int, timeout: float = 120.0,
                 opener: Optional[Callable[[str, float], bytes]] = None):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout
        self._open = opener or _urlopen

    def get(self, path: str) -> Any:
        if not path.startswith("/api/"):
            raise TraceQueryError(f"not an omp-stats API path: {path}")
        try:
            return json.loads(self._open(self.base + path, self.timeout) or b"null")
        except urllib.error.HTTPError as exc:
            raise TraceQueryError(f"{path} → HTTP {exc.code}") from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise TraceQueryError(f"{path} failed: {exc}") from exc

    def trace(self, file: str) -> dict:
        trace = self.get(f"/api/session/trace?file={quote(str(file), safe='')}")
        if not isinstance(trace, dict) or "tracks" not in trace:
            raise TraceQueryError(f"no trace for {file}")
        return trace

    def entry(self, file: str, entry_id: str) -> Optional[dict]:
        try:
            got = self.get(f"/api/session/entry?file={quote(str(file), safe='')}&id={quote(entry_id, safe='')}")
        except TraceQueryError:
            return None
        return got.get("entry") if isinstance(got, dict) else None


def _urlopen(url: str, timeout: float) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


# ---------------------------------------------------------------- sessions

@dataclass
class SessionIndex:
    """Exported Hermes sessions: export-state key (session id) -> absolute transcript path."""

    sessions_dir: Path
    paths: dict[str, Path] = field(default_factory=dict)

    @classmethod
    def load(cls, sessions_dir: Path, state_path: Path) -> SessionIndex:
        try:
            data = json.loads(Path(state_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        paths = {k: Path(sessions_dir) / v["path"] for k, v in (data.get("sessions") or {}).items()
                 if isinstance(v, dict) and v.get("path")}
        return cls(Path(sessions_dir), paths)

    def roots(self) -> list[tuple[str, Path]]:
        """Top-level sessions (``<project>/<file>``; subagents sit one level deeper), newest first."""
        rows = [(k, p) for k, p in self.paths.items() if len(p.relative_to(self.sessions_dir).parts) == 2]
        return sorted(rows, key=lambda kp: kp[1].name, reverse=True)

    def file_for(self, session: str) -> Optional[Path]:
        if session in self.paths:
            return self.paths[session]
        for key, path in self.paths.items():  # profile-qualified keys ("clean:<id>") and file stems
            if key.endswith(":" + session) or path.stem == session or path.stem.endswith("_" + session):
                return path
        candidate = Path(session)
        if candidate.is_absolute() and candidate.suffix == ".jsonl":
            try:
                candidate.resolve().relative_to(self.sessions_dir.resolve())
            except ValueError as exc:
                raise TraceQueryError("session file is outside the /stats sessions dir") from exc
            return candidate
        return None

    def session_id(self, file: Path | str) -> str:
        file = Path(file)
        for key, path in self.paths.items():
            if path == file:
                return key.split(":", 1)[-1]
        return file.stem.rsplit("_", 3)[-1] if "_" in file.stem else file.stem


def pick_sessions(index: SessionIndex, spec: str, current: str, count: int = 1, extra: int = 0) -> list[Path]:
    """``current`` (this session), ``latest``/``previous`` (newest other sessions), ``last N``,
    or a Hermes session id / exported file. ``extra`` adds that many fallback candidates after the
    picks (for skipping sessions with nothing recorded)."""
    spec = (spec or "current").strip()
    others = [p for k, p in index.roots() if k.split(":", 1)[-1] != current]
    m = re.fullmatch(r"(?:last|latest)\s+(\d+)", spec, re.IGNORECASE)
    if m:
        count = int(m.group(1))
    if spec == "current":
        path = index.file_for(current) if current else None
        if path is None:
            raise TraceQueryError("this session is not exported yet; ask about 'latest' or a session id")
        picked = [path] + others[: count - 1]
    elif spec in ("latest", "last") or m:
        picked = others[:count + extra]
    elif spec == "previous":
        picked = others[1: 1 + count + extra]
    else:
        path = index.file_for(spec)
        if path is None:
            raise TraceQueryError(f"unknown session {spec!r}: use current, latest, previous, last N or a session id")
        picked = [path] + [p for p in others if p != path][: count - 1]
    if len(picked) < count:
        raise TraceQueryError(f"only {len(picked)} exported session(s) match {spec!r}; {count} needed")
    return picked


# ---------------------------------------------------------------- analysis

def _quantile(xs: list[float], q: float) -> Optional[float]:
    if not xs:
        return None
    s = sorted(xs)
    i = (len(s) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def fmt_ms(ms: Optional[float]) -> str:
    if ms is None:
        return "-"
    if ms < 60_000:
        return f"{ms / 1000:.1f}s"
    m = int(ms // 60_000)
    if m < 60:
        return f"{m}m {int(ms % 60_000 // 1000):02d}s"
    return f"{m // 60}h {m % 60:02d}m"


def spans(trace: dict) -> Iterable[tuple[dict, dict]]:
    for track in trace.get("tracks") or []:
        for span in track.get("spans") or []:
            yield span, track


def _dur(span: dict) -> int:
    return max(0, int(span.get("end", 0)) - int(span.get("start", 0)))


def _short(text: Any, n: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _span_row(span: dict, track: dict, t0: int, detail: int = 0) -> dict:
    row = {"id": span["id"], "kind": span.get("kind"), "label": _short(span.get("label"), 60),
           "ms": _dur(span), "at": "+" + fmt_ms(int(span.get("start", t0)) - t0)}
    if track.get("id") != "main":
        row["track"] = track.get("id")
    if span.get("isError"):
        row["error"] = span.get("errorKind") or True
    if span.get("tokens"):
        row["tokens"] = span["tokens"]
    if span.get("cost"):
        row["cost"] = round(span["cost"], 4)
    if detail and span.get("detail"):
        row["detail"] = _short(span["detail"], detail)
    return row


def tool_stats(trace: dict) -> list[dict]:
    by: dict[str, dict] = {}
    for span, track in spans(trace):
        if span.get("kind") != "tool":
            continue
        r = by.setdefault(span.get("label") or "?", {"tool": span.get("label") or "?", "calls": 0, "errors": 0,
                                                       "ms": [], "slowest": None})
        r["calls"] += 1
        r["errors"] += 1 if span.get("isError") else 0
        r["ms"].append(_dur(span))
        if r["slowest"] is None or _dur(span) > r["slowest"][0]:
            r["slowest"] = (_dur(span), span["id"])
    out = []
    for r in by.values():
        out.append({"tool": r["tool"], "calls": r["calls"], "errors": r["errors"], "totalMs": sum(r["ms"]),
                    "p50Ms": round(_quantile(r["ms"], 0.5) or 0), "p95Ms": round(_quantile(r["ms"], 0.95) or 0),
                    "maxMs": max(r["ms"]), "slowestId": r["slowest"][1]})
    return out


def track_stats(trace: dict) -> list[dict]:
    rows = []
    for track in trace.get("tracks") or []:
        ss = track.get("spans") or []
        if not ss:
            continue
        model = [s for s in ss if s.get("kind") == "model"]
        tools = [s for s in ss if s.get("kind") == "tool"]
        rows.append({"id": track.get("id"), "label": _short(track.get("label"), 48), "model": track.get("model"),
                     "requests": len(model), "modelMs": sum(_dur(s) for s in model), "tools": len(tools),
                     "toolErrors": sum(1 for s in tools if s.get("isError")),
                     "tokens": sum(s.get("tokens") or 0 for s in model),
                     "cost": round(sum(s.get("cost") or 0 for s in model), 4),
                     "wallMs": max(s.get("end", 0) for s in ss) - min(s.get("start", 0) for s in ss)})
    return rows


def idle_gaps(trace: dict, min_ms: int = 30_000) -> list[dict]:
    """Stretches where no model/tool/subagent span was running (waiting on the user or a job)."""
    busy = sorted((int(s["start"]), int(s["end"]), s["id"]) for s, _ in spans(trace)
                  if s.get("kind") in ("model", "tool", "subagent", "background"))
    gaps, end, after = [], None, None
    for a, b, sid in busy:
        if end is not None and a - end >= min_ms:
            gaps.append({"fromMs": end, "toMs": a, "ms": a - end, "after": after, "before": sid})
        if end is None or b >= end:
            end, after = b, sid
    return sorted(gaps, key=lambda g: -g["ms"])


def analyze_trace(trace: dict, session_id: str, intent: str, top: int = 8) -> dict:
    """Bounded facts about one trace. Every row carries the id the model can hand to ``trace_resolve``."""
    s = trace.get("summary") or {}
    t0 = int(trace.get("startedAt") or 0)
    wall = s.get("wallMs") or 1
    all_spans = list(spans(trace))
    tools = tool_stats(trace)
    by_tool_key = {"tool_failures": lambda r: (r["errors"], r["calls"]), "errors": lambda r: (r["errors"], r["calls"])}
    tools.sort(key=by_tool_key.get(intent, lambda r: (r["totalMs"], r["calls"])), reverse=True)
    longest = sorted((x for x in all_spans if x[0].get("kind") in ("model", "tool", "subagent")),
                     key=lambda x: -_dur(x[0]))
    failed = [x for x in all_spans if x[0].get("isError")]
    gaps = idle_gaps(trace)
    out: dict[str, Any] = {
        "session": {"id": session_id, "title": _short(trace.get("title"), 90), "file": trace.get("file"),
                    "startedAt": t0, "endedAt": trace.get("endedAt"), "wall": fmt_ms(s.get("wallMs"))},
        "summary": {k: s.get(k) for k in ("wallMs", "modelMs", "toolMs", "idleMs", "turns", "requests",
                                          "toolCalls", "subagents", "totalTokens", "unpricedRequests")},
        "share": {k: round((s.get(k) or 0) / wall, 3) for k in ("modelMs", "toolMs", "idleMs")},
        "tools": tools[:top],
        "longest": [_span_row(sp, tr, t0, 80) for sp, tr in longest[:top]],
        "failures": {"count": len(failed), "spans": [_span_row(sp, tr, t0, 100) for sp, tr in failed[:top]]},
        "idle": [{**g, "at": "+" + fmt_ms(g["fromMs"] - t0)} for g in gaps[: min(top, 5)]],
        "tracks": sorted(track_stats(trace), key=lambda r: -(r["cost"] or r["modelMs"]))[:top],
    }
    out["summary"]["costTotal"] = round(s.get("costTotal") or 0, 4) if s.get("totalTokens") else None
    if len(tools) > top:
        out["tools_omitted"] = len(tools) - top
    return out


def compare_traces(a: dict, b: dict) -> dict:
    keys = ("wallMs", "modelMs", "toolMs", "idleMs", "requests", "toolCalls", "totalTokens", "costTotal")
    sa, sb = a.get("summary") or {}, b.get("summary") or {}
    return {k: {"older": sa.get(k), "newer": sb.get(k),
                "ratio": round((sb.get(k) or 0) / sa[k], 2) if sa.get(k) else None} for k in keys}


def analyze_range(intent: str, rng: str, data: dict, top: int = 8) -> dict:
    """Bounded facts from range endpoints (tools/errors/stats/frustration)."""
    out: dict[str, Any] = {"range": rng}
    tools = data.get("tools")
    if isinstance(tools, dict):
        rows = sorted(tools.get("byTool") or [], key=lambda r: (r.get("errors", 0), r.get("calls", 0)), reverse=True)
        calls = sum(r.get("calls", 0) for r in rows)
        errs = sum(r.get("errors", 0) for r in rows)
        out["tools"] = {"calls": calls, "errors": errs, "errorRate": round(errs / calls, 4) if calls else 0,
                        "top": [{k: r.get(k) for k in ("tool", "calls", "errors", "costShare")} for r in rows[:top]]}
    errors = data.get("errors")
    if isinstance(errors, list):
        groups: dict[str, dict] = {}
        for e in errors:
            sig = re.sub(r"\d+", "#", str(e.get("errorMessage") or ""))[:120]
            g = groups.setdefault(sig, {"signature": sig, "count": 0, "models": set(), "ids": []})
            g["count"] += 1
            g["models"].add(e.get("model"))
            if len(g["ids"]) < 3:
                g["ids"].append(e.get("id"))
        out["requestErrors"] = {"count": len(errors), "groups": [
            {**g, "models": sorted(m for m in g["models"] if m)}
            for g in sorted(groups.values(), key=lambda g: -g["count"])[:top]]}
    stats = data.get("stats")
    if isinstance(stats, dict):
        ov = stats.get("overall") or {}
        out["usage"] = {
            "overall": {k: ov.get(k) for k in ("totalRequests", "totalCost", "cacheRate", "errorRate",
                                               "totalInputTokens", "totalOutputTokens")},
            "byModel": [{k: r.get(k) for k in ("model", "provider", "totalRequests", "totalCost")}
                        for r in sorted(stats.get("byModel") or [], key=lambda r: -(r.get("totalCost") or 0))[:top]],
            "byAgentType": [{k: r.get(k) for k in ("agentType", "totalRequests", "totalCost")}
                            for r in stats.get("byAgentType") or []]}
    frus = data.get("frustration")
    if isinstance(frus, dict):
        out["frustration"] = {"overall": frus.get("overall"),
                              "byModel": (frus.get("byModel") or [])[:top]}
    return out


def fit(payload: dict, budget: int = ANALYSIS_BUDGET) -> dict:
    """Shrink list rows until the JSON fits ``budget``; say what was cut."""
    def size(p):
        return len(json.dumps(p, separators=(",", ":"), default=str))
    cut: dict[str, int] = {}
    while size(payload) > budget - 240:
        lists = [(path, lst) for path, lst in _lists(payload) if len(lst) > 2]
        if not lists:
            break
        path, lst = max(lists, key=lambda pl: len(json.dumps(pl[1], default=str)))
        drop = max(1, len(lst) // 3)
        del lst[-drop:]
        key = re.sub(r"\[\d+\]", "[]", path)
        cut[key] = cut.get(key, 0) + drop
    if cut:
        payload.setdefault("truncation", []).append(
            "rows cut to fit: " + ", ".join(f"{k} -{n}" for k, n in cut.items())[:220])
    return payload


def _lists(node: Any, path: str = "") -> Iterable[tuple[str, list]]:
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "truncation":
                continue
            yield from _lists(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        yield path, node
        for i, v in enumerate(node):
            if isinstance(v, (dict, list)):
                yield from _lists(v, f"{path}[{i}]")


# ---------------------------------------------------------------- slice for the board

def trim_trace(trace: dict, budget: int) -> tuple[dict, list[str]]:
    """A copy of ``trace`` the kit cards accept, under ``budget`` bytes: details are shortened first,
    then the shortest unremarkable tool spans go (errors, long spans and every model/turn stay)."""
    notes: list[str] = []
    t = json.loads(json.dumps(trace))
    t.pop("cwd", None)
    for cap in (240, 80, 0):
        for span, _ in spans(t):
            if span.get("detail") and len(span["detail"]) > cap:
                span["detail"] = span["detail"][:cap] + ("…" if cap else "")
            if not span.get("detail"):
                span.pop("detail", None)
        if len(json.dumps(t, separators=(",", ":"))) <= budget:
            if cap < 240:
                notes.append(f"span details shortened to {cap} chars in the board")
            return t, notes
    tool_spans = sorted((s for s, _ in spans(t) if s.get("kind") == "tool" and not s.get("isError")), key=_dur)
    drop: set[str] = set()
    size = len(json.dumps(t, separators=(",", ":")))
    for s in tool_spans:
        if size <= budget:
            break
        drop.add(s["id"])
        size -= len(json.dumps(s, separators=(",", ":"))) + 1
    for track in t.get("tracks") or []:
        track["spans"] = [s for s in track.get("spans") or [] if s["id"] not in drop]
    if drop:
        notes.append(f"{len(drop)} short successful tool spans left out of the board (analysis counts them)")
    return t, notes


def _entry_view(entry: Optional[dict]) -> Optional[dict]:
    """What the span drawer reads from an entry: usage, model, provider, stop reason, error."""
    msg = (entry or {}).get("message") if isinstance(entry, dict) else None
    if not isinstance(msg, dict):
        return None
    keep = {k: msg[k] for k in ("role", "model", "provider", "stopReason", "usage", "ttft", "errorMessage")
            if k in msg}
    return {"message": keep} if keep else None


def build_slice(traces: list[dict], range_data: dict, api: Optional[StatsApi], rng: str,
                entry_ids: Iterable[tuple[str, str]] = (), budget: int = SLICE_BUDGET) -> tuple[dict, list[str]]:
    """Fixture-shaped data (``{generatedAt, sessions, traces, entries, api}``) for the kit cards."""
    notes: list[str] = []
    per = max(40_000, (budget - 40_000) // max(1, len(traces)))
    out_traces, sessions = {}, []
    for tr in traces:
        trimmed, n = trim_trace(tr, per)
        notes += n
        out_traces[tr["file"]] = trimmed
        s = tr.get("summary") or {}
        sessions.append({"file": tr["file"], "title": tr.get("title"), "startedAt": tr.get("startedAt"),
                         "endedAt": tr.get("endedAt"), "requests": s.get("requests"), "toolCalls": s.get("toolCalls"),
                         "subagents": s.get("subagents"), "totalTokens": s.get("totalTokens"),
                         "costTotal": s.get("costTotal"), "harness": "hermes"})
    entries = {}
    if api is not None:
        for file, entry_id in list(dict.fromkeys(entry_ids))[:16]:
            view = _entry_view(api.entry(file, entry_id))
            if view:
                entries[f"{file}#{entry_id}"] = view
    api_map: dict[str, Any] = {}
    for key, value in range_data.items():
        if key == "tools" and isinstance(value, dict):
            value = {"byTool": value.get("byTool") or [], "byToolModel": [], "series": value.get("series") or []}
        if key == "stats" and isinstance(value, dict):
            value = {k: value.get(k) for k in ("overall", "byModel", "byAgentType", "costSeries", "timeSeries")}
        path = {"tools": "/api/stats/tools", "errors": "/api/stats/errors", "stats": "/api/stats",
                "providers": "/api/stats/providers", "frustration": "/api/stats/frustration"}.get(key)
        if path:
            api_map[f"{path}?range={rng}"] = value
    for path in ("/api/stats/errors?range=7d", "/api/stats/errors?range=30d"):
        api_map.setdefault(path, [])  # the errors card's Requests tab fetches one of these
    return {"generatedAt": int(time.time() * 1000), "sessions": sessions, "traces": out_traces,
            "entries": entries, "api": api_map}, notes


def cards_for(intent: str, n_traces: int, has_range: set[str]) -> list[dict]:
    """The board for an intent: kit card kinds (``KINDS_T``), each naming the slice input it reads."""
    trace_cards = {
        "explain_slowness": [("trace-summary", {}, "Where the wall time went: model, tools, idle"),
                             ("trace", {}, "The waterfall; long spans and idle bridges show the cause"),
                             ("trace-tools", {"sort": "p95", "scope": "trace"}, "Tools by p95 latency in this session")],
        "subagent_cost": [("trace-summary", {}, "Cost and model time per track"),
                          ("trace", {}, "Child tracks with their cumulative cost lanes")],
        "tool_failures": [("trace-tools", {"sort": "errors", "scope": "trace"}, "Tools ranked by failures"),
                          ("trace-errors", {"tab": "spans"}, "Failed spans grouped by tool and kind"),
                          ("trace", {}, "Timeline with failed spans in red")],
        "errors": [("trace-errors", {"tab": "spans"}, "Failed spans grouped by tool and kind"),
                   ("trace", {}, "Timeline with failures highlighted")],
        "walkthrough": [("trace-summary", {}, "Headline numbers"), ("trace", {}, "Waterfall with transcript")],
        "session_overview": [("trace-summary", {}, "Headline numbers"), ("trace", {}, "The waterfall")],
    }
    if intent == "compare_sessions" and n_traces >= 2:
        return [{"kind": "trace-compare", "input": ["trace1", "trace0"], "why": "Older on the left, newer on the right"},
                {"kind": "trace-summary", "input": "trace1", "why": "Older session"},
                {"kind": "trace-summary", "input": "trace0", "why": "Newer session"}]
    if intent == "cost_breakdown" and "stats" in has_range:
        cards = [{"kind": "trace-usage", "input": "stats", "why": "Estimate by model", "options": {"view": "models"}}]
        if "providers" in has_range:
            cards.append({"kind": "trace-usage", "input": "providers", "why": "Same range by billing component",
                          "options": {"view": "components"}})
        return cards
    if intent == "frustration" and "frustration" in has_range:
        return [{"kind": "trace-frustration", "input": "frustration", "why": "User sentiment by model"}]
    rows = trace_cards.get(intent) or trace_cards["session_overview"]
    return [{"kind": k, "input": "trace0", "why": why, **({"options": o} if o else {})} for k, o, why in rows]


# ---------------------------------------------------------------- references

def make_ref(session: str, kind: str = "session", ids: Iterable[str] = (), rng: Optional[tuple[int, int]] = None,
             layers: Iterable[str] = ()) -> str:
    parts = ["v0", f"s={session}", f"k={kind}"]
    ids = [i for i in ids if i]
    if ids:
        parts.append("ids=" + ",".join(ids))
    if rng:
        parts.append(f"r={int(rng[0])}-{int(rng[1])}")
    layers = [x for x in layers if x in LAYERS]
    if layers:
        parts.append("l=" + ",".join(layers))
    return REF_PREFIX + ";".join(parts)


def parse_ref(text: str) -> dict:
    """``@trace:v0;s=..;k=..;ids=..;r=..;l=..`` (or the bare ``v0;...`` value, or ``trace-ref:v0 {json}``)."""
    text = (text or "").strip()
    if text.startswith("trace-ref:v0"):
        try:
            raw = json.loads(text[len("trace-ref:v0"):].strip())
        except ValueError as exc:
            raise TraceQueryError("trace-ref:v0 needs a JSON object") from exc
        ref = {"s": raw.get("session"), "k": raw.get("kind", "selection"), "ids": raw.get("ids") or [],
               "r": raw.get("range"), "l": raw.get("layers") or []}
    else:
        m = REF_RE.search(text)
        value = m.group(1) if m else text
        if not value.startswith("v0;"):
            raise TraceQueryError("not a trace reference (expected @trace:v0;s=<session>;...)")
        fields = dict(p.split("=", 1) for p in value.split(";")[1:] if "=" in p)
        rng = None
        if fields.get("r"):
            a, _, b = fields["r"].partition("-")
            rng = [int(a), int(b)] if a.isdigit() and b.isdigit() else None
        ref = {"s": fields.get("s"), "k": fields.get("k", "selection"),
               "ids": [i for i in (fields.get("ids") or "").split(",") if i], "r": rng,
               "l": [x for x in (fields.get("l") or "").split(",") if x]}
    if not ref["s"] or not _ID_RE.match(str(ref["s"])):
        raise TraceQueryError("trace reference has no valid session")
    ref["ids"] = [i for i in ref["ids"] if isinstance(i, str) and _ID_RE.match(i)][:24]
    if ref["r"] is not None and (len(ref["r"]) != 2 or ref["r"][0] > ref["r"][1]):
        ref["r"] = None
    ref["l"] = [x for x in ref["l"] if x in LAYERS]
    return ref


def range_summary(trace: dict, t0: int, t1: int, top: int = 6) -> dict:
    inside = [(s, t) for s, t in spans(trace) if s.get("end", 0) >= t0 and s.get("start", 0) <= t1]
    clip = lambda s: max(0, min(int(s["end"]), t1) - max(int(s["start"]), t0))
    by_kind: dict[str, int] = {}
    for s, _ in inside:
        by_kind[s.get("kind")] = by_kind.get(s.get("kind"), 0) + clip(s)
    tools: dict[str, list] = {}
    for s, _ in inside:
        if s.get("kind") == "tool":
            tools.setdefault(s.get("label"), []).append(clip(s))
    start = int(trace.get("startedAt") or t0)
    return {"from": "+" + fmt_ms(t0 - start), "to": "+" + fmt_ms(t1 - start), "ms": t1 - t0,
            "spans": len(inside), "busyMsByKind": by_kind,
            "tools": sorted(({"tool": k, "calls": len(v), "ms": sum(v)} for k, v in tools.items()),
                            key=lambda r: -r["ms"])[:top],
            "failures": [_span_row(s, t, start, 100) for s, t in inside if s.get("isError")][:top],
            "longest": [_span_row(s, t, start, 100) for s, t in
                        sorted(inside, key=lambda x: -clip(x[0])) if s.get("kind") != "turn"][:top]}


def _entry_text(entry: Optional[dict], limit: int) -> Optional[dict]:
    """A bounded view of a journal entry: role, model, usage, stop reason, text and tool calls."""
    msg = (entry or {}).get("message") if isinstance(entry, dict) else None
    if not isinstance(msg, dict):
        return None
    out = {k: msg[k] for k in ("role", "model", "provider", "stopReason", "usage", "toolName", "isError",
                               "errorMessage") if k in msg}
    content = msg.get("content")
    texts, calls = [], []
    if isinstance(content, str):
        texts.append(content)
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                texts.append(block.get("text") or "")
            elif block.get("type") == "toolCall":
                calls.append({"name": block.get("name"),
                              "args": _short(json.dumps(block.get("arguments"), ensure_ascii=False), 400)})
    if texts:
        out["text"] = _short("\n".join(texts), limit)
    if calls:
        out["toolCalls"] = calls[:6]
    return out


def resolve(api: StatsApi, index: SessionIndex, ref: dict, text_limit: int = 1_200) -> dict:
    """Details for a reference: each id's span (+ its journal entry), tool rows, or a time range."""
    file = index.file_for(ref["s"])
    if file is None:
        raise TraceQueryError(f"unknown session {ref['s']!r}")
    trace = api.trace(str(file))
    start = int(trace.get("startedAt") or 0)
    by_id = {s["id"]: (s, t) for s, t in spans(trace)}
    tools = {r["tool"]: r for r in tool_stats(trace)}
    out: dict[str, Any] = {"session": {"id": ref["s"], "title": _short(trace.get("title"), 90)},
                           "kind": ref["k"], "items": []}
    budget = text_limit
    for item in ref["ids"]:
        if item.startswith("tool:") and item[5:] in tools:
            r = tools[item[5:]]
            slow = sorted(((s, t) for s, t in spans(trace) if s.get("kind") == "tool" and s.get("label") == item[5:]),
                          key=lambda x: (-int(bool(x[0].get("isError"))), -_dur(x[0])))[:5]
            out["items"].append({"id": item, "tool": r, "spans": [_span_row(s, t, start, 160) for s, t in slow]})
            continue
        if item not in by_id:
            out["items"].append({"id": item, "missing": True})
            continue
        span, track = by_id[item]
        row = {**_span_row(span, track, start, 600), "start": span.get("start"), "end": span.get("end")}
        if span.get("model"):
            row["model"] = span["model"]
        if span.get("childTrackId"):
            row["childTrack"] = span["childTrackId"]
        if span.get("entryId") and budget > 200:
            got = _entry_text(api.entry(track.get("file") or trace["file"], span["entryId"]), budget)
            if got:
                row["entry"] = got
                budget -= len(got.get("text", ""))
        out["items"].append(row)
    if ref.get("r"):
        out["range"] = range_summary(trace, ref["r"][0], ref["r"][1])
    if ref.get("l"):
        out["layers"] = ref["l"]
    return fit(out, ANALYSIS_BUDGET + 2_000)


def describe(resolved: dict) -> str:
    """Prompt text for an expanded ``@trace:`` reference."""
    return ("[trace selection from the /stats board — the user picked these; ids work with trace_resolve "
            "and trace_query(focus=...)]\n" + json.dumps(resolved, ensure_ascii=False, separators=(",", ":"),
                                                         default=str))


# ---------------------------------------------------------------- rendering

def render_handle(payload: dict) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return digest


# T3's html_render refuses a page whose stylesheets or style attributes use a viewport-height unit, and
# it scans the whole document, script text included (apps/server/src/htmlRender/HtmlRender.ts).
_CSS_SOURCE = re.compile(r"""<!--[\s\S]*?(?:-->|$)|<style\b[^>]*(?:>|$)([\s\S]*?)(?:</style\s*>|$)|"""
                         r"""\sstyle\s*=\s*(?:"([^"]*)(?:"|$)|'([^']*)(?:'|$)|([^\s>]+))""", re.IGNORECASE)
_VIEWPORT_HEIGHT = re.compile(r"(?<![\w.+/])(?:\d+(?:\.\d+)?|\.\d+)[sld]?vh(?![\w-])", re.IGNORECASE)
_STYLE_WORD = re.compile(r"style", re.IGNORECASE)


def viewport_height_unit(html: str) -> Optional[str]:
    for m in _CSS_SOURCE.finditer(html):
        found = _VIEWPORT_HEIGHT.search(next((g for g in m.groups() if g is not None), ""))
        if found:
            return found.group(0)
    return None


def fill_template(template: str, payload: dict) -> str:
    if template.count(TEMPLATE_TOKEN) != 1:
        raise TraceQueryError(f"inline template must contain {TEMPLATE_TOKEN} exactly once")
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    # Trace text (tool args, titles) must not end the script element, open a comment, or read as a
    # style attribute to the host's stylesheet scan; JSON escapes keep the values intact.
    data = _STYLE_WORD.sub(lambda m: f"\\u{ord(m.group(0)[0]):04x}{m.group(0)[1:]}", data.replace("<", "\\u003c"))
    return template.replace(TEMPLATE_TOKEN, data, 1)


def write_render(renders_dir: Path, template_path: Path, payload: dict) -> dict:
    """Write the board; returns ``{handle, path, bytes}`` (``handle`` is what html_render takes)."""
    try:
        template = Path(template_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise TraceQueryError(
            f"no inline template at {template_path}; build it with the ephemeral-ui kit: "
            f"node tools/stats-inline.mjs --template {template_path}") from exc
    html = fill_template(template, payload)
    if len(html) > HTML_LIMIT:
        raise TraceQueryError(f"board is {len(html)} chars, over the {HTML_LIMIT} html_render limit")
    unit = viewport_height_unit(html)
    if unit:
        raise TraceQueryError(f"inline template uses a viewport height unit ({unit}) that html_render refuses; "
                              "rebuild it with the current tools/stats-inline.mjs")
    digest = render_handle(payload)
    renders_dir = Path(renders_dir)
    renders_dir.mkdir(parents=True, exist_ok=True)
    path = renders_dir / f"{digest}.html"
    path.write_text(html, encoding="utf-8")
    _prune(renders_dir, keep=64)
    return {"handle": RENDER_PREFIX + digest, "path": str(path), "chars": len(html)}


def _prune(directory: Path, keep: int) -> None:
    files = sorted(directory.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in files[keep:]:
        try:
            stale.unlink()
        except OSError:
            pass


def read_render(renders_dir: Path, value: Any) -> Optional[str]:
    """The board behind a ``trace-render:<hex>`` handle, or None if ``value`` is not one."""
    m = RENDER_RE.match(value) if isinstance(value, str) else None
    if not m:
        return None
    try:
        return (Path(renders_dir) / f"{m.group(1)}.html").read_text(encoding="utf-8")
    except OSError:
        return None


def is_html_tool(tool_name: str) -> bool:
    """T3's ``html_render``/``html_preview`` under any MCP server prefix (``mcp__<server>__html_render``)."""
    name = (tool_name or "").rsplit("__", 1)[-1].rsplit(".", 1)[-1]
    return name in ("html_render", "html_preview") or (tool_name or "").endswith(("_html_render", "_html_preview"))


# ---------------------------------------------------------------- the query

@dataclass
class Query:
    question: str = ""
    intent: Optional[str] = None
    session: str = "current"
    range: Optional[str] = None
    layers: Optional[list[str]] = None
    focus: list[str] = field(default_factory=list)
    focus_range: Optional[list[int]] = None
    tool: Optional[str] = None
    top: int = 8
    render: bool = True

    @classmethod
    def from_args(cls, args: dict) -> Query:
        args = dict(args or {})
        plan = args.get("plan") if isinstance(args.get("plan"), dict) else None
        q = cls(question=str(args.get("question") or (plan or {}).get("q") or ""))
        q.intent = args.get("intent") or (plan or {}).get("intent")
        scope = (plan or {}).get("scope") or {}
        q.session = str(args.get("session") or scope.get("session") or "current")
        if scope.get("count") and q.intent == "compare_sessions" and q.session in ("latest", "current"):
            q.session = f"last {int(scope['count'])}"
        q.range = args.get("range") or scope.get("range")
        q.layers = args.get("layers") or (plan or {}).get("layers")
        ref = args.get("ref")
        if ref:
            parsed = parse_ref(str(ref))
            q.session = parsed["s"]
            q.focus = parsed["ids"]
            q.focus_range = parsed["r"]
            q.layers = q.layers or parsed["l"] or None
        if args.get("focus"):
            q.focus = [str(i) for i in args["focus"] if isinstance(i, str) and _ID_RE.match(i)][:24]
        if isinstance(args.get("focus_range"), list) and len(args["focus_range"]) == 2:
            q.focus_range = [int(args["focus_range"][0]), int(args["focus_range"][1])]
        q.tool = args.get("tool")
        q.top = max(3, min(int(args.get("top") or 8), 20))
        q.render = args.get("render", True) is not False
        if q.intent and q.intent not in INTENT_IDS:
            raise TraceQueryError(f"unknown intent {q.intent!r}; one of {', '.join(INTENT_IDS)}")
        if not q.intent:
            q.intent, auto = classify(q.question)
            q.layers = q.layers or auto
        q.layers = [x for x in (q.layers or default_layers(q.intent)) if x in LAYERS] or ["spans"]
        q.range = q.range if q.range in RANGES else range_for(q.question, q.intent)
        if q.intent == "compare_sessions" and not q.session.startswith("last"):
            q.session = q.session if q.session not in ("current", "latest") else "last 2"
        return q


RANGE_CALLS = {
    "tool_failures": ("tools",),
    "errors": ("errors",),
    "cost_breakdown": ("stats", "providers"),
    "frustration": ("frustration",),
    "subagent_cost": ("stats",),
}
RANGE_PATHS = {"tools": "/api/stats/tools", "errors": "/api/stats/errors", "stats": "/api/stats",
               "providers": "/api/stats/providers", "frustration": "/api/stats/frustration"}


def run_query(q: Query, api: StatsApi, index: SessionIndex, current: str, renders_dir: Path,
              template_path: Optional[Path]) -> dict:
    """Execute ``q``; returns the tool result (analysis + render handle + refs)."""
    started = time.monotonic()
    result: dict[str, Any] = {"v": 0, "intent": q.intent, "question": q.question or None, "range": q.range,
                              "layers": q.layers}
    traces: list[dict] = []
    if q.intent not in RANGE_INTENTS:
        count = 2 if q.intent == "compare_sessions" else 1
        relative = q.session in ("latest", "last", "previous") or q.session.startswith(("last ", "latest "))
        files = pick_sessions(index, q.session, current, count, extra=12 if relative else 0)
        skipped = 0
        for f in files:
            trace = api.trace(str(f))
            if relative and not (trace.get("summary") or {}).get("turns"):
                skipped += 1  # a session that never got a turn (opened and closed) answers nothing
                continue
            traces.append(trace)
            if len(traces) == count:
                break
        if len(traces) < count:
            raise TraceQueryError(f"found {len(traces)} session(s) with recorded turns for {q.session!r}")
        if skipped:
            result.setdefault("truncation", []).append(f"skipped {skipped} newer session(s) with no turns")
    range_data: dict[str, Any] = {}
    for key in RANGE_CALLS.get(q.intent, ()):
        try:
            range_data[key] = api.get(f"{RANGE_PATHS[key]}?range={q.range}")
        except TraceQueryError as exc:
            result.setdefault("truncation", []).append(f"{key} unavailable: {exc}")
    if traces:
        sid = index.session_id(traces[0]["file"])
        result["analysis"] = analyze_trace(traces[0], sid, q.intent, q.top)
        if q.tool:
            result["analysis"]["tools"] = [r for r in tool_stats(traces[0]) if r["tool"] == q.tool] or \
                result["analysis"]["tools"]
        if len(traces) == 2:
            # pick_sessions returns newest first; the board and the deltas read older -> newer
            result["older"] = analyze_trace(traces[1], index.session_id(traces[1]["file"]), q.intent, 3)
            result["delta"] = compare_traces(traces[1], traces[0])
        if q.focus or q.focus_range:
            focus_ref = {"s": sid, "k": "focus", "ids": q.focus, "r": q.focus_range, "l": []}
            result["focus"] = resolve(api, index, focus_ref, text_limit=800)
        result["ref"] = make_ref(sid, "session", layers=q.layers)
    if range_data:
        result["rangeAnalysis"] = analyze_range(q.intent, q.range, range_data, q.top)
    fit(result)
    if q.render:
        result["render"] = _render(q, api, index, traces, range_data, renders_dir, template_path, result)
    result["elapsedMs"] = int((time.monotonic() - started) * 1000)
    return result


def _render(q: Query, api: StatsApi, index: SessionIndex, traces: list[dict], range_data: dict,
            renders_dir: Path, template_path: Optional[Path], result: dict) -> dict:
    if template_path is None:
        return {"error": "rendering is off (no inline template configured)"}
    wanted = set(q.focus)
    entry_ids: list[tuple[str, str]] = []
    for tr in traces[:1]:
        model = sorted(((s, t) for s, t in spans(tr) if s.get("kind") == "model" and s.get("entryId")),
                       key=lambda x: (-int(x[0]["id"] in wanted), -_dur(x[0])))
        entry_ids += [(t.get("file") or tr["file"], s["entryId"]) for s, t in model[:10]]
    data, notes = build_slice(traces, range_data, api, q.range, entry_ids)
    # Inputs are named like the plan's calls: trace0 (newest), trace1 (older, compare only).
    inputs = {f"trace{i}": tr["file"] for i, tr in enumerate(traces)}
    sid = index.session_id(traces[0]["file"]) if traces else None
    payload = {
        "v": 0,
        "title": (q.question or q.intent.replace("_", " ")).strip()[:120],
        "intent": q.intent,
        "range": q.range,
        "layers": q.layers,
        "cards": cards_for(q.intent, len(traces), set(range_data)),
        "inputs": inputs,
        "session": sid,
        "sessions": {tr["file"]: index.session_id(tr["file"]) for tr in traces},
        "focus": {"ids": q.focus, "range": q.focus_range},
        # what the reader should know about the board; analysis trimming is the model's business
        "notes": notes + [n for n in result.get("truncation") or [] if not n.startswith("rows cut")],
        "slice": data,
    }
    try:
        written = write_render(renders_dir, template_path, payload)
    except TraceQueryError as exc:
        return {"error": str(exc)}
    return {**written, "title": f"/stats · {payload['title']}"[:200], "height": 1100 if traces else 700,
            "cards": [c["kind"] for c in payload["cards"]], "notes": notes,
            "how": "call html_render with html set to the handle string exactly (the plugin swaps in the "
                   "board), the title and height above; do not paste HTML"}
