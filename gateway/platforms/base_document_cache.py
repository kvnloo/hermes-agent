"""Prepare safe display names for cached inbound documents."""

from pathlib import Path


_DOCUMENT_NAME_BUDGET = 255 - len("doc_") - 12 - len("_")


def safe_document_cache_name(filename: str) -> str:
    """Keep a sanitized leaf name within the 255-byte filesystem component limit."""
    safe_name = (Path(filename).name if filename else "document").replace("\x00", "").strip()
    if not safe_name or safe_name in {".", ".."}:
        safe_name = "document"
    # The UUID prefix takes 17 bytes. Keep any already-fitting name unchanged.
    if len(safe_name.encode("utf-8")) <= _DOCUMENT_NAME_BUDGET:
        return safe_name

    # Only names that cannot fit need UTF-8-safe shortening. Preserve the extension.
    stem, dot, ext = safe_name.rpartition(".")
    if not dot:
        stem, ext = safe_name, ""
    stem = stem.encode("utf-8")[:180].decode("utf-8", errors="ignore").rstrip() or "document"
    ext = ext.encode("utf-8")[:32].decode("utf-8", errors="ignore")
    return f"{stem}.{ext}" if ext else stem
