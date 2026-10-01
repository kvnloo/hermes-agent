#!/usr/bin/env python3
"""F14 standing regression set: run every pinned probe on one worktree inside the xf sandbox and write
a verdict map. FACTORY.md section 13 row 2; the map is the per-arm guard compared under P5 ("F14 guards equal").

    f14_run.py run <worktree> <out.json> --label <label> [--only <id-substring>]
    f14_run.py compare <baseline.json> <other.json>          # exit 0 equal, 1 different, 2 not comparable
    f14_run.py set                                           # print the set hash and probe ids

* The set is f14_set.json beside this file; its canonical-JSON sha256 goes in every map, and maps with
  different set hashes are never compared.
* Every probe is its own cell: a fresh process in a fresh bwrap (xf-sandbox.sh) with its own run dir
  <runs>/<label>/<NN>-<slug> (created with exist_ok=False), so HOME and HERMES_HOME are never shared.
* Serial, in set order, one cell at a time; pytest probes use one worker (-j 1) and no file retry.
* Verdicts: PASS, FAIL, ERROR (crash, timeout, missing output), INFRA (the sandbox refused the cell or a
  blocked exec was logged), SKIP (pytest skipped every test).
* Only placeholders reach the map: <worktree>, <run>, <tmp>. Standard library only; the host side never
  imports worktree code.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
W0 = HERE.parent
SET_FILE = HERE / "f14_set.json"
SANDBOX = W0 / "sandbox" / "xf-sandbox.sh"
RUNS = W0 / "runs"
PROBES_DIR = HERE / "probes"
SCHEMA = "xf.f14.verdicts.v1"
SANDBOX_REFUSALS = {64: "usage", 65: "refused path", 97: "denylisted selection"}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_set() -> tuple[dict, str]:
    data = json.loads(SET_FILE.read_text(encoding="utf-8"))
    canon = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return data, hashlib.sha256(canon.encode("utf-8")).hexdigest()


class Norm:
    """Path and noise normalisation so markers and fingerprints are comparable across runs and worktrees."""

    def __init__(self, wt: Path, run: Path):
        self.pairs = [(str(run), "<run>"), (str(wt), "<worktree>")]

    def __call__(self, s: str) -> str:
        for a, b in self.pairs:
            s = s.replace(a, b)
        s = re.sub(r"/tmp/[A-Za-z0-9_.\-]+", "<tmp>", s)
        s = re.sub(r"0x[0-9a-fA-F]{6,}", "0x?", s)
        return s


ERR_LINE = re.compile(r"^\s*(?:E\s+)?([A-Za-z_][\w.]*(?:Error|Exception|Exit)\b.*|AssertionError.*|assert .*)$")


def failure_marker(rc: int, out: str, norm: Norm) -> str:
    lines = [ln for ln in out.splitlines() if ERR_LINE.match(ln)]
    tail = norm(lines[-1].strip())[:240] if lines else ""
    return f"rc={rc}" + (f": {tail}" if tail else "")


def fp(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ── judges: (probe, rc, out, outdir, norm) -> {id: (verdict, marker, fingerprint)} ──

def j_marker(p, rc, out, od, norm):
    m = p["judge"]["marker"]
    if rc == 0 and m in out:
        return {p["id"]: ("PASS", "", None)}
    return {p["id"]: ("FAIL", failure_marker(rc, out, norm) + ("" if m in out else f" | marker absent: {m}"), None)}


def j_json_verdict_map(p, rc, out, od, norm):
    f = od / p["judge"]["file"]
    subs = p["judge"]["subs"]
    if not f.exists():
        return {f"{p['id']}::{s}": ("ERROR", failure_marker(rc, out, norm) + " | no result file", None) for s in subs}
    v = read_json(f).get("verdict", {})
    res = {}
    for s in subs:
        got = v.get(s)
        res[f"{p['id']}::{s}"] = ("PASS", "", None) if got == "PASS" else (
            ("FAIL", f"verdict={got}", None) if got == "FAIL" else ("ERROR", f"scenario missing (verdict={got})", None))
    return res


def j_json_verdict_field(p, rc, out, od, norm):
    f = od / p["judge"]["file"]
    if not f.exists():
        return {p["id"]: ("ERROR", failure_marker(rc, out, norm) + " | no result file", None)}
    d = read_json(f)
    got = d.get(p["judge"]["field"])
    if got == "PASS" and rc == 0:
        return {p["id"]: ("PASS", "", None)}
    detail = {k: d.get(k) for k in ("provider_overflows", "learned_image_cost_after") if k in d}
    return {p["id"]: ("FAIL", f"rc={rc} verdict={got} {json.dumps(detail, sort_keys=True)}", None)}


def j_worktree_prefix(p, rc, out, od, norm):
    f = od / p["judge"]["file"]
    if rc != 0 or not f.exists():
        return {p["id"]: ("ERROR" if not f.exists() else "FAIL", failure_marker(rc, out, norm), None)}
    d = read_json(f)
    pw = d.get("per_worktree") or []
    checks = [
        ("stable_equal", d.get("stable_equal") is True),
        ("same_agent_rebuild_equal", d.get("same_agent_rebuild_equal") == [True, True]),
        ("restore_matches", len(pw) == 2 and all(x.get("restore_matches") is True for x in pw)),
        # 9da8df8d26: quoted operator text after the prompt cannot override the persisted runtime cwd,
        # so the stored prompt plus a trailing decoy still matches the runtime.
        ("trailing_decoy_cannot_override", len(pw) == 2 and all(x.get("trailing_decoy_matches") is True for x in pw)),
        ("drift_rejected", len(pw) == 2 and all(x.get("drift_rejected") is True for x in pw)),
        ("stable_has_no_cwd", len(pw) == 2 and all(x.get("stable_has_cwd") is False for x in pw)),
    ]
    bad = [n for n, ok in checks if not ok]
    obs = {"stable_equal": d.get("stable_equal"), "stable_common_prefix_chars": d.get("stable_common_prefix_chars"),
           "stable_sha256": [x.get("stable_sha256") for x in pw], "stable_chars": [x.get("stable_chars") for x in pw]}
    return {p["id"]: ("FAIL" if bad else "PASS", ("failed: " + ", ".join(bad)) if bad else "", fp(obs))}


def j_native_preflight(p, rc, out, od, norm):
    f = od / p["judge"]["file"]
    subs = p["judge"]["subs"]
    if not f.exists():
        return {f"{p['id']}::{s}": ("ERROR", failure_marker(rc, out, norm) + " | no result file", None) for s in subs}
    d = read_json(f)
    res = {}
    for s in subs:
        v = d.get(s)
        if not isinstance(v, dict):
            res[f"{p['id']}::{s}"] = ("ERROR", "scenario missing", None)
            continue
        if s.startswith("capture"):
            checks = [("turn1_completed", v.get("turn1_completed") is True),
                      ("checkpoint_persisted", v.get("checkpoint_persisted") is True),
                      ("turn2_completed", v.get("turn2_completed") is True),
                      ("no local compression on turn 2", v.get("local_compress_calls_turn2") == 0)]
            obs = {k: v.get(k) for k in ("local_compress_calls_turn2", "local_compress_calls_turn3", "provider_requests_total")}
        elif s == "restore":
            checks = [("checkpoint restored", (v.get("restored_checkpoint_chars") or 0) > 0),
                      ("resume_completed", v.get("resume_completed") is True),
                      ("no local compression on resume", v.get("local_compress_calls_resume") == 0)]
            obs = {k: v.get(k) for k in ("local_compress_calls_resume", "provider_requests_resume")}
        else:  # over_threshold_negative: deferral is one request, not a disable
            fired = (v.get("local_compress_calls_turn2") or 0) + (v.get("local_compress_calls_turn3") or 0)
            checks = [("local compression fires once real usage is over threshold", fired >= 1)]
            obs = {k: v.get(k) for k in ("local_compress_calls_turn2", "local_compress_calls_turn3")}
        bad = [n for n, ok in checks if not ok]
        res[f"{p['id']}::{s}"] = ("FAIL" if bad else "PASS", ("failed: " + ", ".join(bad)) if bad else "", fp(obs))
    return res


def j_goal_parity(p, rc, out, od, norm):
    f = od / p["judge"]["file"]
    if rc != 0 or not f.exists():
        return {p["id"]: ("ERROR" if not f.exists() else "FAIL", failure_marker(rc, out, norm), None)}
    text = norm(f.read_text(encoding="utf-8"))
    rows = json.loads(text)
    if len(rows) != p["judge"]["rows"]:
        return {p["id"]: ("FAIL", f"rows={len(rows)} expected {p['judge']['rows']}", fp(rows))}
    return {p["id"]: ("PASS", "", fp(rows))}


def j_pytest_junit(p, rc, out, od, norm):
    f = od / p["judge"]["file"]
    if not f.exists():
        return {p["id"]: ("ERROR", failure_marker(rc, out, norm) + " | no junit file", None)}
    root = ET.parse(f).getroot()
    cases, sysout = [], ""
    for tc in root.iter("testcase"):
        name = f"{tc.get('classname', '')}::{tc.get('name', '')}"
        state = "passed"
        for child in tc:
            if child.tag in ("failure", "error"):
                state = child.tag
            elif child.tag == "skipped":
                state = "skipped"
            elif child.tag == "system-out":
                sysout += child.text or ""
        cases.append((name, state))
    cases.sort()
    n = {s: sum(1 for _, x in cases if x == s) for s in ("passed", "failure", "error", "skipped")}
    counts = f"{n['passed']} passed, {n['failure']} failed, {n['error']} error, {n['skipped']} skipped"
    want = p["judge"].get("expect_tests")
    if not cases:
        return {p["id"]: ("ERROR", f"rc={rc}: no tests collected", None)}
    if n["failure"] or n["error"]:
        bad = [c for c, s in cases if s in ("failure", "error")]
        return {p["id"]: ("FAIL", f"{counts}: {', '.join(bad)[:200]}", fp(cases))}
    if n["passed"] == 0:
        return {p["id"]: ("SKIP", counts, fp(cases))}
    if want is not None and n["passed"] != want:
        return {p["id"]: ("FAIL", f"{counts}: expected {want} passed", fp(cases))}
    sm = p["judge"].get("stdout_marker")
    if sm and sm not in (sysout + out):
        return {p["id"]: ("FAIL", f"{counts}: marker absent: {sm}", fp(cases))}
    if rc != 0:
        return {p["id"]: ("FAIL", f"rc={rc} with {counts}", fp(cases))}
    return {p["id"]: ("PASS", "", fp(cases))}


def j_context_cap(p, rc, out, od, norm):
    cap = p["judge"]["cap"]
    if rc != 0 or "DONE f14" not in out:
        return {p["id"]: ("FAIL", failure_marker(rc, out, norm), None)}
    keep, bad = [], []
    for ln in out.splitlines():
        head = ln.split(" ", 1)[0]
        if head in ("SPAWN", "CYCLE", "MODEL_SWITCH", "CONFIG", "CONFIG_EXCEPTION", "ACCOUNTING", "LEGACY_RESOLVED", "SUMMARY_INPUT_CHARS"):
            keep.append(norm(ln))
        if head == "SPAWN":
            s = json.loads(ln.split(" ", 1)[1])
            if s.get("child") != cap:
                bad.append(f"spawn child trigger {s.get('child')} != {cap}")
        elif head == "CYCLE":
            c = json.loads(ln.split(" ", 1)[1])
            if c.get("trigger", 0) > cap or c.get("cap") != cap:
                bad.append(f"cycle {c.get('cycle')} trigger {c.get('trigger')} cap {c.get('cap')}")
        elif head == "MODEL_SWITCH":
            _, window, thr, capv = ln.split()
            if int(thr) > cap:
                bad.append(f"model switch {window}: trigger {thr} > {cap}")
    if not any(k.startswith("CYCLE") for k in keep):
        bad.append("no CYCLE lines")
    return {p["id"]: ("FAIL" if bad else "PASS", "; ".join(bad)[:240], fp(keep))}


def j_goal_scope(p, rc, out, od, norm):
    f = od / p["judge"]["file"]
    if rc != 0 or not f.exists():
        return {p["id"]: ("ERROR" if not f.exists() else "FAIL", failure_marker(rc, out, norm), None)}
    d = read_json(f)
    checks = []
    for label in ("cli", "gateway", "tui"):
        procs = (d.get(label) or {}).get("processes")
        checks.append((f"{label} judge sees own process only", procs == ["proc_own"]))
    checks.append(("delegation WAIT lifts on batch return", d.get("lifecycle_still_waiting") is False
                   and (d.get("lifecycle_completion_pending") or 0) >= 1))
    bad = [n for n, ok in checks if not ok]
    obs = {k: d.get(k) for k in ("cli", "gateway", "tui", "active", "old_pid_waiting", "old_session_waiting",
                                 "long_timer_still_waiting", "completion_judge_calls", "lifecycle_initial_pending",
                                 "lifecycle_completion_pending", "lifecycle_aux_calls", "lifecycle_still_waiting")}
    return {p["id"]: ("FAIL" if bad else "PASS", ("failed: " + ", ".join(bad)) if bad else "", fp(obs))}


def j_goal_repaste(p, rc, out, od, norm):
    m = p["judge"]["marker"]
    if rc != 0 or m not in out:
        return {p["id"]: ("FAIL", failure_marker(rc, out, norm), None)}
    i = out.rfind("{\n")
    try:
        summary = json.loads(out[i:].split("\n}\n")[0] + "\n}")
        summary.pop("artifact", None)
    except Exception:
        summary = None
    return {p["id"]: ("PASS", "", fp(summary) if summary is not None else None)}


def j_readtool(p, rc, out, od, norm):
    f = od / p["judge"]["file"]
    subs = p["judge"]["subs"]
    if not f.exists():
        return {f"{p['id']}::{s}": ("ERROR", failure_marker(rc, out, norm) + " | no result file", None) for s in subs}
    d = read_json(f)
    res = {}
    for s in subs:
        c = d.get(s)
        res[f"{p['id']}::{s}"] = ("ERROR", "case missing", None) if not c else (c["verdict"], norm(c["marker"]), c.get("fingerprint"))
    return res


JUDGES = {"marker": j_marker, "json_verdict_map": j_json_verdict_map, "json_verdict_field": j_json_verdict_field,
          "worktree_prefix": j_worktree_prefix, "native_preflight": j_native_preflight, "goal_parity": j_goal_parity,
          "pytest_junit": j_pytest_junit, "context_cap": j_context_cap, "goal_scope": j_goal_scope,
          "goal_repaste": j_goal_repaste, "readtool": j_readtool}


def sub_ids(p) -> list[str]:
    subs = p["judge"].get("subs")
    return [f"{p['id']}::{s}" for s in subs] if subs else [p["id"]]


def git_ro(wt: Path, *args) -> str:
    return subprocess.run(["git", "-C", str(wt), *args], capture_output=True, text=True, check=False).stdout.strip()


def run_probe(p: dict, idx: int, wt: Path, label_dir: Path) -> tuple[dict, dict]:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", p["id"]).strip("-")
    run = label_dir / f"{idx:02d}-{slug}"
    run.mkdir(parents=False, exist_ok=False)
    outdir = run / "out"
    outdir.mkdir()
    norm = Norm(wt, run)
    subst = {"{wt}": str(wt), "{run}": str(run), "{out}": str(outdir), "{probes}": str(PROBES_DIR)}

    def fill(s: str) -> str:
        for k, v in subst.items():
            s = s.replace(k, v)
        return s

    argv = [fill(a) for a in p["argv"]]
    if p["kind"] == "script":
        env = {"PYTHONDONTWRITEBYTECODE": "1", **{k: fill(v) for k, v in (p.get("env") or {}).items()}}
        argv = ["env", *[f"{k}={v}" for k, v in sorted(env.items())], *argv]
    cmd = [str(SANDBOX), str(run), str(wt), "--", *argv]
    timeout = p.get("timeout_s", 300)
    t0 = time.monotonic()
    try:
        cp = subprocess.run(cmd, cwd=str(wt), capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=timeout, stdin=subprocess.DEVNULL)
        rc, out = cp.returncode, cp.stdout + "\n" + cp.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc, timed_out = 124, True
        out = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
    wall = round(time.monotonic() - t0, 1)
    (run / "output.txt").write_text(out, encoding="utf-8")
    blocked_log = run / "blocked-exec.log"
    blocked = len(blocked_log.read_text(encoding="utf-8").splitlines()) if blocked_log.exists() else 0
    ids = sub_ids(p)
    if rc in SANDBOX_REFUSALS:
        res = {i: ("INFRA", f"sandbox rc={rc} ({SANDBOX_REFUSALS[rc]})", None) for i in ids}
    elif blocked:
        res = {i: ("INFRA", f"blocked exec logged ({blocked} line(s))", None) for i in ids}
    elif timed_out:
        res = {i: ("ERROR", f"TIMEOUT after {timeout}s", None) for i in ids}
    else:
        try:
            res = JUDGES[p["judge"]["name"]](p, rc, out, outdir, norm)
        except Exception as exc:
            res = {i: ("ERROR", f"judge error: {type(exc).__name__}: {norm(str(exc))[:200]}", None) for i in ids}
        for i in ids:  # a judge must answer for every pinned id
            res.setdefault(i, ("ERROR", "no verdict from judge", None))
    meta = {"rc": rc, "wall_s": wall, "blocked_exec": blocked, "run_dir": f"<runs>/{label_dir.name}/{run.name}"}
    return res, meta


def cmd_run(a) -> int:
    data, set_sha = load_set()
    wt = Path(a.worktree).resolve()
    if not (wt / ".git").exists():
        print(f"not a git worktree: {a.worktree}", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", a.label):
        print("label must match [A-Za-z0-9_.-]+", file=sys.stderr)
        return 2
    label_dir = RUNS / a.label
    label_dir.mkdir(parents=True, exist_ok=False)  # never reuse a label: fresh homes only
    out_path = Path(a.out)
    started = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.monotonic()
    verdicts, meta, expectations = {}, {}, {}
    probes = [p for p in data["probes"] if not a.only or a.only in p["id"]]
    for idx, p in enumerate(probes, 1):
        res, m = run_probe(p, idx, wt, label_dir)
        meta[p["id"]] = m
        for i, (v, mk, f) in res.items():
            verdicts[i] = {"verdict": v, "marker": mk, "fingerprint": f}
        exp = p.get("expect_on_base")
        if exp:
            obs = verdicts[p["id"]]["verdict"] if p["id"] in verdicts else None
            expectations[p["id"]] = {"expected": exp["verdict"], "observed": obs, "match": obs == exp["verdict"], "why": exp["why"]}
        print(f"[{idx:02d}/{len(probes)}] {p['id']}: " + ", ".join(f"{i.split('::')[-1]}={verdicts[i]['verdict']}" for i in res)
              + f"  ({m['wall_s']}s rc={m['rc']})", flush=True)
    counts = {}
    for v in verdicts.values():
        counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
    doc = {
        "schema": SCHEMA, "label": a.label, "set": data["set"], "set_rev": data["rev"], "set_sha256": set_sha,
        "runner_sha256": sha256_file(Path(__file__)), "sandbox_sha256": sha256_file(SANDBOX),
        "probe_helpers_sha256": {q.name: sha256_file(q) for q in sorted(PROBES_DIR.glob("*.py"))},
        "worktree_head": git_ro(wt, "rev-parse", "HEAD"), "worktree_dirty": bool(git_ro(wt, "status", "--porcelain")),
        "only": a.only, "started_utc": started, "wall_s": round(time.monotonic() - t0, 1),
        "counts": counts, "verdicts": dict(sorted(verdicts.items())), "expect_on_base": expectations,
        "flaky": data.get("flaky", []), "excluded": data.get("excluded", []), "cells": meta,
        "label_note": "OBSERVED: every verdict comes from a cell this runner executed; <runs> is the factory runs dir",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    mism = [k for k, e in expectations.items() if not e["match"]]
    print(f"F14 {a.label}: {counts} in {doc['wall_s']}s; set {set_sha[:12]}; expectation mismatches: {mism or 'none'}")
    return 0


def comparable(doc: dict) -> dict:
    return {k: (v["verdict"], v["marker"], v["fingerprint"]) for k, v in doc["verdicts"].items()}


def cmd_compare(a) -> int:
    x, y = read_json(Path(a.a)), read_json(Path(a.b))
    if x.get("set_sha256") != y.get("set_sha256") or x.get("only") or y.get("only"):
        print("NOT COMPARABLE: different set hash or a partial (--only) run")
        return 2
    flaky = {f["id"] if isinstance(f, dict) else f for f in (x.get("flaky") or []) + (y.get("flaky") or [])}
    cx, cy = comparable(x), comparable(y)
    diffs = []
    for k in sorted(set(cx) | set(cy)):
        if k in flaky or k.split("::")[0] in flaky:
            continue
        if cx.get(k) != cy.get(k):
            diffs.append((k, cx.get(k), cy.get(k)))
    for k, l, r in diffs:
        print(f"DIFF {k}\n  {a.a}: {l}\n  {a.b}: {r}")
    print("EQUAL" if not diffs else f"DIFFERENT: {len(diffs)} id(s)", f"(flaky excluded: {sorted(flaky)})" if flaky else "")
    return 0 if not diffs else 1


def cmd_set(a) -> int:
    data, set_sha = load_set()
    print(json.dumps({"set_sha256": set_sha, "probes": [p["id"] for p in data["probes"]],
                      "verdict_ids": [i for p in data["probes"] for i in sub_ids(p)],
                      "excluded": data["excluded"], "flaky": data.get("flaky", [])}, indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run")
    r.add_argument("worktree")
    r.add_argument("out")
    r.add_argument("--label", required=True)
    r.add_argument("--only", default=None, help="substring filter on probe id (partial maps are never comparable)")
    c = sp.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    sp.add_parser("set")
    a = ap.parse_args(argv)
    return {"run": cmd_run, "compare": cmd_compare, "set": cmd_set}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
