"""Read-only copied-session lineage browser; this is not an in-file entry DAG."""
from __future__ import annotations

from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method
_profile_scoped = _registry.profile_scoped


def _tree_rows(db) -> list[dict]:
    from hermes_state_common import _shape_preview, _sql_preview_raw

    # Metadata and the existing bounded first-prompt preview only: no history
    # hydration, token flush or recursive SQL (damaged cycles stay browseable).
    rows = db._read_all(f"""
        SELECT s.id, s.title, s.started_at, s.message_count, s.source, s.cwd,
               s.parent_session_id, s.model_config, s.end_reason, {_sql_preview_raw()}
        FROM sessions s WHERE s.hidden = 0 AND s.archived = 0
        ORDER BY s.started_at DESC, s.id DESC
    """)
    result = []
    for raw in rows:
        row = dict(raw)
        config = _parse_model_config(row.get("model_config"), quiet=True)
        if _denied_source(row) or config.get("_delegate_from"):
            continue
        parent = row.get("parent_session_id")
        point = config.get("_branch_point")
        point = point if isinstance(point, dict) and point.get("parent_session_id") == parent else {}
        target = point.get("message_id")
        count = point.get("copied_message_count")
        result.append({
            "id": row["id"], "title": row.get("title") or "", "preview": _shape_preview(row.get("_preview_raw")),
            "started_at": row.get("started_at") or 0, "message_count": row.get("message_count") or 0,
            "source": row.get("source") or "", "cwd": row.get("cwd") or "",
            "parent_session_id": parent,
            "edge_kind": "fork" if parent and config.get("_branched_from") == parent else "parent" if parent else "root",
            "branch_message_id": target if type(target) is int and target > 0 else None,
            "copied_message_count": count if type(count) is int and count >= 0 else None,
            "_end_reason": row.get("end_reason"),
        })
    reasons = {row["id"]: row["_end_reason"] for row in result}
    for row in result:
        if row["edge_kind"] == "parent" and reasons.get(row["parent_session_id"]) == "compression":
            row["edge_kind"] = "continuation"
        del row["_end_reason"]
    return result


def _tree_page(rows: list[dict], params: dict) -> dict:
    by_id = {row["id"]: row for row in rows}
    words = _str_param(params, "query").casefold().split()
    matches = [row for row in rows if all(word in " ".join(
        str(row.get(key) or "") for key in ("id", "title", "cwd", "source", "preview")).casefold() for word in words)]
    active_path = set()
    current = params.get("active_session_id")
    while current in by_id and current not in active_path:
        active_path.add(current)
        current = by_id[current]["parent_session_id"]
    sort = params.get("sort", "recent")
    sorters = {
        "recent": lambda row: (-row["started_at"], row["id"]),
        "title": lambda row: (row["title"].casefold(), row["id"]),
        "path": lambda row: (row["cwd"].casefold(), row["id"]),
    }
    matches.sort(key=lambda row: (row["id"] not in active_path,
                                  row["id"] != params.get("selected_session_id"), sorters[sort](row)))
    offset, limit = params.get("offset", 0), params.get("limit", 200)
    page = matches[offset:offset + limit]
    included = {row["id"] for row in page}
    ancestors = []
    for row in page:
        current = row["parent_session_id"]
        while current in by_id and current not in included:
            included.add(current)
            parent = by_id[current]
            ancestors.append(parent)
            current = parent["parent_session_id"]
    end = offset + len(page)
    return {"sessions": page, "ancestors": ancestors, "total": len(matches),
            "next_offset": end if end < len(matches) else None}


@method("session.tree")
@_profile_scoped
def _(rid, params: dict) -> dict:
    from pydantic import ValidationError
    from .contracts.sessions import SessionTreeParams

    try:
        params = SessionTreeParams.model_validate(params).model_dump(mode="json")
    except ValidationError as exc:
        return _err(rid, 4000, str(exc))
    with _profile_db(params) as db:
        if db is None:
            return _db_unavailable_error(rid, code=5006)
        try:
            return _ok(rid, _tree_page(_tree_rows(db), params))
        except Exception as exc:
            return _err(rid, 5006, str(exc))


@method("session.rename")
@_profile_scoped
def _(rid, params: dict) -> dict:
    from pydantic import ValidationError
    from .contracts.sessions import SessionRenameParams

    try:
        params = SessionRenameParams.model_validate(params).model_dump(mode="json")
    except ValidationError as exc:
        return _err(rid, 4000, str(exc))
    target, title = _str_param(params, "session_key"), _str_param(params, "title")
    if not title:
        return _err(rid, 4021, "title required")
    with _profile_db(params, writer=True) as db:
        if db is None:
            return _db_unavailable_error(rid, code=5007)
        row = db.get_session(target)
        if not row or row.get("hidden") or row.get("archived") or _denied_source(row):
            return _err(rid, 4007, "session not found")
        try:
            db.set_session_title(target, title)
            canonical = db.get_session_title(target)
            if canonical != title:
                return _err(rid, 5007, "rename was not persisted")
        except ValueError as exc:
            return _err(rid, 4022, str(exc))
        except Exception as exc:
            return _err(rid, 5007, str(exc))
        return _ok(rid, {"session_key": target, "title": canonical})


def register(server) -> None:
    bind_module(globals(), server, skip=("_",))
