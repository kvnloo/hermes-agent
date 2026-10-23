"""Source-adapted excerpt: liuhao1024/hermes-agent PR 116846 head 96dc75192a82.
2026-10-23. Exact regex/predicate and stage-write invocation; helpers injected.
"""
import json
import re
from typing import Any, Dict, List

_BG_DELETE_ACTIONS = ("replace", "remove")

_BG_NO_SAVE_RE = re.compile(
    r"\b(?:"
    r"ask(?:ed|s|ing)?(?:\s+\w+){0,2}?\s+not\s+to\s+(?:save|store|keep|remember)"
    r"|request(?:ed|s|ing)?(?:\s+\w+){0,2}?\s+not\s+to\s+(?:save|store|keep|remember)"
    r"|not\s+to\s+(?:save|store)\s+(?:it|this|that)"
    r"|(?:do(?:es)?\s+not|don['’]t|never)\s+(?:save|store|remember)\s+(?:this|that|it)"
    r")\b",
    re.IGNORECASE)


def _consent_sensitive_add(action, content) -> bool:
    return action == "add" and bool(content) and bool(_BG_NO_SAVE_RE.search(content))


def destructive_ops(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The replace/remove ops of a staged memory payload, single-op or batch shape."""
    ops = (payload.get("operations") or []) if payload.get("action") == "batch" else [payload]
    return [op for op in ops if (op or {}).get("action") in _BG_DELETE_ACTIONS]


def _background_delete_gate(store, action, operations, target="memory", content=None,
                            old_text=None):
    from tools.skill_provenance import is_unattended_review

    if not is_unattended_review():
        return None
    delete_hit = action in _BG_DELETE_ACTIONS or any(
        isinstance(op, dict) and op.get("action") in _BG_DELETE_ACTIONS for op in (operations or []))
    consent_hit = _consent_sensitive_add(action, content) or any(
        isinstance(op, dict) and _consent_sensitive_add(op.get("action"), op.get("content"))
        for op in (operations or []))
    if not delete_hit and not consent_hit:
        return None
    reason = ("delete memory entries" if delete_hit else
              "persist a fact the user asked not to save")
    payload = ({"action": "batch", "target": target, "operations": operations}
               if operations is not None else
               {"action": action, "target": target, "content": content, "old_text": old_text})
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
            "message": (f"Background review may not {reason} unattended. The proposed "
                        f"{'batch' if operations is not None else action} was staged for your approval — "
                        "review it with /memory pending (approve to apply, discard to drop)."),
        }, ensure_ascii=False)
    except Exception:
        logger.warning("Failed to stage background-review consolidation; denying", exc_info=True)
        return tool_error(
            "Background review may not delete memory entries ('replace'/'remove', including in a "
            "batch) nor persist a fact the user asked not to save; plain 'add' is still available.",
            success=False)
