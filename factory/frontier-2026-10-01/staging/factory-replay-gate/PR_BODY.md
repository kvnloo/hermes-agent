> **Not for upstream as a standalone PR.** This is an internal note on downstream tooling (route `internal`, never offered alone). It is not a pull-request body and should not be posted as one. The only upstream form this work could take is the small ride-along described in the last section, attached to a real test-hermeticity fix, and only if that fix's reviewers want it.

## What the branch adds

`evals/_factory/gate_runner.py` checks a candidate fix the way a reviewer would, for our own promotion pipeline. It runs the candidate's regression tests against base and head in fresh, isolated processes, and passes the candidate only when all four of these hold:

- **Red on base.** The candidate's test files, copied onto base, fail on every repeat and print the recorded assertion text.
- **Green on head.** They pass on every repeat. Mixed results are reported as flaky.
- **Negative control.** Each non-test hunk of the fix is reverted on its own (or a recorded sabotage patch, named relative to the spec, is applied), and at least one must turn the tests red again. Hunks that no test notices are listed.
- **No adjacent regressions.** No adjacent test file that passes on base fails on head.

Each process starts with an empty environment, a fresh `HOME`/`HERMES_HOME`, and a `PATH` of `/usr/bin:/bin` plus a `python` shim. The interpreter's own bin directory, where the `hermes` console scripts live, is not on that `PATH`. Each process also loads a small `sitecustomize` audit hook that:

- allows loopback connects only;
- refuses name lookups for other hosts;
- refuses opens under the real `~/.hermes`;
- refuses an exec whose argument list, or the command text handed to a shell (`shell=True`, `bash -c`, `os.system`), has `hermes` or `hermes_cli.main` as a word.

