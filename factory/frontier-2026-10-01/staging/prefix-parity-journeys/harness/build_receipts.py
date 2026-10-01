"""Build the public receipts for staging/prefix-parity-journeys from a private raw set (run after
run_receipts.sh).

r02 superseded r01 (kept unchanged, private, in private/superseded-r01/): a new head on a fresh main,
the LEAF raw evidence r01 lacked, and receipts scrubbed for publication (no local paths, host name,
session/turn ids or message text).

r03 re-issues r02 from the same sealed raw set (private/raw-r02/, no run repeated): the host-load range
is computed from the recorded per-run load1 instead of typed by hand, the raw set and the as-run harness
moved under private/, and this file carries no local paths. Local values come from the environment:
  H_GIT        the bare repo holding BASE and HEAD (required)
  RAW          the raw directory (default <staging>/private/raw-r02)
  REV, PREV    this and the superseded revision (default r20261001-03, r20261001-02)
  PREV_DIR     where the superseded receipts live (default private/superseded-r02)
  AS_RUN_DIR   the private as-run harness copy, cited by sha256 (default private/harness-r02)
  WT, SCRATCH, HERMES_VENV, LIVE_HOME, PROBE_TMP   scrubbed to <wt>, <scratch>, <venv>, <live-home>,
               <probe-tmp> when set; the user's home, user name and host name are always scrubbed.
A raw set whose MANIFEST.sha256 already exists is verified, never rewritten; a new one is scrubbed in
place and then sealed.
"""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import re
import socket
import statistics
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

R = Path(__file__).resolve().parents[1]
ENV = os.environ
RAW = Path(ENV.get("RAW") or R / "private" / "raw-r02").resolve()
REV = ENV.get("REV", "r20261001-03")
PREV = ENV.get("PREV", "r20261001-02")
PREV_DIR = ENV.get("PREV_DIR", "private/superseded-r02")
AS_RUN_DIR = ENV.get("AS_RUN_DIR", "private/harness-r02")
H_GIT = ENV.get("H_GIT", "")
REISSUE = {  # per-revision note on what changed against PREV; empty for a fresh run
    "r20261001-03": "Re-issue of r20261001-02 from the same sealed raw set (manifest sha256 unchanged); no run "
                    "was repeated. Changed: env.host_load (r02 said '5-15 on 10 cores'; the recorded load1_end "
                    "values range as stated here), raw.dir/manifest (the raw set moved to private/raw-r02/), "
                    "inputs.harness (harness/ now takes local paths from the environment; the files that "
                    "produced the raw are cited by sha256 in inputs.harness_as_run), id and supersedes. Every "
                    "other field equals r02. Re-running with harness/ needs HERMES_VENV, LIVE_HOME and TH for "
                    "sandbox.sh, and RAW and PROBE_TMP passed through to run_receipts.sh.",
}
BASE = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
HEAD = "ddf4748d31cb5dc65e7cd0b0c5b27b98d63ae880"
NEW = ("messaging_gateway_restarts", "api_server_runs_restarts", "acp_restarts")
CHANGED = ("tests/e2e/core/history/test_prefix_stability.py", "tests/e2e/core/history/_helpers.py",
           "tests/e2e/core/parity/_drive_acp.py", "tests/e2e/core/parity/_drive_gateway.py",
           "tests/e2e/core/parity/_gateway_child.py")

_HOST = socket.gethostname().split(".")[0]
_USER = getpass.getuser()
_SID = r"\b20\d{6}_\d{6}_[0-9a-f]{6,8}\b"
_UUID = r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"


