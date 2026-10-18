"""Agent hub projection over the existing registry and canonical session store.

Durable lineage grants read access, never live control. No transcript path or task
index supplied by a client is opened, and no completed child is restarted.
"""
from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method


def _hub_stored(db, owner):
    """Walk delegate and compression edges only; UNION makes damaged cycles finite."""
    roots = {str(owner.get("session_key") or ""), str(getattr(owner.get("agent"), "session_id", "") or "")}
    roots.discard("")
    if db is None or not roots:
        return []
    # Include earlier compression segments so children dispatched before rotation remain visible.
    seeds = set(roots)
    for root in roots:
        seeds.update(db._resume_lineage_ids(root))
    marks = ",".join("?" for _ in seeds)
    with db._read_ctx() as conn:
        rows = conn.execute(f"""WITH RECURSIVE tree(id) AS (
            SELECT id FROM sessions WHERE id IN ({marks})
            UNION SELECT s.id FROM sessions s JOIN tree t ON s.parent_session_id = t.id
            JOIN sessions p ON p.id = t.id
            WHERE s.source = 'subagent' OR
                  (json_valid(s.model_config) AND json_extract(s.model_config, '$._delegate_from') = t.id)
                  OR p.end_reason = 'compression'
        ) SELECT s.* FROM sessions s JOIN tree t ON t.id = s.id
          WHERE s.id NOT IN ({marks}) ORDER BY s.started_at, s.id""", [*seeds, *seeds]).fetchall()
    return [dict(row) for row in rows]


def _hub_row(record, *, owned, stored=None):
    import json

    stored = stored or {}
    config = stored.get("model_config") or "{}"
    try:
        config = json.loads(config) if isinstance(config, str) else config
    except ValueError:
        config = {}
    if not isinstance(config, dict):
        config = {}
    agent = record.get("agent")
    child_sid = str(getattr(agent, "session_id", "") or stored.get("id") or "") or None
    status = record.get("status") or {
        "completed": "completed", "normal": "completed", "error": "failed", "failed": "failed",
        "interrupted": "cancelled", "cancelled": "cancelled",
    }.get(stored.get("end_reason"), "unknown")
    if record.get("cancel_requested") and status in {"running", "idle", "pending", "queued", "starting"}:
        status = "cancel_requested"
    role = getattr(agent, "_delegate_role", None) or config.get("_delegate_role")
    controllable = owned and child_sid is not None and agent is not None and role != "advisor"
    active = status in {"running", "idle", "pending", "queued", "starting"}
    return {
        "id": child_sid or record["subagent_id"], "subagent_id": record.get("subagent_id") or config.get("_subagent_id"),
        "child_session_id": child_sid,
        "parent_id": record.get("parent_id") or config.get("_parent_subagent_id") or stored.get("parent_session_id"),
        "goal": record.get("goal") or config.get("_delegate_goal") or stored.get("title") or "Subagent",
        "model": record.get("model") or stored.get("model"), "status": status,
        "last_tool": record.get("last_tool"),
        "actions": {"send": bool(controllable and active and record.get("accepting_steer") and callable(getattr(agent, "steer", None))),
                    "stop": bool(controllable and active and (callable(getattr(agent, "hard_interrupt", None)) or callable(getattr(agent, "interrupt", None)))),
                    "transcript": bool(stored)},
    }


@method("subagent.hub")
@_registry.profile_scoped
def _agent_hub(rid, params):
    sid = _str_param(params, "session_id")
    transport, owner = _current_session_steer_authority(sid)
    if transport is None or owner is None:
        return _err(rid, 4001, "session not found or not owned by this transport")
    with _session_db(owner) as db:
        stored = {row["id"]: row for row in _hub_stored(db, owner)}
    owned = {r["subagent_id"] for r in _owned_subagent_records(sid, transport, owner)}
    rows = {}
    for record in _visible_subagent_records(sid, transport, owner):
        csid = str(getattr(record.get("agent"), "session_id", "") or "")
        row = _hub_row(record, owned=record["subagent_id"] in owned, stored=stored.pop(csid, None))
        rows[row["id"]] = row
    for child in stored.values():
        row = _hub_row({}, owned=False, stored=child)
        rows[row["id"]] = row
    return _ok(rid, {"agents": list(rows.values())})


@method("subagent.transcript")
@_registry.profile_scoped
def _agent_transcript(rid, params):
    from pydantic import ValidationError
    from tui_gateway.contracts.agent_hub import AgentTranscriptParams

    try:
        request = AgentTranscriptParams.model_validate(params)
    except ValidationError as exc:
        return _err(rid, 4000, str(exc))
    transport, owner = _current_session_steer_authority(request.session_id)
    if transport is None or owner is None:
        return _err(rid, 4001, "session not found or not owned by this transport")
    with _session_db(owner) as db:
        children = {row["id"] for row in _hub_stored(db, owner)}
        if request.child_session_id not in children:
            return _err(rid, 4044, "child transcript not found in this conversation")
        # Same projection while running and after completion: no lossy live-log replacement.
        rows = db.get_messages(request.child_session_id, include_compacted=True, include_ancestors=True,
                               offset=request.offset, limit=request.limit + 1)
    more = len(rows) > request.limit
    return _ok(rid, {"child_session_id": request.child_session_id, "available": True,
                     "messages": rows[:request.limit],
                     "next_offset": request.offset + request.limit if more else None})


def _hub_control(rid, params, *, stop):
    from pydantic import ValidationError
    from tui_gateway.contracts.agent_hub import AgentControlParams, AgentMessageParams
    from tools.delegate_tool_registry import _active_subagents, _active_subagents_lock, _subagent_transport_matches
    from agent.interrupt_compat import request_hard_interrupt

    try:
        request = (AgentControlParams if stop else AgentMessageParams).model_validate(params)
    except ValidationError as exc:
        return _err(rid, 4000, str(exc))
    transport, owner = _current_session_steer_authority(request.session_id)
    if transport is None or owner is None:
        return _err(rid, 4001, "session not found or not owned by this transport")
    rejected = {"status": "rejected"}
    with _active_subagents_lock:
        record = _active_subagents.get(request.subagent_id)
        if not record or record.get("owner_session_id") != request.session_id or record.get("owner_session_record") is not owner:
            return _ok(rid, rejected)
        if not _subagent_transport_matches(record, transport):
            return _ok(rid, rejected)
        agent = record.get("agent")
        if str(getattr(agent, "session_id", "")) != request.child_session_id:
            return _ok(rid, rejected)
        row = _hub_row(record, owned=True)
        if not row["actions"]["stop" if stop else "send"]:
            return _ok(rid, rejected)
        if not stop:
            if not request.text.strip():
                return _err(rid, 4000, "text must not be blank")
            # Acceptance and final steering drain use the same lock.
            accepted = bool(agent.steer(request.text))
            return _ok(rid, {"status": "queued"} if accepted else rejected)
    accepted = bool(request_hard_interrupt(agent, "Agent hub stop requested"))
    if accepted:
        with _active_subagents_lock:
            if _active_subagents.get(request.subagent_id) is record:
                record["cancel_requested"] = True
    return _ok(rid, {"status": "cancel_requested"} if accepted else rejected)


@method("subagent.message")
@_registry.profile_scoped
def _agent_message(rid, params):
    return _hub_control(rid, params, stop=False)


@method("subagent.stop")
@_registry.profile_scoped
def _agent_stop(rid, params):
    return _hub_control(rid, params, stop=True)


def register(server):
    bind_module(globals(), server)
    server._LONG_HANDLERS = server._LONG_HANDLERS | _registry.names()
