"""F15-lite (T0): each in-process guard class blocks, and escapes when that one class is removed.

    python f15_guard_canary.py <runner worktree> <scratch dir> <out.json>

Escapes stay on the host: the connect target is this host's own non-loopback address with a local
listener, the lookup is of a numeric address (no resolver traffic), the open hits a decoy "live home"
file and every exec form (argv, shell=True, bash -c, bare name via PATH) runs a decoy `hermes` script
that only touches a marker file. The PATH class only asks shutil.which("hermes"); it never runs it.

Round 1 (verifier finding): adds the shell-text exec class (shell=True, bash -c, PATH) and the
"interpreter bin dir not on the cell PATH" class, so 7 classes instead of 5.

Round 2 (verifier finding): records the exec matcher's known limits against the intact guard. The
shell text is split into words, not parsed, so a glob, quote concatenation, a backslash escape or a
variable that builds the name runs the decoy by absolute path; so does code that imports hermes_cli.
These are OBSERVED escapes written down as a limit; they are not a PASS criterion. Three controls
(plain shell=True, the whole word inside a variable assignment, python -m hermes_cli.main) must block.
"""
import hashlib, json, os, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

wt, scratch, out_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(wt))
from evals._factory import gate_runner as gr  # noqa: E402

PY = os.environ.get("XF_PYTHON") or sys.executable  # <venv-python>: the interpreter the cells use (read-only)
GUARD = gr.GUARD
SHELL_FORMS = ("hermes_exec_shell", "hermes_exec_bash_c", "hermes_exec_path")
SABOTAGE = {  # class -> (canary checks that must all flip, checks that must stay blocked, edit that removes only that class)
    "nonloopback_connect": (("nonloopback_connect",), (), 'raise OSError(errno.ENETUNREACH, "factory guard: non-loopback connect blocked")', "pass"),
    "name_lookup": (("name_lookup",), (), 'raise socket.gaierror(socket.EAI_NONAME, "factory guard: name lookup blocked")', "pass"),
    "live_home_open": (("live_home_open",), (), 'raise PermissionError(errno.EACCES, "factory guard: live Hermes home is off limits", path)', "pass"),
    "hermes_exec": (("hermes_exec", *SHELL_FORMS), (), 'raise PermissionError(errno.EPERM, "factory guard: exec of a Hermes entrypoint blocked")', "pass"),
    # Only the shell-text split removed: the argv form must still block, every shell form must escape.
    "hermes_exec_shell_text": (SHELL_FORMS, ("hermes_exec",), "shell = next((i for i, x in enumerate(argv) if os.path.basename(x) in _SHELLS), len(argv))", "shell = len(argv)"),
}
rows = []
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
gr.GUARD = GUARD
run = gr.new_run(scratch, f"f15-intact-{stamp}", PY)
intact = gr.canary(run)
rows.append({"arm": "intact", "passed": intact["passed"], "checks": intact["checks"], "blocked_events": intact["blocked_events"]})
for cls, (flip, keep, old, new) in SABOTAGE.items():
    assert GUARD.count(old) == 1, old
    gr.GUARD = GUARD.replace(old, new)
    run = gr.new_run(scratch, f"f15-no-{cls}-{stamp}", PY)
    res = gr.canary(run)
    rows.append({"arm": f"without {cls}", "escaped": all(res["checks"][c] is False for c in flip) and all(res["checks"][c] for c in keep),
                 "must_flip": list(flip), "must_stay_blocked": list(keep), "checks": res["checks"]})
gr.GUARD = GUARD
# PATH class: put the interpreter's bin dir (where its hermes console scripts live) back on the cell PATH.
run = gr.new_run(scratch, f"f15-no-path_shim-{stamp}", PY)
shutil.rmtree(run.dir / "bin")
os.symlink(os.path.dirname(PY), run.dir / "bin")
res = gr.canary(run)
rows.append({"arm": "without hermes_not_on_path", "escaped": res["checks"]["hermes_on_path"] is False and all(res["checks"][c] for c in ("hermes_exec", *SHELL_FORMS)),
             "must_flip": ["hermes_on_path"], "must_stay_blocked": ["hermes_exec", *SHELL_FORMS], "checks": res["checks"]})
# Selection layer: the H1 denylist in lint_spec.
spec = {"xf_spec": 1, "kind": "redgreen", "id": "x", "base": {"pin": "0" * 40}, "head": {"commit": "1" * 40},
        "probe": {"kind": "pytest", "files": ["tests/e2e/core/upgrade/test_update.py"]}, "oracle": {"red_markers": ["x"]}}
lint_blocked = any("denylisted" in p for p in gr.lint_spec(spec))
saved = gr.DENY_GLOBS
gr.DENY_GLOBS = ()
lint_escaped = not any("denylisted" in p for p in gr.lint_spec(spec))
gr.DENY_GLOBS = saved
rows.append({"arm": "selection denylist", "blocked": lint_blocked, "escaped_without_globs": lint_escaped})

