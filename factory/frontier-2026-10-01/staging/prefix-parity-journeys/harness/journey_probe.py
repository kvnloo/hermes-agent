"""Scratch T1 probe for the prefix-parity-journeys staging branch (NOT part of the upstream commit).

Drives the committed C17 journeys (tests/e2e/core/history/test_prefix_stability.py::run_journey)
against the loopback FakeLLMServer and reports, per journey, OBSERVED request-stream metrics:

  E07  prefix breaks (all / at the compaction / unexpected), tools-array drift, compaction nesting,
       usage == billed, state.db integrity, system-prompt sizes, summary carried per request.
  E08  (--identity) a recording plugin on post_api_request: hook records vs main requests,
       turn_id shape <session>:<task>:<8hex>, session part in the journey's lineage, one turn_id per
       user turn, first_chunk_at presence.

Run from the worktree root, inside bwrap --unshare-net (loopback only), with HOME/HERMES_HOME set to
a scratch dir. Writes one JSON document to --out.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.path.insert(0, os.getcwd())

from tests.e2e.core.history import test_prefix_stability as c17  # noqa: E402
from tests.e2e.core.history._helpers import (  # noqa: E402
    NO_BACKGROUND_REVIEW, OFFLINE_CONFIG, Script, Spawned, assert_usage_matches, integrity_ok, is_summary,
    lineage, prefix_breaks, tools_breaks,
)
from tests.fakes.fake_llm_provider import FakeLLMServer, write_hermes_home  # noqa: E402

RECORDER = "prefix-probe-recorder"
TURN_ID_RE = re.compile(r"^(?P<session>.+):(?P<task>.+):(?P<hex>[0-9a-f]{8})$")


def write_recorder(hermes_home: Path, log: Path) -> str:
    plugin = hermes_home / "plugins" / RECORDER
    plugin.mkdir(parents=True)
    (plugin / "plugin.yaml").write_text(f"name: {RECORDER}\nversion: 1.0.0\ndescription: E08 recorder\n",
                                        encoding="utf-8")
    (plugin / "__init__.py").write_text(
        "import json, os\n"
        "KEYS = ('task_id', 'turn_id', 'api_request_id', 'session_id', 'platform', 'api_call_count',\n"
        "        'first_chunk_at', 'started_at', 'message_count', 'finish_reason')\n"
        "def register(ctx):\n"
        "    def _post(**kw):\n"
        f"        with open({str(log)!r}, 'a', encoding='utf-8') as fh:\n"
        "            fh.write(json.dumps({'pid': os.getpid(), **{k: kw.get(k) for k in KEYS}}, default=str) + '\\n')\n"
        "    ctx.register_hook('post_api_request', _post)\n",
        encoding="utf-8")
    return f"plugins:\n  enabled:\n  - {RECORDER}\n"


def run_one(name: str, root: Path, identity: bool) -> dict:
    root.mkdir(parents=True, exist_ok=False)
    home = root / "home"
    home.mkdir()
    hermes_home = root / "hermes_home"
    cwds = {"a": root / "work-a", "b": root / "work-b"}
    for d in cwds.values():
        d.mkdir()
    script, spawned = Script(), Spawned()
    hook_log = root / "post_api_request.jsonl"
    out: dict = {"journey": name, "hops": len(c17.JOURNEYS[name]),
                 "surfaces": sorted({h[0] for h in c17.JOURNEYS[name]})}
    started = time.monotonic()
    with FakeLLMServer(script) as srv:
        extra = OFFLINE_CONFIG + NO_BACKGROUND_REVIEW
        hermes_home.mkdir(parents=True)
        if identity:
            extra += write_recorder(hermes_home, hook_log)
        write_hermes_home(hermes_home, srv.base_url, extra_config=extra)
        world = {"srv": srv, "script": script, "home": home, "hermes_home": hermes_home, "cwds": cwds,
                 "spawned": spawned}
        try:
            sid, openings, compaction_idx = c17.run_journey(world, c17.JOURNEYS[name])
            out["run_journey"] = "ok"
        except Exception as exc:  # noqa: BLE001 - recorded, metrics still computed where possible
            sid, openings, compaction_idx = None, [], None
            out["run_journey"] = f"{type(exc).__name__}: {str(exc)[:600]}"
        finally:
            out["leaked_pids"] = spawned.reap()
        main = srv.main_requests()
    out["wall_s"] = round(time.monotonic() - started, 1)
    out["main_requests"] = len(main)
    out["aux_requests"] = sum(1 for r in srv.requests if r["kind"] == "aux")
    out["process_lives"] = len(openings)
    out["compaction_idx"] = compaction_idx
    breaks = prefix_breaks(main, tools=False)
    out["prefix_breaks"] = [{"request": i, "why": why[:240]} for i, why in breaks]
    out["prefix_breaks_total"] = len(breaks)
    out["prefix_breaks_at_compaction"] = sum(1 for i, _ in breaks if i == compaction_idx)
    out["prefix_breaks_unexpected"] = sum(1 for i, _ in breaks if i != compaction_idx)
    drift = [(i, w) for i, w in tools_breaks(main) if i != compaction_idx]
    out["tools_drift"] = [{"request": i, "why": w[:240]} for i, w in drift]
    sys_lens = [len(c17._system_text(r)) for r in main]
    out["system_prompt_chars"] = sys_lens
    out["summary_in_request"] = [any(is_summary(m) for m in r["messages"]) for r in main]
    if compaction_idx:
        before, after = c17._system_text(main[compaction_idx - 1]), c17._system_text(main[compaction_idx])
        out["compaction_nests_previous_prompt"] = after != before and before in after
    else:
        out["compaction_nests_previous_prompt"] = None
    if sid:
        try:
            assert_usage_matches(hermes_home, lineage(hermes_home, sid), srv.requests, name)
            out["usage_matches_billed"] = True
        except AssertionError as exc:
            out["usage_matches_billed"] = f"FAIL: {str(exc)[:300]}"
        try:
            integrity_ok(hermes_home)
            out["db_integrity_ok"] = True
        except AssertionError as exc:
            out["db_integrity_ok"] = f"FAIL: {exc}"
        out["lineage_len"] = len(lineage(hermes_home, sid))
    unexpected = out["prefix_breaks_unexpected"]
    out["verdict_e07"] = ("PASS" if out["run_journey"] == "ok" and unexpected == 0 and not drift
                          and out["compaction_nests_previous_prompt"] in (False, None)
                          and out.get("usage_matches_billed") is True else "FAIL")
    if identity:
        recs = [json.loads(line) for line in hook_log.read_text(encoding="utf-8").splitlines()] if hook_log.exists() else []
        chain = set(lineage(hermes_home, sid)) if sid else set()
        shaped = [r for r in recs if TURN_ID_RE.match(str(r.get("turn_id") or ""))]
        in_lineage = [r for r in shaped if TURN_ID_RE.match(r["turn_id"])["session"] in chain]
        sid_ok = [r for r in recs if r.get("session_id") in chain]
        user_turns = sum(1 for _s, _c, turns in c17.JOURNEYS[name] for t in turns if t != "/compress")
        out["e08"] = {
            "hook_records": len(recs),
            "main_requests": len(main),
            "join_completeness_pct": round(100.0 * min(len(recs), len(main)) / len(main), 1) if main else None,
            "turn_id_well_formed_pct": round(100.0 * len(shaped) / len(recs), 1) if recs else None,
            "turn_id_session_in_lineage_pct": round(100.0 * len(in_lineage) / len(recs), 1) if recs else None,
            "session_id_in_lineage_pct": round(100.0 * len(sid_ok) / len(recs), 1) if recs else None,
            "distinct_turn_ids": len({r.get("turn_id") for r in recs}),
            "user_turns": user_turns,
            "api_request_id_present_pct": round(100.0 * sum(1 for r in recs if r.get("api_request_id")) / len(recs), 1) if recs else None,
            "first_chunk_at_present_pct": round(100.0 * sum(1 for r in recs if r.get("first_chunk_at")) / len(recs), 1) if recs else None,
            "platforms": sorted({str(r.get("platform")) for r in recs}),
            "sample": recs[:2],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--journeys", default=",".join(c17.JOURNEYS))
    ap.add_argument("--identity", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    run_root = Path(tempfile.mkdtemp(prefix="probe-", dir=os.environ.get("PROBE_TMP") or None))
    results = []
    for name in args.journeys.split(","):
        try:
            results.append(run_one(name, run_root / name, args.identity))
        except Exception:  # noqa: BLE001
            results.append({"journey": name, "harness_error": traceback.format_exc()[-2000:]})
        print(json.dumps({k: results[-1].get(k) for k in ("journey", "verdict_e07", "prefix_breaks_unexpected",
                                                         "wall_s", "run_journey")}), flush=True)
    Path(args.out).write_text(json.dumps({"label": args.label, "results": results}, indent=1, default=str),
                              encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
