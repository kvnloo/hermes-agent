#!/usr/bin/env python3
"""Select the one explicit current Firstmate causality evidence revision."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MetadataError(ValueError):
    """Raised when revision metadata cannot select one current revision."""


def select_current(metadata: dict[str, Any]) -> dict[str, Any]:
    pointer = metadata.get("currentRevision")
    revisions = metadata.get("revisions")
    superseded = metadata.get("superseded")
    if not isinstance(pointer, str) or not pointer:
        raise MetadataError("missing or invalid currentRevision")
    if not isinstance(revisions, dict) or pointer not in revisions:
        raise MetadataError("currentRevision does not select a revisions entry")
    if not isinstance(superseded, dict):
        raise MetadataError("missing superseded revision history")
    if pointer in superseded:
        raise MetadataError("currentRevision is ambiguously also superseded")
    current = revisions[pointer]
    if not isinstance(current, dict) or current.get("status") != "current":
        raise MetadataError("selected revision is not explicitly current")
    other_current = [key for key, value in revisions.items() if isinstance(value, dict) and value.get("status") == "current" and key != pointer]
    if other_current:
        raise MetadataError("multiple revisions are marked current")
    return current


def load_current(path: Path) -> dict[str, Any]:
    return select_current(json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(load_current(root / "proactivity-root-cause.json"), indent=2, sort_keys=True))