# Known limits of the word match (round 2): each form calls the decoy by absolute path from inside a guarded cell.
run = gr.new_run(scratch, f"f15-limits-{stamp}", PY)
decoy, ddir = str(run.decoy_hermes), str(run.decoy_hermes.parent)
marker = run.decoy_hermes.parent / "EXECUTED"
pkg = run.dir / "decoy-pkg" / "hermes_cli"  # a decoy hermes_cli package that only touches the same marker
pkg.mkdir(parents=True)
(pkg / "__init__.py").write_text("")
(pkg / "main.py").write_text(f"open({str(marker)!r}, 'w').close()\n")
LIMIT_FORMS = [  # (form, expected: "blocked" for a control, "evades" for a documented limit, the call made in the cell)
    ("control: shell=True, plain", "blocked", f"subprocess.run({decoy + ' update'!r}, shell=True)"),
    ("control: whole word in a variable assignment (X=hermes; $X)", "blocked", f"subprocess.run('X=hermes; {ddir}/$X update', shell=True)"),
    ("control: python -m hermes_cli.main", "blocked", "subprocess.run([sys.executable, '-m', 'hermes_cli.main'])"),
    ("glob (herme?)", "evades", f"subprocess.run({ddir + '/herme? update'!r}, shell=True)"),
    ("quote concatenation (her''mes)", "evades", f"subprocess.run({ddir + '/her' + chr(39) * 2 + 'mes update'!r}, shell=True)"),
    ("backslash escape (her\\mes)", "evades", f"subprocess.run({ddir + '/her' + chr(92) + 'mes update'!r}, shell=True)"),
    ("variable expansion that builds the name (X=her; ${X}mes)", "evades", f"subprocess.run('X=her; {ddir}/${{X}}mes update', shell=True)"),
    ("python -c 'import hermes_cli.main'", "evades", "subprocess.run([sys.executable, '-c', 'import hermes_cli.main'])"),
]
limits = []
for i, (form, expected, call) in enumerate(LIMIT_FORMS):
    marker.unlink(missing_ok=True)
    code = f"import subprocess, sys\ntry:\n    {call}\nexcept PermissionError as exc:\n    print('BLOCKED', exc)\n"
    cell = gr.run_cell(run, f"limit-{i}", [PY, "-c", code], run.dir / "decoy-pkg", timeout=60)
    ran = marker.exists()
    limits.append({"form": form, "expected": expected, "decoy_ran": ran, "blocked_events": len(cell["blocked"]),
                   "cell_infra": cell["infra"], "as_expected": (not ran and cell["infra"]) if expected == "blocked" else (ran and not cell["infra"])})
controls = [r for r in limits if r["expected"] == "blocked"]
evasions = [r for r in limits if r["expected"] == "evades"]

CLASSES = {"nonloopback_connect": ("nonloopback_connect",), "name_lookup": ("name_lookup",), "live_home_open": ("live_home_open",),
           "hermes_exec_argv": ("hermes_exec",), "hermes_exec_shell_text": SHELL_FORMS, "hermes_not_on_path": ("hermes_on_path",)}
blocked = [all(intact["checks"][c] for c in checks) for checks in CLASSES.values()] + [lint_blocked]
escapes = [r["escaped"] for r in rows if r["arm"].startswith("without ")] + [lint_escaped]
runner_sha = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
receipt = {
    "schema": "xf.experiment.v1", "id": f"F15-lite/r{stamp}", "tier": "T0", "cost_usd": 0, "label": "OBSERVED",
    "question": "Does each guard class block inside a real cell, and escape when only that class is removed?",
    "inputs": {"runner_commit": runner_sha, "gate_runner_sha256": hashlib.sha256((wt / "evals/_factory/gate_runner.py").read_bytes()).hexdigest(),
               "interpreter": "hermes-agent venv python 3.11 (read-only)"},
    "command": "python f15_guard_canary.py <worktree@runner_commit> <scratch> receipts/F15-guard-canary.json",
    "results": {"blocked": f"{sum(blocked)}/{len(blocked)}", "sabotage_escapes": f"{sum(escapes)}/{len(escapes)}",
                "loopback_still_allowed": intact["checks"]["loopback_connect"], "hermes_home_isolated": intact["checks"]["home_isolated"]},
    "arms": rows,
    "known_limits": {"question": "Which lexical forms of a hermes exec does the intact word match miss? (stated limit, not a PASS criterion)",
                     "controls_blocked": f"{sum(not r['decoy_ran'] and r['cell_infra'] for r in controls)}/{len(controls)}",
                     "evasions_ran_unblocked": f"{sum(r['decoy_ran'] and not r['cell_infra'] for r in evasions)}/{len(evasions)}",
                     "forms": limits,
                     "closed_by": "a kernel sandbox (no reachable hermes, read-only root); the in-process guard cannot parse shell text"},
    "verdict": "PASS" if all(blocked) and all(escapes) and intact["passed"] else "FAIL",
    "classes": [*CLASSES, "selection_denylist"],
    "not_measured": ["writes outside the run directory (needs a read-only-root kernel sandbox)",
                     "kernel network namespace (bwrap --unshare-net) layer", "C-extension sockets that bypass Python's socket module",
                     "a shell script file that runs hermes, or a child started with a cleared environment (the guard is not on its PYTHONPATH)"],
}
out_path.write_text(json.dumps(receipt, indent=1) + "\n")
print(receipt["verdict"], receipt["results"])
print("known limits:", {k: v for k, v in receipt["known_limits"].items() if k in ("controls_blocked", "evasions_ran_unblocked")})
for r in limits:
    print(" ", r["form"], "->", "ran" if r["decoy_ran"] else "blocked", "(as expected)" if r["as_expected"] else "(UNEXPECTED)")