def _scrub_rules() -> list[tuple[str, str]]:
    """Local literals from the environment (longest first), then generic patterns, then a catch-all."""
    lits = [(ENV.get(k, ""), ph) for k, ph in (("WT", "<wt>"), ("SCRATCH", "<scratch>"), ("HERMES_VENV", "<venv>"),
                                               ("LIVE_HOME", "<live-home>"), ("PROBE_TMP", "<probe-tmp>"))]
    lits += [(str(R), "<staging>"), (str(Path.home()), "<home>")]
    rules = [(re.escape(v.rstrip("/")), ph) for v, ph in sorted(lits, key=lambda x: len(x[0]), reverse=True)
             if len(v.rstrip("/")) > 1]
    rules += [(r"/tmp/pytest-of-[^/\s\"']+", "<pytest-tmp>"), (rf"\b{re.escape(_HOST)}\b", "<host>"),
              (_SID, "<sid>"), (_UUID, "<uuid>"),
              (r"/(?:tmp|mnt|home|workspace|var)/[^\s\"'<>]*", "<path>")]
    return rules


# Applied to new raw files in place and, defensively, to everything a receipt quotes.
_SCRUB = _scrub_rules()
_FORBIDDEN = re.compile(rf"/(tmp|mnt|home|workspace|var)/|\b{re.escape(_HOST)}\b|\b{re.escape(_USER)}\b|{_SID}"
                        rf"|{_UUID}|[\w.+-]+@[\w-]+\.\w+")


def scrub(text: str) -> str:
    for pat, rep in _SCRUB:
        text = re.sub(pat, rep, text)
    return text


def short(msg: str) -> str:
    """A failure message without quoted prompt bytes: keep the marker, drop the diverging text."""
    msg = scrub(msg or "").split("\nassert ")[0]  # pytest's rewritten operands quote prompt text
    msg = re.sub(r"(first diverging byte at \d+):[^\n]*", r"\1", msg)
    return msg[:600]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args: str) -> str:
    assert H_GIT, "set H_GIT to the bare repo that holds BASE and HEAD"
    return subprocess.run(["git", "-C", H_GIT, *args], check=True, capture_output=True, text=True).stdout.strip()


_PLACEHOLDERS = sorted({rep[1:-1] for _pat, rep in _SCRUB}, key=len, reverse=True)


def seal_raw() -> str:
    m = RAW / "MANIFEST.sha256"
    if m.exists():  # already sealed: verify, never rewrite
        listed = dict(line.split()[::-1] for line in m.read_text(encoding="utf-8").splitlines())
        present = {p.name for p in RAW.iterdir() if p.is_file() and p.name != "MANIFEST.sha256"}
        assert set(listed) == present, f"raw set differs from its manifest: {sorted(set(listed) ^ present)[:5]}"
        bad = [n for n, h in listed.items() if sha(RAW / n) != h]
        assert not bad, f"raw files changed since sealing: {bad[:5]}"
        return sha(m)
    for p in sorted(RAW.iterdir()):
        if p.name == "MANIFEST.sha256" or not p.is_file():
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        s = scrub(t)
        if p.suffix == ".xml":  # keep junit well-formed: placeholders are escaped inside XML
            for name in _PLACEHOLDERS:
                s = s.replace(f"<{name}>", f"&lt;{name}&gt;")
        if s != t:
            p.write_text(s, encoding="utf-8")
    m = RAW / "MANIFEST.sha256"
    m.write_text("".join(f"{sha(p)}  {p.name}\n" for p in sorted(RAW.iterdir())
                         if p.is_file() and p.name != "MANIFEST.sha256"), encoding="utf-8")
    return sha(m)


def runs() -> dict:
    out = {}
    for line in (RAW / "runs.jsonl").read_text().splitlines():
        d = json.loads(line)
        out[d["run"]] = {k: v for k, v in d.items()}
    return out


def junit(name: str) -> list[dict]:
    p = RAW / f"{name}.junit.xml"
    if not p.exists():
        return []
    rows = []
    for tc in ET.parse(p).iter("testcase"):
        st, msg = "passed", ""
        for c in tc:
            if c.tag in ("failure", "error", "skipped"):
                st, msg = c.tag, c.get("message") or ""
        if st == "skipped" and "#76215" in msg:
            st = "xfailed"
        rows.append({"test": f"{tc.get('classname', '').rsplit('.', 1)[-1]}::{tc.get('name')}"
                     if "acp_adapter" in (tc.get("classname") or "") else tc.get("name"),
                     "time_s": float(tc.get("time") or 0), "outcome": st, "message": short(msg)})
    return rows


