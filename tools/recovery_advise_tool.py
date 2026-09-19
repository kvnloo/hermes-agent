"""FlyForge recovery controller tool for Hermes.

Typed operational events -> bounded recovery action via evolution-lab.
Secrets fail closed at L0. Qwen remains escalation; this is the fast specialist.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from tools.registry import registry, tool_error

_DEFAULT_REPO = Path("/workspace/evolution-lab")


def _repo() -> Path:
    env = os.environ.get("FLYFORGE_EVOLUTION_LAB")
    return Path(env) if env else _DEFAULT_REPO


def _ensure_import_path() -> None:
    root = _repo()
    if not root.is_dir():
        raise FileNotFoundError(f"evolution-lab not found at {root}")
    text = str(root)
    if text not in sys.path:
        sys.path.insert(0, text)


def recovery_advise_tool(
    *,
    action: str = "plan",
    harness: str = "hermes",
    family: str | None = None,
    event: Dict[str, Any] | None = None,
    fields: Dict[str, Any] | None = None,
    retry: int | None = None,
    budget: float | None = None,
) -> str:
    try:
        _ensure_import_path()
        from evolution_lab.recovery_cli import handle_request
    except Exception as exc:  # pragma: no cover - environment dependent
        return tool_error(f"recovery controller unavailable: {exc}")

    payload: Dict[str, Any] = {
        "action": action or "plan",
        "harness": harness or "hermes",
        "family": family or os.environ.get("FLYFORGE_RECOVERY_FAMILY", "local_plasticity"),
    }
    if event is not None:
        payload["event"] = event
    if fields is not None:
        payload["fields"] = fields
    if retry is not None:
        payload["retry"] = retry
    if budget is not None:
        payload["budget"] = budget
    try:
        result = handle_request(payload)
    except Exception as exc:
        return tool_error(str(exc))
    return json.dumps(result, indent=2)


def check_recovery_advise_requirements() -> bool:
    try:
        _ensure_import_path()
        from evolution_lab.splits import splits_exist

        return splits_exist(_repo() / "data" / "p0")
    except Exception:
        return False


RECOVERY_ADVISE_SCHEMA = {
    "name": "recovery_advise",
    "description": (
        "FlyForge Hermes recovery controller. Map a sanitized operational event "
        "to one bounded action: retry, restart_sandbox, escalate, noop, or page_human. "
        "Never pass secrets, tokens, credentials, or vault payloads."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["plan", "advise", "observe", "status"],
                "description": "plan=observe+advise (default)",
            },
            "harness": {
                "type": "string",
                "enum": ["hermes", "omp", "pi", "cursor"],
                "description": "Calling harness label",
            },
            "family": {
                "type": "string",
                "enum": ["local_plasticity", "rule"],
                "description": "Specialist family (default local_plasticity)",
            },
            "event": {
                "type": "object",
                "description": "Sanitized operational event (tool failure, hub death, rate limit, policy hit)",
                "additionalProperties": True,
            },
            "fields": {
                "type": "object",
                "description": "Pre-sanitized observation fields (skip observe)",
                "additionalProperties": True,
            },
            "retry": {"type": "integer", "minimum": 0, "maximum": 4},
            "budget": {"type": "number", "minimum": 0, "maximum": 1},
        },
    },
}


registry.register(
    name="recovery_advise",
    toolset="recovery",
    schema=RECOVERY_ADVISE_SCHEMA,
    handler=lambda args, **kw: recovery_advise_tool(
        action=args.get("action", "plan"),
        harness=args.get("harness", "hermes"),
        family=args.get("family"),
        event=args.get("event"),
        fields=args.get("fields"),
        retry=args.get("retry"),
        budget=args.get("budget"),
    ),
    check_fn=check_recovery_advise_requirements,
    emoji="🪰",
)
