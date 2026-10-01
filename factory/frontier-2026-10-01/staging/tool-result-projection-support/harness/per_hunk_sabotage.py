"""Per-hunk sabotage (FACTORY section 8 step 9): revert each non-test fix hunk alone and re-run the
wire test with the canonical runner. A hunk is pinned when reverting it re-REDs test A or test B.

The fix is everything the arm adds on top of main outside tests/: the carrier's 11 non-test files
(as rebased) plus the fold-in gate patch. The arm is rebuilt from a clean checkout before every hunk.

Usage (from anywhere; worktree is modified and restored):
  <venv python> per_hunk_sabotage.py <worktree> <main sha> <arm commit> <gate patch> <out.json> <testhome>
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

WT, MAIN, ARM, GATE, OUT, TESTHOME = sys.argv[1:7]
PY = sys.executable  # the venv interpreter running this harness is handed to run_tests.sh
TEST = "tests/e2e/core/history/test_tool_result_projection_wire.py"
NODES = {"test_projection_breaks_the_prefix_once_per_paid_batch_and_never_undoes_itself": "A",
         "test_projection_never_invalidates_replayed_preserved_thinking": "B"}


def git(*args, check=True, input=None):
    return subprocess.run(["git", *args], cwd=WT, capture_output=True, text=True, check=check, input=input).stdout


def rebuild():
    git("checkout", "-q", "--detach", ARM)
    git("checkout", "-q", "--", ".")
    git("clean", "-fdq", "--", "agent", "tools", "gateway", "tui_gateway", "hermes_cli", "scripts", "website")
    git("apply", GATE)


def run_wire():
    env = {"PATH": "/usr/bin:/bin", "HOME": TESTHOME, "HERMES_HOME": TESTHOME + "/.hermes", "HERMES_PYTHON": PY,
           "LANG": "C.UTF-8"}
    t0 = time.monotonic()
    proc = subprocess.run(["bash", "scripts/run_tests.sh", "-j", "2", TEST, "-q"], cwd=WT, env=env,
                          capture_output=True, text=True)
    text = proc.stdout + proc.stderr
    failed = sorted({NODES.get(m, m) for m in re.findall(r"FAILED \S+::(\w+)", text)})
    errors = sorted(set(re.findall(r"ERROR \S+::(\w+)", text)))
    summary = next((ln.strip() for ln in text.splitlines() if ln.startswith("=== Summary")), "")
    first_error = next((ln.strip() for ln in text.splitlines() if ln.lstrip(" ║").startswith("E ")), "")
    return {"failed": failed, "errors": errors, "summary": summary, "first_error_line": first_error[:240],
            "wall_s": round(time.monotonic() - t0, 1)}


rebuild()
fix_diff = git("diff", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/", MAIN, "--", ".", ":(exclude)tests")
# split into single-hunk patches
patches, file_header, in_header, cur_file = [], [], False, None
for line in fix_diff.splitlines(keepends=True):
    if line.startswith("diff --git"):
        file_header, in_header = [line], True
        cur_file = line.rstrip("\n").split(" b/", 1)[1]
    elif line.startswith("@@"):
        in_header = False
        patches.append({"file": cur_file, "hunk": line.strip()[:120], "text": "".join(file_header) + line})
    elif in_header:
        file_header.append(line)
    else:
        patches[-1]["text"] += line

baseline = run_wire()
results = []
for i, p in enumerate(patches):
    rebuild()
    applied = subprocess.run(["git", "apply", "-R", "-"], cwd=WT, input=p["text"], capture_output=True, text=True)
    entry = {"n": i + 1, "file": p["file"], "hunk": p["hunk"],
             "added_lines": sum(1 for ln in p["text"].splitlines() if ln.startswith("+") and not ln.startswith("+++"))}
    if applied.returncode != 0:
        entry.update(reverted=False, note=applied.stderr.strip()[:200])
    else:
        r = run_wire()
        entry.update(reverted=True, **r, red_again=bool(r["failed"] or r["errors"]))
    results.append(entry)
    print(json.dumps({k: entry.get(k) for k in ("n", "file", "hunk", "failed", "red_again")}), flush=True)
rebuild()
git("checkout", "-q", "--", ".")
out = {"label": "OBSERVED (scripts/run_tests.sh -j 2, one run per hunk)", "main": MAIN, "arm": ARM,
       "gate_patch": Path(GATE).name, "baseline": baseline, "hunks": results,
       "pinned": [f"{r['file']} {r['hunk']}" for r in results if r.get("red_again")],
       "unpinned": [f"{r['file']} {r['hunk']}" for r in results if r.get("reverted") and not r.get("red_again")]}
Path(OUT).write_text(json.dumps(out, indent=2), encoding="utf-8")
