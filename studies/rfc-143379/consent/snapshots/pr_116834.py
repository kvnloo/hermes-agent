"""Source-adapted excerpt: chelsealong/hermes-agent PR 116834 head f678f4c7e5d9.
2026-10-23. Exact predicates and stage-write invocation; standalone helpers injected.
"""
import json
from typing import Any, Dict, List

_BG_DELETE_ACTIONS = ("replace", "remove")


def destructive_ops(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The replace/remove ops of a staged memory payload, single-op or batch shape."""
    ops = (payload.get("operations") or []) if payload.get("action") == "batch" else [payload]
    return [op for op in ops if (op or {}).get("action") in _BG_DELETE_ACTIONS]


def _background_op_needs_staging(payload: Dict[str, Any]) -> bool:
    """The PR's target-based USER.md guard, preserving operational MEMORY.md adds."""
    if destructive_ops(payload):
        return True
    if payload.get("target") != "user":
        return False
    ops = (payload.get("operations") or []) if payload.get("action") == "batch" else [payload]
    return any((op or {}).get("action") == "add" for op in ops)


def _background_delete_gate(store, action, operations, target="memory", content=None,
                            old_text=None):
    from tools.skill_provenance import is_unattended_review

    if not is_unattended_review():
        return None
    payload = ({"action": "batch", "target": target, "operations": operations}
               if operations is not None else
               {"action": action, "target": target, "content": content, "old_text": old_text})
    if not _background_op_needs_staging(payload):
        return None
    detail = ("; ".join(_batch_op_line(op) for op in operations) if operations is not None
              else _batch_op_line({"action": action, "content": content, "old_text": old_text}))
    try:
        if (unmatched := _pin_matched_entries(store, payload)) is not None:
            return unmatched
        from tools import write_approval as wa
        record = wa.stage_write(
            wa.MEMORY, payload,
            summary=(f"background review consolidation ({'batch' if operations is not None else action} "
                     f"on {target}): {detail}")[:200],
            origin=wa.current_origin())
        return json.dumps({
            "success": True, "staged": True, "proposal_staged": True, "pending_id": record["id"],
            "message": ("Background review may not delete memory entries or add to the user profile "
                        f"unattended. The proposed {'batch' if operations is not None else action} was "
                        "staged for your approval — review it with /memory pending "
                        "(approve to apply, discard to drop)."),
        }, ensure_ascii=False)
    except Exception:
        logger.warning("Failed to stage background-review consolidation; denying", exc_info=True)
        return tool_error(
            "Background review may not delete memory entries ('replace'/'remove', including in a "
            "batch) or add to the user profile unattended; 'add' to memory is still available.",
            success=False)
