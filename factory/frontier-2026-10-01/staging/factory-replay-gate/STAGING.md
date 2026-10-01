+++
xf_staging = 1
id = "factory-replay-gate"
version = 1                # the logical branch was moved to each amended commit on instruction; every earlier commit is kept under an archive ref and a patch (see [archive]), so no version is lost (FACTORY R2/S7)
title = "$0 promotion-gate runner: base/head probes with an egress guard, asserted red-on-base, negative control and receipts"
promotion_form = "eval-contribution"   # unchanged in rounds 1, 2 and 3: internal tooling, never a standalone upstream PR (D5/P11); PR_BODY.md is an internal note, not a PR body
branch = "staging/factory-replay-gate"   # logical id and local ref in the scratch mirror h.git
branch_physical = "staged/factory-replay-gate on kvnloo/hermes-agent when pushed (OD-0 resolved by the staged/ rename: the fork's legacy refs/heads/staging blocks refs/heads/staging/<id>); not pushed yet"
branch_sha = "732919ad7dcd2173ba000af989b084583c231a59"
status = "STAGED"          # round-2 re-verify findings (2) fixed in round 3; P5 PENDING (F14 not run); re-verify pending. Internal route: best class reachable is Wave-0 "factory-ready"; never PROMOTION_READY alone (D5)
route = "internal"
feature = "promotion-gates-factory + offline-replay-ab-substrate (catalog)"
invariant = "A candidate is KEEP only if, in isolated guarded processes, its tests fail on base with the recorded markers, pass on head every rep, fail again when a fix hunk is reverted, and no adjacent file regresses."

[base]
repo = "NousResearch/hermes-agent"
sha = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
fetched_at = "2026-10-01T16:09Z (git ls-remote: refs/heads/main = 44a1ce9724; re-checked 16:22Z, unchanged)"
previous = [
  { sha = "e8c97320ac", note = "round-2 parent; main is 23 commits later at 44a1ce9724, none touching evals/, tests/evals/, scripts/ or agent/relay_runtime.py; the slice was re-applied (cherry-pick, clean) onto 44a1ce9724 in round 3" },
  { sha = "aea969677c", note = "round-1 parent; main is 6 commits later at e8c97320ac, none touching evals/, tests/evals/ or scripts/run_tests*; the slice was re-applied (cherry-pick, clean) onto e8c97320ac in round 2" },
  { sha = "572e4f4fad", note = "round-0 parent" },
]

[upstream]
rfc = ["NousResearch/hermes-agent#110671 (kvnloo, open: Harness Evolver Phase 0, pathology archive + credit-gate calibration)"]
fork_threads = ["kvnloo/hermes-agent#322 (factory thread: common receipt + failure-injection runner)", "kvnloo/hermes-agent#318", "kvnloo/hermes-agent#323", "kvnloo/evolution-lab#20"]
related_open = [
  { pr = 127952, author = "dskwe", note = "fixes NousResearch/hermes-agent#127898 (aniruddhaadak80): postmortem cache_prefix_wire passes vacuously and reads the real ~/.hermes log; touches evals/postmortem/run.py:41 and the probe, not run.py:47; no overlap with this branch (re-checked round 3 at 16:22Z: still open, same 2 files)" },
  { pr = 109924, author = "MaxFreedomPollard", note = "changes how agent/agent_init.py claims the openrouter-prewarm thread; adjacent to the FINDING's suspected start site, not a hermeticity fix (re-checked round 3: still open)" },
]
competitors = []
demand = { score = 5, source = "impact lens (offline-replay-ab-substrate); promotion-gates-factory 5" }
maintainer_signal = "none; maintainer-fit lens scores downstream-only items 1 (not a value judgement); test-infra-only waves went 4/4 NOT_PLANNED"

[[members]]
ref = "refs/fork/feat/evolver-phase0-gate-calibration"
sha = "20eb166106c1648420629022a3eb84ba20081457"
role = "donor: validity/activation/credit gate semantics and calibration design (2 commits, 11 files, +1,375); activation (red-on-base, green-on-patched) re-implemented, not vendored"
rebase = "merge-tree clean vs main 44a1ce9724 (12,296 behind, 2 ahead; re-measured round 3)"

[[members]]
ref = "refs/fork/lab/evals/hermes-stack-receipts-v0"
sha = "22b0c745d59c34dd9ee49d98d4bb7ef9b4abed60"
role = "donor: receipt rules (verified_success null stays unknown; execution never upgrades it; exact revisions; private raw stays local); its z0eval.hermes_stack_experiment.v0 schema is a per-cell arm schema and is not the gate receipt shape (2 files, +91)"
rebase = "merge-tree clean vs main 44a1ce9724 (460 behind, 2 ahead; re-measured round 3)"

[[donors]]
sha = "78e0d296d6"
author = "Teknium <127238744+teknium1@users.noreply.github.com>"
role = "loopback-only connect guard + environment reset pattern (evals/provider_fallback/probe_104260.py)"
trailer = "Co-authored-by: Teknium <127238744+teknium1@users.noreply.github.com>"

[ownership]
searched_at = "2026-10-01T09:30Z (round-1 spot re-check 11:25Z; round-2 re-check 11:55Z; round-3 re-check of NousResearch/hermes-agent#127952, NousResearch/hermes-agent#109924, NousResearch/hermes-agent#110671 and NousResearch/hermes-agent#127898 at 16:22Z: all still open)"
queries = ["red on base", "evals runner base head negative control", "postmortem run.py HERMES_HOME setdefault", "evals harness egress guard loopback", "promotion gate red green sabotage", "evolver credit gate calibration", "fetch_model_metadata test network", "test_length_continuation_thinking_exhaustion"]
open_external = []
related = [127898, 127952, 109924]
verdict = "ours (downstream tooling; no upstream owner of a gate runner)"
excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[ride_with]                # D5/P11: never offered alone. The only candidate real fix found so far:
real_fix = { id = "unit-test metadata-fetch hermeticity (not yet written or filed)", evidence = "receipts/FINDING-unit-test-metadata-fetch.json", offer = "only the guard + per-hunk revert check, at a neutral path, as a helper for that fix's own regression test; drop the work-order envelope and receipt format" }

[evidence]
receipts = [   # pass 5 (round 3, runner 732919ad7d); the per-spec receipts each experiment cites are pinned inside it by sha256; FINDING is unchanged since round 1; pass 4 is kept in receipts/pass4/
  { id = "F11", path = "receipts/F11-runner-calibration.json", sha256 = "c0b6bc6834441e9b21c02ce21eee3e1755e6b82a8e5e8b15ac521c2d0fcace55" },
  { id = "E30-lite", path = "receipts/E30-gate-calibration-lite.json", sha256 = "2d0052e0c45e872afc1abe9c3081ec745b24129f72a175094ba2e43cb199d5f4" },
  { id = "E48", path = "receipts/E48-validator-faults.json", sha256 = "5bc136f0cf3f3dc2f0454469673e6877c1aa3f79298ac16dfb6f232851b0d61b" },
  { id = "F15-lite", path = "receipts/F15-guard-canary.json", sha256 = "006d4dcf80a0f38af0897b88abb2ab107c0faff0ec124adabdce60699dc0eadc" },
  { id = "C1", path = "receipts/C1-envelope-only.json", sha256 = "29e71ff9e52cc73dbd6aecc196edf01701d5530d7299099df6ce89ab283aeeb4" },
  { id = "FINDING", path = "receipts/FINDING-unit-test-metadata-fetch.json", sha256 = "b1dacfcb46824632779e42ef89c3ca5fd0c06bb77f85697aea01d8609665aabf" },
]
red = { test = "tests/evals/test_factory_gate_runner.py", main = "44a1ce9724", marker = "ModuleNotFoundError: No module named 'evals._factory'" }
red_fix = [
  { runner = "2a4253258b (round-2 head; archive ref staging/factory-replay-gate-r2)", markers = ["AssertionError: assert ('KEEP' == 'INFRA'"], note = "round 3: test file of 732919ad7d on 2a4253258b's runner; 2 of 3 tests pass, 1 of 3 fails: the new test, at test line 124 (the pin cell's blocked lookup was dropped and the run came out KEEP)" },
  { runner = "be292fd2ba (round-0 head; archive ref staging/factory-replay-gate-r0)", markers = ["AssertionError: assert [] == ['receipt con...e local path']", "AssertionError: assert ('KEEP' == 'INFRA'", "AssertionError: the decoy hermes ran"], note = "round 3 re-run: 3 of 3 tests fail, at test lines 80, 124 and 152; pytest truncates the first and adds \"Right contains one more item: 'receipt contains an absolute local path'\"" },
]
green = { result = "3 of 3 tests pass", runs = "3/3 at 732919ad7d" }
negative_control = { mutations = 12, result = "12 of 12 RED (round 3 at 732919ad7d)", detail = "guard stops raising on connect; red column hard-wired PASS; sabotage applied forward; head not given the later tests; shell-text split removed; interpreter bin dir back on PATH; sabotage patch read from cwd; absolute-path rule removed; Relay pin scrub removed; Relay pin cell not appended to the run's cells; verdict ignores INFRA cells; pin imports agent.relay_runtime when the arm lacks it (RED only with an editable install under the live home, as here)" }
adjacent = { files = ["tests/evals/", "evals/postmortem/tests/test_postmortem_harness.py"], result = "9 of 9 tests pass, 0 fail (4 files)" }
guards = { F14 = "NOT_RUN" }   # FACTORY 11.1: P5 needs F14 guards equal; F14 is queued, not run, so P5 is PENDING. No F14 harness imports evals/_factory (static grep on 44a1ce9724), which is not an observation of equal guards
not_tested = ["F14 standing regression set (P5 guards)", "kernel sandbox layer (bwrap)", "writes outside the run directory", "a shell script file that runs hermes, or a child with a cleared env (no guard on its PYTHONPATH)", "a disposable pm.build_env venv", "paid or local-model arms", "passes 1-4 receipts were made by runners that dropped the Relay pin cell's blocked attempts (0 such events in the kept pass-2/3 run directories; pass-4 run directories not kept)"]
known_limits = "OBSERVED, not just untested (F15-lite known_limits): the exec check is a word match, not a shell parser. Quoting, globbing, backslash escapes and variable expansion that builds the name ran the decoy hermes by absolute path with 0 blocked events and no INFRA, and so did python -c 'import hermes_cli.main'. Only a kernel sandbox closes this."

