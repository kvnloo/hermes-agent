"""Target-addressed undo for renderers; the canonical rewind still owns persistence."""
from __future__ import annotations

import hashlib
import json

from agent.context_compressor import retryable_user_text, user_originated_turn_view
from hermes_state_rewind import _comparison_content


def _target_snapshot(session: dict, target: int) -> tuple[int, str, int, str]:
    from tui_gateway import server

    if session.get("_compute_host_active"):
        raise ValueError("Targeted rewind is unavailable for a compute-host-owned history.")
    key = session.get("session_key")
    if not key:
        raise ValueError("Targeted rewind needs a stored session with durable message ids.")
    with server._session_db(session) as db:
        if db is None:
            raise ValueError("Session database is unavailable.")
        durable = db.get_messages_as_conversation(key, include_row_ids=True, repair_alternation=True)
    users = [m for m in durable if user_originated_turn_view(m) is not None]
    ordinal = next((i for i, m in enumerate(users) if m.get("_row_id") == target), None)
    if ordinal is None:
        raise ValueError("This message is not a rewindable user turn in the active history (it may be an ancestor or merged turn).")
    warm = [m for m in server._history_without_ephemeral_scaffolding(session.get("history", []))
            if user_originated_turn_view(m) is not None]
    live = user_originated_turn_view(users[ordinal])
    warm_live = user_originated_turn_view(warm[ordinal]) if ordinal < len(warm) else None
    if live is None or warm_live is None or len(warm) != len(users) or _comparison_content(warm_live) != _comparison_content(live):
        raise ValueError("Session history changed or cannot be aligned with the stored transcript. Reopen it before rewinding.")
    text = retryable_user_text(live.get("content"))
    token = hashlib.sha256(json.dumps(durable, sort_keys=True, default=str).encode()).hexdigest()
    return ordinal, text, len(users) - ordinal, token


def undo(rid, params: dict, session: dict, *, preview: bool = False) -> dict:
    from tui_gateway import server

    busy = server._err(rid, 4009, server.busy_message("undo", bool(session.get("_manual_compress_active"))))
    if session.get("running"):
        return busy
    target = params.get("target_message_id")
    if target is not None and (type(target) is not int or target < 1):
        return server._err(rid, 4000, "target_message_id must be a positive integer row id.")
    if preview and target is None:
        return server._err(rid, 4000, "A rewind preview requires target_message_id.")
    result: dict = {"removed": 0}
    with session["history_lock"]:
        if session.get("running"):
            return busy
        try:
            if target is not None:
                ordinal, text, turns, token = _target_snapshot(session, target)
                result.update(text=text, turns_removed=turns, history_token=token)
                if preview:
                    return server._ok(rid, result)
                if params.get("expected_history_token") not in (None, token):
                    return server._err(rid, 4009, "History changed after confirmation. Choose Rewind again to confirm the new turn count.")
                installed, _, removed = server._rewind_active_session_history(session, ordinal, require_retryable=True, target_message_id=target)
                result.update(removed=removed, messages=server._history_to_messages(installed, profile_home=session.get("profile_home")))
            else:
                history = server._history_without_ephemeral_scaffolding(session.get("history", []))
                users = sum(1 for m in history if user_originated_turn_view(m) is not None)
                if users:
                    result["removed"] = server._rewind_active_session_history(session, users - 1)[2]
        except Exception as exc:
            return server._err(rid, 5008, f"undo: {exc}")
    if result["removed"]:
        server._tui_model_friction("retry" if params.get("intent") == "retry" else "undo", session)
    return server._ok(rid, result)
