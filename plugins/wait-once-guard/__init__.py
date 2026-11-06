"""wait-once-guard: refuse foreground ``sleep`` over 10 s in ``terminal`` calls.

Each "sleep N; check" poll is a full API turn that re-sends the whole context (oss-factory#319:
~113-213 Mtok/wk). The terminal schema already says to wait once; this makes it deterministic.
Background calls and sleeps <= 10 s (pacing, bounded ``until ...; do sleep 5; done`` loops) pass.
Decisions (no command text) go to $HERMES_HOME/wait-once-guard/decisions.jsonl for the A/B.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

MAX_FG_SLEEP_S = 10.0
_TOOLS = {"terminal", "mcp__terminal"}
_UNIT = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}
_SHELL_SLEEP = re.compile(r"(?<![\w.-])sleep\s+((?:\d+(?:\.\d+)?[smhd]?\s*)+)(?=$|[\s;&|)])")
_PY_SLEEP = re.compile(r"\btime\.sleep\(\s*(\d+(?:\.\d+)?)\s*\)")
_ARG = re.compile(r"(\d+(?:\.\d+)?)([smhd]?)")

MESSAGE = (
    "BLOCKED by wait-once-guard: foreground sleep of {n:g} s (limit 10 s). Every sleep+check poll "
    "re-sends your whole context. Wait once instead: start the job with terminal(background=true, "
    "notify=true) and do other work or end the turn, or call process_manage wait once. To wait for "
    "readiness inside one call, use a bounded loop with short sleeps, e.g. "
    "`timeout 300 bash -c 'until <check>; do sleep 5; done'`."
)


def longest_sleep(command: str) -> float:
    """Longest single sleep (seconds) in a shell command; GNU ``sleep 1m 30s`` sums its args."""
    best = 0.0
    for m in _SHELL_SLEEP.finditer(command):
        best = max(best, sum(float(v) * _UNIT[u] for v, u in _ARG.findall(m.group(1))))
    for m in _PY_SLEEP.finditer(command):
        best = max(best, float(m.group(1)))
    return best


def _log(decision: str, seconds: float, session_id: str) -> None:
    try:
        d = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))) / "wait-once-guard"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "decisions.jsonl", "a") as f:
            f.write(json.dumps({"ts": time.time(), "decision": decision, "sleep_s": seconds,
                                "session_id": session_id}) + "\n")
    except Exception:
        pass


def check(tool_name=None, args=None, session_id="", **_kwargs):
    if tool_name not in _TOOLS or not isinstance(args, dict) or args.get("background") in (True, "true"):
        return None
    command = args.get("command")
    if not isinstance(command, str):
        return None
    n = longest_sleep(command)
    if n <= MAX_FG_SLEEP_S:
        return None
    _log("block", n, session_id or "")
    return {"action": "block", "message": MESSAGE.format(n=n)}


def register(ctx):
    ctx.register_hook("pre_tool_call", check)
