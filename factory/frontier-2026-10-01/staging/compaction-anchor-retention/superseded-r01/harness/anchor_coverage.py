#!/usr/bin/env python3
"""Anchor-index coverage harness ($0, T0; no LLM, no network, no private data).

Arms are alternative copies of agent/context_compressor.py. Each arm is loaded in its own
subprocess as ``agent.context_compressor`` on top of a checkout (the other agent.* modules
come from that checkout), and only its ``_ANCHOR_PATTERNS`` / ``_build_anchor_index`` are
exercised.

Experiments:
  E03p  gold reachability: the 90 committed gold answers in
        evals/compaction/results/SCORECARD-2026-08-15.md (6 banks, 4 lineages), hand-labelled
        by identifier class. A gold is "reachable" when, written in region text, some
        anchor row would capture it verbatim. OBSERVED over the committed strings;
        whether the gold text actually sat in the compacted region is NOT known.
  E03s  synthetic survival: each bank's in-scope golds planted once each (assistant text)
        inside a seeded synthetic region at three filler densities; survival = needle
        present in the real _build_anchor_index output. MODELED (synthetic regions).
  F02s  budget audit over the same synthetic regions (sections chars vs
        _LEAN_ANCHOR_BUDGET_CHARS, whole index chars, chars/4 token estimate) plus the
        strict-additivity check (base section lines are a prefix of the arm's).
  N01   noise audit: the arm's rows over a public in-repo text corpus
        (website/docs/**/*.md + AGENTS.md); dotted keys are cross-checked against the
        flattened DEFAULT_CONFIG key set.

Usage (driver):
  anchor_coverage.py --checkout <worktree> --arm base=<file> --arm branch=<file> ... --out <json>
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------- isolation (lifted from
# evals/provider_fallback/probe_104260.py): loopback-only sockets, scratch HOME/HERMES_HOME.
_blocked: list[str] = []
_orig_connect = socket.socket.connect


def _loopback_only(self, address):
    if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
        _blocked.append(str(address))
        raise RuntimeError("anchor_coverage blocks non-loopback network")
    return _orig_connect(self, address)


socket.socket.connect = _loopback_only

# ---------------------------------------------------------------- frozen gold labels
# (bank, index) -> (class, needles, natural_variant_or_None). Classes in OUT_OF_SCOPE are
# prose / numbers / names that an identifier index is not meant to carry.
OUT_OF_SCOPE = {"prose", "number", "name", "date", "quote", "title"}
LABELS: dict[tuple[str, int], tuple[str, list[str], str | None]] = {
    ("sweep/30b95351c7", 1): ("prose", [], None),
    ("sweep/30b95351c7", 2): ("number", [], None),
    ("sweep/30b95351c7", 3): ("symbol", ["backgroundThrottling"], None),
    ("sweep/30b95351c7", 4): ("error_message", ["Auto merge is not allowed for this repository (enablePullRequestAutoMerge)"],
                              "GraphQL: Auto merge is not allowed for this repository (enablePullRequestAutoMerge)"),
    ("sweep/30b95351c7", 5): ("prose", [], None),
    ("sweep/30b95351c7", 6): ("prose", [], None),
    ("sweep/30b95351c7", 7): ("file_path", ["tests/test_packaging_metadata.py"], None),
    ("sweep/30b95351c7", 8): ("prose", [], None),
    ("sweep/30b95351c7", 9): ("prose", [], None),
    ("sweep/30b95351c7", 10): ("number", [], None),
    ("sweep/30b95351c7", 11): ("number", [], None),
    ("sweep/30b95351c7", 12): ("title", [], None),
    ("sweep/30b95351c7", 13): ("pr_issue", ["82980"], "PR #82980 watcher: === ALL GREEN (streak=1, checks=46) ==="),
    ("sweep/30b95351c7", 14): ("sha", ["ee33edd5804689243f974536ef7aecb9"], None),
    ("sweep/30b95351c7", 15): ("sha", ["f9d64b9a9d8b306f64851c1a13869d96ad5d7869"], None),
    ("sweep/5be475cde0", 1): ("command", ['gh issue list --search "<topic>" --state open --limit 100 --json number,title'], None),
    ("sweep/5be475cde0", 2): ("prose", [], None),
    ("sweep/5be475cde0", 3): ("pr_issue", ["#32263"], None),
    ("sweep/5be475cde0", 4): ("pr_issue", ["#60593", "#61969"], None),
    ("sweep/5be475cde0", 5): ("command", ['git log -S "<symbol>"'], None),
    ("sweep/5be475cde0", 6): ("prose", [], None),
    ("sweep/5be475cde0", 7): ("prose", [], None),
    ("sweep/5be475cde0", 8): ("prose", [], None),
    ("sweep/5be475cde0", 9): ("prose", [], None),
    ("sweep/5be475cde0", 10): ("error_message", ["Blocked: `git <op>` would rewrite Hermes's live source checkout (/home/teknium/.hermes/hermes-agent) and can mix module"], None),
    ("sweep/5be475cde0", 11): ("error_message", ["No space left on device"],
                               "Fatal error: error writing to /tmp/ccH06T4r.s: No space left on device"),
    ("sweep/5be475cde0", 12): ("number", [], None),
    ("sweep/5be475cde0", 13): ("pr_issue", ["#86645"], None),
    ("sweep/5be475cde0", 14): ("prose", [], None),
    ("sweep/5be475cde0", 15): ("error_keyword", ["ModuleNotFoundError: No module named 'hermes_cli.dashboard_auth'"], None),
    ("gui/36d3d87e0b", 1): ("pr_issue", ["#86617"], None),
    ("gui/36d3d87e0b", 2): ("prose", [], None),
    ("gui/36d3d87e0b", 3): ("file_path_suffix", ["tests/hermes_cli/test_session_recovery_lost_and_found.py:327"], None),
    ("gui/36d3d87e0b", 4): ("prose", [], None),
    ("gui/36d3d87e0b", 5): ("pr_issue", ["#84287"], None),
    ("gui/36d3d87e0b", 6): ("prose", [], None),
    ("gui/36d3d87e0b", 7): ("email", ["602028@ky-tech.com.cn"], None),
    ("gui/36d3d87e0b", 8): ("error_message", ["Blocked: `git <op>` would rewrite Hermes's live source checkout"], None),
    ("gui/36d3d87e0b", 9): ("prose", [], None),
    ("gui/36d3d87e0b", 10): ("error_message", ["GraphQL: Pull Request has merge conflicts (mergePullRequest)"], None),
    ("gui/36d3d87e0b", 11): ("title", [], None),
    ("gui/36d3d87e0b", 12): ("prose", [], None),
    ("gui/36d3d87e0b", 13): ("date", [], None),
    ("gui/36d3d87e0b", 14): ("error_message", ["Property 'onToggleUnread' is missing in type"],
                             "src/app.tsx(12,7): error TS2741: Property 'onToggleUnread' is missing in type '{ id: string; }'"),
    ("gui/36d3d87e0b", 15): ("name", [], None),
    ("gui/9c55c707b6", 1): ("pr_issue", ["#85162", "#82285"], None),
    ("gui/9c55c707b6", 2): ("prose", [], None),
    ("gui/9c55c707b6", 3): ("symbol", ["implemented_on_main", "cannot_reproduce", "incoherent"], None),
    ("gui/9c55c707b6", 4): ("handle", ["@gui8515"], None),
    ("gui/9c55c707b6", 5): ("error_message", ["Hermes backend exited (0)"], None),
    ("gui/9c55c707b6", 6): ("prose", [], None),
    ("gui/9c55c707b6", 7): ("prose", [], None),
    ("gui/9c55c707b6", 8): ("task_id", ["sa-2-7318d0ba"], None),
    ("gui/9c55c707b6", 9): ("prose", [], None),
    ("gui/9c55c707b6", 10): ("error_keyword", ["AssertionError: assert 't2' == 't1'"], None),
    ("gui/9c55c707b6", 11): ("prose", [], None),
    ("gui/9c55c707b6", 12): ("file_bare", ["use-prompt-actions/index.ts", "session-tile-actions.ts"], None),
    ("gui/9c55c707b6", 13): ("sha", ["bddadfe9e21e24b3d52e2b15f138c42474dede42"], None),
    ("gui/9c55c707b6", 14): ("error_message", ["GraphQL: Pull Request has merge conflicts (mergePullRequest)"], None),
    ("gui/9c55c707b6", 15): ("file_path", ["apps/desktop/src/app/session/hooks/use-session-actions/utils.ts"], None),
    ("prmerge/703ae2774a", 1): ("pr_issue", ["#63359"], None),
    ("prmerge/703ae2774a", 2): ("symbol", ["subagent_lifecycle"], None),
    ("prmerge/703ae2774a", 3): ("number", [], None),
    ("prmerge/703ae2774a", 4): ("prose", [], None),
    ("prmerge/703ae2774a", 5): ("pr_issue", ["#64436"], None),
    ("prmerge/703ae2774a", 6): ("prose", [], None),
    ("prmerge/703ae2774a", 7): ("name", [], None),
    ("prmerge/703ae2774a", 8): ("pr_issue", ["#64204"], None),
    ("prmerge/703ae2774a", 9): ("config_key", ["plugins.stream_reasoning_deltas"], None),
    ("prmerge/703ae2774a", 10): ("prose", [], None),
    ("prmerge/703ae2774a", 11): ("symbol", ["nvapi-redaction"], None),
    ("prmerge/703ae2774a", 12): ("symbol", ["on_stream_start", "on_stream_delta", "on_stream_end", "on_interim_message"], None),
    ("prmerge/703ae2774a", 13): ("prose", [], None),
    ("prmerge/703ae2774a", 14): ("pr_issue", ["#64230"], None),
    ("prmerge/703ae2774a", 15): ("pr_issue", ["#65447"], None),
    ("acp/f45358df19", 1): ("quote", [], None),
    ("acp/f45358df19", 2): ("pr_issue", ["#6391"], None),
    ("acp/f45358df19", 3): ("file_path", ["hermes_cli/models.py"], None),
    ("acp/f45358df19", 4): ("symbol", ["alibaba-coding-plan"], None),
    ("acp/f45358df19", 5): ("quote", [], None),
    ("acp/f45358df19", 6): ("error_message", ["Blocked: `git checkout` would rewrite Hermes's live source checkout (/home/teknium/.hermes/hermes-agent) and can mix mod"], None),
    ("acp/f45358df19", 7): ("prose", [], None),
    ("acp/f45358df19", 8): ("sha", ["24ba86627515ad5fda69a39ef338c365713448bc"], None),
    ("acp/f45358df19", 9): ("prose", [], None),
    ("acp/f45358df19", 10): ("sql", ["UPDATE kanban_notify_subs SET delivery_mode = 'notify+wake' WHERE platform != 'tui'"], None),
    ("acp/f45358df19", 11): ("file_path_suffix", ["tests/gateway/test_kanban_notifier_apiserver_wake.py::test_apiserver_sub_wakes_real_session_via_self_post"], None),
    ("acp/f45358df19", 12): ("prose", [], None),
    ("acp/f45358df19", 13): ("handle", ["@Tranquil-Flow"], None),
    ("acp/f45358df19", 14): ("prose", [], None),
    ("acp/f45358df19", 15): ("file_path", ["plugins/platforms/slack/adapter.py"], None),
}
NEEDLE_PREFIX = 100  # long needles compare on their first 100 chars (rows cap values near that)


def parse_banks(scorecard: str) -> list[tuple[str, int, str]]:
    out, tx, bank = [], None, None
    for line in scorecard.splitlines():
        m = re.match(r"### Transcript: (\w+)", line)
        if m:
            tx = m.group(1)
        m = re.search(r"15 exam questions \(questions-([0-9a-f]+)\.json\)", line)
        if m:
            bank, n = f"{tx}/{m.group(1)}", 0
        m = re.match(r"\s+gold: `(.*)`\s*$", line)
        if m:
            n += 1
            out.append((bank, n, m.group(1)))
    return out


# ---------------------------------------------------------------- arm loading
def load_arm(checkout: str, arm_file: str):
    sys.path.insert(0, checkout)
    spec = importlib.util.spec_from_file_location("agent.context_compressor", arm_file)
    mod = importlib.util.module_from_spec(spec)
    import agent  # noqa: F401  (package from the checkout)
    sys.modules["agent.context_compressor"] = mod
    spec.loader.exec_module(mod)
    return mod


def row_values(mod, text: str) -> dict[str, list[str]]:
    vals = {}
    for label, pattern, _cap in mod._ANCHOR_PATTERNS:
        vals[label] = [m.group(0).strip().rstrip(".,;:") for m in pattern.finditer(text)]
    return vals


def reachable(mod, text: str, needles: list[str]) -> tuple[int, int, list[str]]:
    vals = row_values(mod, text)
    hit, rows = 0, set()
    for nd in needles:
        key = nd[:NEEDLE_PREFIX]
        found = [lab for lab, vs in vals.items() if any(key in v for v in vs)]
        if found:
            hit += 1
            rows.update(found)
    return hit, len(needles), sorted(rows)


# ---------------------------------------------------------------- synthetic regions (MODELED)
DENSITIES = {
    # counts of DISTINCT filler identifiers per class; each repeated 1..rep_max times (Zipf-ish)
    "sparse": dict(files=8, errors=4, prs=10, shas=4, urls=2, handles=2, dotted=4, fatal=2, tasks=2, prose=40, rep_max=3),
    "medium": dict(files=60, errors=30, prs=80, shas=20, urls=10, handles=10, dotted=30, fatal=15, tasks=10, prose=200, rep_max=5),
    "dense": dict(files=400, errors=200, prs=300, shas=100, urls=60, handles=60, dotted=150, fatal=100, tasks=80, prose=800, rep_max=8),
}
WORDS = ("the deploy step reran after rebasing onto main and the watcher stayed green while we waited "
         "for review comments on the batch so nothing else changed in this pass").split()


def _filler_items(rng: random.Random, d: dict) -> list[str]:
    hx = lambda n: "".join(rng.choice("0123456789abcdef") for _ in range(n))  # noqa: E731
    seg = lambda: rng.choice(["agent", "tools", "gateway", "hermes_cli", "apps/desktop/src", "tests/agent", "plugins/platforms"])  # noqa: E731
    items = []
    items += [f"{seg()}/{'_'.join(rng.sample(WORDS, 2))}_{i}.py" for i in range(d["files"])]
    items += [f"{rng.choice(['ValueError', 'KeyError', 'RuntimeError', 'AssertionError'])}: case {i} {' '.join(rng.sample(WORDS, 6))}" for i in range(d["errors"])]
    items += [f"#{rng.randint(10000, 129999)}" for _ in range(d["prs"])]
    items += [hx(40) for _ in range(d["shas"])]
    items += [f"https://github.com/NousResearch/hermes-agent/pull/{rng.randint(10000, 129999)}" for _ in range(d["urls"])]
    items += [f"@user{rng.randint(100, 99999)}" for _ in range(d["handles"])]
    items += [f"{rng.choice(['self', 'compression', 'agent', 'msg', 'delegation'])}.{rng.choice(WORDS)}_{rng.choice(WORDS)}_{i}" for i in range(d["dotted"])]
    items += [f"fatal: {' '.join(rng.sample(WORDS, 5))} {i}" for i in range(d["fatal"])]
    items += [f"sa-{rng.randint(0, 9)}-{hx(8)}" for _ in range(d["tasks"])]
    return items


def synthetic_region(golds: list[str], density: str, seed: int) -> list[dict]:
    rng = random.Random(f"{density}:{seed}")
    d = DENSITIES[density]
    lines = []
    for item in _filler_items(rng, d):
        reps = min(d["rep_max"], max(1, int(rng.paretovariate(1.3))))
        lines += [item] * reps
    lines += [" ".join(rng.choice(WORDS) for _ in range(14)) for _ in range(d["prose"])]
    rng.shuffle(lines)
    msgs: list[dict] = []
    for i in range(0, len(lines), 6):
        role = "assistant" if (i // 6) % 2 == 0 else "tool"
        msgs.append({"role": role, "content": "\n".join(lines[i:i + 6])})
    for g in golds:  # each gold once, in assistant text, on its own line
        pos = rng.randrange(len(msgs) + 1)
        msgs.insert(pos, {"role": "assistant", "content": f"Recorded for the batch:\n{g}\nMoving on."})
    return msgs


def sections_of(index: str) -> list[str]:
    return index.split("\n")[3:-1] if index else []


# ---------------------------------------------------------------- per-arm worker
def worker(checkout: str, arm_file: str, scorecard_path: str, seeds: int) -> dict:
    mod = load_arm(checkout, arm_file)
    budget = mod._LEAN_ANCHOR_BUDGET_CHARS
    golds = parse_banks(Path(scorecard_path).read_text(encoding="utf-8"))
    # E03p
    e03p = []
    for bank, n, gold in golds:
        cls, needles, natural = LABELS[(bank, n)]
        row = {"bank": bank, "n": n, "class": cls, "in_scope": cls not in OUT_OF_SCOPE}
        if needles:
            h, t, rows = reachable(mod, gold, needles)
            row.update(raw_hit=h, raw_total=t, raw_rows=rows)
            if natural:
                h2, t2, rows2 = reachable(mod, natural, needles)
                row.update(natural_hit=h2, natural_total=t2, natural_rows=rows2)
        e03p.append(row)
    # E03s + F02s
    by_bank: dict[str, list[str]] = {}
    for bank, n, gold in golds:
        cls, needles, natural = LABELS[(bank, n)]
        if needles:
            by_bank.setdefault(bank, []).append((natural or gold, needles, cls))
    e03s, f02 = [], []
    for density in DENSITIES:
        for seed in range(seeds):
            for bank, items in sorted(by_bank.items()):
                region = synthetic_region([g for g, _, _ in items], density, seed)
                t0 = time.perf_counter()
                index = mod._build_anchor_index(region)
                dt = time.perf_counter() - t0
                secs = sections_of(index)
                labels_emitted = [s.split(":", 1)[0] for s in secs]
                f02.append({"density": density, "seed": seed, "bank": bank,
                            "sections_chars": sum(len(s) for s in secs), "index_chars": len(index),
                            "labels": labels_emitted, "sections": secs, "build_s": round(dt, 5),
                            "region_chars": sum(len(m["content"]) for m in region)})
                for g, needles, cls in items:
                    hit = sum(1 for nd in needles if nd[:NEEDLE_PREFIX] in index)
                    e03s.append({"density": density, "seed": seed, "bank": bank, "class": cls,
                                 "hit": hit, "total": len(needles)})
    # N01 noise audit over public docs
    root = Path(checkout)
    corpus = [root / "AGENTS.md"] + sorted((root / "website" / "docs").rglob("*.md"))
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in corpus)
    corpus_sha = hashlib.sha256(text.encode()).hexdigest()
    noise = {}
    try:
        from hermes_cli.config_defaults import DEFAULT_CONFIG

        def flat(d, pre=""):
            for k, v in d.items():
                key = f"{pre}{k}"
                yield key
                if isinstance(v, dict):
                    yield from flat(v, key + ".")
        cfg_keys = set(flat(DEFAULT_CONFIG))
    except Exception as exc:  # pragma: no cover
        cfg_keys, noise["config_import_error"] = set(), repr(exc)
    t0 = time.perf_counter()
    vals = row_values(mod, text)
    noise["scan_s"] = round(time.perf_counter() - t0, 4)
    for label, vs in vals.items():
        counts: dict[str, int] = {}
        for v in vs:
            counts[v] = counts.get(v, 0) + 1
        top = sorted(counts, key=lambda v: -counts[v])[:15]
        entry = {"matches": len(vs), "distinct": len(counts), "top15": [[v, counts[v]] for v in top]}
        if label == "dotted keys":
            distinct = list(counts)
            entry["distinct_in_DEFAULT_CONFIG"] = sum(1 for v in distinct if v in cfg_keys)
            entry["top15_in_DEFAULT_CONFIG"] = sum(1 for v in top if v in cfg_keys)
        noise[label] = entry
    noise.update(corpus_files=len(corpus), corpus_chars=len(text), corpus_sha256=corpus_sha,
                 default_config_keys=len(cfg_keys))
    # whole-region timing on a ~2 MB dense region (single run, noisy; OBSERVED wall only)
    big = synthetic_region([], "dense", 999) * 3
    t0 = time.perf_counter()
    mod._build_anchor_index(big)
    big_s = time.perf_counter() - t0
    return {"arm_file_sha256": hashlib.sha256(Path(arm_file).read_bytes()).hexdigest(),
            "labels": [lab for lab, _p, _c in mod._ANCHOR_PATTERNS], "budget": budget,
            "E03p": e03p, "E03s": e03s, "F02s": f02, "N01": noise,
            "timing_big_region": {"chars": sum(len(m["content"]) for m in big), "build_s": round(big_s, 4)},
            "egress_blocked": list(_blocked)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkout", required=True)
    ap.add_argument("--arm", action="append", default=[])
    ap.add_argument("--scorecard", default="evals/compaction/results/SCORECARD-2026-08-15.md")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out")
    ap.add_argument("--worker", nargs=2, metavar=("ARM_FILE", "OUT"))
    a = ap.parse_args()
    scorecard = str(Path(a.checkout) / a.scorecard)
    if a.worker:
        res = worker(a.checkout, a.worker[0], scorecard, a.seeds)
        Path(a.worker[1]).write_text(json.dumps(res), encoding="utf-8")
        return
    results = {}
    for spec in a.arm:
        name, path = spec.split("=", 1)
        tmp = f"{a.out}.{name}.part"
        subprocess.run([sys.executable, __file__, "--checkout", a.checkout, "--scorecard", a.scorecard,
                        "--seeds", str(a.seeds), "--worker", path, tmp], check=True)
        results[name] = json.loads(Path(tmp).read_text(encoding="utf-8"))
        os.remove(tmp)
    Path(a.out).write_text(json.dumps({"arms": results, "seeds": a.seeds,
                                       "scorecard_sha256": hashlib.sha256(Path(scorecard).read_bytes()).hexdigest()}),
                           encoding="utf-8")


if __name__ == "__main__":
    main()
