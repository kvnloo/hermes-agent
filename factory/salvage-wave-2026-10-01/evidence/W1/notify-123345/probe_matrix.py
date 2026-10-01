"""Dispatch-path probe: coerce_tool_args("terminal") -> _handle_terminal, terminal_tool stubbed."""
import json

from tools import terminal_tool as tt
from tools.arg_coercion import coerce_tool_args

seen = {}


def fake(**kw):
    seen.clear()
    seen.update(kw)
    return json.dumps({"output": "ok"})


tt.terminal_tool = fake
cases = [(True, v) for v in ("true", "false", "yes", "1", "on", "maybe", '["ready"]', "ready", 2, 1.5, True, ["ready"])]
cases += [(False, "false"), (False, "true")]
for bg, v in cases:
    seen.clear()
    args = {"command": "x", "notify": v}
    if bg:
        args["background"] = True
    out = json.loads(tt._handle_terminal(coerce_tool_args("terminal", dict(args))))
    res = ("ERR " + out["error"][:28]) if out.get("error") else f"noc={seen.get('notify_on_complete')} wp={seen.get('watch_patterns')}"
    print(f"{'bg' if bg else 'fg'} notify={v!r:12} -> {res}")
