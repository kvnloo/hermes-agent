"""Durable-only forks for another process/pane; never build or adopt a child agent here."""
from __future__ import annotations

from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method
_profile_scoped = _registry.profile_scoped


def _fork_history(db, session: dict, parent: str, target: int | None) -> list:
    from copy import deepcopy

    # Use the same display lineage as resume, retaining tools and reasoning (the
    # interactive branch picker intentionally keeps only visible text rows).
    _, durable = db.get_resume_conversations(parent)
    warm = list(session.get("display_history_prefix") or []) + list(session.get("history") or [])
    history = _reconcile_display_with_live(durable, warm)
    if target is not None:
        at = next((i for i, message in enumerate(history) if message.get("_row_id") == target
                   and message.get("role") in {"user", "assistant"} and not message.get("tool_calls")), None)
        if at is None:
            raise ValueError("target_message_id is not a user/assistant message in this session's history")
        history = history[:at + 1]
    if not history:
        raise ValueError("nothing to fork — send a message first")
    # Append stamps child row ids/flush markers. No parent-owned dict may cross
    # that write boundary, including nested content/tool-call structures.
    return deepcopy(_history_without_ephemeral_scaffolding(history))


def _persist_fork(db, session: dict, parent: str, history: list, profile: str) -> str:
    import json

    row = db.get_session(parent)
    if row is None:
        raise ValueError("The parent session is not stored yet.")
    key = _new_session_key()
    model, _ = _live_session_identity(session)
    config = _parse_model_config(row.get("model_config"), quiet=True)
    if (agent := session.get("agent")) is not None:
        config = _runtime_model_config(agent, config)
    config["_branched_from"] = parent
    try:
        _persist_branch(
            db, key, parent, _branch_title(db, parent), history,
            source=_session_source(session), cwd=row.get("cwd"), profile_name=profile,
            model=model or row.get("model") or "", compensate=True, title_source="derived",
            user_id=_session_auth_user_id(session),
            copy_fields=(*_BRANCH_COPY_FIELDS, "tool_calls", "tool_call_id", "tool_name", "api_content",
                         "finish_reason", "effect_disposition", "observed", "_tool_call_uids", "tool_call_uid"))
        db.update_session_meta(key, json.dumps(config), model=model or row.get("model"))
        if row.get("tool_names") is not None:
            pin = row["tool_names"]
            db.update_session_tool_names(key, json.loads(pin) if isinstance(pin, str) else pin)
    except Exception:
        db.delete_session(key)
        raise
    return key


@method("session.fork")
@_profile_scoped
def _(rid, params: dict) -> dict:
    session, error = _sess_nowait(params, rid)
    if error:
        return error
    target = params.get("target_message_id")
    if target is not None and (type(target) is not int or target < 1):
        return _err(rid, 4000, "target_message_id must be a positive integer row id")
    with session["history_lock"]:
        if session.get("running") or session.get("_manual_compress_active"):
            return _err(rid, 4009, "Wait for the current turn to finish before forking.")
        if session.get("_compute_host_active") or session.get("resume_hydrating"):
            return _err(rid, 4009, "Fork needs a fully loaded local session history.")
        parent = _submit_row_target_key(session)
        profile = profile_name_for_home(session.get("profile_home")) or _current_profile_name()
        try:
            with _session_db(session) as db:
                if db is None:
                    return _db_unavailable_error(rid, code=5008)
                history = _fork_history(db, session, parent, target)
                key = _persist_fork(db, session, parent, history, profile)
        except ValueError as exc:
            return _err(rid, 4008, str(exc))
        except Exception as exc:
            return _err(rid, 5008, f"fork failed: {exc}")
    return _ok(rid, {"session_id": key, "parent": parent, "profile": profile, "message_count": len(history)})


def register(server) -> None:
    bind_module(globals(), server, skip=("_",))
