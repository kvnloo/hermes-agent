"""Per-hunk sabotage, round 2 (FACTORY section 8 step 9). Successor of ``per_hunk_sabotage.py``
(kept unchanged for the round-1 receipt), with two additions:

1. Each failing run is classified by HOW it failed. ``project_stale_tool_results`` is fail-open: it
   catches any exception, logs "Tool-result projection failed; sending the unprojected transcript"
   and sends the request unprojected. A reverted hunk that raises inside the pass therefore turns
   projection off, and test A then fails by assertion although the cause is a crash. Such runs are
   reported as ``assertion_via_swallowed_exception`` with the exception line; a failure with no
   swallowed exception is ``assertion``; an exception that reaches the test is ``crash``.
2. The gate patch's hunks are reverted one at a time as well (on top of the full arm), and each gate
   revert also runs the extra probes named on the command line (Bedrock Converse, third-party
   Messages endpoint), whose outputs are summarised next to the wire-test result.

A hunk is pinned when reverting it re-REDs test A or test B. The arm is rebuilt from a clean
checkout before every hunk.

Usage:
  <venv python> per_hunk_sabotage_r2.py <worktree> <main sha> <arm commit> <gate patch> <out.json> <testhome> \
      [<probe name>=<probe script> ...]
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WT, MAIN, ARM, GATE, OUT, TESTHOME = sys.argv[1:7]
PROBES = dict(arg.split("=", 1) for arg in sys.argv[7:])
PY = sys.executable  # the venv interpreter running this harness is handed to run_tests.sh and the probes
TEST = "tests/e2e/core/history/test_tool_result_projection_wire.py"
NODES = {"test_projection_breaks_the_prefix_once_per_paid_batch_and_never_undoes_itself": "A",
         "test_projection_never_invalidates_replayed_preserved_thinking": "B"}
SWALLOW = "Tool-result projection failed; sending the unprojected transcript"
EXC_LINE = re.compile(r"^[\s║]*([A-Za-z_][\w.]*(?:Error|Exception)): (.*)$")


def git(*args, check=True, input=None):
    return subprocess.run(["git", *args], cwd=WT, capture_output=True, text=True, check=check, input=input).stdout


def rebuild():
    git("checkout", "-q", "--detach", ARM)
    git("checkout", "-q", "--", ".")
    git("clean", "-fdq", "--", "agent", "tools", "gateway", "tui_gateway", "hermes_cli", "scripts", "website")
    git("apply", GATE)


def swallowed(text):
    lines, found = text.splitlines(), []
    for i, line in enumerate(lines):
        if SWALLOW in line:
            for nxt in lines[i + 1:i + 60]:
                m = EXC_LINE.match(nxt)
                if m:
                    found.append(f"{m.group(1)}: {m.group(2)}"[:200])
                    break
    return sorted(set(found))


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
    swallowed_exc = swallowed(text)
    if not (failed or errors):
        how = None
    elif errors or (first_error and "AssertionError" not in first_error):
        how = "crash"
    elif swallowed_exc:
        how = "assertion_via_swallowed_exception"
    else:
        how = "assertion"
    return {"failed": failed, "errors": errors, "summary": summary, "first_error_line": first_error[:240],
            "swallowed_exceptions": swallowed_exc, "failed_how": how, "wall_s": round(time.monotonic() - t0, 1)}


def run_probe(name, script):
    out = Path(tempfile.mkdtemp(prefix=f"sab-{name}-", dir=os.environ.get("TMPDIR") or "/tmp")) / "out.json"
    scratch = out.parent / "scratch"
    scratch.mkdir()
    env = {"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "F04_SCRATCH": str(scratch)}
    proc = subprocess.run([PY, script, WT, str(out), f"gate-revert-{name}"], env=env, capture_output=True, text=True)
    if not out.exists():
        return {"rc": proc.returncode, "error": (proc.stderr or proc.stdout).strip().splitlines()[-1:]}
    data = json.loads(out.read_text(encoding="utf-8"))
    keep = ("requests", "projection_passes", "pass_request_indices", "invalidated_thinking_blocks",
            "invalidated_replays", "thinking_blocks_on_wire", "sum_request_chars", "outcomes", "egress_blocked")
    return {"rc": proc.returncode, **{k: data[k] for k in keep if k in data},
            "keys": sorted(k for k in data if k not in keep)}


def split_hunks(diff_text):
    patches, file_header, in_header, cur_file = [], [], False, None
    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git"):
            file_header, in_header = [line], True
            cur_file = line.rstrip("\n").split(" w/" if " w/" in line else " b/", 1)[1]
        elif line.startswith("@@"):
            in_header = False
            patches.append({"file": cur_file, "hunk": line.strip()[:120], "text": "".join(file_header) + line})
        elif in_header:
            file_header.append(line)
        else:
            patches[-1]["text"] += line
    return patches


def revert_and_run(p, n, source, probes):
    rebuild()
    applied = subprocess.run(["git", "apply", "-R", "-"], cwd=WT, input=p["text"], capture_output=True, text=True)
    entry = {"n": n, "source": source, "file": p["file"], "hunk": p["hunk"],
             "added_lines": sum(1 for ln in p["text"].splitlines() if ln.startswith("+") and not ln.startswith("+++"))}
    if applied.returncode != 0:
        entry.update(reverted=False, note=applied.stderr.strip()[:200])
        return entry
    r = run_wire()
    entry.update(reverted=True, **r, red_again=bool(r["failed"] or r["errors"]))
    if probes:
        entry["probes"] = {name: run_probe(name, script) for name, script in probes.items()}
    return entry


rebuild()
carrier_diff = git("diff", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/", MAIN, "--", ".", ":(exclude)tests")
# The gate is applied on top of the carrier's new module, so the module's single new-file hunk includes it;
# the gate's own hunks are reverted separately below.
carrier_hunks = split_hunks(carrier_diff)
gate_hunks = split_hunks(Path(GATE).read_text(encoding="utf-8"))

baseline = run_wire()
results = []
for i, p in enumerate(carrier_hunks):
    results.append(revert_and_run(p, i + 1, "carrier (+ gate where it sits in the new module)", {}))
    print(json.dumps({k: results[-1].get(k) for k in ("n", "file", "hunk", "failed", "failed_how")}), flush=True)
for j, p in enumerate(gate_hunks):
    results.append(revert_and_run(p, len(carrier_hunks) + j + 1, f"gate patch hunk {j + 1}", PROBES))
    print(json.dumps({k: results[-1].get(k) for k in ("n", "file", "hunk", "failed", "failed_how", "probes")}),
          flush=True)
rebuild()
git("checkout", "-q", "--", ".")
out = {"label": "OBSERVED (scripts/run_tests.sh -j 2, one run per hunk)", "main": MAIN, "arm": ARM,
       "gate_patch": Path(GATE).name, "baseline": baseline, "hunks": results,
       "pinned": [f"{r['file']} {r['hunk']} [{r['failed_how']}]" for r in results if r.get("red_again")],
       "unpinned": [f"{r['file']} {r['hunk']}" for r in results if r.get("reverted") and not r.get("red_again")],
       "not_reverted": [f"{r['file']} {r['hunk']}" for r in results if not r.get("reverted")]}
Path(OUT).write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({k: out[k] for k in ("pinned", "unpinned", "not_reverted")}, indent=1))
