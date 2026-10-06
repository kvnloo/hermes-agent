#!/usr/bin/env python3
"""Conservative semantic-anchor probe for Change IR fixtures.

This tool finds textual evidence only. It never claims semantic equivalence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ANCHOR_STATES = {"present", "partial", "missing"}


def _candidate_files(root: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _first_hit(files: list[Path], term: str) -> dict[str, Any] | None:
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, 1):
            if term in line:
                return {"path": str(path), "line": lineno, "text": line.strip()[:240]}
    return None


def probe_anchor(root: Path, anchor: dict[str, Any]) -> dict[str, Any]:
    files = _candidate_files(root, anchor.get("paths", []))
    all_terms = list(anchor.get("all_terms", []))
    any_terms = list(anchor.get("any_terms", []))
    terms = list(dict.fromkeys(all_terms + any_terms))
    hits = {term: _first_hit(files, term) for term in terms}

    all_ok = all(hits.get(term) is not None for term in all_terms)
    any_ok = not any_terms or any(hits.get(term) is not None for term in any_terms)
    any_hit = any(hit is not None for hit in hits.values())

    if all_ok and any_ok:
        state = "present"
    elif any_hit:
        state = "partial"
    else:
        state = "missing"

    return {
        "id": anchor["id"],
        "description": anchor.get("description", ""),
        "state": state,
        "files_scanned": [str(path) for path in files],
        "hits": hits,
    }


def probe_operation(root: Path, operation: dict[str, Any]) -> dict[str, Any]:
    anchors = [probe_anchor(root, anchor) for anchor in operation.get("anchors", [])]
    states = [anchor["state"] for anchor in anchors]
    if states and all(state == "present" for state in states):
        anchor_state = "present"
    elif states and all(state == "missing" for state in states):
        anchor_state = "missing"
    elif states:
        anchor_state = "partial"
    else:
        anchor_state = "missing"

    return {
        "id": operation["id"],
        "description": operation.get("description", ""),
        "anchor_state": anchor_state,
        "anchors": anchors,
        "expected_refresh_state": operation.get("expected_refresh_state"),
        "note": operation.get("note"),
    }


def probe_fixture(root: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    operations = [probe_operation(root, op) for op in fixture.get("operations", [])]
    return {
        "change_id": fixture["change_id"],
        "title": fixture.get("title", ""),
        "repo": str(root.resolve()),
        "operations": operations,
        "warning": (
            "Anchor states are textual evidence only. They do not prove semantic "
            "equivalence or determine a refresh state."
        ),
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# Refresh probe: {result['change_id']}",
        "",
        result["warning"],
        "",
        "| operation | anchor state | expected fixture state |",
        "|---|---|---|",
    ]
    for op in result["operations"]:
        lines.append(
            f"| `{op['id']}` | {op['anchor_state']} | "
            f"{op.get('expected_refresh_state') or '—'} |"
        )

    for op in result["operations"]:
        lines.extend(["", f"## {op['id']}", "", op["description"]])
        if op.get("note"):
            lines.extend(["", f"Fixture note: {op['note']}"])
        for anchor in op["anchors"]:
            lines.extend(
                [
                    "",
                    f"- `{anchor['id']}`: **{anchor['state']}** — "
                    f"{anchor['description']}",
                ]
            )
            for term, hit in anchor["hits"].items():
                if hit:
                    lines.append(
                        f"  - `{term}` → `{hit['path']}:{hit['line']}`"
                    )
                else:
                    lines.append(f"  - `{term}` → not found")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    result = probe_fixture(args.repo, fixture)

    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render_markdown(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
