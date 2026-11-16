"""Export agent sessions as omp session JSONL so ``omp stats`` can chart and trace them.

The exporter has two halves joined by a small normalized model:

* a *source* (``HermesStateSource`` reads a Hermes ``state.db``) turns its own storage into
  ``SessionRef`` (cheap: identity, lineage, fingerprint) and ``SessionRecord`` (full events);
* the *writer* (``export``) turns records into omp's journal layout under one sessions dir and keeps
  a watermark file so only sessions whose fingerprint changed are rewritten.

A second source (for example another harness's database) only has to implement ``scan()`` and
``load()``; the writer never looks at source storage.

Mapping rules (omp shapes mirrored from ``@oh-my-pi/omp-stats`` ``parser.ts`` / ``trace.ts``):

* one ``session`` header per session; subagents get a ``session_init`` and live one level deeper
  (``<project>/<parent stem>/<child stem>.jsonl``), which is how omp classifies ``subagent``;
* ``message`` entries for user, assistant (``toolCall`` blocks) and ``toolResult`` rows, every
  timestamp taken from the source row. An assistant span runs from the previous row's timestamp to
  its own; omp places a tool span from the calling turn's end to its result row;
* per-model usage rows become ``model_usage`` entries (the only rows omp counts as requests, so
  totals are not double counted). Missing numbers are omitted, never guessed;
* compaction summaries become ``compaction`` entries; a recorded session end becomes a
  ``session_exit`` marker.

Stdlib only. The source database is opened read-only (``mode=ro`` URI).
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Iterator, Optional, Protocol, Sequence

STATE_FILE = "hermes-export-state.json"
STATE_VERSION = 1
DEFAULT_MAX_CHARS = 20_000

# omp records the wire API per request; Hermes records the billing provider. Unknown providers
# fall back to the generic chat-completions API name (omp only stores it as a label).
_PROVIDER_API = {
    "anthropic": "anthropic-messages",
    "claude-code": "anthropic-messages",
    "openai-codex": "openai-codex-responses",
    "openai": "openai-responses",
    "google": "google-generative-ai",
    "gemini": "google-generative-ai",
}


# ---------------------------------------------------------------------------
# Normalized model (source-independent)


@dataclass(frozen=True)
class SessionRef:
    """Cheap identity of one session; ``fingerprint`` changes whenever its export would."""

    key: str
    session_id: str
    parent_key: Optional[str]
    subagent: bool
    started_at: float
    cwd: Optional[str]
    fingerprint: str
    namespace: str = ""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: object = None


@dataclass
class Event:
    """One transcript row. ``kind`` is ``user`` | ``assistant`` | ``tool_result`` | ``compaction``."""

    kind: str
    ts: float
    text: str = ""
    model: Optional[str] = None
    provider: Optional[str] = None
    tool_calls: Sequence[ToolCall] = ()
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    is_error: bool = False
    stop_reason: Optional[str] = None


@dataclass
class UsageRow:
    model: str
    provider: str
    purpose: str
    input: int
    output: int
    cache_read: int
    cache_write: int
    reasoning: int
    calls: int
    ts: Optional[float]
    cost: Optional[float] = None


@dataclass
class SessionRecord:
    ref: SessionRef
    title: Optional[str] = None
    agent: Optional[str] = None
    model: Optional[str] = None
    ended_at: Optional[float] = None
    end_reason: Optional[str] = None
    events: list[Event] = field(default_factory=list)
    usage: list[UsageRow] = field(default_factory=list)


class SessionSource(Protocol):
    name: str

    def scan(self) -> list[SessionRef]: ...

    def load(self, ref: SessionRef) -> SessionRecord: ...


# ---------------------------------------------------------------------------
# Hermes state.db source


def hermes_profile_db(hermes_root: Path, profile: str) -> Path:
    """``state.db`` of a profile: the root's own for ``default``, else ``profiles/<name>/``."""
    if profile in ("", "default"):
        return hermes_root / "state.db"
    return hermes_root / "profiles" / profile / "state.db"


