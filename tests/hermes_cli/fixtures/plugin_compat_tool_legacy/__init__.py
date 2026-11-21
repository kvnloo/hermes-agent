"""Frozen legacy tool plugin used by the behavior compatibility suite.

Keep ``_echo`` in its old, narrow ``handle(args)`` form: it predates every context
keyword the dispatcher now injects. ``_context_probe`` is the ``**kwargs`` control.
"""

import json

calls = []

_SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}}}


def _echo(args):
    calls.append(dict(args))
    return json.dumps({"echo": args.get("text")})


def _context_probe(args, **kwargs):
    return json.dumps({"kwargs": sorted(kwargs)})


def register(ctx):
    ctx.register_tool("legacy_echo", "legacy-tool-fixture",
                      {"name": "legacy_echo", "description": "Echo text.", "parameters": _SCHEMA}, _echo)
    ctx.register_tool("legacy_context_probe", "legacy-tool-fixture",
                      {"name": "legacy_context_probe", "description": "List context keys.",
                       "parameters": {"type": "object", "properties": {}}}, _context_probe)