[gates]
P1 = "N_A"        # no product defect claimed; the runner's need is factory-side
P2 = "PASS"       # no upstream owner; NousResearch/hermes-agent#127952 is adjacent, not overlapping
P3 = "RECORDED"   # 3 files, +974; one invariant; no env vars, no hooks; an 820-line file (under the ~2k bar)
P4 = "N_A"
P5 = "PENDING"    # round 3: FACTORY 11.1 P5 needs "F14 guards equal" and F14 was not run. Met: RED (module absent) on 44a1ce9724, RED of the new assertion on 2a4253258b (3 of 3 tests on be292fd2ba), GREEN 3/3, 12 of 12 negative controls RED, adjacent 9 of 9 pass, flaky = false
P6 = "N_A"        # no value claim
P7 = "PASS"       # one commit whose parent is main 44a1ce9724 (current at the last ls-remote, see [merge_check]), author + subject; never pushed
P8 = "PENDING"    # receipts sha256-pinned here; not frozen to z0evals
P9 = "N_A"        # no upstream text: PR_BODY.md is an internal note marked not-for-upstream (round 1); a ride-along body would be written with the real fix
P10 = "PENDING"   # round 0: 8 findings, fixed in round 1; round-1 re-verify: 5, fixed in round 2; round-2 re-verify: 2, fixed in round 3; re-verify on 732919ad7d pending
P11 = "FAIL"      # eval-only content; must ride a real fix (see [ride_with])
P12 = "N_A"       # never takes a board row alone

[verification]
verifier = "phase-3 blind verifier (round 0 on be292fd2ba; round-1 re-verify on c430541d16; round-2 re-verify on 2a4253258b)"
provenance = "independent"
exact_head = "732919ad7dcd2173ba000af989b084583c231a59"
inputs = "raw diff + repo + this manifest's acceptance gates only"
verdict = ""      # round 0: not accepted (8 findings); round-1 re-verify: not accepted (5 findings: manifest/script privacy, undisclosed shell-text limit, NousResearch/hermes-agent#123635 commit count, red_fix marker, provenance refs); round-2 re-verify: not accepted (2 findings: Relay pin cell's blocked attempts dropped from the receipt, P5 PASS without F14); round-3 re-verify pending
qa_class = ""

[merge_check]
main_sha = "44a1ce9724"
checked_at = "2026-10-01T16:37Z"
clean = true
note = "the commit's parent is main 44a1ce9724, which was still refs/heads/main by git ls-remote at 16:09Z, 16:22Z and 16:37Z, so the slice is one commit on current main and applies trivially. Round-3 proofs and pass 5 ran on it. 23 commits separate the round-2 parent e8c97320ac from 44a1ce9724; none touch evals/, tests/evals/, scripts/ or agent/relay_runtime.py"
recheck = "git merge-tree --write-tree main staging/factory-replay-gate"

[archive]                  # round 2 (provenance), extended in round 3: earlier commits are never deleted. Local refs in the scratch mirror h.git, never pushed; patches next to this file
refs = [
  { ref = "staging/factory-replay-gate-p1", sha = "b01d6dcb8b7ebce29ecda00a9f639adfa851dec3", role = "pass-1 runner (receipts/pass1/)", patch = "archive/factory-replay-gate-p1-b01d6dcb8b.patch", sha256 = "9e7b0dbc50725367d7833682d7b2870d70fa945d1409295a1e36168e6103b83e" },
  { ref = "staging/factory-replay-gate-r0", sha = "be292fd2ba4bed799c3a02ebf579f39389d136c6", role = "round-0 head; pass-2 runner (receipts/pass2/); the red_fix target", patch = "archive/factory-replay-gate-r0-be292fd2ba.patch", sha256 = "0a42f2950f9996059ca59e281fb9cc0b88b3dcb77b0ea39a6a503c62451f8795" },
  { ref = "staging/factory-replay-gate-r1", sha = "c430541d16e639ac6379f2897e888b2890a6ac6c", role = "round-1 head; pass-3 runner (receipts/pass3/)", patch = "archive/factory-replay-gate-r1-c430541d16.patch", sha256 = "954264a2c979f653b265140733fcab7e968ce8806adc8c20e22d60a2fbb23fae" },
  { ref = "staging/factory-replay-gate-r2", sha = "2a4253258bb18b7601c137b37d9d7530276fc2c8", role = "round-2 head; pass-4 runner (receipts/pass4/); the round-3 red_fix target", patch = "archive/factory-replay-gate-r2-2a4253258b.patch", sha256 = "8f2c6b04cab38728fd490f4cc20ea459fca697234f5c3889cfd7f5c7381c0f8f" },
]

[push]
no_follow_tags = true
workflow_push_matches = 0
remote_ref = "refs/heads/staged/factory-replay-gate"
pushed_at = ""

[body]
path = "PR_BODY.md"
kind = "internal-note"   # round 1: was "pr-body"; route internal means no upstream PR body exists (see its ride-along section)
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }  # self-assessed; only matters if a ride-along body is ever written
jargon_lint = "N_A (internal note); the path name evals/_factory must be renamed for any upstream form"
privacy_scan = "PASS (round 3 re-run at 16:37Z; scope: this STAGING.md, PR_BODY.md, receipts/ incl. pass1-4, specs/, experiments/, the patches incl. archive/, 95 files; private/ is local only and never published). Absolute local paths, private addresses, emails other than the noreply author/co-author trailers, and tokens were grepped for; local locations are now placeholders (<xf-root>, <gpu-lock>, <local-router-url>, <live-install>, <scratch>, <venv-python>, <runner-wt>, <repo.git>, <test-home>). Deliberate exceptions, all synthetic: the E48 fixture strings '/home/someone/.hermes/state.db' and '/srv/scratch/.xf-runs/x/arms/head/agent/relay_runtime.py' (fault inputs the validator must refuse), and the unit test's '/srv/run/arms/head' and '/opt/relay/system.toml' (inputs that the validator must refuse and the Relay pin scrub must rewrite)"

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# factory-replay-gate: $0 promotion-gate runner

**Promotion form:** eval-contribution, routed `internal`. It is never an upstream PR on its own (D5, P11). The fork commit is the artifact. An upstream version would only ride along with a real fix (see `[ride_with]`). Rounds 1, 2 and 3 kept this form: no finding showed an external owner or a reason to HOLD. `PR_BODY.md` is now marked as an internal note that is not for upstream, because round 0 had drafted it as a standalone upstream PR, which contradicted this route.

