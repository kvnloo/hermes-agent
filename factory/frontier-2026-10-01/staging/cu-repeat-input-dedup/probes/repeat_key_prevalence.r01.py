#!/usr/bin/env python3
"""Repeat-key prevalence probe (queued T2/T3; T1 dry run with --fake).

Question: how often does a real model put the SAME computer_use key press twice in one
assistant message when the task needs repeated keys, and how many presses reach the
backend on a given Hermes tree (main drops the repeat; staging/cu-repeat-input-dedup keeps it)?

Everything is real except the model endpoint and the device: a real AIAgent turn, the
in-tree no-op computer_use backend as the recording device, approvals answered "once".
Emitted calls are read PASSIVELY (sys.setprofile on the dedup function's ``tool_calls``
argument), so the measurement is the same on main and on the staging tree.

Usage (from anywhere; --tree is the Hermes checkout under test):
  T=$(mktemp -d); HOME=$T HERMES_HOME=$T/.hermes $PY repeat_key_prevalence.py \
      --tree <worktree> --fake --trials 3 --out out.json                     # T1, $0
  ... --base-url http://127.0.0.1:11434/v1 --model qwen2.5:7b --trials 20    # T2, needs OD-1 (64K)
  ... --base-url https://openrouter.ai/api/v1 --model <id> --api-key-env OPENROUTER_API_KEY  # T3, OD-3, owner-launched
Network: loopback plus the --base-url host only; anything else raises.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

PROMPTS = [
    "Move keyboard focus forward two fields: press Tab twice. Use the computer_use tool, one call per key press.",
    "Press the Down arrow key three times with computer_use (one key action per press).",
    "Delete the last two characters by pressing BackSpace twice using computer_use key actions.",
]


def _guard_network(allowed_host: str | None) -> list:
    allowed = {"127.0.0.1", "::1", "localhost"} | ({allowed_host} if allowed_host else set())
    blocked: list = []
    orig = socket.socket.connect

    def connect(self, address):
        if isinstance(address, tuple) and address[0] not in allowed:
            blocked.append(str(address))
            raise OSError(f"probe network guard: {address[0]} is not allowed")
        return orig(self, address)

    socket.socket.connect = connect
    return blocked


def _refuse_live_home() -> Path:
    home, hh = os.environ.get("HOME", ""), os.environ.get("HERMES_HOME", "")
    for p in (home, hh):
        rp = os.path.realpath(p) if p else ""
        if not rp or rp.startswith(("<hermes-home>", os.path.realpath("~/.hermes"))):
            sys.exit(f"refusing: HOME/HERMES_HOME must be an isolated temp dir (got {p!r})")
    return Path(hh)


class _EmittedCalls:
    """Passive observer: the tool_calls list handed to the dedup function, per assistant message."""

    NAMES = {("run_agent.py", "_deduplicate_tool_calls"), ("tool_dispatch_helpers.py", "deduplicate_tool_calls")}

    def __init__(self) -> None:
        self.batches: list = []  # emitted (pre-dedup) per assistant message
        self.kept: list = []     # returned (post-dedup) per assistant message

    def __call__(self, frame, event, arg):
        if (os.path.basename(frame.f_code.co_filename), frame.f_code.co_name) not in self.NAMES:
            return
        if event == "call":
            tcs = frame.f_locals.get("tool_calls") or []
            self.batches.append([(tc.function.name, tc.function.arguments) for tc in tcs])
        elif event == "return" and isinstance(arg, list):
            self.kept.append([(tc.function.name, tc.function.arguments) for tc in arg])


def _key_presses(batch: list) -> list:
    out = []
    for name, raw in batch:
        try:
            args = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        except ValueError:
            continue
        if name == "tool_call" and isinstance(args, dict):
            calls = args.get("calls") or [{"name": args.get("name"), "arguments": args.get("arguments")}]
            if isinstance(calls, list) and len(calls) == 1 and isinstance(calls[0], dict):
                name, args = calls[0].get("name"), calls[0].get("arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        continue
        if name == "computer_use" and isinstance(args, dict) and str(args.get("action", "")).lower() == "key":
            out.append(str(args.get("keys", "")).lower())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--fake", action="store_true", help="T1 dry run against the scripted loopback provider")
    ap.add_argument("--base-url")
    ap.add_argument("--model", default="fake-model")
    ap.add_argument("--api-key-env", default="")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--tool-search", choices=["default", "off"], default="default")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    hermes_home = _refuse_live_home()
    tree = Path(a.tree).resolve()
    sys.path.insert(0, str(tree))
    os.chdir(tree)
    blocked = _guard_network(None if a.fake else urlparse(a.base_url).hostname)

    from tests.fakes.fake_llm_provider import FakeLLMServer, Text, ToolCall, write_hermes_home
    from tools.computer_use import tool as cu_tool
    import tools.computer_use.cua_backend_driver as drv

    srv = None
    if a.fake:
        tab = {"action": "key", "keys": "tab"}

        def respond(rec):  # scripted Tab, Tab in whichever form the request advertises
            body = rec["body"]
            if body["messages"][-1].get("role") == "tool":
                return Text("done")
            names = {t["function"]["name"] for t in body.get("tools") or []}
            wire = ("computer_use", tab) if "computer_use" in names else (
                "tool_call", {"name": "computer_use", "arguments": tab})
            return ToolCall(wire[0], wire[1], parallel=[wire])

        srv = FakeLLMServer(respond)
        srv.start()
        base_url, api_key = srv.base_url, "sk-fake"
    else:
        base_url = a.base_url
        api_key = os.environ.get(a.api_key_env, "sk-local") if a.api_key_env else "sk-local"
    extra = "tools:\n  tool_search:\n    enabled: \"off\"\n" if a.tool_search == "off" else ""
    write_hermes_home(hermes_home, base_url, extra_config=extra)
    (hermes_home / ".env").write_text("", encoding="utf-8")  # never persist a real key

    drv.cua_driver_binary_available = lambda: True
    os.environ["HERMES_INTERACTIVE"] = "1"
    cu_tool.set_approval_callback(lambda command, description, **kw: "once")

    from run_agent import AIAgent

    rows = []
    for trial in range(a.trials):
        for pi, prompt in enumerate(PROMPTS):
            cu_tool.reset_backend_for_tests()
            backend = cu_tool._NoopBackend()
            cu_tool._new_backend = lambda permission_mode, _b=backend: _b
            obs = _EmittedCalls()
            sys.setprofile(obs)
            threading.setprofile(obs)
            t0 = time.time()
            err = None
            agent = AIAgent(provider="custom", base_url=base_url, api_key=api_key, model=a.model, quiet_mode=True,
                            skip_context_files=True, skip_memory=True, enabled_toolsets=["computer_use"],
                            max_iterations=4)
            try:
                agent.run_conversation(prompt)
            except Exception as exc:  # recorded, never hidden
                err = repr(exc)[:300]
            finally:
                sys.setprofile(None)
                threading.setprofile(None)
                agent.close()
            first = obs.batches[0] if obs.batches else []
            emitted = _key_presses(first)
            kept = _key_presses(obs.kept[0]) if obs.kept else []
            rows.append({
                "trial": trial, "prompt": pi, "error": err, "wall_s": round(time.time() - t0, 2),
                "assistant_messages_with_tools": len(obs.batches),
                "first_message_key_presses": emitted,
                "first_message_identical_repeat": len(emitted) != len(set(emitted)),
                "first_message_key_presses_kept_by_dedup": kept,
                "backend_key_presses_whole_turn": sum(1 for n, _ in backend.calls if n == "key"),
            })
    if srv:
        srv.stop()
    n = len(rows)
    rep = [r for r in rows if r["first_message_identical_repeat"]]
    summary = {
        "label": "OBSERVED", "tree": str(tree), "model": a.model, "fake": a.fake, "tool_search": a.tool_search,
        "n_turns": n, "turns_with_identical_key_repeat_in_one_message": len(rep),
        "presses_emitted_in_repeat_turns": sum(len(r["first_message_key_presses"]) for r in rep),
        "presses_kept_by_dedup_in_repeat_turns": sum(len(r["first_message_key_presses_kept_by_dedup"]) for r in rep),
        "backend_presses_whole_turn_in_repeat_turns": sum(r["backend_key_presses_whole_turn"] for r in rep),
        "errors": sum(1 for r in rows if r["error"]), "egress_blocked": blocked,
    }
    Path(a.out).write_text(json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
