"""Hermes RFC #143379 isolated mechanism lab.

This is NOT an import of NousResearch/hermes-agent and NOT an upstream regression
suite. Read/anchor semantics intentionally mirror the reviewed PR excerpts;
other components are synthetic controls for designing follow-up tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Callable
import hashlib
import re

DELIMITER = "\n§\n"
DOC_REFERENCE = re.compile(r"@doc:([A-Za-z0-9][A-Za-z0-9._-]*)")
SAFE_DOC = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def doc_name(raw: str) -> str:
    name = raw[:-3] if raw.endswith(".md") else raw
    if not SAFE_DOC.fullmatch(name) or name in {".", ".."}:
        raise ValueError("invalid chain doc name")
    return name


class IsolatedStore:
    """Subset of the two PRs' file/entry mechanics, used only to test invariants.

    In particular, read() follows both PRs' read logic: no read lock, then
    _set_entries(target, freshly-parsed-raw). add() holds the store file lock.
    """

    def __init__(self, root: Path, *, anchor_limit: int = 2200):
        self.root, self.anchor_limit = Path(root), anchor_limit
        self.root.mkdir(parents=True, exist_ok=True)
        self.memory_entries: list[str] = []
        self._doc_entries: dict[str, list[str]] = {}
        self._locks: dict[Path, Lock] = {}
        self._read_hook: Callable[[Path, str], str] | None = None

    def _path_for(self, target: str) -> Path:
        if target.startswith("doc:"):
            return self.root / "docs" / f"{doc_name(target[4:])}.md"
        if target == "memory":
            return self.root / "MEMORY.md"
        if target == "user":
            return self.root / "USER.md"
        raise ValueError("unsupported target")

    def _read_raw_checked(self, path: Path) -> tuple[str, bool]:
        try:
            raw = path.read_text(encoding="utf-8") if path.exists() else ""
        except (PermissionError, UnicodeDecodeError):
            return "", False
        if self._read_hook:
            raw = self._read_hook(path, raw)
        return raw, True

    @staticmethod
    def _parse_entries(raw: str) -> list[str]:
        return [part.strip() for part in raw.split(DELIMITER) if part.strip()]

    def _set_entries(self, target: str, entries: list[str]) -> None:
        if target.startswith("doc:"):
            self._doc_entries[target[4:]] = entries
        elif target == "memory":
            self.memory_entries = entries
        else:
            raise ValueError("unsupported target")

    def _entries_for(self, target: str) -> list[str]:
        return self._doc_entries.get(target[4:], []) if target.startswith("doc:") else self.memory_entries

    def _char_count(self, target: str) -> int:
        return len(DELIMITER.join(self._entries_for(target)))

    def _char_limit(self, target: str) -> int | None:
        return None if target.startswith("doc:") else self.anchor_limit

    def _usage_pct(self, target: str, count: int) -> str:
        limit = self._char_limit(target)
        return f"{count:,} chars (chain doc — uncapped)" if limit is None else f"{int(min(100, count / limit * 100))}% — {count:,}/{limit:,} chars"

    def _read_file(self, path: Path) -> list[str]:
        return self._parse_entries(path.read_text(encoding="utf-8")) if path.exists() else []

    def chain_doc_names(self, entries: list[str] | None = None) -> list[str]:
        return list(dict.fromkeys(n for entry in (self.memory_entries if entries is None else entries)
                                  for n in DOC_REFERENCE.findall(entry) if SAFE_DOC.fullmatch(n)))

    def doc_stats(self, name: str) -> dict:
        values = self._read_file(self._path_for(f"doc:{name}"))
        return {"name": name, "entries": len(values), "chars": len(DELIMITER.join(values))}

    def orphan_doc_names(self) -> list[str]:
        docs_dir = self.root / "docs"
        referenced = set(self.chain_doc_names(self._read_file(self.root / "MEMORY.md")))
        return sorted(doc_name(p.stem) for p in docs_dir.glob("*.md") if doc_name(p.stem) not in referenced) if docs_dir.exists() else []

    def read(self, target: str) -> dict:
        """Intentionally mirrors PR 141876/116673: disk read -> in-memory set,
        with NO _file_lock enclosing these operations. Not byte-for-byte code."""
        path = self._path_for(target)
        raw, read_ok = self._read_raw_checked(path)
        if not read_ok:
            return {"success": False, "error": "read failed"}
        entries = list(dict.fromkeys(self._parse_entries(raw)))
        self._set_entries(target, entries)
        response = {
            "success": True, "target": target, "entries": entries,
            "usage": self._usage_pct(target, self._char_count(target))
        }
        if target == "memory":
            response["chain_docs"] = [self.doc_stats(n) for n in self.chain_doc_names(entries)]
            if orphans := self.orphan_doc_names():
                response["orphan_docs"] = [self.doc_stats(n) for n in orphans]
        return response

    def _anchor_gate(self, target: str) -> bool:
        return not target.startswith("doc:") or target[4:] in self.chain_doc_names(self._read_file(self.root / "MEMORY.md"))

    def add(self, target: str, entry: str) -> dict:
        if not self._anchor_gate(target):
            return {"success": False, "error": "unreferenced doc"}
        path = self._path_for(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = self._locks.setdefault(path, Lock())
        with lock:
            entries = self._read_file(path)
            self._set_entries(target, entries)
            if entry in entries:
                return {"success": True, "message": "already present"}
            total = len(DELIMITER.join(entries + [entry]))
            if (limit := self._char_limit(target)) is not None and total > limit:
                return {"success": False, "error": "anchor over budget"}
            values = entries + [entry]
            self._set_entries(target, values)
            path.write_text(DELIMITER.join(values), encoding="utf-8")
            return {"success": True}


@dataclass(frozen=True)
class Event:
    event_id: str
    revision: int
    scope: str | None
    source_id: str
    source_digest: str
    value: str
    replaces_id: str | None = None
    caller: str = "user"


class SourceArchive:
    """Synthetic independent verifier of scoped, revisioned, source-backed recall.

    Immutable events model the required contract; this is NOT a proposed second DB.
    """
    def __init__(self) -> None:
        self.events: list[Event] = []
        self.sources: dict[str, str] = {}

    def append(self, *, scope: str | None, source_id: str, value: str,
               replaces_id: str | None = None, caller: str = "user") -> Event:
        if source_id in self.sources:
            raise ValueError("source is immutable")
        revision = len(self.events) + 1
        e = Event(f"evt-{revision:04d}", revision, scope, source_id,
                  hashlib.sha256(value.encode()).hexdigest(), value,
                  replaces_id=replaces_id, caller=caller)
        self.events.append(e)
        self.sources[source_id] = value
        return e

    def retrieve(self, *, scope: str, source_id: str) -> dict:
        # Unknown, missing, or cross-workstream scopes NEVER widen to global.
        candidates = [e for e in self.events if e.source_id == source_id]
        if not candidates or candidates[0].scope != scope or not scope:
            return {"verdict": "ABSTAIN", "reason": "missing or unauthorized source"}
        e = candidates[0]
        if hashlib.sha256(self.sources.get(source_id, "").encode()).hexdigest() != e.source_digest:
            return {"verdict": "ABSTAIN", "reason": "source revision mismatch"}
        seen = {e.event_id}
        # Only explicitly user-accepted corrections can supersede user evidence.
        while True:
            successors = [v for v in self.events if v.replaces_id == e.event_id and v.scope == scope and v.caller == "user"]
            if not successors:
                break
            candidate = max(successors, key=lambda v: v.revision)
            if candidate.event_id in seen:
                return {"verdict": "ABSTAIN", "reason": "correction cycle"}
            seen.add(candidate.event_id)
            e = candidate
            if hashlib.sha256(self.sources.get(e.source_id, "").encode()).hexdigest() != e.source_digest:
                return {"verdict": "ABSTAIN", "reason": "corrected source revision mismatch"}
        return {"verdict": "FOUND", "source_id": e.source_id, "event_id": e.event_id,
                "value": e.value, "revision": e.revision}


class BoundedDocReader:
    """Design alternative: read only a byte range, plus a resumption offset."""
    def __init__(self, max_bytes: int = 4096):
        self.max_bytes = max_bytes

    def read(self, path: Path, start: int = 0) -> dict:
        if start < 0:
            raise ValueError("negative cursor")
        if self.max_bytes < 4:
            raise ValueError("max_bytes must fit any UTF-8 codepoint")
        with path.open("rb") as f:
            f.seek(0, 2)
            total = f.tell()
            if start > total:
                raise ValueError("cursor past end of file")
            f.seek(start)
            data = f.read(self.max_bytes)
        # Cursor always falls on a UTF-8 boundary. If the last codepoint is
        # partial, send it in the next chunk; never replace exact bytes with U+FFFD.
        while data:
            try:
                text = data.decode("utf-8", errors="strict")
                break
            except UnicodeDecodeError as e:
                if e.end != len(data):
                    raise
                data = data[:e.start]
        else:
            text = ""
        if start < total and not data:
            raise ValueError("no complete UTF-8 codepoint fits in max_bytes")
        return {"data": text, "bytes": len(data),
                "next_cursor": start + len(data) if start + len(data) < total else None}
