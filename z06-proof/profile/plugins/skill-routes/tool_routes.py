"""tool-routes: deterministic tool-choice gate for skill-routes (Z06, analyst 2026-11-05).

Why: skill-routes only nudges from Kevin's message (pre_llm_call). The 7-day audit found the nudge
was ignored in 7 of 8 X-link sessions that skipped agent-reach. Agents also pick X and GitHub URLs
themselves, which the nudge never sees, and they repeat calls that already failed hard
(x_search out of credits, gh not logged in, identical timed-out commands).

Three rule kinds, all table-driven from tool_routes.yaml:
  route   -> the first matching generic call is blocked with the right command. Repeating the identical
             call passes (that is the fallback path), so the gate can never strand the agent.
  breaker -> after a hard, non-retryable error, the next call of the same tool/binary/command is blocked
             (max_blocks times, default 1) with the doctor to run. A call that runs the doctor passes and clears it.
  hint    -> after a failure whose retry can still work (gh auth hiccups, timeouts), nothing is blocked; the
             failed result gets one line naming the doctor or the better shape (once per session per rule).
Replay (7 days, all profiles) showed blocking those two would have stopped 21 of 25 later gh calls and 25
of 45 timed-out reruns that succeeded, so they are hints, not breakers.
Fails open: any internal error returns None.
"""
import json
import logging
import re
from pathlib import Path

import yaml

_log = logging.getLogger(__name__)
CFG = Path(__file__).resolve().parent / "tool_routes.yaml"
_cfg = {"mtime": None, "routes": [], "breakers": [], "hints": []}
_hinted = set()  # (session, hint id)
_seen = {}      # (session, rule id, args-hash) -> True once blocked; the identical retry passes
_tripped = {}   # (session, breaker key) -> blocks left before the breaker lets calls through again


def _load():
    m = CFG.stat().st_mtime
    if _cfg["mtime"] != m:
        c = yaml.safe_load(CFG.read_text()) or {}
        for r in c.get("routes", []) + c.get("breakers", []) + c.get("hints", []):
            for k in ("tools", "args", "result", "doctor"):
                if r.get(k):
                    r[k + "_re"] = re.compile(re.sub(r"\s*\n\s*", "", r[k]), re.I)
        _cfg.update(mtime=m, routes=c.get("routes", []), breakers=c.get("breakers", []), hints=c.get("hints", []))
    return _cfg


def _blob(args):
    return args if isinstance(args, str) else json.dumps(args or {}, ensure_ascii=False, sort_keys=True)


def _cmd(args):
    return (args or {}).get("command", "") if isinstance(args, dict) else ""


def _bkey(b, tool, args):
    scope = b.get("scope", "tool")
    if scope == "command":
        return (b["id"], tool, _cmd(args).strip())
    if scope == "binary":
        m = re.search(b.get("binary", r"$^"), _cmd(args))
        return (b["id"], tool, m.group(0) if m else None)
    return (b["id"], tool)


def pre(tool_name="", args=None, session_id="", task_id="", **_):
    try:
        cfg, blob, sid = _load(), _blob(args), session_id or task_id or "-"
        for b in cfg["breakers"]:
            key = _bkey(b, tool_name, args)
            if (sid, key) in _tripped:
                if b.get("doctor_re") and b["doctor_re"].search(blob):
                    _tripped.pop((sid, key), None)          # running the doctor clears the breaker
                    return None
                left = _tripped[(sid, key)] = _tripped[(sid, key)] - 1
                if left <= 0:
                    _tripped.pop((sid, key), None)          # told enough times; let the agent decide
                return {"action": "block", "message": f"[tool-routes:{b['id']}] {b['message']}"}
        for r in cfg["routes"]:
            if r["tools_re"].fullmatch(tool_name) and r["args_re"].search(blob):
                k = (sid, r["id"], hash(blob))
                if k in _seen:
                    return None                              # identical retry = deliberate fallback
                _seen[k] = True
                return {"action": "block", "message": f"[tool-routes:{r['id']}] {r['message']} "
                        "(If that path fails, repeat this exact call and it will run.)"}
    except Exception as e:
        _log.warning("tool-routes pre: %s", e)
    return None


def post(tool_name="", args=None, result=None, session_id="", task_id="", **_):
    try:
        cfg, sid = _load(), session_id or task_id or "-"
        text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
        for b in cfg["breakers"]:
            if b["tools_re"].fullmatch(tool_name) and b["result_re"].search(text[:4000]):
                key = _bkey(b, tool_name, args)
                if key[-1] is not None:
                    _tripped[(sid, key)] = int(b.get("max_blocks", 1))
    except Exception as e:
        _log.warning("tool-routes post: %s", e)
    return None


def hint(tool_name="", args=None, result=None, session_id="", task_id="", **_):
    """transform_tool_result: append one doctor line to a matching failed result; never blocks."""
    try:
        cfg, sid = _load(), session_id or task_id or "-"
        if not isinstance(result, str):
            return None
        for h in cfg["hints"]:
            if (sid, h["id"]) in _hinted or not h["tools_re"].fullmatch(tool_name) or not h["result_re"].search(result[:4000]):
                continue
            if h.get("binary") and not re.search(h["binary"], _cmd(args)):
                continue
            _hinted.add((sid, h["id"]))
            return f"{result}\n[tool-routes:{h['id']}] {h['message']}"
    except Exception as e:
        _log.warning("tool-routes hint: %s", e)
    return None