**Upstream RFC:** NousResearch/hermes-agent#110671 (ours, open). **Fork threads:** kvnloo/hermes-agent#322 (factory thread), kvnloo/hermes-agent#318, kvnloo/hermes-agent#323, kvnloo/evolution-lab#20. All five were re-checked open at 16:22Z (round 3).

**Branch on the fork:** `staged/factory-replay-gate` when pushed. OD-0 is resolved for this item by that rename, because the fork's legacy `refs/heads/staging` blocks any `staging/<id>` ref. Locally, in the scratch mirror, the branch is still `staging/factory-replay-gate`. Earlier commits are kept under local archive refs `staging/factory-replay-gate-p1`, `-r0`, `-r1` and `-r2` (see `[archive]`); they are not for pushing.

## Round 3: re-verifier findings (round 2, on `2a4253258b`) and what changed

| # | Finding | Fix in round 3 |
|---|---|---|
| 1 | Guard signal gap: `run_gate` called `run_cell()` directly for the Relay pin cell, so that cell's blocked attempts and INFRA flag never reached the verdict, the denominators or the safety counters. The pin cell imports head code. On the unit test's own known-good toy scenario, its guard log had 2 blocked `open` events on live-checkout files (`agent/__init__.py` and its `.pyc`, reached through the venv's editable hermes-agent install), yet the receipt was KEEP, valid, with `home_blocked = 0`. `PR_BODY.md` ("Any blocked attempt marks the run as infrastructure-tainted"), the module docstring and the commit message overstated this, and the validator's "KEEP cannot include blocked attempts" rule was bypassed. | **Code + test + text.** Reproduced first on the round-2 runner (2 blocked opens dropped; KEEP; `validate_receipt() == []`; `home_blocked = 0`). Fixed in 5 code lines: the pin cell is appended to the run's cells, so its blocked attempts count in `safety.*_blocked` and its INFRA flag in `denominators`; `_receipt()` makes the verdict INFRA when any cell is INFRA (before, only an INFRA gate did), with `refusal_reasons` naming the cells; and the pin probe imports `agent.relay_runtime` only when the head arm has `agent/relay_runtime.py`, so it never resolves a runtime that an editable install finds outside the arm. New test `test_a_blocked_attempt_in_the_relay_pin_cell_taints_the_run`: a toy head whose `resolve_plugin_sources()` swallows a guard-blocked name lookup must give INFRA with `refusal_reasons == ['infra cells: relay-pin']`, `egress_blocked == 1`, `denominators.infra == 1`, scrubbed config paths and a valid receipt. It is RED on the round-2 runner (`AssertionError: assert ('KEEP' == 'INFRA'`, test line 124). The docstring, commit message and `PR_BODY.md` now say that any INFRA cell, the Relay pin cell included and the canary's expected blocks aside, makes the run INFRA. Pass-2/3 run directories show 0 blocked events in every real-arm Relay pin cell (pass-4 run directories were not kept); pass 5 on the fixed runner is below. |
| 2 | Gate overstated: P5 was PASS, but FACTORY §11.1 P5 includes "F14 guards equal", F14 is in Queued experiments (not run), and `[evidence]` had no `guards` field. | **Text.** P5 is now PENDING in `[gates]` and the gate checklist, and `[evidence].guards = { F14 = "NOT_RUN" }`. RED, GREEN 3/3, 12 negative controls and ADJACENT are met; F14 is not. No F14 harness imports `evals/_factory` (grep over the F14 harness paths on `44a1ce9724`), but that is a static argument, not the "guards equal" observation P5 asks for, so it is not recorded as N_A. |

Because the runner changed, the commit was re-applied onto main `44a1ce9724` (current at 16:09Z by `git ls-remote`, still current at 16:22Z) and amended. It is now `732919ad7d`, the only commit on top of that main. RED on main, RED on the round-2 runner `2a4253258b` and on the round-0 runner `be292fd2ba`, GREEN 3/3, 12/12 negative controls, adjacent and ruff were re-run on it. All 8 gate specs, E48, F15-lite and C1 were re-run against it (pass 5): same gates and verdicts as pass 4, one more cell per run that reaches the Relay pin, and 0 blocked attempts in all 7 of those pin cells.

## Round 2: re-verifier findings (round 1, on `c430541d16`) and what changed

| # | Finding | Fix in round 2 |
|---|---|---|
| 1 | Privacy: the Queued experiments section had absolute local paths and a private tailnet endpoint, and the cited `specs/run_all.sh`, `experiments/c1_envelope_only.py` and `experiments/f15_guard_canary.py` hard-coded the session scratch path, the mirror path and the live interpreter. `privacy_scan` covered only the receipts. | **Text + scripts.** The queued commands now use placeholders (`<xf-root>`, `<gpu-lock>`, `<local-router-url>`, `<live-install>`, `<venv-python>`, `<runner-wt>`, `<repo.git>`, `<test-home>`, `<scratch>`). `run_all.sh` takes every location from the environment (`W`, `XF_REPO`, `XF_PYTHON`, `HOME`, optional `XF_SCRATCH`) and refuses to run with the real home. The two experiment scripts read `XF_PYTHON` (default: the running interpreter). The pass-3 `run_all.sh` is kept in `private/` only. `[body].privacy_scan` now names its scope: this file, `PR_BODY.md`, receipts, specs, experiments and patches. |
| 2 | The exec guard's limit was not disclosed: the shell-text check splits words on metacharacters and does not parse the shell, so a glob, quote concatenation or a backslash escape ran the decoy `hermes` with 0 blocked events and no INFRA. | **Code (docstring and commit message only) + text + evidence.** The module docstring and the commit message now say the check is a word match, not a shell parser, and name what evades it: quoting, globbing, backslash escapes, variable expansion that builds the name, code importing `hermes_cli`, and the other console scripts run by absolute path. The guard code is byte-identical to round 1. F15-lite gained a `known_limits` arm that measures this against the intact guard: 5/5 evasion forms ran the decoy unblocked, and 3/3 controls blocked (plain `shell=True`, the whole word inside a variable assignment, `python -m hermes_cli.main`). The "fail-closed" wording in NOT_TESTED, the Exec guard gate row and `PR_BODY.md` were corrected. |
| 3 | Number wrong: NousResearch/hermes-agent#123635 has 9 commits, not 8, so `ac0b07597d` is the 8th of 9. The F11-N2 base is `a7c2df3846`, the commit the PR landed on, not `ac0b07597d^`, so the graded change is the PR's first 8 commits. | **Text.** Re-measured (`gh pr view`: 9 commits; `git log a7c2df3846..8ded06be29`: 9 commits by Halldrix, `dc8e544986` first, `ac0b07597d` 8th, `8ded06be29` 9th). The round-1 table row below, the F11-N2 evidence row and `PR_BODY.md` now say so. |
| 4 | `[evidence].red_fix.markers[0]` quoted a parenthetical gloss as if it were observed output. | **Text.** Re-ran the test file against `be292fd2ba`'s runner. The markers are now the verbatim pytest `E` lines: `AssertionError: the decoy hermes ran` (test line 126) and `AssertionError: assert [] == ['receipt con...e local path']` (test line 80, truncated by pytest). |
| 5 | Provenance at risk: the force-moved branch left `be292fd2ba` (round-0 runner, red_fix target, pass-2 receipts) and `b01d6dcb8b` (pass-1 runner) unreferenced, so a gc could drop them. | **Refs + patches.** Local archive refs `staging/factory-replay-gate-p1` (`b01d6dcb8b`), `-r0` (`be292fd2ba`) and `-r1` (`c430541d16`, round-1 head) now hold every earlier commit. Their `format-patch` files are in `archive/` with sha256 in `[archive]` (the r0 patch hash matches the round-0 verifier's `0a42f295…`). Pass-3 receipts are kept in `receipts/pass3/`. |

Because the docstring and commit message changed, the commit was re-applied onto main `e8c97320ac` (current at 11:50Z) and amended. It is now `2a4253258b`, the only commit on top of that main; by 12:13Z main was 2 unrelated commits further on (`040b6df2c4`) and merge-tree is still clean. RED, RED-on-`be292fd2ba`, GREEN 3/3, 9/9 negative controls, adjacent and ruff were re-run on it. All 8 gate specs, E48, F15-lite and C1 were re-run against it (pass 4).

## Round 1: verifier findings and what changed

| # | Finding (round 0, on `be292fd2ba`) | Fix in round 1 |
|---|---|---|
| 1 | Exec guard gap: a shell-string exec (`shell=True`, `bash -c`, `shell=True` bare name via PATH) ran the decoy `hermes` unblocked, and the cell PATH started with the interpreter's bin dir, where the real `hermes` console script lives. | **Code.** The guard now splits everything a shell is handed into words (after the first `sh`/`bash`/… in argv, and `os.system`'s command) before matching `hermes` / `hermes_cli.main`. The cell PATH is now a `python`/`python3` shim plus `/usr/bin:/bin`. The canary gained 4 checks (`shell=True`, `bash -c`, PATH form, `hermes` not on PATH). The unit test gained an independent `shell=True` probe. F15-lite now has 7 classes. The remaining limits are written into the docstring, commit message, this manifest and PR_BODY.md. *(Round 2: that list missed the word-match limits; see round 2 row 2.)* |
| 2 | Receipts carried absolute paths (Relay pin error), and the validator matched only `/home/` and `/Users/`. | **Code.** The Relay pin probe replaces known roots with placeholders, and any other absolute path keeps only its basename. `validate_receipt()` now refuses any absolute POSIX path. The two leaking pass-2 receipts were moved to `private/pass2-receipts/` (local only). All 8 gate receipts were re-run (pass 3), and all are valid under the new rule. |
| 3 | NousResearch/hermes-agent#123545 / "first cut" mislabelled. | **Text.** NousResearch/hermes-agent#123545 is an issue (Lifeweavers). The PR is NousResearch/hermes-agent#123635 (Halldrix, closed; its commits landed on main). `ac0b07597d` is the 8th of its 9 commits on main *(corrected in round 2; round 1 said "next-to-last of its 8")*, a write-path "harden … from a parallel review" commit. `8ded06be29` is the same author's next commit (the 9th), a separate read-path fix, and the tests are the author's own. The spec's base `a7c2df3846` is the commit the PR landed on, so the graded change is the PR's first 8 commits. Corrected in the F11-N2 row and in PR_BODY.md. |
| 4 | Calibration "met" was weaker than presented. | **Text.** The gate is now "met at the KEEP/refused level, weak as calibration", with the caveats listed below. The F11 receipt now carries a gate-level match against pre-registration (5/6), a discrimination note per negative, and the caveats. "Pre-registered before pass 1" was corrected. |
| 5 | PR_BODY.md overclaimed and conflicted with the route. | **Text.** It was rewritten as an internal note that is not for upstream. It gives an accurate guard description, the honest known-bad reading, and a ride-along section that matches Next step 6. `[body].kind` is now `internal-note`. |
| 6 | Stale member rebase counts; the F11-N1 label was wrong. | **Text.** Counts were re-measured against `aea969677c`. N1 is now labelled as head `354d499511`, the parent of revert `658e6c885d`, which serves as base. |
| 7 | The slice's parent was 16 commits behind main. | **Code.** The commit was re-applied onto main `aea969677c` (clean cherry-pick), so the slice is literally one commit on that main. By 11:36Z main had moved 6 commits to `e8c97320ac`, none touching `evals/`, `tests/evals/` or `scripts/run_tests*`, and merge-tree is still clean. *(Round 2 re-applied it onto `e8c97320ac`.)* |
| 8 | A recorded sabotage path was resolved from the cwd and untested. The "canary in every run" claim should be 7/8. | **Code + text.** The patch path is now resolved relative to the spec's directory, and the unit test covers that branch (NC7 proves it). The canary is 7/8 in pass 3 as well, because N3 was BLOCKED before any canary ran. |

## Invariant

A candidate is KEEP only when all of these hold, each in a fresh guarded process:

- its tests fail on base with the recorded markers;
- they pass on head on every rep;
- they fail again when a fix hunk is reverted;
- no adjacent file regresses.

Real call path: `python -m evals._factory.gate_runner run` → `git worktree` / `git merge-tree` arms → `bash scripts/run_tests.sh` in each arm. Each cell gets an empty env, a scratch HOME/HERMES_HOME, and a PATH made of a python shim plus `/usr/bin:/bin`, and it loads a `sitecustomize` audit-hook guard. The guard reaches pytest through run_tests.sh's own `$HOME/.hermes/pytest_live_guard.py` hook.

## Premise re-check on current main (`44a1ce9724`)

- `evals/_factory` does not exist on main. `evals/postmortem/run.py` still gates only the last column (`run.py:82`) and still uses `env.setdefault("HERMES_HOME")` (`run.py:47`). The file is unchanged since `572e4f4fad` (re-read on `44a1ce9724` in round 3).
- Nobody upstream owns a gate runner. The nearest work is NousResearch/hermes-agent#127952 by dskwe (open). It fixes NousResearch/hermes-agent#127898 and changes only `run.py:41` and the probe. This branch leaves `run.py` alone. If the setdefault matters upstream, support NousResearch/hermes-agent#127952's thread rather than folding a `run.py` fix in here.

## Member branches

| Ref | SHA | Role | Rebase (vs main `44a1ce9724`) |
|---|---|---|---|
| `refs/fork/feat/evolver-phase0-gate-calibration` | `20eb166106` | Donor of the gate semantics (validity / activation / credit) and the calibration design. The activation idea is re-implemented, not vendored. | merge-tree clean; 12,296 behind, 2 ahead (11 files, +1,375) |
| `refs/fork/lab/evals/hermes-stack-receipts-v0` | `22b0c745d5` | Donor of the receipt rules: `verified_success` null stays unknown, exact revisions, private raw stays local. Its arm schema is not the gate receipt shape. | merge-tree clean; 460 behind, 2 ahead (2 files, +91) |
| `staging/factory-replay-gate` (local; `staged/factory-replay-gate` on the fork) | `732919ad7d` | The first slice: `evals/_factory/{__init__,gate_runner}.py` and `tests/evals/test_factory_gate_runner.py`, 3 files, +974 | 1 commit; its parent is main `44a1ce9724` |

## First slice: COMMITTED (amended in rounds 1, 2 and 3)

The slice is commit `732919ad7dcd2173ba000af989b084583c231a59`, whose parent is main `44a1ce9724`. Author: Kevin Rajan (noreply), author date unchanged. Subject: `feat(evals): add a downstream promotion-gate runner with guarded cells`. It carries a `Co-authored-by` credit to Teknium for the guard pattern. Round 3 changed the runner and the test file: `git diff 2a4253258b 732919ad7d -- evals/_factory tests/evals` is 37 insertions and 6 deletions. In `gate_runner.py` (+11, -6), 5 code lines change, 3 added and 2 edited: the pin cell appended to the run's cells, the `infra_cells` list, the INFRA rule, its refusal reason, and the pin's `src.exists()` condition. The other +6/-4 is docstring. The test file gains 26 lines: one test and its toy Relay runtime. The commit message gained the same two statements as the docstring. Round 2's `2a4253258b` (parent `e8c97320ac`), round 1's `c430541d16` (parent `aea969677c`), round 0's `be292fd2ba` and pass 1's `b01d6dcb8b` (both parent `572e4f4fad`) are superseded but kept under archive refs (`[archive]`). The local branch `staging/factory-replay-gate` was forced to the new commit, and nothing was pushed.

The artifact of record is `factory-replay-gate.patch` (`git format-patch -1`, sha256 `d9296df0c2ee814d7e56a83032d8bd54ef1420f1a6c24f5caf23ca519aa06b36`). Earlier patches are in `archive/`. The worktree has been removed.

**What it does:**

- Runs one claimed `work_order`. The spec's sha256 must match, and the runner never selects work.
- Materializes the base and head arms, optionally merging head onto base with merge-tree. A conflict makes the run BLOCKED.
- Asserts RED, GREEN, per-hunk sabotage (or a recorded sabotage patch named relative to the spec) and ADJACENT, plus a recorded ownership gate.
- Runs a guard canary before any probe. Its blocks are the expected ones and are not counted. The canary checks:
  - loopback allowed;
  - non-loopback connect and name lookup blocked;
  - decoy live-home open blocked;
  - a decoy `hermes` exec blocked in argv, `shell=True`, `bash -c` and PATH forms, with the decoy never run;
  - no `hermes` on the cell PATH;
  - HOME/HERMES_HOME under the run directory.
- The guard only sees what Python does. A shell script file that runs `hermes`, a child started with a cleared env, C-extension sockets and `ctypes` are not inspected.
- The exec check is a word match, not a shell parser. It refuses any argv token, or any word of shell text split on metacharacters, whose basename is `hermes` or that starts with `hermes_cli.main`. Quoting (`her''mes`), globbing (`herme?`), backslash escapes and variable expansion that builds the name (`${X}mes`) evade it when `hermes` is called by absolute path, and so does code importing `hermes_cli` (`python -c 'import hermes_cli.main'`). F15-lite measures these. A hard boundary needs a kernel sandbox.
- Every cell except the canary counts in the receipt, including the Relay pin cell, which imports head code. A blocked attempt marks its cell INFRA, and any INFRA cell makes the run INFRA, never KEEP (round 3; before, the Relay pin cell's blocked attempts were dropped).
- Writes an `xf.receipt.v1` receipt (a superset of SPEC §4) and validates it:
  - every number is labeled OBSERVED;
  - revisions are full SHAs;
  - Relay pins are resolved only from the head arm's own `agent/relay_runtime.py` and recorded with local paths replaced by placeholders;
  - the validator refuses any absolute local path;
  - `verified_success` stays null.

**Proof (round 3, on main `44a1ce9724`, exact head `732919ad7d`; isolated HOME/HERMES_HOME, `run_tests.sh -j 2`):**

| Column | Result |
|---|---|
| RED on main `44a1ce9724` | Test file alone (`evals/_factory` moved out, then moved back): `ModuleNotFoundError: No module named 'evals._factory'`. |
| RED of the round-3 assertion on the round-2 runner `2a4253258b` | `2a4253258b`'s `gate_runner.py` copied over the head's, then restored by file copy. 2 of 3 tests pass and 1 of 3 fails: the new test, `AssertionError: assert ('KEEP' == 'INFRA'` (test line 124; the pin cell's blocked lookup was dropped and the run came out KEEP). |
| RED on the round-0 runner `be292fd2ba` | Same method. 3 of 3 tests fail: `AssertionError: assert [] == ['receipt con...e local path']` (test line 80), `AssertionError: assert ('KEEP' == 'INFRA'` (test line 124) and `AssertionError: the decoy hermes ran` (test line 152). |
| GREEN | 3 of 3 tests pass, on each of 3 runs at `732919ad7d` |
| Negative controls (each restored by file copy, no stash) | 12 of 12 turn the test file RED, listed below. |
| Adjacent | `tests/evals/` plus `evals/postmortem/tests/test_postmortem_harness.py`: 4 files, 9 of 9 tests pass (3 in the slice's own file, 6 in the 3 files main already had). |
| Lint | `ruff check` clean. The file was not `ruff format`ted, as in round 0. |

The twelve negative controls, each RED (verbatim `E` lines; the first 9 are the round-2 set, re-run):

- NC1, connect logged but not raised: `AssertionError: ['validity: guard canary failed']`, `assert 'INFRA' == 'KEEP'`; 3 of 3 tests fail.
- NC2c, red column hard-wired PASS: the already-fixed assertion fails, `assert {'result': 'P...agree': '2/2'} == {'result': 'F...epro_on_base'}`.
- NC3, sabotage applied forward: `AssertionError: ['sabotage: no sabotage re-REDs: the test does not pin the change']`, `assert 'DISCARD' == 'KEEP'` (2 of 3 tests fail).
- NC4, head not given the later tests: `assert 'KEEP' == 'DISCARD'`.
- NC5, shell-text split removed: canary fails, `assert 'INFRA' == 'KEEP'` (3 of 3 tests fail).
- NC6, interpreter bin dir back on PATH: canary fails, `assert 'INFRA' == 'KEEP'` (3 of 3 tests fail).
- NC7, sabotage patch read from cwd: `FileNotFoundError: [Errno 2] No such file or directory: 'break-add.patch'`.
- NC8, absolute-path rule removed: `assert [] == ['receipt con...e local path']`.
- NC9, Relay pin scrub removed: the new test fails, `At index 1 diff: '/opt/relay/system.toml' != '<abs>/system.toml'`. (In round 2 this control was caught only through the live-checkout path that the editable install leaked into the toy scenario's pin error. Round 3 stops that leak, so the new test carries an out-of-root config path to keep the scrub pinned without depending on the venv.)
- NC10, Relay pin cell not appended to the run's cells: `AssertionError: assert ('KEEP' == 'INFRA'`.
- NC11, verdict ignores INFRA cells outside the gates: `AssertionError: assert ('KEEP' == 'INFRA'`.
- NC12, pin imports `agent.relay_runtime` even when the arm lacks it: the known-good toy scenario turns INFRA, `AssertionError: ['infra cells: relay-pin']`, `assert 'INFRA' == 'KEEP'`. **Environment-dependent:** this control is RED only where the interpreter has an editable hermes-agent install that resolves `agent` from a checkout under the live home, as the venv used here does. On an interpreter without such an install the import is skipped (no `nemo_relay`) or fails without a blocked attempt, and no test catches the mutation.

Proof outputs are in `private/round3-proof/` (local only); rounds 1 and 2 are in `private/round1-proof/` and `private/round2-proof/`. So is the repro of round-3 finding 1 (`repro_pin_gap.py`): on the round-2 runner the toy known-good run's pin cell logged 2 blocked opens and the receipt was still KEEP, valid, `home_blocked = 0`, 8 cells, 0 INFRA; on `732919ad7d` the same scenario logs 0 pin events and is KEEP with 9 cells, 0 INFRA.

## Evidence

All experiments ran on the `cpu` lane at $0. The interpreter was the hermes-agent venv (Python 3.11.14, read-only).

Per-spec receipts are in `receipts/` (pass 5, runner `732919ad7d`, 16:22Z-16:36Z). Specs and envelopes are in `specs/`, unchanged since pass 2; `specs/run_all.sh` and the two experiment scripts changed in round 2 only in how they find the interpreter, mirror and worktree (environment variables instead of hard-coded local paths), and `experiments/summarize.py` gained a pass-5 history entry in round 3. Raw cell outputs are in `private/` (local only; pass-5 run directories in `private/pass5-runs/`). Earlier passes are in `receipts/pass1/`, `receipts/pass2/`, `receipts/pass3/` and `receipts/pass4/`. The two pass-2 receipts that leaked a path (F11-N1 sha256 `8463f789…`, E30-N1 sha256 `821f583d…`) are kept byte-exact only in `private/pass2-receipts/`.

| Experiment | Receipt | Verdict | Label | n | Numbers |
|---|---|---|---|---|---|
| F11: runner calibration (pass 5) | `receipts/F11-runner-calibration.json` | 6/6 at the KEEP/refused level; **weak as calibration** | OBSERVED | 6 specs, 48 probe cells (43 in pass 4; pass 5 counts the Relay pin cell in each of the 5 runs that reach it) | Known-good: 3/3 KEEP with all four columns PASS. Known-bad: 3/3 refused, false-READY 0. Gate-level match against pre-registration: 5/6. Known-bad with non-trivial gate discrimination: 0/3. |
| F11-P1 fork-50 on `572e4f4fad` | `receipts/F11-P1-fork50.json` | KEEP | OBSERVED | 10 cells | RED 3/3 (`assert ['over', 'under'] == ['under']`), GREEN 3/3, 1/1 hunks re-RED, ADJ equal |
| F11-P2 fork-112 on `572e4f4fad` (spec rev 2) | `receipts/F11-P2-fork112-r2.json` | KEEP | OBSERVED | 13 cells | RED 3/3, GREEN 3/3, 3/4 hunks re-RED. **Unpinned again in passes 3, 4 and 5:** `tools/process_registry.py -2340,6` (the `finally: session._kill_source = ""` clear). |
| F11-P3 fork-47 v2 on `572e4f4fad` | `receipts/F11-P3-fork47v2.json` | KEEP | OBSERVED | 11 cells | RED 3/3 (`assert 100.0 == 0.0`, `assert True is False`), GREEN 3/3, 2/2 hunks re-RED, ADJ equal |
| F11-N1 no-op length-stop change, later reverted: head `354d499511` (the parent of revert `658e6c885d`), base = the revert | `receipts/F11-N1-noop-revert.json` | INFRA (refused) | OBSERVED | 7 cells | Every RED/GREEN cell blocked a lookup of `openrouter.ai` (see FINDING): 6 of 7 cells INFRA; the 7th, the Relay pin cell, had 0 blocked attempts (completeness 0.143). Underlying RED was FAIL `no_repro_on_base`, but from guard-tainted cells. Pre-registered as "refused at RED", so this is **not** a gate-level match. |
| F11-N2: base `a7c2df3846` (the main commit NousResearch/hermes-agent#123635 by Halldrix landed on; the PR fixes issue NousResearch/hermes-agent#123545) to head `ac0b07597d`, the 8th of the PR's 9 commits (write-path hardening), so the graded change is the PR's first 8 commits; graded on the tests the same author added in the 9th commit `8ded06be29` (a separate read-path fix) | `receipts/F11-N2-review-fix.json` | DISCARD | OBSERVED | 7 cells | RED 3/3, GREEN 0/3 `not_fixed`, as pre-registered. **Trivial refusal:** those 8 commits never attempted the read-path defect the tests pin. It does exercise `tests_from` injection into head. |
| F11-N3 fork-111 head (NEEDS-REWORK) | `receipts/F11-N3-fork111-conflict.json` | BLOCKED | OBSERVED | 0 cells | merge-tree conflict in `tools/checkpoint_manager.py` and `tests/hermes_cli/test_profile_rename_checkpoints.py`, as pre-registered. Refused before any gate or canary ran. |
| E30-lite: gate vs reverted PRs (pass 5) | `receipts/E30-gate-calibration-lite.json` | UNINFORMATIVE (n=3) | OBSERVED | 1 positive, 2 negatives | Positive `8ded06be29`: four columns PASS, 4/4 hunks re-RED. Negatives refused 1/2 (the refusal is F11-N1's INFRA). **False credit 1/2:** `79dbb1450e` (NousResearch/hermes-agent#124792, reverted by `6ca1924763`) passes all four columns, 2/2 hunks re-RED. |
| E48: receipt validator (pass 5) | `receipts/E48-validator-faults.json` | PASS | OBSERVED | 10 + 2 fixtures | 10/10 core faults refused. 2/2 extra refused: `verified_success` self-upgrade, and the new non-home absolute path (the pass-2 leak shape). Clean pass-5 receipt (F11-P1) accepted. `verified_success` null on every fault. |
| F15-lite: guard canary (pass 5) | `receipts/F15-guard-canary.json` | PASS, plus a stated limit | OBSERVED | 7 classes + 8 limit forms | 7/7 blocked and 7/7 escape when only that class is removed: connect, lookup, live-home open, hermes exec (argv), hermes exec (shell text: `shell=True`, `bash -c`, PATH), no `hermes` on the cell PATH, and the test denylist. With only the shell split removed, the argv form still blocks. Loopback allowed, HERMES_HOME isolated. **Known limits (round 2, not a PASS criterion):** against the intact guard, 5/5 evasion forms ran the decoy with 0 blocked events and no INFRA (glob `herme?`, quote concatenation `her''mes`, backslash escape, `X=her; ${X}mes`, `python -c 'import hermes_cli.main'`), while 3/3 controls blocked (plain `shell=True`, `X=hermes; $X`, `python -m hermes_cli.main`). Escapes stayed on the host and ran only the decoy (a script, or a decoy `hermes_cli` package resolved from the cell's cwd). |
| C1: envelope-only (pass 5) | `receipts/C1-envelope-only.json` | PASS | OBSERVED | 4 cases | 4/4 refused (spec hash, kind, civ, no work order) before any run directory existed. Script: `experiments/c1_envelope_only.py`. |
| FINDING: upstream test hermeticity | `receipts/FINDING-unit-test-metadata-fetch.json` | recorded (re-observed) | OBSERVED | 1 file | On main `aea969677c` (and earlier `572e4f4fad`), `tests/agent/test_length_continuation_thinking_exhaustion.py` starts `fetch_model_metadata` (the GET at `agent/model_metadata.py:909`). That is a real lookup of openrouter.ai under `run_tests.sh`; 10 passed, 1 blocked lookup. Not filed. Not re-run on `44a1ce9724`: the test file and `agent/agent_init.py` are unchanged there, and `agent/model_metadata.py` changed only at line 1708+ since `aea969677c` (and not at all since `e8c97320ac`), so line 909 is the same GET. |

**Earlier passes.** Pass 1 used runner `b01d6dcb8b` (`receipts/pass1/`). It surfaced four problems, and all four were fixed before pass 2:

1. F11-N2 was falsely accepted (PARTIAL), because tests from `inject.tests_from` went to base only. The runner now injects them into head too. This change was made after pass 1, partly so that N2 is refused, and the unit test pins it (NC4).
2. F11-P2 rev 1 refused a known-good item, because pytest `-q` truncates the repr (`'p...ss.kill'`). Spec rev 2 was written after pass 1 to fix the marker; it is a marker-authoring lesson.
3. The exec denylist matched a docstring that mentions `execvp`. It now matches call syntax only.
4. The Relay pin crashed. The venv's `nemo_relay` rejects main's `validate(additional_plugins_toml=...)`. It is now recorded as an `error` field.

Pass 2 used runner `be292fd2ba` (`receipts/pass2/`, except F11-N1 and E30-N1, which are kept in `private/pass2-receipts/`). Pass 3 used runner `c430541d16` (`receipts/pass3/`). Pass 4 used runner `2a4253258b` (`receipts/pass4/`). Passes 2 to 5 match gate for gate and verdict for verdict. Pass 5 differs only in counting: each run that reaches the Relay pin has one more cell, the pin cell, and in all 7 such runs it logged 0 blocked attempts, so no verdict moved. No pass after pass 2 changed the specs.

## Acceptance gates (selection)

| Gate | Status | Evidence |
|---|---|---|
| Calibration: 3 known-good pass the four D2 checks, 3 known-bad refused | **met at the KEEP/refused level; weak as calibration** | F11 pass 5 (same gates and verdicts as passes 3 and 4): 3/3 KEEP, 3/3 refused, false-READY 0. Caveats: (1) no known-bad shows non-trivial gate discrimination: N1 was refused only as INFRA, N2 trivially (its 8 graded commits never attempted the defect the 9th commit's tests pin), and N3 at materialization before any gate ran; (2) the match against the pre-registered gate is 5/6, because N1 was pre-registered "refused at RED (no_repro_on_base)" and observed INFRA; (3) the runner was changed after pass 1 so that N2 would be refused, and F11-P2's RED marker was rewritten after pass 1 refused it (spec rev 2, 04:25 vs 04:17), so not every spec was pre-registered before pass 1; (4) there is no held-out set. |
| Self-test: the egress guard blocks a non-loopback connect | **met** | A canary runs in every run that gets past materialization. F15-lite (pass 5): 7/7 classes blocked, 7/7 escape when removed. |
| Exec guard: no exec of `hermes` | **met only for Python-initiated execs that name `hermes` as a plain word (argv, or shell text without quoting, globbing, escapes or name-building expansion); limited** | Canary and F15-lite cover the argv, `shell=True`, `bash -c` and PATH forms, plus `hermes` not on the cell PATH. Not covered: a shell script file that runs `hermes`, a child with a cleared env, other `hermes-*` console scripts run by absolute path (they are not on PATH), and the word-match evasions OBSERVED in F15-lite `known_limits` (quoting, globbing, backslash escapes, name-building variable expansion, `python -c 'import hermes_cli.main'`). Only a kernel sandbox closes these. Through pass 4, a blocked exec in the Relay pin cell would not have reached `exec_blocked` or the verdict (round-3 finding 1); from round 3 it does, and makes the run INFRA. |
| No run touches `~/.hermes`; resolved HERMES_HOME is under scratch | **met for the 8 gate specs; see caveat for the toy scenario** | Canary `home_isolated` was true in 7/8 pass-5 runs (and in 7/8 pass-3 and pass-4 runs); N3 was BLOCKED before any canary ran. `home_blocked = 0` in all 8 pass-5 receipts, which now include the Relay pin cell. **Caveat (round-3 finding 1):** through pass 4 the pin cell was not counted. In the unit test's toy known-good scenario on the round-2 runner, it made 2 attempts to open live-checkout files (via the editable install); both were blocked, so nothing was read, but the receipt still said `home_blocked = 0` and KEEP. Round 3 counts that cell and no longer makes that import. The live home is denied by password-database path, not `$HOME`. **Caveat:** the interpreter is the live venv, readable but never writable (`interpreter_writes_refused = 0`). |
| Receipts validate against the schema | **met (stdlib validator)** | 8/8 pass-5 gate receipts are `valid` under the validator (unchanged since round 1), which also refuses absolute paths. Through pass 4 the validator's "KEEP cannot include blocked attempts or INFRA cells" rule could not see the pin cell; from round 3 it can, and `_receipt()` no longer computes KEEP when any cell is INFRA. E48: 10/10 core and 2/2 extra. There is no JSON Schema document yet. |
| Consumes work_order envelopes only; never a scheduler | **met** | C1 (pass 5): 4/4 refused, 0 run directories. The source has no loop, timer, queue read or GitHub call. |
| Fork CI not used (G2) | **met** | Nothing pushed; all runs were local. |

## Cross-item notes produced by this run

These are for their owners. They are not changes made here.

- **fork-112 (READY, a row of the staged-PR queue kvnloo/hermes-agent#404):** the `finally: session._kill_source = ""` hunk (`tools/process_registry.py -2340,6`) is not pinned by any test. Reverting it alone keeps every test green, in passes 2, 3 and 4. Without that line, a natural exit after a kill could be misattributed. Either add a test or say why none is needed.
- **Upstream hermeticity:** see FINDING, re-observed on main `aea969677c` (the test file and `agent/agent_init.py` are unchanged on `44a1ce9724`, and `agent/model_metadata.py` changed only at line 1708+, so line 909 is still the GET). It is the most concrete candidate "real fix" for this runner to ride along with (P11).
- **Relay pin:** the hermes-agent venv's `nemo_relay` cannot drive main's `resolve_plugin_sources()`. This confirms that factory runs need a disposable `pm.build_env` venv rather than the live one.
- **Editable install:** when an arm lacks a package, such as the unit test's toy repo without `agent/`, the venv's editable hermes-agent install resolves imports from the live checkout under the live home. The guard blocks that open. Through round 2 this happened in the Relay pin cell of the toy known-good scenario, and because that cell was not counted (round-3 finding 1), the 2 blocked opens skipped the counters and the run stayed KEEP; the only trace was the pin's `error` string, which is what surfaced the path in round 2's NC9. Round 3 counts the pin cell, so such a block now makes the run INFRA, and the pin no longer imports `agent.relay_runtime` when the arm lacks it, so the toy scenario no longer reaches the live checkout. Any other probe that imports a package the arm lacks would still hit the editable install; it is blocked, and its cell and the run are INFRA.

## Gate checklist (P1-P12)

| Gate | Status | Why |
|---|---|---|
| P1 | N_A | There is no product defect claim. The runner's need is factory-side; `run.py`'s last-column-only gate is still on main. |
| P2 | PASS | No upstream owner. NousResearch/hermes-agent#127952 is adjacent. |
| P3 | RECORDED | One invariant, 3 files (+974), no env vars or hooks. The runner is 820 lines. |
| P4 | N_A | |
| P5 | PENDING | FACTORY §11.1 P5 includes "F14 guards equal", and F14 has not been run (`[evidence].guards`, Queued experiments). The rest is met in round 3: RED on `44a1ce9724`, RED of the new assertion on `2a4253258b` (and 3 of 3 tests on `be292fd2ba`), GREEN 3/3, 12 of 12 negative controls RED, adjacent 9 of 9 pass, `flaky = false`. |
| P6 | N_A | |
| P7 | PASS | One commit on main `44a1ce9724` (main at 16:09Z and 16:22Z by `git ls-remote`; see `[merge_check]` for the last re-check); author and subject unchanged; not pushed |
| P8 | PENDING | Receipts are sha256-pinned here but not frozen to z0evals. |
| P9 | N_A | No upstream text exists. `PR_BODY.md` is an internal note marked as not for upstream. |
| P10 | PENDING | Round 0 found 8 problems; round 1 fixed them. The round-1 re-verify found 5; round 2 fixed them. The round-2 re-verify found 2; round 3 fixed them. Re-verify is pending on `732919ad7d`. |
| P11 | FAIL by design | Eval-only content (D5); see `[ride_with]`. |
| P12 | N_A | |

## Queued experiments (not run)

Placeholders (round 2; the local values stay in the private run notes): `<xf-root>` is the factory's private store, `<gpu-lock>` the host's GPU flock file, `<local-router-url>` the local model router's OpenAI-compatible base URL, `<live-install>` the live Hermes install directory that bwrap masks with a tmpfs, `<venv-python>` the interpreter, `<runner-wt>` a worktree at the staging commit, `<wt-main>` a worktree at main, `<repo.git>` the git mirror, `<test-home>` an isolated test home and `<scratch>` a scratch directory.

### E20: A/A noise floor on a local model (T2)

- **Needs:** OD-1 (a router preset of at least 64K, actually served) and OD-2 (the CLI inside bwrap from a disposable venv).
- **Constraints:** GPU flock, strictly serial, never preempting Quackles.

```bash
VENV=<xf-root>/venvs/<uv.lock sha12>   # python -m pm.build_env --source <wt> --out $VENV --group dev --group test
RUN=<xf-root>/cells/E20-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $RUN/home/.hermes
# $RUN/home/.hermes/config.yaml: model.provider=custom, base_url=<local-router-url>, default=<64K preset id>, api_key=no-key-required
flock <gpu-lock> bwrap --ro-bind / / --dev /dev --proc /proc --bind $RUN $RUN --tmpfs <live-install> \
  --unshare-pid --die-with-parent --clearenv --setenv HOME $RUN/home --setenv ABEVAL_HOME $RUN/home/.hermes \
  --setenv ABEVAL_ROOT $RUN/abeval --setenv PYTHON $VENV/bin/python --setenv PATH $VENV/bin:/usr/bin:/bin \
  bash <wt-main>/evals/toolperf_abeval/run_all.sh <wt-main> <wt-main> 5 <64K preset id>
```

### E20-paid (T3)

Needs OD-3. The owner launches it with injected credentials; workers hold none.

```bash
ABEVAL_HOME=<owner home> bash evals/toolperf_abeval/run_all.sh <wt-main> <wt-main> 5 qwen/qwen3-coder-30b-a3b-instruct
```

The A/A uses the same tree in both arms. Report per-task SD and MDE, median, p95 and n.

### E30-full: reverted-PR battery of at least 10 negatives, the kill switch ($0 T1, heavy)

Run it in a CPU-quiet window. It is also the held-out set the calibration lacks: specs are written and hashed before any run, and the runner is frozen at one commit for the whole battery.

```bash
git -C <repo.git> log --since=2026-09-01 --format='%H %s' main | grep -iE '^[0-9a-f]+ (revert|Revert ")' > reverts.txt
# For each revert R of commit X: spec base=X^ head=X files=<X's test files> markers=["AssertionError"], expected="refused"
python3 specs/make_specs.py   # extended with the reverts list, then:
W=<runner-wt> XF_REPO=<repo.git> XF_PYTHON=<venv-python> HOME=<test-home> specs/run_all.sh $(cut -d' ' -f1 reverts.txt | sed 's/^/E30-R-/')
```

Also run the evolver's own synthetic-negative harness. Do this only after reading its `run_test` for isolation (S15):

```bash
git -C <repo.git> worktree add --detach <scratch>/evolver-calib-wt refs/fork/feat/evolver-phase0-gate-calibration
cd <scratch>/evolver-calib-wt
HOME=<test-home> HERMES_HOME=<test-home>/.hermes <venv-python> -m evolver.calibrate --repo . --workdir <scratch>/evolver-calib --report receipts/E30-evolver-calibrate.json --skip-credit
```

### F14: standing regression set ×2 on base-of-day ($0 T1)

Run each harness through the runner's cell (`gate_runner.run_cell`) so every probe gets the guard:

```bash
python -m evals.postmortem.run --repo <wt-main>   # HERMES_HOME forced by the cell
python evals/provider_fallback/probe_104120.py <wt-main>   # also probe_104260.py and probe_104360.py
python evals/token_accounting/replay_gates.py <wt-main>    # also ab_image_cost_calibration.py and worktree_prompt_prefix.py
bash scripts/run_tests.sh evals/compaction/test_region_scoping.py -q
```

### F15-full: the kernel layer ($0 T0)

Wrap the same runner in bwrap with `--unshare-net`, a read-only root and `--bind $RUN $RUN`. This adds the classes the in-process guard cannot cover: a write outside `$RUN` must fail with EROFS, and a shell script file, or any of the word-match evasions in F15-lite's `known_limits`, must find no `hermes` it can reach.

```bash
bwrap --ro-bind / / --dev /dev --proc /proc --bind $RUN $RUN --tmpfs <live-install> --unshare-net --unshare-pid \
  --clearenv --setenv HOME $RUN/home --setenv PATH /usr/bin:/bin --setenv XF_PYTHON <venv-python> \
  <venv-python> experiments/f15_guard_canary.py <runner-wt> $RUN receipts/F15-full.json
```

## NOT_TESTED

- **Kernel isolation:** the guard is in-process and Python-level. C-extension sockets, `ctypes`, and writes outside the run directory are not blocked. No bwrap or netns layer was used.
- **Exec guard limits:** a shell script file that runs `hermes`, and a child started with a cleared environment, are not inspected. Other console scripts (`hermes-agent`, `hermes-acp`) are not on the cell PATH but are not refused by absolute path. Matching is a word match, not a shell parser. It is fail-closed only for plain text: any argv token, or word of shell text split on metacharacters, whose basename is `hermes`, or that starts with `hermes_cli.main`, is refused, including a directory named `hermes` and `X=hermes`. Quoting (`her''mes`), globbing (`herme?`), backslash escapes and variable expansion that builds the name (`${X}mes`) evade it, and so does code importing `hermes_cli` (`python -c 'import hermes_cli.main'`). This is OBSERVED in F15-lite `known_limits`: those forms ran the decoy with 0 blocked events and no INFRA. They need deliberate obfuscation plus an absolute path, because `hermes` is not on the cell PATH. Only a kernel sandbox closes this.
- **Interpreter:** this is the live hermes-agent venv (Python 3.11.14), used read-only. Its `nemo_relay` is incompatible with main, so the Relay `config_paths` were never resolved. A disposable `pm.build_env` venv was not built.
- **Ownership:** the ownership gate consumes the recorded verdicts (2026-09-30 readiness). The runner does no `gh` search of its own.
- **F14 (P5 guards):** the standing regression set has not been run on base or on this arm, so P5 is PENDING, not PASS. No F14 harness imports `evals/_factory` (static grep), which is not the same as "guards equal".
- **Relay pin cell, passes 1-4:** through round 2 the pin cell's blocked attempts and INFRA flag were dropped from the verdict, denominators and safety counters (round-3 finding 1). Passes 1-4 receipts were made that way. The pass-2 and pass-3 run directories show 0 blocked events in every real-arm pin cell (each imported `./agent/relay_runtime.py` from the arm); pass-4 run directories were not kept. The only case observed with dropped blocks is the unit test's toy scenario (2 blocked opens through the editable install). Pass 5 counts the pin cell.
- **Relay pin scope:** the pin imports head code (`agent/relay_runtime.py` and what it imports) in a guarded cell. A blocked attempt there now makes the run INFRA, but a pin that resolves `config_paths` without any blocked attempt is not otherwise checked.
- **Not run:** the full test suite, real providers, local models (OD-1), the CLI (OD-2), paid runs (OD-3), F14, the round-3 re-verify, and any z0evals freeze.
- **Scope:** E30 is n=3 and cannot act as the kill switch yet. One false credit is on record. The calibration has no held-out set.

## Next steps

1. **Owner:** OD-0 is resolved for this item by pushing as `staged/factory-replay-gate`. OD-5 (the executor's home: evolution-lab `xf` vs these in-tree adapters) is still open. Neither blocks local use.
2. **Blind verifier (round 3):** read exact head `732919ad7d` against this manifest's acceptance gates.
3. **Run E30-full** (at least 10 reverted-PR negatives, specs hashed before the run, runner frozen) before any frontier branch moves to PROMOTION_READY. One false credit (79dbb1450e) is already known.
4. **Build the disposable venv** (`python -m pm.build_env`) and re-run F11 in it with Relay pins resolved. Then add the bwrap layer (F15-full).
5. **Hand the fork-112 unpinned-hunk note** to the kvnloo/hermes-agent#404 row owner.
6. **If upstream use is ever wanted:** drop the work-order wrapper, rename `evals/_factory` to a neutral path, and offer only the guard and per-hunk sabotage as review tooling alongside the metadata-fetch hermeticity fix. Never offer them alone.
7. **Run F14** (the standing regression set, on base and on this arm, twice each) through the runner's cells, so that P5 can move from PENDING to PASS or FAIL. Added in round 3; numbered last only so that the earlier rounds' reference to step 6 stays valid.

## History

| Time (UTC) | Status | Worker | Reason |
|---|---|---|---|
| 2026-10-01T09:15Z | CANDIDATE → EVIDENCED | staging builder (Claude Code, Opus 5.5) | Runner committed (`b01d6dcb8b`); specs written; pass-1 calibration |
| 2026-10-01T09:37Z | EVIDENCED | staging builder | Pass 1 found 3 runner issues and 1 spec issue. Amended to `be292fd2ba` and re-proved RED/GREEN/NC1-4/ADJ. |
| 2026-10-01T09:51Z | STAGED | staging builder | Pass 2: F11 6/6, E48 10/10, F15-lite 5/5 + 5/5, C1 4/4. E30-lite UNINFORMATIVE with 1 false credit. Local branch `staging/factory-replay-gate` → `be292fd2ba`. |
| 2026-10-01T10:30Z | STAGED (changes required) | phase-3 blind verifier | 8 problems: exec-guard gap, absolute paths in 2 receipts, NousResearch/hermes-agent#123545 mislabel, calibration overstated, PR_BODY conflicts with route, stale counts/N1 label, parent behind main, sabotage path + 7/8 canary. |
| 2026-10-01T11:40Z | STAGED | staging fixer, round 1 (Claude Code, Opus 5.5) | All 8 fixed. Code: shell-text exec guard, PATH shim, Relay pin scrub, absolute-path validator rule, spec-relative sabotage path; re-applied onto main `aea969677c` as `c430541d16`; RED/GREEN 3/3/NC 9/9/ADJ re-proved. Pass 3 of all 8 specs, E48 10/10 + 2/2, F15-lite 7/7 + 7/7, C1 4/4, FINDING re-observed. Text: N1/N2 labels, calibration caveats, counts, PR_BODY reframed as an internal note. Local branch forced to `c430541d16`; OD-0 resolved by the `staged/` rename. |
| 2026-10-01 (after 11:40Z) | STAGED (changes required) | phase-3 re-verifier, round 1 | 5 problems: absolute paths and a tailnet endpoint in this manifest and its cited scripts; exec guard's shell-text limit undisclosed (glob / quote / escape forms ran the decoy); NousResearch/hermes-agent#123635 has 9 commits, not 8, and N2's base is the PR's landing commit; red_fix marker carried a gloss; `be292fd2ba` and `b01d6dcb8b` unreferenced after the force-move. |
| 2026-10-01T12:15Z | STAGED | staging fixer, round 2 (Claude Code, Opus 5.5) | All 5 fixed. Archive refs `-p1`/`-r0`/`-r1` plus patches. Docstring and commit message state the word-match limits; re-applied onto main `e8c97320ac` as `2a4253258b`; RED, RED-on-`be292fd2ba`, GREEN 3/3, NC 9/9, ADJ and ruff re-proved. Pass 4: all 8 specs, E48 10/10 + 2/2, F15-lite 7/7 + 7/7 plus `known_limits` (5/5 evasions ran, 3/3 controls blocked), C1 4/4. Scripts and queued commands use placeholders; privacy scan widened. Local branch forced to `2a4253258b`; nothing pushed. |
| 2026-10-01 (after 12:15Z) | STAGED (changes required) | phase-3 re-verifier, round 2 | 2 problems: the Relay pin cell's blocked attempts and INFRA flag were dropped from the verdict, denominators and safety counters (reproduced on the unit test's toy known-good scenario: 2 blocked opens, still KEEP and valid), contradicting `PR_BODY.md`, the docstring and the commit message; P5 PASS although F14 (part of P5) was not run. |
| 2026-10-01T16:38Z | STAGED | staging fixer, round 3 (Claude Code, Opus 5.5) | Both fixed. Code: pin cell appended to the run's cells, any INFRA cell makes the run INFRA (with a refusal reason), pin imports only the arm's own `agent/relay_runtime.py`; one new test, RED on `2a4253258b`; docstring, commit message and `PR_BODY.md` corrected. Re-applied onto main `44a1ce9724` as `732919ad7d`; RED on main, RED on `2a4253258b` and `be292fd2ba`, GREEN 3/3, NC 12/12, ADJ 9 of 9 and ruff re-proved. Pass 5: all 8 specs (same verdicts), E48 10/10 + 2/2, F15-lite 7/7 + 7/7 plus `known_limits` (5/5 evasions ran, 3/3 controls blocked), C1 4/4. P5 set to PENDING with `guards = { F14 = "NOT_RUN" }`. Archive ref `-r2` plus patch; pass-4 receipts kept in `receipts/pass4/`. Local branch forced to `732919ad7d`; nothing pushed. |