def tally(rows: list[dict]) -> str:
    c: dict[str, int] = {}
    for r in rows:
        c[r["outcome"]] = c.get(r["outcome"], 0) + 1
    return ", ".join(f"{v} {k}" for k, v in sorted(c.items())) or "no junit"


def _cores() -> str:
    """'<physical> cores / <logical> threads' from /proc/cpuinfo (Linux), else the logical count."""
    try:
        ids, cur = set(), {}
        for line in Path("/proc/cpuinfo").read_text().splitlines() + [""]:
            if not line.strip():
                if "core id" in cur:
                    ids.add((cur.get("physical id"), cur["core id"]))
                cur = {}
            elif ":" in line:
                k, v = line.split(":", 1)
                cur[k.strip()] = v.strip()
        if ids:
            return f"{len(ids)} cores / {os.cpu_count()} threads"
    except OSError:
        pass
    return f"{os.cpu_count()} logical CPUs"


def first_break(msg: str) -> dict | None:
    m = re.search(r"request (\d+) \(in hop (\d+) \((\w+) in", msg)
    return {"request": int(m.group(1)), "hop": int(m.group(2)), "surface": m.group(3)} if m else None


def main() -> None:
    manifest_sha = seal_raw()
    rr = runs()
    egress = json.loads((RAW / "egress_canary.json").read_text())
    old = dict(line.split()[::-1] for line in (R / PREV_DIR / "SHA256SUMS").read_text().splitlines())
    blobs = {f: git("rev-parse", f"{HEAD}:{f}")[:12] for f in CHANGED}
    blobs["tests/fakes/fake_llm_provider.py"] = git("rev-parse", f"{HEAD}:tests/fakes/fake_llm_provider.py")[:12] + " (unchanged)"
    loads = [float(v["load1_end"]) for v in rr.values() if v.get("load1_end")]
    raw_rel = RAW.relative_to(R).as_posix() if RAW.is_relative_to(R) else f"<raw>/{RAW.name}"
    common = {
        "schema": "xf.receipt.v1", "tier": "T1", "staging": "prefix-parity-journeys", "base_revision": BASE,
        "head_revision": HEAD, "provenance": "self", "cost_usd": 0.0,
        "env": {"python": "3.11.14 (<venv>, read-only bind; live home masked)",
                "network": "loopback only (netns); egress canary below",
                "relay": "nemo-relay init failed (installed plugin older than tree); journeys ran Relay-off",
                "host_load": f"shared host; load1 at the end of each run is recorded per run "
                             f"({min(loads):.2f}-{max(loads):.2f} over {len(loads)} runs, on {_cores()})"},
        "sandbox": "bwrap --dev-bind / / --tmpfs <live-home> --ro-bind <venv> <venv> --unshare-net --unshare-pid "
                   "--die-with-parent --clearenv; HOME/HERMES_HOME = scratch testhome; children get fixture homes",
        "raw": {"dir": f"{raw_rel} (private; path-scrubbed before sealing; never published or frozen)",
                "manifest": f"{raw_rel}/MANIFEST.sha256", "manifest_sha256": manifest_sha},
        "egress_canary": egress,
        "ai_assistance": "Claude Code (Opus 5.5) wrote the journeys, probes and arms; disclosed per repository policy",
        "origin_refs": ["NousResearch/hermes-agent#104414", "NousResearch/hermes-agent#45499",
                        "NousResearch/hermes-agent#120116", "NousResearch/hermes-agent#76215",
                        "NousResearch/hermes-agent#76224", "NousResearch/hermes-agent#88364",
                        "kvnloo/hermes-agent#319"],
        "privacy": "public-aggregate: no local paths, host name, session/turn ids or prompt text",
    }

    as_run = R / AS_RUN_DIR

    def inputs(*arms: str) -> dict:
        d = {"harness": {f"harness/{h.name}": sha(h) for h in sorted((R / "harness").glob("*")) if h.is_file()}}
        if as_run.is_dir():
            d["harness_as_run"] = {
                "dir": f"{AS_RUN_DIR} (private: local paths inline)",
                "note": "the files that produced the raw set; harness/ is the same code with local paths taken from "
                        "the environment",
                "sha256": {f"{AS_RUN_DIR}/{h.name}": sha(h) for h in sorted(as_run.glob("*")) if h.is_file()}}
        d.update({"arms": {f"arms/{a}": sha(R / "arms" / a) for a in arms}, "test_blobs_at_head": blobs})
        return d

    def write(stem: str, rid: str, body: dict) -> None:
        old_name = f"{stem}-{PREV}.json"
        sup = {"id": rid.replace(REV, PREV), "sha256": old.get(old_name),
               "path": f"{PREV_DIR}/{old_name}"} if old_name in old else None
        doc = {**common, "id": rid, "supersedes": sup, **({"reissue": REISSUE[REV]} if REV in REISSUE else {}),
               **body}
        text = json.dumps(doc, indent=2)
        bad = _FORBIDDEN.findall(text)
        assert not bad, f"{stem}: private data in public receipt: {bad[:5]}"
        p = R / "receipts" / f"{stem}-{REV}.json"
        p.write_text(text + "\n", encoding="utf-8")
        print(p.name, sha(p)[:16])

    cmd_c17 = ("<wt>$ harness/sandbox.sh bash scripts/run_tests.sh -j 2 --include-integration "
               "tests/e2e/core/history/test_prefix_stability.py -q -rxX --tb=line --junitxml=<raw>/<run>.junit.xml "
               "(HERMES_TEST_FILE_RETRIES=0)")
    cmd_all = (f"<wt>$ harness/sandbox.sh /usr/bin/env MAIN_REF={BASE} bash harness/run_receipts.sh "
               "(sequential; every run's rc/head/dirty/load1 in <raw>/runs.jsonl)")
    probe = {r["journey"]: r for r in json.loads((RAW / "e07_probe.json").read_text())["results"]}
    keep = ("surfaces", "process_lives", "main_requests", "aux_requests", "compaction_idx", "prefix_breaks_total",
            "prefix_breaks_at_compaction", "prefix_breaks_unexpected", "prefix_breaks", "tools_drift",
            "compaction_nests_previous_prompt", "usage_matches_billed", "db_integrity_ok", "system_prompt_chars",
            "summary_in_request", "verdict_e07", "wall_s", "run_journey")

    def pj(r: dict) -> dict:
        out = {k: r.get(k) for k in keep}
        out["prefix_breaks"] = [{"request": b["request"], "why": short(b["why"])} for b in r.get("prefix_breaks") or []]
        return out

    # --- E07: first slice proof (GREEN gated, RED ungated) + per-journey request-stream metrics ----------
    slice_rows, red_rows = junit("slice_full"), junit("red_ungated")
    main_rows = junit("adjacent_main_test_prefix_stability")
    t_new = sum(r["time_s"] for r in slice_rows if any(n in r["test"] for n in NEW))
    t_old = sum(r["time_s"] for r in slice_rows if not any(n in r["test"] for n in NEW))
    acp = probe["acp_restarts"]
    ci = acp.get("compaction_idx")
    write("E07", f"E07/{REV}", {
        "spec": {"question": "Is the request prefix byte-stable over process restarts and one compaction on the "
                             "messaging gateway, api_server /v1/runs and ACP?",
                 "falsifier": "a journey green while a sabotage that breaks prefix bytes is applied (NC receipt), "
                              "or a red journey with no reproducible product cause"},
        "inputs": inputs("red-ungate-known.patch"),
        "commands": [cmd_all, cmd_c17, "red: git apply arms/red-ungate-known.patch && " + cmd_c17 + " -k acp_restarts",
                     "<wt>$ harness/sandbox.sh $PY harness/journey_probe.py --out <raw>/e07_probe.json"],
        "runs": {k: rr.get(k) for k in ("slice_full", "red_ungated", "e07_probe")},
        "green": {"run": "slice_full", "tally": tally(slice_rows), "outcomes": slice_rows},
        "red": {"run": "red_ungated", "patch": "arms/red-ungate-known.patch (known_gate off; scratch, not shipped)",
                "tally": tally(red_rows), "outcomes": red_rows},
        "per_journey": {j: pj(r) for j, r in probe.items()},
        "measurements": [
            {"name": "new_journeys_green", "value": sum(1 for r in slice_rows if any(n in r["test"] for n in NEW[:2])
                                                         and r["outcome"] == "passed"), "of": 2, "label": "OBSERVED"},
            {"name": "acp_restarts_gated_outcome", "value": next((r["outcome"] for r in slice_rows
                                                                  if "acp_restarts" in r["test"]), None),
             "label": "OBSERVED"},
            {"name": "acp_unexpected_prefix_breaks", "value": acp.get("prefix_breaks_unexpected"), "label": "OBSERVED"},
            {"name": "acp_system_prompt_chars_before_after_compaction",
             "value": [acp["system_prompt_chars"][ci - 1], acp["system_prompt_chars"][ci]] if ci else None,
             "label": "OBSERVED"},
            {"name": "c17_file_wall_s_head", "value": rr["slice_full"]["wall_s"], "label": "OBSERVED",
             "detail": f"6 journeys; new three {t_new:.1f}s, existing three {t_old:.1f}s (pytest per-test times); "
                       f"load1 at end {rr['slice_full']['load1_end']}"},
            {"name": "c17_file_wall_s_main", "value": (rr.get("adjacent_main_test_prefix_stability") or {}).get("wall_s"),
             "label": "OBSERVED", "detail": f"3 journeys on main {BASE[:10]}, same run; per-test "
                                            f"{sum(r['time_s'] for r in main_rows):.1f}s"},
            {"name": "ci_e2e_budget_headroom", "value": "far under HERMES_TEST_FILE_TIMEOUT=900 s; adds about one "
                                                         "minute to one of 3 e2e workers", "label": "MODELED"},
        ],
        "verdict": "KEEP",
        "not_tested": ["real provider cache billing", "Relay ATOF/ATIF exporters", "serve WS, A2A, relay connector, "
                       "/goal continuation", "cwd change between lives on msg/api/acp"],
    })

    # --- E08: identity joins on turn_id --------------------------------------------------------------
    e08 = json.loads((RAW / "e08_probe.json").read_text())["results"]
    per = {}
    for r in e08:
        m = {k: v for k, v in (r.get("e08") or {"error": r.get("harness_error") or r.get("run_journey")}).items()
             if k != "sample"}
        per[r["journey"]] = {"surfaces": r.get("surfaces"), "verdict_e07_under_recorder": r.get("verdict_e07"),
                             "prefix_breaks_unexpected": r.get("prefix_breaks_unexpected"), **m}
    hooks = sum(v.get("hook_records") or 0 for v in per.values())
    reqs = sum(v.get("main_requests") or 0 for v in per.values())
    write("E08", f"E08/{REV}", {
        "spec": {"question": "Do post_api_request payloads carry a joinable Hermes turn_id "
                             "(<session>:<task>:<8hex>) and api_request_id on every surface, one per main request, "
                             "across restarts and a compaction?",
                 "falsifier": "a surface with hook records missing, malformed turn_ids, or session ids outside the "
                              "journey's lineage"},
        "inputs": inputs(), "commands": [cmd_all, "<wt>$ harness/sandbox.sh $PY harness/journey_probe.py --identity "
                                                  "--out <raw>/e08_probe.json"],
        "runs": {"e08_probe": rr.get("e08_probe")},
        "observer_effect": "one in-process plugin hook (post_api_request), no prompt injection; prefix verdicts under "
                           "the recorder are listed per journey for comparison with E07",
        "per_journey": per,
        "totals": {"journeys": len(per), "hook_records": hooks, "main_requests": reqs,
                   "per_journey_hook_records": {j: v.get("hook_records") for j, v in per.items()}},
        "redaction": "per-record samples (turn_id, api_request_id, session_id, task_id, pid, timestamps) are omitted "
                     "(FACTORY S5); their shape is counted in turn_id_well_formed_pct; raw records stay private",
        "label_default": "OBSERVED", "verdict": "KEEP",
        "not_tested": ["api_request_id equality with the provider-side request (the fake does not echo it)",
                       "Relay TURN_SCOPE equality (Relay off in this venv)", "tool_call_id joins",
                       "serve WS, cron, A2A surfaces"],
    })

    # --- Negative controls -------------------------------------------------------------------------------
    nc = {}
    for name, patch in (("nc1_full", "nc1-per-request-timestamp.patch"), ("nc2_full", "nc2-restart-rebuild-nonce.patch")):
        rows = junit(name)
        nc[name] = {"arm_patch": f"arms/{patch}", "run": rr.get(name), "tally": tally(rows), "outcomes": rows,
                    "first_unexpected_break": {r["test"].split("[")[-1].rstrip("]"): first_break(r["message"])
                                               for r in rows}}
    write("NC-sabotage", f"NC/{REV}", {
        "spec": {"question": "Do the journeys catch prefix sabotage? NC1 = per-request timestamp in the system message "
                             "(acceptance gate 2); NC2 = stored prompt treated stale on every fresh agent plus a "
                             "per-build nonce (#104414 shape).",
                 "falsifier": "any journey still passing under NC1 or NC2"},
        "inputs": inputs("nc1-per-request-timestamp.patch", "nc2-restart-rebuild-nonce.patch"),
        "commands": [cmd_all, "git apply arms/<nc patch> && " + cmd_c17 + " && git checkout -- <arm files>"],
        "arms": nc, "label_default": "OBSERVED",
        "measurements": [{"name": f"{k}_journeys_failed", "value": sum(o["outcome"] == "failure" for o in v["outcomes"]),
                          "of": len(v["outcomes"]), "label": "OBSERVED"} for k, v in nc.items()],
        "verdict": "PASS" if all(v["outcomes"] for v in nc.values())
        and all(o["outcome"] == "failure" for v in nc.values() for o in v["outcomes"]) else "FAIL",
        "reading": "first_unexpected_break gives, per journey, the first request outside the compaction whose prefix "
                   "changed and the process life (hop) it belongs to; hop 1 = inside the first life",
    })

    # --- ACP arms ----------------------------------------------------------------------------------------
    arms = {"main": {"patch": None, "gated": [r for r in slice_rows if "acp_restarts" in r["test"]],
                     "ungated": red_rows, "probe": {k: pj(acp).get(k) for k in (
                         "prefix_breaks", "compaction_nests_previous_prompt", "system_prompt_chars",
                         "summary_in_request", "verdict_e07")}}}
    for n, patch in (("fixA", "acp-fixA-no-cached-system-message.patch"),
                     ("hp76224", "acp-hp76224-in-place-compaction.patch"), ("both", "acp-both.patch")):
        pr = RAW / f"acp_{n}_probe.json"
        pn = json.loads(pr.read_text())["results"][0] if pr.exists() else {}
        arms[n] = {"patch": f"arms/{patch}", "gated": junit(f"acp_{n}_c17"), "ungated": junit(f"acp_{n}_ungated"),
                   "runs": [rr.get(f"acp_{n}_c17"), rr.get(f"acp_{n}_ungated"), rr.get(f"acp_{n}_probe")],
                   "probe": {k: pj(pn).get(k) for k in ("prefix_breaks", "compaction_nests_previous_prompt",
                                                         "system_prompt_chars", "summary_in_request", "verdict_e07",
                                                         "usage_matches_billed", "run_journey")}}
    write("ACP-arms", f"ACP-arms/{REV}", {
        "spec": {"question": "Which change makes acp_restarts pass: dropping system_message from the ACP compress_now "
                             "call (fixA), the in-place-compaction idea of #76224/#88364 hand-ported to "
                             "acp_adapter/commands.py (hp76224), or both?",
                 "varied": "acp_adapter/commands.py only", "falsifier": "fixA or hp76224 alone makes the journey pass"},
        "inputs": inputs("acp-fixA-no-cached-system-message.patch", "acp-hp76224-in-place-compaction.patch",
                         "acp-both.patch", "red-ungate-known.patch"),
        "external_fixes": [
            {"pr": 76224, "author": "JonthanaHanh", "commit_author": "RelaxJonh", "head": "20a047b7f2",
             "state": "OPEN, DIRTY (pre-#109610 acp_adapter/server.py + tests/acp/)"},
            {"pr": 88364, "author": "dosenr", "head": "f02e1487a8", "state": "OPEN, DIRTY; builds on #76224 "
             "(Co-authored-by RelaxJonh), sets compression_in_place at ACP agent construction, real-SessionDB restart "
             "test; also fixes #49226"}],
        "arm_note": "hp76224 is a hand-port of the shared idea (compression_in_place instead of detaching _session_db), "
                    "not either PR head; folding it in would need Co-authored-by for RelaxJonh and dosenr",
        "commands": [cmd_all, "git apply arms/<patch> [+ arms/red-ungate-known.patch] && " + cmd_c17 +
                     " -k acp_restarts; harness/journey_probe.py --journeys acp_restarts --out <raw>/acp_<arm>_probe.json"],
        "arms": arms, "label_default": "OBSERVED",
    })

    # --- LEAF: candidate own leaf at unit level, on main ----------------------------------------------
    # Two files per run: run_tests.sh forwards --junitxml to each per-file pytest, so the junit keeps only
    # the last file; the tallies come from the runner's own summary line in the raw log instead.
    def leaf_run(n: str) -> dict:
        log = (RAW / f"{n}.log").read_text(encoding="utf-8", errors="replace")
        m = re.search(r"=== Summary: (\d+) files, (\d+) tests passed, (\d+) failed", log)
        asserts = sorted({short(line.lstrip("║ ").strip()) for line in log.splitlines()
                          if line.lstrip("║ ").startswith("E   ")})
        return {"run": rr.get(n), "summary": m.group(0).strip("= ") if m else "no summary line",
                "files": int(m.group(1)) if m else None, "passed": int(m.group(2)) if m else None,
                "failed": int(m.group(3)) if m else None, "failing_assertions": asserts,
                "per_file": [short(line.strip()) for line in log.splitlines() if re.search(r"[✓✗] tests/acp_adapter/", line)]}

    leaf = {n: leaf_run(n) for n in ("leaf_base", "leaf_test_only", "leaf_full", "leaf_fix_old_test")}
    for n in leaf:
        leaf[n]["tally"] = f"{leaf[n]['passed']} passed, {leaf[n]['failed']} failed ({leaf[n]['files']} files)"
    write("LEAF-acp-nesting", f"LEAF-acp-nesting/{REV}", {
        "staging": "prefix-parity-journeys (ride_with candidate: acp-compress-prompt-nesting)",
        "head_revision": None,
        "candidate_patch": {"path": "arms/candidate-acp-compress-no-nesting.patch",
                            "sha256": sha(R / "arms" / "candidate-acp-compress-no-nesting.patch"),
                            "files": ["acp_adapter/commands.py (+2/-3)", "tests/acp_adapter/test_server.py (+3/-2)"]},
        "inputs": inputs("candidate-acp-compress-no-nesting.patch"),
        "commands": [cmd_all + "; LEAF runs on a detached MAIN_REF checkout",
                     "git apply --include=<glob> arms/candidate-acp-compress-no-nesting.patch && harness/sandbox.sh bash "
                     "scripts/run_tests.sh -j 2 tests/acp_adapter/test_server.py tests/acp_adapter/test_acp_commands.py "
                     "-q --tb=short --junitxml=<raw>/<run>.junit.xml; globs: none (leaf_base), tests/* (leaf_test_only), "
                     "* (leaf_full), acp_adapter/* (leaf_fix_old_test)"],
        "runs": leaf,
        "proof": {"adjacent_base": leaf["leaf_base"]["tally"], "red_on_main": leaf["leaf_test_only"]["tally"],
                  "green": leaf["leaf_full"]["tally"], "old_test_pins_bug": leaf["leaf_fix_old_test"]["tally"],
                  "negative_control": "leaf_test_only is the fix with its production line reverted",
                  "e2e": "ACP-arms receipt: fixA alone removes the nesting; acp_restarts passes only with both"},
        "label_default": "OBSERVED",
        "verdict": "KEEP (candidate own leaf; not on this branch by design: the first slice is test-only)",
    })

    # --- E09 smoke (harness validation only) ---------------------------------------------------------
    p9 = RAW / "e09_smoke.json"
    if p9.exists():
        e09 = json.loads(p9.read_text())

        def med(rows: list[dict], k: str) -> float | None:
            v = [r[k] for r in rows if r.get(k) is not None]
            return round(statistics.median(v), 1) if v else None

        write("E09-smoke", f"E09-smoke/{REV}", {
            "label_default": "OBSERVED (smoke)",
            "spec": {"question": "Does the submit->first-delta harness run on tui_gateway, api_server /v1/runs (SSE) "
                                 "and ACP? NOT the E09 measurement: shared host, n=5, no A/A, no ABBA.",
                     "falsifier": "harness error or missing timestamps on any surface"},
            "inputs": inputs(), "commands": [cmd_all, "<wt>$ harness/sandbox.sh $PY harness/e09_first_delta.py "
                                                      "--surfaces gw,api,acp --reps 5 --warmup 1 --delay 0.05 --order AB "
                                                      "--out <raw>/e09_smoke.json"],
            "runs": {"e09_smoke": rr.get("e09_smoke")},
            "load1": [e09.get("load1_start"), e09.get("load1_end")], "provider_ttft_s": e09.get("delay_s"),
            "per_surface": {r["surface"]: {"error": r.get("error"), "n": len(r.get("rows") or []),
                                           **{f"median_{k}": med(r.get("rows") or [], k)
                                              for k in ("pre_api_ms", "first_delta_ms", "delivery_ms", "complete_ms")}}
                            for r in e09["runs"]},
            "verdict": "HARNESS_OK (numbers are smoke, not evidence)",
        })

    # --- Adjacent ------------------------------------------------------------------------------------
    adj = {}
    for b in ("test_entrypoint_parity", "test_transcript_ledger"):
        br, mn = junit(f"adjacent_branch_{b}"), junit(f"adjacent_main_{b}")
        adj[b] = {"branch": {"run": rr.get(f"adjacent_branch_{b}"), "tally": tally(br), "outcomes": br},
                  "main": {"run": rr.get(f"adjacent_main_{b}"), "tally": tally(mn), "outcomes": mn},
                  "identical_pass_fail_set": sorted((r["test"], r["outcome"]) for r in br)
                  == sorted((r["test"], r["outcome"]) for r in mn) and bool(br)}
    write("ADJ", f"ADJ/{REV}", {
        "spec": {"question": "Do the suites that share the changed helpers (including the refactored drive_acp) keep "
                             "their pass/fail set?"},
        "inputs": inputs(), "commands": [cmd_all + "; branch first, then git checkout --detach MAIN_REF"],
        "adjacent": adj, "main_revision": BASE, "label_default": "OBSERVED",
    })

    sums = R / "receipts" / "SHA256SUMS"
    sums.write_text("".join(f"{sha(p)}  {p.name}\n" for p in sorted((R / "receipts").glob(f"*-{REV}.json"))),
                    encoding="utf-8")
    print("SHA256SUMS written; raw manifest", manifest_sha[:16])


if __name__ == "__main__":
    main()
