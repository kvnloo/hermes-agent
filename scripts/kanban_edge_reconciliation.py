#!/usr/bin/env python3
"""Generate a read-only dangling Kanban edge reconciliation manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

QUERY = """SELECT
  l.parent_id,
  l.child_id,
  CASE
    WHEN p.id IS NULL AND c.id IS NULL THEN 'both_missing'
    WHEN p.id IS NULL THEN 'missing_parent'
    WHEN c.id IS NULL THEN 'missing_child'
  END AS structural_class,
  p.id, p.status, p.assignee, p.tenant, p.created_at, p.completed_at,
  c.id, c.status, c.assignee, c.tenant, c.created_at, c.completed_at
FROM task_links AS l
LEFT JOIN tasks AS p ON p.id = l.parent_id
LEFT JOIN tasks AS c ON c.id = l.child_id
WHERE p.id IS NULL OR c.id IS NULL
ORDER BY l.parent_id, l.child_id"""

COUNT_QUERY = """SELECT
  (SELECT COUNT(*) FROM tasks) AS task_count,
  (SELECT COUNT(*) FROM task_links) AS link_count,
  (SELECT COUNT(*) FROM task_links l
     LEFT JOIN tasks p ON p.id = l.parent_id
     LEFT JOIN tasks c ON c.id = l.child_id
   WHERE p.id IS NULL OR c.id IS NULL) AS dangling_count"""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _typed(value: Any) -> list[Any]:
    if value is None:
        return ["null", None]
    if isinstance(value, bytes):
        return ["blob", value.hex()]
    if isinstance(value, int):
        return ["integer", value]
    if isinstance(value, float):
        return ["real", repr(value)]
    return ["text", str(value)]


def _ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def logical_sentinel(conn: sqlite3.Connection) -> dict[str, Any]:
    """Hash all schema and row values in the current read transaction."""
    digest = hashlib.sha256()
    tables: list[dict[str, Any]] = []
    schema_rows = conn.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    digest.update(
        json.dumps([list(row) for row in schema_rows], ensure_ascii=False, separators=(",", ":")).encode()
    )
    for (table_name,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ):
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({_ident(table_name)})")]
        select = ", ".join(_ident(column) for column in columns)
        order = ", ".join(_ident(column) for column in columns)
        row_count = 0
        for row in conn.execute(f"SELECT {select} FROM {_ident(table_name)} ORDER BY {order}"):
            digest.update(json.dumps([_typed(value) for value in row], separators=(",", ":")).encode())
            digest.update(b"\n")
            row_count += 1
        tables.append({"name": table_name, "rows": row_count})
    return {"sha256": digest.hexdigest(), "tables": tables}


def _endpoint(row: sqlite3.Row, prefix: str) -> dict[str, Any] | None:
    endpoint_id = row[f"{prefix}_endpoint_id"]
    if endpoint_id is None:
        return None
    return {
        "id": endpoint_id,
        "status": row[f"{prefix}_status"],
        "assignee": row[f"{prefix}_assignee"],
        "tenant": row[f"{prefix}_tenant"],
        "created_at": row[f"{prefix}_created_at"],
        "completed_at": row[f"{prefix}_completed_at"],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    source = report["source"]
    counts = report["counts"]
    lines = [
        "# Production Kanban dangling-edge reconciliation manifest",
        "",
        f"Observed: `{report['observed_at']}`",
        f"Database: `{source['canonical_path']}`",
        f"Identity: device `{source['device']}`, inode `{source['inode']}`",
        f"SQLite user/schema version: `{source['user_version']}` / `{source['schema_version']}`",
        f"Input file SHA-256: `{source['input_file_sha256']}`",
        f"Query SHA-256: `{report['query_sha256']}`",
        "",
        "## Read-only proof",
        "",
        f"- Open mode: `{source['open_mode']}`; `PRAGMA query_only={str(source['query_only']).upper()}`.",
        f"- Logical sentinel before: `{report['logical_sentinel']['before']['sha256']}`.",
        f"- Logical sentinel after: `{report['logical_sentinel']['after']['sha256']}`.",
        f"- Equal: `{report['logical_sentinel']['equal']}`.",
        f"- External post-transaction sentinel equal: `{report['logical_sentinel']['external_equal']}`.",
        f"- Input file SHA-256 after: `{source['output_file_sha256']}` (equal: `{source['file_hash_equal']}`).",
        "- No INSERT, UPDATE, DELETE, schema statement, backup, checkpoint, or writable connection is used.",
        "",
        "## Fresh counts",
        "",
        f"- Tasks: **{counts['tasks']}**",
        f"- Dependency edges: **{counts['links']}**",
        f"- Dangling edges: **{counts['dangling']}**",
        f"- Missing parent: **{counts['missing_parent']}**",
        f"- Missing child: **{counts['missing_child']}**",
        f"- Both endpoints missing: **{counts['both_missing']}**",
        "",
        "## Decision policy",
        "",
        "Structural absence is proven only within this exact board snapshot. Cross-board/legacy provenance is UNKNOWN because no provenance registry is present in the canonical database. Every edge therefore defaults to proposed `retain` with low confidence. These are proposals only; this manifest authorizes no mutation.",
        "",
        "## Exact query",
        "",
        "```sql",
        report["query"],
        "```",
        "",
        "## Dangling edges",
        "",
        "| Parent | Child | Structural class | Surviving endpoint metadata | Provenance | Proposed action | Confidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for edge in report["edges"]:
        endpoint = edge["parent"] or edge["child"]
        metadata = "none" if endpoint is None else "; ".join(
            f"{key}={value}" for key, value in endpoint.items() if value is not None
        )
        lines.append(
            f"| `{edge['parent_id']}` | `{edge['child_id']}` | `{edge['structural_class']}` | "
            f"{metadata} | `UNKNOWN` | `retain` | `low` |"
        )
    lines.extend([
        "",
        "## Governance boundary",
        "",
        "Any migration is a separate Captain-approved card requiring a backup, rollback plan, and independent verifier. Blind deletion is explicitly rejected.",
        "",
        "## Reproduction",
        "",
        "```text",
        report["reproduction_command"],
        "```",
        "",
    ])
    return "\n".join(lines)


def generate(db_arg: str, json_path: Path, markdown_path: Path, seals_path: Path) -> dict[str, Any]:
    supplied = Path(db_arg).expanduser()
    if not supplied.is_absolute():
        raise ValueError("--db must be an explicit absolute path; ambient board resolution is forbidden")
    canonical = supplied.resolve(strict=True)
    stat_before = canonical.stat()
    file_hash_before = _file_sha256(canonical)
    uri = f"file:{quote(str(canonical), safe='/')}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("PRAGMA query_only").fetchone()[0] != 1:
            raise RuntimeError("SQLite query_only could not be enabled")
        conn.execute("BEGIN")
        before = logical_sentinel(conn)
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
        schema_version = conn.execute("PRAGMA schema_version").fetchone()[0]
        task_count, link_count, dangling_count = conn.execute(COUNT_QUERY).fetchone()
        rows = conn.execute(
            "SELECT l.parent_id, l.child_id, "
            "CASE WHEN p.id IS NULL AND c.id IS NULL THEN 'both_missing' "
            "WHEN p.id IS NULL THEN 'missing_parent' ELSE 'missing_child' END AS structural_class, "
            "p.id AS parent_endpoint_id, p.status AS parent_status, p.assignee AS parent_assignee, "
            "p.tenant AS parent_tenant, p.created_at AS parent_created_at, p.completed_at AS parent_completed_at, "
            "c.id AS child_endpoint_id, c.status AS child_status, c.assignee AS child_assignee, "
            "c.tenant AS child_tenant, c.created_at AS child_created_at, c.completed_at AS child_completed_at "
            "FROM task_links l LEFT JOIN tasks p ON p.id=l.parent_id LEFT JOIN tasks c ON c.id=l.child_id "
            "WHERE p.id IS NULL OR c.id IS NULL ORDER BY l.parent_id, l.child_id"
        ).fetchall()
        after = logical_sentinel(conn)
        conn.rollback()
    finally:
        conn.close()

    post_conn = sqlite3.connect(uri, uri=True)
    try:
        post_conn.execute("PRAGMA query_only=ON")
        post_conn.execute("BEGIN")
        external_after = logical_sentinel(post_conn)
        post_conn.rollback()
    finally:
        post_conn.close()
    stat_after = canonical.stat()
    file_hash_after = _file_sha256(canonical)

    classes = {"missing_parent": 0, "missing_child": 0, "both_missing": 0}
    edges = []
    for row in rows:
        classes[row["structural_class"]] += 1
        edges.append({
            "parent_id": row["parent_id"],
            "child_id": row["child_id"],
            "structural_class": row["structural_class"],
            "parent": _endpoint(row, "parent"),
            "child": _endpoint(row, "child"),
            "provenance": {"classification": "UNKNOWN", "cross_board_or_legacy_evidence": None},
            "proposal": {
                "action": "retain",
                "rationale": "Endpoint absence is proven in this snapshot, but origin and intended dependency are not; retain pending owner review.",
                "confidence": "low",
                "executed": False,
            },
        })
    if len(edges) != dangling_count:
        raise RuntimeError("count/detail query mismatch")

    command = (
        f"python scripts/kanban_edge_reconciliation.py --db {canonical} "
        f"--json {json_path} --markdown {markdown_path} --seals {seals_path}"
    )
    report = {
        "schema_version": 1,
        "kind": "no-write-production-kanban-edge-reconciliation",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "supplied_path": str(supplied),
            "canonical_path": str(canonical),
            "device": stat_before.st_dev,
            "inode": stat_before.st_ino,
            "size_before": stat_before.st_size,
            "size_after": stat_after.st_size,
            "mtime_ns_before": stat_before.st_mtime_ns,
            "mtime_ns_after": stat_after.st_mtime_ns,
            "user_version": user_version,
            "schema_version": schema_version,
            "input_file_sha256": file_hash_before,
            "output_file_sha256": file_hash_after,
            "file_hash_equal": file_hash_before == file_hash_after,
            "open_mode": "SQLite URI mode=ro",
            "query_only": True,
        },
        "logical_sentinel": {
            "scope": "all non-internal SQLite schema objects and all values in all user tables",
            "before": before,
            "after": after,
            "equal": before == after,
            "external_after": external_after,
            "external_equal": before == external_after,
        },
        "query": QUERY,
        "query_sha256": _sha256_bytes(QUERY.encode()),
        "counts": {"tasks": task_count, "links": link_count, "dangling": dangling_count, **classes},
        "redaction": {
            "excluded": ["tasks.body", "tasks.result", "task_comments", "event payloads", "credentials", "secrets"],
            "surviving_endpoint_fields": ["id", "status", "assignee", "tenant", "created_at", "completed_at"],
        },
        "policy": {
            "proposals_only": True,
            "default_when_provenance_absent": {"provenance": "UNKNOWN", "action": "retain", "confidence": "low"},
            "migration_authority": False,
            "future_migration_requirements": ["separate Captain-approved card", "backup", "rollback", "independent verifier"],
        },
        "edges": edges,
        "reproduction_command": command,
    }
    if not report["logical_sentinel"]["equal"]:
        raise RuntimeError("logical sentinel changed inside the read transaction")

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")
    seals = {
        "schema_version": 1,
        "algorithm": "sha256",
        "files": {
            json_path.name: _file_sha256(json_path),
            markdown_path.name: _file_sha256(markdown_path),
        },
    }
    seals_path.write_text(json.dumps(seals, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, help="explicit absolute production DB path")
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--seals", required=True, type=Path)
    args = parser.parse_args()
    report = generate(args.db, args.json, args.markdown, args.seals)
    print(json.dumps({"counts": report["counts"], "logical_sentinel": report["logical_sentinel"]["equal"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
