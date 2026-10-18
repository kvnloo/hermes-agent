"""Validate, redact and bound optional eval companions before sending/persisting them."""
from __future__ import annotations

import json

from pydantic import ValidationError

from .contracts.eval import EvalDisplay, EvalUpdatePayload
from .tool_result_display import bounded_tool_result


def _clean(value):
    from agent.redact import redact_sensitive_text
    from tools.ansi_strip import strip_ansi
    if isinstance(value, str):
        return redact_sensitive_text(strip_ansi(value), code_file=True)
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    return value


def eval_metadata(result):
    try:
        body = json.loads(result) if isinstance(result, str) else result
        if not isinstance(body, dict) or "eval_display" not in body:
            return {}
        display = EvalDisplay.model_validate(_clean(bounded_tool_result(body["eval_display"])))
    except (ValueError, ValidationError, RecursionError):
        return {}
    revision = body.get("eval_revision")
    return {"eval_display": display.model_dump(exclude_none=True),
            **({"eval_revision": revision} if isinstance(revision, int) and revision >= 0 else {})}


def emit_eval_update(sid, value, _emit):
    try:
        update = EvalUpdatePayload.model_validate(_clean(bounded_tool_result(value)))
    except (ValueError, ValidationError, RecursionError):
        return
    _emit("eval.update", sid, update.model_dump(exclude_none=True))
