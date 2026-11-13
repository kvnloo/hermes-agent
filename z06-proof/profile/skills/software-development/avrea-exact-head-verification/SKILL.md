---
name: avrea-exact-head-verification
description: "Use when running Avrea exact-SHA tests or CI speed studies."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [avrea, ci, fleet-runner, exact-head, verification, hermes-tests]
    related_skills: [token-thrifty-agent-routing, oss-factory-kitchen, upstream-contribution]
---

# Exact-head verification on Avrea

## When to Use
Use for heavy test runs on public, committed code: full suites, exact-head probes against upstream PR SHAs, and falsifier batteries for a study PR. Private or uncommitted work goes to `fleet-build --node mbp`. Never run it on groot.

## Procedure
1. **Pin everything.** Use a full 40-hex SHA that exists on the public repo (`gh api repos/O/R/commits/<sha>`). Fetch upstream PR heads by SHA (`git fetch --no-tags https://github.com/U/R.git <sha>`), not via `refs/pull/N/head`. That ref moves when the author force-pushes, and a moved ref makes `git worktree add <sha>` abort the whole script under `set -e`.
2. **Use the shared lane.** Don't add a per-repo workflow. Dispatch through `kvnloo/fleet-runner` `verify.yml`, which needs no app install or Actions setup on the target. Workflows committed to a fork can sit unrun because fork Actions are dormant. The lane checks out `target/` with depth 1, so fetch other heads yourself.
   ```bash
   S=$(dirname $(readlink -f $(which fleet-build)))   # release scripts dir holding fleet-avrea
   $S/fleet-avrea --repo O/R --sha <40hex> --runner avrea-ubuntu-latest-8-vcpu --index official \
     --matrix m.json --parallel 3 --timeout 2400 --fetch 'out/**' --out <ops-dir>/<name>
   ```
   - `m.json` is a JSON list of shell strings, one job each (at most 32). Shard Hermes with `HERMES_TEST_SLICE=i/N`; 3×8 vCPU finished the full suite in about 8.5 minutes per slice.
   - `--fetch` globs are relative to `target/`, so write outputs under `target/out/`. Downloads land in `<out>/artifacts/fleet-files-<i>/`, and receipts in `fleet-result-<i>/receipt.json` (sha, runner, exit code, duration, run_id).
   - Run it in a background terminal with notify, because a dispatch blocks until the run completes.
3. **Budget gate (owner rule): don't stop to check free minutes.** `fleet-avrea-budget` refuses dispatches when its billing snapshot is older than 24 h. When that happens, dispatch directly:
   ```bash
   # request.json: {repository, sha, command: ":", runner, fetch, matrix: "<json list as string>",
   #                parallel, timeout_minutes, request_id: <uuid hex>, package_index: "official"}
   gh workflow run verify.yml -R kvnloo/fleet-runner --ref main --json < request.json
   # run displayTitle == "fleet-<request_id>"; then gh run download <id> -R kvnloo/fleet-runner
   ```
   Note in the run dir that the gate was bypassed. Size runners reasonably (4–8 vCPU); 32 vCPU costs 16× the reference rate.
   - `fleet-avrea-budget check` is not read-only. An allowed check writes a durable reservation. If you only meant to probe, run `fleet-avrea-budget release --reservation-id <id> --undispatched`.
4. **Read results per testcase.** Use JUnit records or `-rA` lines, not summary counters or exit codes. Expected-RED probes must report each assertion's failure message. Add up slice totals in code.
5. **Record and publish.** Write `REPORT.md` in the run dir with run URLs, SHAs, per-slice counts, failure classes and what was NOT_RUN. Post receipts only downstream: a comment on your own study PR, plus link_pull_request. Don't post anything upstream.

## CI speed / runner-sizing experiments
Use this when the task is "make upstream CI faster or cheaper", for example translating a CI-speed article, comparing runner vendors, or changing shard and worker shapes. Do these steps in order. Recipe and metric rules: `references/ci-speed-experiments.md`.
1. **Map the prior art before proposing anything.** Search upstream issues and PRs (open and closed) for CI speed, runners, shards, slices, caches, flakes, merge queue and timing reports. Read the open tracker issue and the closing comments on superseded PRs: maintainers record rejected options and team decisions there. Then read the current workflow files on main (`runs-on`, matrix, worker count, cache keys). Many article steps will already be done or deliberately rejected; mark each one done / rejected / open.
2. **Build the repo dependency graph before triage.** List the upstream repo and who owns each CI area, your fork and its stale CI PRs, the dispatch lane (fleet-runner, .files), the local ops data dir, factory trackers, and external vendors. Search `kvnloo/*` issues and PRs plus ctx history for the earlier experiment record. If none exists, say so plainly; don't claim one.
3. **Join the existing thread instead of opening a new one.** Data goes as a comment on the open upstream tracker or the narrow existing issue. Never open an unrequested "switch vendor" issue. When upstream already pays for a fast vendor at the same list price per vCPU, there is no vendor pitch.
4. **Re-analyze old data against its own controls before reusing a claim.** A control that keeps upstream's partition but changes another variable often shows the headline cause is wrong.
5. **Preregister, then run.** Write the hypothesis, the primary metric, the shapes, n≥5 interleaved repeats, and the post/no-post threshold to `PLAN-*.md` in the ops dir before dispatching. Run the API-only run audit first, because it costs nothing and can end the study.
6. **For autoresearch-style loops**, hill-climb only per-file test CPU seconds under the guard set in the reference, never runner shape. State the engine, model and host, and ask before using billed delegation.

