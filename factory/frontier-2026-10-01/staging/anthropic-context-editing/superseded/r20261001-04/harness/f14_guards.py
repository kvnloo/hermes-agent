"""Run the F14 standing regression set (FACTORY.md section 13, row 2) on one arm of
staging/anthropic-context-editing and write a placeholder-only summary to --raw.

Each probe runs unmodified from the checkout, in a fresh process with an empty environment and its
own throwaway HOME/HERMES_HOME under --private. Full stdout/stderr and any output files stay under
--private (they contain local paths and are never published). The public summary keeps, per probe:
exit code, whether its documented marker was seen, a verdict, the key result fields, and the
sha256 of the output after path/port/pid/timing normalisation.

Probes (the F14 list): token_accounting/{replay_gates, ab_image_cost_calibration,
worktree_prompt_prefix}; native_compaction/ab_checkpoint_preflight; provider_fallback/probe_104120,
probe_104260, probe_104360; goal_command_parity; compaction/test_region_scoping; the postmortem
runner's 9 non-live probes (evals.postmortem.run, live probes excluded); and 4 of the 5 hand-run
review probes (context_cap, deadline, goal_scope, finalizer_schedule).
Not run (listed in the summary's not_run): goal_repaste, which needs a copy of a real session
state.db, and "readtool fixtures via direct read_file only", for which F14 names no command.

Usage:
  HERMES_PYTHON=<venv python> python f14_guards.py --worktree <checkout> --arm base|head \
      --raw raw --private <scratch dir outside the artifact tree>
"""
import argparse
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--worktree", required=True)
ap.add_argument("--arm", required=True, choices=["base", "head"])
ap.add_argument("--raw", required=True)
ap.add_argument("--private", required=True)
ARGS = ap.parse_args()
W = Path(ARGS.worktree).resolve()
RAW = Path(ARGS.raw).resolve()
PRIV = Path(ARGS.private).resolve() / ARGS.arm
PY = os.environ["HERMES_PYTHON"]
if PRIV.exists():
    shutil.rmtree(PRIV)
PRIV.mkdir(parents=True)
RAW.mkdir(parents=True, exist_ok=True)

TAG = "arm"  # same tag on both arms so outputs stay comparable
PM = "evals/postmortem/review_probes"
# (id, argv, extra env, stdout marker or None, output file relative to the probe dir or None)
PROBES = [
    ("token_accounting/replay_gates", ["{py}", "evals/token_accounting/replay_gates.py", "--out", "{out}/result.json"], {}, None, "result.json"),
    ("token_accounting/ab_image_cost_calibration", ["{py}", "evals/token_accounting/ab_image_cost_calibration.py", "--out", "{out}/result.json"], {}, None, "result.json"),
    ("token_accounting/worktree_prompt_prefix", ["{py}", "evals/token_accounting/worktree_prompt_prefix.py"], {"PROBE_OUT": "{out}/probe"}, None, "probe/measurements.json"),
    ("native_compaction/ab_checkpoint_preflight", ["{py}", "evals/native_compaction/ab_checkpoint_preflight.py", "--out", "{out}/result.json"], {}, None, "result.json"),
    ("provider_fallback/probe_104120", ["{py}", "evals/provider_fallback/probe_104120.py", "{repo}"], {}, None, None),
    ("provider_fallback/probe_104260", ["{py}", "evals/provider_fallback/probe_104260.py", "{repo}"], {}, None, None),
    ("provider_fallback/probe_104360", ["{py}", "evals/provider_fallback/probe_104360.py", "{repo}"], {}, None, None),
    ("goal_command_parity", ["{py}", "evals/goal_command_parity.py", "{repo}", "{out}/goalhome", "{out}/result.json"], {}, None, "result.json"),
    # FACTORY lists "bash scripts/run_tests.sh evals/compaction/test_region_scoping.py -q", but that
    # collects 0 tests (the file defines run_mode(), no test_* functions); it is a script with a
    # __main__ block, so it runs as one and must print its own ALL PASS line.
    ("compaction/test_region_scoping", ["{py}", "evals/compaction/test_region_scoping.py"], {}, "scoping tripwire: ALL PASS", None),
    ("postmortem/run_non_live", ["{py}", "-m", "evals.postmortem.run", "--repo", "{repo}"], {}, None, None),
    ("postmortem/context_cap_probe", ["{py}", f"{PM}/context_cap_probe.py", "{repo}", TAG], {}, f"DONE {TAG}", None),
    ("postmortem/deadline_probe", ["{py}", f"{PM}/deadline_probe.py", "{repo}"], {}, "PROBE_COMPLETE", None),
    ("postmortem/goal_scope_probe", ["{py}", f"{PM}/goal_scope_probe.py", "{out}/result.json"], {}, None, "result.json"),
    # README form: pytest -p <plugin> --finalizer-probe=consumer-first on the relay stream test. Run with
    # pytest directly: scripts/run_tests.sh validates the extra flag before the plugin loads and refuses it.
    ("postmortem/finalizer_schedule_probe", ["{py}", "-m", "pytest", "tests/e2e/test_relay_native_openai_stream.py", "-q", "-p",
                                             "evals.postmortem.review_probes.finalizer_schedule_probe", "--finalizer-probe=consumer-first"],
     {}, "2 passed", None),
]
NOT_RUN = [
    {"id": "readtool fixtures via direct read_file only", "why": "F14 (FACTORY.md section 13, row 2) names no script, fixture path or command for this item"},
    {"id": "postmortem/goal_repaste_probe", "why": "reads RF_STATE_COPY (default <tmp>/rf/state_copy.db), a copy of a real session state.db; "
                                                   "this run may not touch real sessions, and no synthetic copy is defined"},
]