The hook only sees what a Python process does. It does not inspect a shell script file that runs `hermes`, or a child process started with a cleared environment (the hook is not on that child's `PYTHONPATH`). It also does not stop C-level sockets, `ctypes`, or writes outside the scratch directory.

The exec check is a word match, not a shell parser: shell text is split on metacharacters and each word is compared. So quoting (`her''mes`), globbing (`herme?`), backslash escapes and variable expansion that builds the name (`${X}mes`) all run `hermes` unblocked, as long as it is called by absolute path, since it is not on the cell `PATH`. Code that imports `hermes_cli` (`python -c 'import hermes_cli.main'`) is not refused either, and neither are the other console scripts (`hermes-agent`, `hermes-acp`) run by absolute path. The quoting, globbing, escape, expansion and import forms were measured against a decoy: each ran it with no blocked event, and the cell was not marked as tainted. (The other console scripts were not measured; the check simply does not name them.) A hard boundary needs a kernel sandbox around the runner.

`scripts/run_tests.sh` drops `PYTHONPATH`, so the hook reaches pytest through that script's existing `$HOME/.hermes/pytest_live_guard.py` plugin hook, inside the scratch home. Before any test runs, a canary process proves that each block works. The exec block is checked in four forms: argument list, `shell=True`, `bash -c`, and a bare name on `PATH`. The canary's blocks are the expected ones and are not counted. In every other process, a blocked attempt marks that process as infrastructure-tainted, and any tainted process marks the whole run as tainted, so it can never pass. That includes the process that records the installed Relay plugin pin by importing the head's `agent/relay_runtime.py`. Until the latest revision, that process's blocked attempts were dropped (see "Behaviour changes" below).

The runner writes a JSON receipt with pinned SHAs and per-gate results. Local paths in it are replaced by placeholders, and the receipt validator refuses any absolute path. It leaves verification status unset, because a self-run is not independent review.

The loopback-only connect guard and the environment reset follow Teknium's `evals/provider_fallback/probe_104260.py`; the commit carries a `Co-authored-by` line for him.

### Behaviour changes in the latest revision

- The Relay-pin process now counts like any other probe process. Its blocked attempts appear in the receipt's safety counters and its taint in the cell denominators, and a run with any tainted process is reported as infrastructure-tainted, never as passing. Before, a run whose pin process had a blocked attempt could still pass. In the unit test's own known-good scenario, the pin process had 2 blocked file opens and the run still passed.
- The pin process imports `agent.relay_runtime` only when the head checkout has `agent/relay_runtime.py`. Before, a checkout without it could pick the module up from an editable install elsewhere (here, a checkout under the real `~/.hermes`, which the guard blocked).
- Each receipt now has one more cell (the pin process) for every run that gets past the canary.

## What the calibration runs showed, and what they did not

- **Known-good.** Three already-reviewed fixes (rate-limit headers, kill attribution, `save_over_limit`), re-based on main `572e4f4fad`, passed every check: red on 3 of 3 repeats, green on 3 of 3 repeats, at least one reverted hunk turned the tests red again in each, and adjacent files were equal.
- **Known-bad.** Three candidates were refused, but none of them tests the gates hard:
  - A no-op change that was later reverted was refused **only as infrastructure-tainted**. Its test file resolves `openrouter.ai` during the run (see below), so no cell produced a trustworthy red result.
  - NousResearch/hermes-agent#123635 by Halldrix landed on main as 9 commits. Its first 8 (from `a7c2df3846`, the commit it landed on, up to `ac0b07597d`, the 8th, a write-path hardening commit) were graded on the tests the same author added in the 9th commit (`8ded06be29`, a separate read-path fix). Any red/green check refuses them, because those 8 commits never touched that path. The case does exercise "grade head on the later tests too".
  - A fork head that conflicts with main was refused by `git merge-tree`, before any check ran.
- **Tuning.** After the first pass, the runner was changed (so that head is graded on the later tests) and one known-good spec's expected failure text was rewritten. There is no held-out set.
- **One false credit.** One reverted upstream fix (NousResearch/hermes-agent#124792) passed every check. Its tests pin the behaviour it changed, not the one it broke. Red/green checks cannot see that class of problem.

## Found along the way

On main `aea969677c` (the test file, `agent/agent_init.py` and the cited fetch at `agent/model_metadata.py` line 909 are unchanged on `44a1ce9724`), `tests/agent/test_length_continuation_thinking_exhaustion.py`, run under `scripts/run_tests.sh`, starts `agent/model_metadata.py` `fetch_model_metadata` in a background thread. That thread resolves `openrouter.ai` to fetch the models list. The 10 tests still pass, so an unguarded run quietly contacts openrouter.ai. The trace is consistent with the `openrouter-prewarm` thread that `agent/agent_init.py` starts, but this is not confirmed, and it is not known which fixture leaves it enabled. It has not been reported upstream. NousResearch/hermes-agent#109924 (MaxFreedomPollard, open) changes how that prewarm thread is claimed, not test hermeticity.

## If it ever rides along upstream

The only form considered is a ride-along on a real fix, never this branch as it stands. The candidate is a hermeticity fix for the test above. If that fix's thread wants review tooling:

- drop the work-order envelope and the receipt format;
- move the code out of `evals/_factory` to a neutral path;
- offer only the guard and the per-hunk revert check, as a small helper used by that fix's own regression test.

That PR would get its own body, following `.github/PULL_REQUEST_TEMPLATE.md`. This note is not that body.

## Tests on this branch

- `scripts/run_tests.sh tests/evals/test_factory_gate_runner.py -q`: 3 of 3 tests pass on this branch (one commit on main `44a1ce9724`), on each of 3 runs. Without `evals/_factory`, the file fails at import (`No module named 'evals._factory'`).
- Run against the previous runner revision (`2a4253258b`), 1 of the 3 tests fails: the new Relay-pin test, because the pin process's blocked name lookup was dropped and the run passed (`AssertionError: assert ('KEEP' == 'INFRA'`).
- Run against the first reviewed runner revision (`be292fd2ba`), 3 of 3 tests fail: a receipt carrying an absolute path is accepted, the pin process's blocked lookup is dropped, and a `shell=True` exec of the decoy `hermes` runs it (`AssertionError: the decoy hermes ran`).
- Negative controls: 12 of 12 turn the test file red. Each mutation is applied alone:
  - the guard logs connects without raising;
  - the red check is hard-wired to pass;
  - hunks are applied forward instead of reverted;
  - head is not given the later tests;
  - shell-text splitting is removed;
  - the interpreter's bin directory is put back on `PATH`;
  - the recorded sabotage patch is read relative to the working directory;
  - the absolute-path rule is removed from the validator;
  - the Relay-pin path scrub is removed;
  - the Relay-pin process is left out of the receipt's cells;
  - the verdict ignores tainted processes outside the four checks;
  - the pin process imports `agent.relay_runtime` even when the checkout lacks it. This one is red only on an interpreter whose editable hermes-agent install points into the real `~/.hermes`, as the one used here does. Elsewhere no test catches it.
- Adjacent: `scripts/run_tests.sh tests/evals/ evals/postmortem/tests/test_postmortem_harness.py -q`: 9 of 9 tests pass, in 4 files.
- POSIX-only (`pwd`, `nice`, process groups); the test skips on Windows. Not tried on macOS. Linux (CachyOS), Python 3.11.14.

AI assistance: the runner, the tests, the runs above and this note were written with Claude Code (Opus 5.5).
