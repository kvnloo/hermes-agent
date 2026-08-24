"""Hermes Privilege Harness unprivileged requester plugin."""

import logging

from . import guard

logger = logging.getLogger("hermes-vip.plugin")


def register(ctx):
    ctx.register_hook("pre_tool_call", _hook)
    ctx.register_tool(
        name="privilege_request",
        toolset="terminal",
        description=(
            "Request one typed operation from an external privilege broker. "
            "A separately authenticated operator must approve it."
        ),
        schema={
            "name": "privilege_request",
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "operation_id": {"type": "string", "description": "Catalog operation identifier"},
                    "slots": {
                        "type": "object",
                        "description": "Typed catalog slot values",
                        "additionalProperties": {"type": ["string", "integer", "boolean"]},
                    },
                    "reason": {"type": "string", "description": "Why the operation is needed"},
                    "profile": {"type": "string", "description": "Hermes profile correlation"},
                    "session": {"type": "string", "description": "Hermes session correlation"},
                },
                "required": ["operation_id", "slots", "reason", "profile", "session"],
            },
        },
        handler=lambda args, **kw: guard.request(
            args.get("operation_id", ""), args.get("slots", {}), args.get("reason", ""),
            args.get("profile", ""), args.get("session", ""),
        ),
    )
    logger.info("privilege requester plugin ready")


def _hook(tool_name, args, **kwargs):
    return guard.check(tool_name, args if isinstance(args, dict) else {})
