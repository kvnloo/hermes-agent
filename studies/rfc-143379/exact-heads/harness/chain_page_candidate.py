"""Downstream candidate, not upstream behavior: bounded reads of real chain-doc files.

Both decoded content UTF-8 bytes AND the complete compact UTF-8 JSON response are
at most 4096 bytes. Envelope means every serialized byte except the JSON encoding
of the content value; escaping is charged to the complete-response bound. Thus a
page usually contains less than 4096 source bytes. Offsets address exact on-disk
bytes, not MemoryStore's stripped/deduplicated entry view. The cursor is portable
JSON state (not an authorization token) pinned to checkout SHA, absolute doc path,
file SHA-256 and byte length. Cooperative writes use the actual store file lock.
Every page hashes the source with bounded working memory; this is O(file size)
I/O per page, not a claim of bounded total I/O or a production indexing solution.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PAGE_BYTES = 4096


def serialize(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _error(code: str) -> dict:
    return {"success": False, "error": code}


def read_chain_page(store, doc: str, checkout_sha: str, cursor: dict | None = None) -> dict:
    """Read actual ``MemoryStore._path_for(doc_target(name))``; never call unbounded read.

    Resuming with changed source content fails closed. Reads intentionally retain
    upstream orphan readability; anchor presence is not a read permission. There
    is no write/approval bypass: this helper only reads a synthetic store's file.
    """
    from tools.memory_tool_store import doc_name, doc_target

    name = doc_name(doc)
    if name is None:
        return _error("invalid_doc")
    if not store.target_enabled("memory"):
        return _error("memory_disabled")
    path = Path(store._path_for(doc_target(name))).resolve()
    try:
        with store._file_lock(path):
            with path.open("rb") as stream:
                digest = hashlib.sha256()
                total = 0
                while block := stream.read(65536):
                    digest.update(block)
                    total += len(block)
                source = {"checkout_sha": checkout_sha, "path": str(path),
                          "sha256": digest.hexdigest(), "bytes": total}
                offset = 0
                if cursor is not None:
                    if not isinstance(cursor, dict) or cursor.get("version") != 1:
                        return _error("invalid_cursor")
                    if cursor.get("source") != source:
                        return _error("source_changed")
                    offset = cursor.get("byte_offset")
                    if type(offset) is not int or not 0 <= offset <= total:
                        return _error("invalid_offset")
                stream.seek(offset)
                raw = stream.read(PAGE_BYTES)
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError as exc:
                    if exc.reason != "unexpected end of data" or offset + len(raw) == total:
                        return _error("invalid_utf8_or_offset")
                    text = raw[:exc.start].decode("utf-8")

                def response(prefix: str) -> dict:
                    end = offset + len(prefix.encode("utf-8"))
                    return {"success": True, "source": source, "byte_offset": offset,
                            "next_byte_offset": end, "content": prefix, "eof": end == total,
                            "next_cursor": None if end == total else
                            {"version": 1, "source": source, "byte_offset": end}}

                page = response(text)
                if len(serialize(page).encode("utf-8")) > PAGE_BYTES:
                    # All prefixes below len(text) are non-EOF, with monotonic wire size.
                    low, high = 0, len(text) - 1
                    while low <= high:
                        middle = (low + high) // 2
                        candidate = response(text[:middle])
                        if len(serialize(candidate).encode("utf-8")) <= PAGE_BYTES:
                            low = middle + 1
                        else:
                            high = middle - 1
                    if high <= 0:
                        return _error("envelope_exceeds_page_budget")
                    page = response(text[:high])
                if not page["content"] and not page["eof"]:
                    return _error("no_progress")
                return page
    except (OSError, UnicodeError):
        return _error("source_unreadable")
