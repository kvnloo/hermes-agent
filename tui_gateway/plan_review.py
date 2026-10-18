"""Authoritative plan state belongs to the existing live session, not the renderer.

It intentionally expires with that session. No heading-based inference or durable
second store; toggling mode, starting a turn or changing history revokes decisions.
"""
from __future__ import annotations

import copy
import re
import threading
import uuid


def plan_state(session):
    return session.setdefault("plan_review", {
        "enabled": False, "generating": False, "plan": None,
        "history_version": session.get("history_version", 0), "lock": threading.RLock(),
    })


def plan_snapshot(session):
    state = plan_state(session)
    valid = state["history_version"] == session.get("history_version", 0)
    return {"enabled": state["enabled"], "generating": state["generating"],
            "plan": copy.deepcopy(state["plan"]) if valid else None}


def begin_plan_generation(session, agent):
    state = plan_state(session)
    with state["lock"]:
        state["approved"] = (copy.deepcopy(state["plan"]) if not state["enabled"]
                             and state["plan"] and state["plan"]["decision"] == "approved"
                             and state["history_version"] == session.get("history_version", 0) else None)
        agent._plan_mode = state["enabled"]
        state["generating"] = state["enabled"]
        # Even an interrupted or empty replacement must invalidate the old plan.
        state["previous"] = state["plan"] if state["enabled"] else None
        state["plan"] = None


def finish_plan_generation(session, text, status, result=None):
    if isinstance(result, dict) and (result.get("failed") or result.get("completed") is False):
        status = "error"
    state = plan_state(session)
    with state["lock"]:
        if state["generating"] and status == "complete" and isinstance(text, str) and text.strip():
            previous = state.get("previous")
            state["plan"] = {
                "id": previous["id"] if previous else str(uuid.uuid4()),
                "revision": previous["revision"] + 1 if previous else 1,
                "text": text, "annotations": [], "decision": "pending",
            }
        state["generating"] = False
        state["history_version"] = session.get("history_version", 0)
        state.pop("previous", None)


def plan_turn_note(session):
    state = plan_state(session)
    with state["lock"]:
        if state["enabled"]:
            return "Plan mode is active. Use read-only tools only; return a plan for user review. Do not execute or delegate."
        approved = state.pop("approved", None)
        if not approved:
            return ""
        notes = "\n".join(f"Section {note['section'] + 1}: {note['text']}" for note in approved["annotations"])
        return (f"The user approved exactly plan {approved['id']} revision {approved['revision']}. "
                f"Use these reviewed bytes, not an earlier transcript draft:\n\n{approved['text']}\n\n{notes}")


def plan_section_count(text):
    fence = None
    count = 0
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
        elif marker:
            fence = marker[1]
        elif re.match(r"^ {0,3}#{1,6}[\t ]+\S", line):
            count += 1
    return max(1, count)