def git(*args):
    return subprocess.run(["git", *args], cwd=W, check=True, capture_output=True, text=True).stdout


def normalise(text: str, home: Path, out: Path) -> str:
    for p, ph in ((str(out), "<out>"), (str(home), "<home>"), (str(W), "<worktree>"), (str(PRIV), "<private>"), (PY, "<venv-python>")):
        text = text.replace(p, ph)
    text = re.sub(r"/tmp/[^\s\"',)\]]+", "<tmp>", text)
    text = re.sub(r"(127\.0\.0\.1|localhost|\[::1\]|::1)[:,] ?\d{2,5}", r"\1:<port>", text)
    text = re.sub(r"\b\d+(\.\d+)?\s?(s|ms|sec|seconds)\b", "<t>", text)
    text = re.sub(r"\b[0-9a-f]{40}\b", "<sha>", text)
    text = re.sub(r"\b20\d\d-\d\d-\d\d[T ]\d\d:\d\d:\d\d(\.\d+)?(Z|[+-]\d\d:?\d\d)?", "<ts>", text)
    return text


def run(pid, argv, extra, marker, outfile):
    slug = pid.replace("/", "__")
    pdir = PRIV / slug
    home, out = pdir / "home", pdir / "out"
    (home / ".hermes").mkdir(parents=True)
    out.mkdir()
    fmt = {"py": PY, "repo": str(W), "out": str(out)}
    argv = [a.format(**fmt) for a in argv]
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "HERMES_HOME": str(home / ".hermes"), "HERMES_DISABLE_LAZY_INSTALLS": "1",
           "HERMES_DISABLE_MODEL_METADATA_FETCH": "1", "TZ": "UTC", "LANG": "C.UTF-8", "TMPDIR": str(pdir)}
    env.update({k: v.format(**fmt) for k, v in extra.items()})
    t0, c0 = time.monotonic(), resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        p = subprocess.run(argv, cwd=W, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        rc, text = p.returncode, p.stdout + "\n--- stderr ---\n" + p.stderr
    except subprocess.TimeoutExpired:
        rc, text = 124, "TIMEOUT"
    c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    (pdir / "output.txt").write_text(text, encoding="utf-8")
    stdout_part = text.split("\n--- stderr ---\n")[0]
    file_text = None
    if outfile and (out / outfile).exists():
        file_text = (out / outfile).read_text(encoding="utf-8", errors="replace")
    dirty = git("status", "--porcelain").strip()
    if dirty:  # a probe wrote into the checkout: record it, then restore the tree
        subprocess.run(["git", "checkout", "-q", "--", "."], cwd=W, check=True)
        subprocess.run(["git", "clean", "-fdq"], cwd=W, check=True)
    summary_marker = None
    if pid == "postmortem/run_non_live":
        table = {}
        for ln in stdout_part.splitlines():
            m = re.match(r"^(#\d+)\s+(\S+)\s+(PASS|FAIL\S*)", ln)
            if m:
                table[f"{m.group(1)} {m.group(2)}"] = m.group(3)
        key = {"probes": table, "n": len(table), "pass": sum(v == "PASS" for v in table.values())}
        verdict = "PASS" if rc == 0 and table and all(v == "PASS" for v in table.values()) else "FAIL"
    else:
        summary_marker = (marker in stdout_part) if marker else None
        key = None
        if file_text is not None:
            try:
                key = json.loads(normalise(file_text, home, out))
            except json.JSONDecodeError:
                key = {"unparsed_sha256": hashlib.sha256(normalise(file_text, home, out).encode()).hexdigest()}
        verdict = "PASS" if rc == 0 and summary_marker in (True, None) else "FAIL"
        if pid == "token_accounting/replay_gates" and isinstance(key, dict):
            verdict = "PASS" if rc == 0 and all(v == "PASS" for v in key.get("verdict", {}).values()) else "FAIL"
    norm_out = normalise(stdout_part, home, out)
    (pdir / "output.normalised.txt").write_text(norm_out, encoding="utf-8")
    if file_text is not None:
        (pdir / "file.normalised.txt").write_text(normalise(file_text, home, out), encoding="utf-8")
    pytest_summary = [ln.strip() for ln in stdout_part.splitlines() if ln.strip().startswith("=== Summary:")]
    return {
        "id": pid, "rc": rc, "marker": marker, "marker_found": summary_marker, "verdict": verdict,
        "pytest_summary": [re.sub(r" in [0-9.]+s.*", "", s) for s in pytest_summary] or None,
        "stdout_normalised_sha256": hashlib.sha256(norm_out.encode()).hexdigest(),
        "file_normalised_sha256": hashlib.sha256(normalise(file_text, home, out).encode()).hexdigest() if file_text is not None else None,
        "key": key, "wrote_into_checkout": bool(dirty),
        "wall_s": round(time.monotonic() - t0, 1),
        "cpu_core_s": round((c1.ru_utime - c0.ru_utime) + (c1.ru_stime - c0.ru_stime), 1),
        "command": " ".join(normalise(a, home, out) for a in argv),
    }


def main() -> int:
    assert git("status", "--porcelain").strip() == "", "checkout dirty before F14"
    sha = git("rev-parse", "HEAD").strip()
    rows = []
    for pid, argv, extra, marker, outfile in PROBES:
        row = run(pid, argv, extra, marker, outfile)
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("id", "rc", "verdict", "marker_found", "wall_s")}), flush=True)
    assert git("status", "--porcelain").strip() == "", "checkout dirty after F14"
    doc = {"arm": ARGS.arm, "commit": sha, "probes": rows, "not_run": NOT_RUN,
           "env": "env -i PATH=/usr/bin:/bin HOME=<home> HERMES_HOME=<home>/.hermes HERMES_DISABLE_LAZY_INSTALLS=1 "
                  "HERMES_DISABLE_MODEL_METADATA_FETCH=1 TZ=UTC LANG=C.UTF-8 TMPDIR=<probe dir>; fresh <home> per probe; cwd <worktree>",
           "wall_s_total": round(sum(r["wall_s"] for r in rows), 1), "cpu_core_s_total": round(sum(r["cpu_core_s"] for r in rows), 1)}
    text = json.dumps(doc, indent=2) + "\n"
    for bad in [f"/{d}/" for d in ("tmp", "home", "workspace", "mnt", "Users")]:
        assert bad not in text, f"absolute path {bad!r} left in the public summary"
    (RAW / f"f14_{ARGS.arm}.json").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