## Hermes test environment
- `scripts/run_tests.sh` bootstraps itself through `run-in-hermes-env`, but that environment doesn't put `uv` on PATH or install the extras. Expect around 50 false failures ("requires real uv", missing `fal_client`, the real-HERMES_HOME guard).
- Instead, mirror `.github/actions/setup-pm` in one shell. Run `scripts/ci/setup_toolchain.py` `prepare` → `install` → `dependencies --test-environment`, with `GITHUB_ENV`/`GITHUB_PATH`/`GITHUB_OUTPUT` pointed at temp files, loading them after each phase. Use `--home $RUNNER_TEMP/setup-pm` and CI's extras.
- The working script is `scripts/ci-setup.sh` in this skill. Base64 it into the matrix command, `source` it, then run `scripts/run_tests.sh` or `$HERMES_PYTHON -m pytest`.
- Before reusing the saved script on a newer head, reconcile its extras list with that head's `.github/workflows/tests.yml`. CI adds optional extras that `all` excludes, and a stale list causes collection errors.
- Pass extra pytest plugins as `-p<name>` with no space. Hermes CLI imports pre-parse a separate `-p` as a profile flag and abort collection across the suite.
- `studies/` is not collected by the canonical suite. Run study probes explicitly.

## Pitfalls
- **Reconcile concurrent experiment lanes before dispatching.** Inspect recent fleet runs by candidate SHA/title and the other harness's active assignment. Do not duplicate a peer's full suite; scope independent falsifiers separately and publish the exact ownership/run IDs downstream.
- **Keep failed setup separate from test verdicts.** A stale `uv.lock` rejected by PM is an exact-candidate environment failure, not a failing collected test. If a separately pinned control provisions a compatible interpreter for narrow diagnostics, preserve candidate source/lock bytes, use the explicit `HERMES_PYTHON` seam, and label the results non-canonical compatibility diagnostics—not full-suite or lockfile certification.
- **Preserve test-path ownership.** A candidate may already contain the shared runner's injection filename and JSON fixture. Stage unchanged independent probes and their relative fixtures together in a new test subdirectory; never overwrite author tests or count a collision as candidate failure.
- **Challenge fixture-specific repairs with a held-out identifier.** If production denial code recognizes the synthetic fixture prefix, preserve the original no-retain condition and origin but rename only that identifier in a separate diagnostic. Keep the published battery unchanged and distinguish boundary challenges from end-to-end model consent.
- **Check that encoding fixtures write bytes, not escapes.** A fixture that writes the literal text `\xef\xbb\xbf` gives a false RED, and the failure message shows escaped backslashes (`'\\xef…'`). Look for that before reporting any encoding finding.
- **Check what the `-k` selectors deselect.** Runners with per-head selectors silently skip newly added cases ("19 deselected"). Run the whole probe file without `-k` after adding cases.
- **An expected-RED diagnostic exits nonzero by design.** Report each probe's verdict, not job success. List skipped cases ("no read on this head") separately.
- **A failure on a single timing assertion outside the area under study is a flake.** Name it with its margin and leave it unclaimed rather than counting it against the change.
- **Direct dispatch JSON must be all strings.** `gh workflow run verify.yml --json` rejects numbers (`parallel`, `timeout_minutes`). At the start of a UTC month, `fleet-avrea-budget` refuses with "snapshot is not for the current UTC month": dispatch directly, per the owner rule.
- **`--fetch 'out/**'` drops the `out/` prefix.** Files land directly in `artifacts/fleet-files-<i>/`. Analyzers should find run dirs by a marker file, not by an `out` directory name.
- **Don't `git push` from a blobless (`--filter=blob:none`) clone to the fork.** It hangs on lazy blob fetches. Create the base branch on the fork through the API (`git/refs` with the upstream SHA, which the fork network already has). Then recreate each commit with the git-data API and check that the tree SHA matches the local one. The tool is `hermes-ci-sizing/autoresearch/harness/gh_publish.py` in the ops store.
- **For whole-job timings, use a fresh VM per run.** Back-to-back full runs in one checkout leaked state (the 3rd and 4th runs failed identically on base and candidate). Interleave several variants on one VM only for single-file timings.
- **Before trusting a candidate commit built with sabotage branches, grep it for every sabotage string.** An amend in a shell without a git identity once folded all three sabotage edits into the candidate.
- **When a reported finding turns out to be an artifact, retract it publicly and promptly.** Post a correction comment that names the bad rows and the cause, and fix REPORT.md in place.