def hermes_profiles(hermes_root: Path) -> list[str]:
    """Every profile with a ``state.db`` under a Hermes root (``default`` = the root itself)."""
    names = ["default"] if (hermes_root / "state.db").is_file() else []
    profiles_dir = hermes_root / "profiles"
    if profiles_dir.is_dir():
        names += sorted(p.name for p in profiles_dir.iterdir() if (p / "state.db").is_file())
    return names


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _ms(ts: float) -> int:
    return round(ts * 1000)


def _json_or_none(text: Optional[str]) -> object:
    if not text:
        return None
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def _tool_result_is_error(content: Optional[str]) -> bool:
    """Hermes tools report failure as JSON ``{"error": ...}`` or ``{"success": false}``."""
    data = _json_or_none(content) if content and content.lstrip().startswith("{") else None
    if not isinstance(data, dict):
        return False
    return bool(data.get("error")) or data.get("success") is False


_FINISH_TO_STOP = {"tool_calls": "toolUse", "stop": "stop", "length": "length", "end_turn": "stop"}


class HermesStateSource:
    """Sessions of one Hermes profile's ``state.db``, opened read-only."""

    def __init__(self, db_path: Path, profile: str = "default", namespace: str = ""):
        self.db_path = Path(db_path)
        self.profile = profile
        self.namespace = namespace
        self.name = f"hermes:{profile}"
        self._conn: Optional[sqlite3.Connection] = None
        self._session_cols: set[str] = set()
        self._message_cols: set[str] = set()
        self._has_usage = False

    # -- connection -----------------------------------------------------------------------------

    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            uri = f"file:{self.db_path.resolve()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=10)
            conn.row_factory = sqlite3.Row
            self._session_cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)")}
            self._message_cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)")}
            self._has_usage = bool(conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='session_model_usage'").fetchone())
            self._conn = conn
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _col(self, name: str, alias: str = "s") -> str:
        return f"{alias}.{name}" if name in self._session_cols else "NULL"

    def _key(self, session_id: str) -> str:
        return f"{self.namespace}{session_id}"

    # -- scan -----------------------------------------------------------------------------------

    def scan(self) -> list[SessionRef]:
        conn = self._db()
        c = self._col
        usage_fp = ("(SELECT count(*) || ':' || total(input_tokens) || ':' || total(output_tokens) || ':' ||"
                    " total(cache_read_tokens) || ':' || total(api_call_count) || ':' ||"
                    " total(estimated_cost_usd) || ':' || total(actual_cost_usd) || ':' ||"
                    " COALESCE(max(last_seen), '')"
                    " FROM session_model_usage u WHERE u.session_id = s.id)") if self._has_usage else "''"
        rows = conn.execute(
            f"""SELECT s.id, s.parent_session_id, {c('source')} AS source, {c('model_config')} AS model_config,
                       s.started_at, {c('ended_at')} AS ended_at, {c('cwd')} AS cwd, {c('title')} AS title,
                       {c('transcript_revision')} AS rev, {c('rewind_count')} AS rewinds,
                       {c('message_count')} AS message_count, {c('last_activity_at')} AS last_activity,
                       (SELECT max(id) FROM messages m WHERE m.session_id = s.id) AS max_mid,
                       (SELECT count(*) FROM messages m WHERE m.session_id = s.id) AS n_rows,
                       {usage_fp} AS usage_fp
                FROM sessions s"""
        ).fetchall()
        ids = {r["id"] for r in rows}
        refs = []
        for r in rows:
            parent = r["parent_session_id"] if r["parent_session_id"] in ids else None
            config = _json_or_none(r["model_config"]) if r["model_config"] else None
            delegated_from = config.get("_delegate_from") if isinstance(config, dict) else None
            subagent = parent is not None and (r["source"] == "subagent" or delegated_from == parent)
            fingerprint = "|".join(str(r[k]) for k in (
                "max_mid", "n_rows", "rev", "rewinds", "message_count", "ended_at", "last_activity",
                "title", "usage_fp", "parent_session_id", "cwd"))
            refs.append(SessionRef(
                key=self._key(r["id"]), session_id=r["id"],
                parent_key=self._key(parent) if parent else None, subagent=subagent,
                started_at=float(r["started_at"]), cwd=r["cwd"] or None,
                fingerprint=fingerprint, namespace=self.namespace))
        return refs

    # -- load -----------------------------------------------------------------------------------

    def load(self, ref: SessionRef) -> SessionRecord:
        conn = self._db()
        c = self._col
        s = conn.execute(
            f"""SELECT s.id, s.model, {c('billing_provider')} AS provider, {c('title')} AS title,
                       {c('source')} AS source, {c('ended_at')} AS ended_at, {c('end_reason')} AS end_reason
                FROM sessions s WHERE s.id = ?""", (ref.session_id,)).fetchone()
        record = SessionRecord(ref=ref)
        if s is None:
            return record
        record.title = s["title"]
        record.ended_at = s["ended_at"]
        record.end_reason = s["end_reason"]
        record.agent = "subagent" if ref.subagent else None
        if self._has_usage:
            record.usage = self._usage(ref.session_id)
        model = s["model"] or (record.usage[0].model if record.usage else None)
        provider = s["provider"] or (record.usage[0].provider if record.usage else None) or "hermes"
        record.model = model
        record.events = list(self._events(ref.session_id, model or "unknown", provider))
        return record

    def _usage(self, session_id: str) -> list[UsageRow]:
        rows = self._db().execute(
            "SELECT * FROM session_model_usage WHERE session_id = ? ORDER BY COALESCE(first_seen, 0), model",
            (session_id,)).fetchall()
        out = []
        for r in rows:
            keys = r.keys()
            actual = r["actual_cost_usd"] if "actual_cost_usd" in keys else None
            estimated = r["estimated_cost_usd"] if "estimated_cost_usd" in keys else None
            status = r["cost_status"] if "cost_status" in keys else None
            # A recorded cost status means Hermes priced the row (``included`` = subscription, 0);
            # without one the zero is unknown spend, so the cost stays absent for omp to estimate.
            cost = None
            if actual:
                cost = float(actual)
            elif status:
                cost = float(estimated or 0.0)
            out.append(UsageRow(
                model=r["model"], provider=r["billing_provider"] or "hermes", purpose=r["task"] or "main",
                input=int(r["input_tokens"] or 0), output=int(r["output_tokens"] or 0),
                cache_read=int(r["cache_read_tokens"] or 0), cache_write=int(r["cache_write_tokens"] or 0),
                reasoning=int(r["reasoning_tokens"] or 0), calls=int(r["api_call_count"] or 0),
                ts=r["last_seen"] if "last_seen" in keys else None, cost=cost))
        return out

    def _events(self, session_id: str, model: str, provider: str) -> Iterator[Event]:
        cols = self._message_cols
        visible = "AND (active = 1 OR compacted = 1)" if {"active", "compacted"} <= cols else ""
        summary_col = "_compressed_summary" if "_compressed_summary" in cols else "0"
        rows = self._db().execute(
            f"""SELECT role, content, tool_call_id, tool_calls, tool_name, timestamp, finish_reason,
                       {summary_col} AS summary
                FROM messages WHERE session_id = ? {visible} ORDER BY id""", (session_id,))
        for r in rows:
            role, ts = r["role"], float(r["timestamp"])
            text = r["content"] or ""
            if r["summary"]:
                yield Event("compaction", ts, text=text)
            elif role == "user":
                yield Event("user", ts, text=text)
            elif role == "assistant":
                calls = []
                raw_calls = _json_or_none(r["tool_calls"])
                for call in raw_calls if isinstance(raw_calls, list) else []:
                    if not isinstance(call, dict):
                        continue
                    fn = call["function"] if isinstance(call.get("function"), dict) else {}
                    call_id, name = call.get("id") or call.get("call_id"), fn.get("name") or call.get("name")
                    if not call_id or not name:
                        continue
                    args = fn.get("arguments")
                    parsed = _json_or_none(args) if isinstance(args, str) else args
                    calls.append(ToolCall(str(call_id), str(name), parsed if parsed is not None else args))
                stop = _FINISH_TO_STOP.get(r["finish_reason"] or "", r["finish_reason"] or None)
                if stop is None:
                    stop = "toolUse" if calls else "stop"
                yield Event("assistant", ts, text=text, model=model, provider=provider,
                            tool_calls=tuple(calls), stop_reason=stop)
            elif role == "tool":
                yield Event("tool_result", ts, text=text, tool_call_id=r["tool_call_id"],
                            tool_name=r["tool_name"], is_error=_tool_result_is_error(text))


# ---------------------------------------------------------------------------
# Writer: normalized records -> omp journal


def project_dir_name(cwd: Optional[str], fallback: str) -> str:
    """omp's project folder encoding: ``/workspace/.files`` -> ``--workspace-.files--``."""
    encoded = (cwd or "").strip("/").replace("/", "-")
    return f"--{encoded or fallback}--"


def session_stem(ref: SessionRef) -> str:
    stamp = _iso(ref.started_at).replace(":", "-").replace(".", "-")
    return f"{stamp}_{ref.session_id}"


def _cap(text: str, max_chars: int) -> str:
    if max_chars and len(text) > max_chars:
        return text[:max_chars] + f"\n…[{len(text) - max_chars} chars truncated by hermes export]"
    return text


def render_session(record: SessionRecord, max_chars: int = DEFAULT_MAX_CHARS) -> list[dict]:
    """omp journal entries for one session, chained by ``parentId`` in transcript order."""
    ref = record.ref
    header = {"type": "session", "version": 3, "id": ref.session_id, "timestamp": _iso(ref.started_at),
              "cwd": ref.cwd or ""}
    if record.title:
        header["title"] = record.title
    entries: list[dict] = [header]
    last_id: Optional[str] = None

    def add(entry: dict) -> None:
        nonlocal last_id
        entry["parentId"] = last_id
        last_id = entry["id"]
        entries.append(entry)

    if ref.subagent:
        init = {"type": "session_init", "id": "init", "timestamp": _iso(ref.started_at),
                "agent": record.agent or "subagent"}
        if record.model:
            init["resolvedModel"] = record.model
        add(init)

    prev_ts: Optional[float] = None
    for index, event in enumerate(record.events):
        entry_id = f"e{index}"
        stamp = _iso(event.ts)
        if event.kind == "compaction":
            add({"type": "compaction", "id": entry_id, "timestamp": stamp,
                 "summary": _cap(event.text, max_chars)})
        elif event.kind == "user":
            add({"type": "message", "id": entry_id, "timestamp": stamp,
                 "message": {"role": "user", "content": [{"type": "text", "text": _cap(event.text, max_chars)}],
                             "timestamp": _ms(event.ts)}})
        elif event.kind == "assistant":
            content: list[dict] = []
            if event.text:
                content.append({"type": "text", "text": _cap(event.text, max_chars)})
            for call in event.tool_calls:
                content.append({"type": "toolCall", "id": call.id, "name": call.name,
                                "arguments": call.arguments if call.arguments is not None else {}})
            # No ``api``/``usage``: per-call usage is not recorded by Hermes, so these rows feed the
            # trace (spans, tool calls) while the ``model_usage`` rows below carry the token totals.
            message = {"role": "assistant", "content": content, "model": event.model or "unknown",
                       "provider": event.provider or "hermes", "completedAt": _ms(event.ts)}
            if event.stop_reason:
                message["stopReason"] = event.stop_reason
            if prev_ts is not None and prev_ts <= event.ts:
                message["timestamp"] = _ms(prev_ts)
            else:
                message["timestamp"] = _ms(event.ts)
            add({"type": "message", "id": entry_id, "timestamp": stamp, "message": message})
        elif event.kind == "tool_result":
            message = {"role": "toolResult", "toolCallId": event.tool_call_id or "",
                       "toolName": event.tool_name or "tool",
                       "content": [{"type": "text", "text": _cap(event.text, max_chars)}],
                       "isError": event.is_error, "timestamp": _ms(event.ts)}
            add({"type": "message", "id": entry_id, "timestamp": stamp, "message": message})
        else:
            continue
        prev_ts = event.ts

    usage_entries: list[dict] = []
    for index, row in enumerate(record.usage):
        usage: dict[str, object] = {"input": row.input, "output": row.output, "cacheRead": row.cache_read,
                 "cacheWrite": row.cache_write,
                 "totalTokens": row.input + row.output + row.cache_read + row.cache_write}
        if row.reasoning:
            usage["reasoningTokens"] = row.reasoning
        if row.cost is not None:
            usage["cost"] = {"total": row.cost}
        ts = row.ts or record.ended_at or (record.events[-1].ts if record.events else ref.started_at)
        add({"type": "model_usage", "id": f"u{index}", "timestamp": _iso(ts), "purpose": row.purpose,
             "api": _PROVIDER_API.get(row.provider, "openai-completions"), "provider": row.provider,
             "model": row.model, "usage": usage, "stopReason": "stop"})
        # The trace headline sums assistant usage, and Hermes has usage only per session and model:
        # one zero-width marker turn per usage row carries that total (no ``api``, so the stats
        # ingest still counts the ``model_usage`` row above exactly once).
        usage_entries.append({"type": "message", "id": f"t{index}", "timestamp": _iso(ts), "message": {
            "role": "assistant", "model": row.model, "provider": row.provider, "usage": usage,
            "stopReason": "stop", "timestamp": _ms(ts), "completedAt": _ms(ts),
            "content": [{"type": "text", "text": f"Hermes usage total ({row.purpose}): {row.calls} API calls"}]}})
    for entry in usage_entries:
        add(entry)

    if record.ended_at:
        add({"type": "custom", "customType": "session_exit", "id": "exit", "timestamp": _iso(record.ended_at),
             "data": {"kind": record.end_reason or "ended", "reason": record.end_reason or "ended",
                      "recordedAt": _iso(record.ended_at)}})
    return entries


@dataclass
class ExportReport:
    sessions_dir: Path
    scanned: int = 0
    written: int = 0
    unchanged: int = 0
    removed: int = 0
    seconds: float = 0.0
    paths: dict[str, Path] = field(default_factory=dict)

    def summary(self) -> str:
        return (f"{self.written} written, {self.unchanged} unchanged, {self.removed} removed "
                f"of {self.scanned} sessions in {self.seconds:.1f}s → {self.sessions_dir}")


def _layout(refs: Iterable[SessionRef], fallback: str) -> dict[str, Path]:
    """Relative transcript path per session key: roots under their project dir, subagents nested."""
    by_key = {r.key: r for r in refs}
    paths: dict[str, Path] = {}

    def resolve(ref: SessionRef, seen: frozenset) -> Path:
        if ref.key in paths:
            return paths[ref.key]
        parent = by_key.get(ref.parent_key) if ref.subagent and ref.parent_key else None
        if parent is not None and parent.key not in seen:
            parent_path = resolve(parent, seen | {ref.key})
            path = parent_path.with_suffix("") / f"{session_stem(ref)}.jsonl"
        else:
            path = Path(project_dir_name(ref.cwd, fallback)) / f"{session_stem(ref)}.jsonl"
        paths[ref.key] = path
        return path

    for ref in by_key.values():
        resolve(ref, frozenset())
    return paths


def _write_atomic(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".jsonl", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for entry in entries:
                fh.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        _unlink_quiet(tmp)
        raise


def _unlink_quiet(path: str | Path) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _load_state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": STATE_VERSION, "sessions": {}}
    if not isinstance(data, dict) or data.get("version") != STATE_VERSION:
        return {"version": STATE_VERSION, "sessions": {}}
    data.setdefault("sessions", {})
    return data


def state_file(sessions_dir: Path) -> Path:
    """The watermark file ``export`` keeps next to ``sessions_dir``."""
    return Path(sessions_dir).parent / STATE_FILE


def export(sources: Sequence[SessionSource], sessions_dir: Path, *, state_path: Optional[Path] = None,
           only_keys: Optional[set[str]] = None, max_chars: int = DEFAULT_MAX_CHARS,
           fallback_project: str = "hermes", force: bool = False) -> ExportReport:
    """Write changed sessions of every source into ``sessions_dir``; return what happened.

    ``only_keys`` limits writing to those sessions (and keeps everything else's watermark), which
    lets a caller export the current session first and the backlog later.
    """
    started = time.monotonic()
    sessions_dir = Path(sessions_dir)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_path or state_file(sessions_dir)
    state = _load_state(state_path)
    known: dict = state["sessions"]
    report = ExportReport(sessions_dir=sessions_dir)

    refs_by_source: list[tuple[SessionSource, list[SessionRef]]] = [(s, s.scan()) for s in sources]
    all_refs = [r for _, refs in refs_by_source for r in refs]
    report.scanned = len(all_refs)
    layout = _layout(all_refs, fallback_project)
    report.paths = {k: sessions_dir / p for k, p in layout.items()}

    for source, refs in refs_by_source:
        for ref in refs:
            if only_keys is not None and ref.key not in only_keys:
                continue
            rel = layout[ref.key]
            previous = known.get(ref.key) or {}
            target = sessions_dir / rel
            if (not force and previous.get("fp") == ref.fingerprint and previous.get("path") == str(rel)
                    and target.exists()):
                report.unchanged += 1
                continue
            if previous.get("path") and previous.get("path") != str(rel):
                _unlink_quiet(sessions_dir / previous["path"])
            _write_atomic(target, render_session(source.load(ref), max_chars=max_chars))
            known[ref.key] = {"fp": ref.fingerprint, "path": str(rel)}
            report.written += 1

    if only_keys is None:
        live = {r.key for r in all_refs}
        namespaces = {getattr(s, "namespace", "") for s in sources}
        for key in [k for k in known if k not in live]:
            # Only prune sessions owned by a source exported in this run ("" owns every key).
            if not any(key.startswith(ns) for ns in namespaces):
                continue
            if known[key].get("path"):
                _unlink_quiet(sessions_dir / known[key]["path"])
            del known[key]
            report.removed += 1

    state_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=state_path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    os.replace(tmp, state_path)
    report.seconds = time.monotonic() - started
    return report


def session_tree_keys(refs: Iterable[SessionRef], key: str) -> set[str]:
    """``key``, its subagent ancestors up to the root and every subagent below that root."""
    by_key = {r.key: r for r in refs}
    root = by_key.get(key)
    seen: set[str] = set()
    while root is not None and root.subagent and root.parent_key in by_key and root.key not in seen:
        seen.add(root.key)
        root = by_key[root.parent_key]
    if root is None:
        return {key}
    children: dict[str, list[str]] = {}
    for r in by_key.values():
        if r.subagent and r.parent_key:
            children.setdefault(r.parent_key, []).append(r.key)
    out, stack = set(), [root.key]
    while stack:
        current = stack.pop()
        if current in out:
            continue
        out.add(current)
        stack.extend(children.get(current, ()))
    return out


def hermes_sources(hermes_root: Path, profile: str, all_profiles: bool = False) -> list[HermesStateSource]:
    """Sources for one profile (no key namespace) or every profile (keys namespaced ``<profile>:``)."""
    if not all_profiles:
        return [HermesStateSource(hermes_profile_db(hermes_root, profile), profile)]
    return [HermesStateSource(hermes_profile_db(hermes_root, name), name, namespace=f"{name}:")
            for name in hermes_profiles(hermes_root)]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export Hermes sessions as omp session JSONL.")
    parser.add_argument("--db", type=Path, help="state.db to read (default: the profile's)")
    parser.add_argument("--hermes-root", type=Path, default=Path.home() / ".hermes")
    parser.add_argument("--profile", default=os.environ.get("HERMES_PROFILE", "default"))
    parser.add_argument("--all-profiles", action="store_true")
    parser.add_argument("--out", type=Path, required=True, help="omp sessions dir to write")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--force", action="store_true", help="rewrite every session")
    args = parser.parse_args(argv)
    if args.db:
        sources = [HermesStateSource(args.db, args.profile)]
    else:
        sources = hermes_sources(args.hermes_root, args.profile, args.all_profiles)
    try:
        report = export(sources, args.out, max_chars=args.max_chars, force=args.force)
    finally:
        for source in sources:
            source.close()
    print(report.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
