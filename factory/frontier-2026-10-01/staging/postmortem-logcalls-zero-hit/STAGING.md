+++
xf_staging = 1
id = "postmortem-logcalls-zero-hit"
version = 1
title = "evals/postmortem: count zero-hit and usage-unavailable calls in logcalls (and the two live cache probes)"
promotion_form = "eval-contribution"
branch = "staging/postmortem-logcalls-zero-hit"       # local name in the scratch bare mirror h.git
branch_fork = "staged/postmortem-logcalls-zero-hit"   # name on kvnloo/hermes-agent when pushed (owner)
branch_physical = "local-only in h.git (not pushed). OD-0 RESOLVED by the rename: the fork's legacy refs/heads/staging @28790e597c blocks refs/heads/staging/<id>, so the fork ref is staged/<id>. A push of staged/postmortem-logcalls-zero-hit matches 0 workflow push triggers (PROOF/r20261001-02)."
branch_sha = "dd4dd10611e8c23c7579a4ddb95655abebbaca27"
branch_v2 = ""           # round 3: commit message re-read against the code and PR body, accurate, unchanged; no -v2 ref created
status = "STAGED"        # commit + self-evidence done; round-0 verifier CHANGES_REQUIRED (text only) -> round-1 re-verify accepted with 4 non-blocking advisories -> handled in round 3; P2, P8-P12 still PENDING; P11 needs the #121135 fold-in route or OD-7
route = "eval-fix"       # offered first as a ride-along fold-in on #121135 (D5); standalone only if #121135 merges without it AND F06/E19 on real logs show the bias (OD-7, P11)
feature = "postmortem-logcalls-zero-hit-fix"
invariant = "Every reader of the per-call 'API call #N' log line counts a call whose line has no cache= (a zero-hit call) and accounts for usage=unavailable lines separately, instead of silently dropping them."

[base]
repo = "NousResearch/hermes-agent"
sha = "234badf4012af380d23c91eae55d045a69c69ffb"
fetched_at = "2026-10-01T08:51Z (main @ 2026-10-01 03:50:55 -0500)"
first_built_on = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0 (rebased to 234badf401; the 11 intervening commits touch none of evals/postmortem, agent/turn_usage.py, agent/usage_pricing.py, hermes_logging.py, tests/agent/test_turn_usage_log_line.py)"
declared_main = "34f8ec3b407e50bad3ae27e4cd79d65212061356"   # round 3: upstream main (commit date 2026-10-01T17:29:37Z), read 2026-10-01T18:34Z; RED, GREEN 3/3 and ADJACENT re-run there in the sandbox (PROOF/r20261001-03); commit stays on 234badf401
declared_main_previous = "aea969677c60a1bb72fe227fdfb98f196a2092cc (round 1, fetched 2026-10-01T11:04Z, PROOF/r20261001-02); e8c97320ac (seen at round-1 close) is an ancestor of the new main"
invalidate_on = ["evals/postmortem", "agent/turn_usage.py", "agent/usage_pricing.py", "hermes_logging.py", "tests/agent/test_turn_usage_log_line.py", ".github/workflows"]
declared_main_drift = "74 commits 234badf401..34f8ec3b40 (38 since aea969677c). Among invalidate_on only agent/usage_pricing.py changed: e2d311e5e6 and 5bb6127c5b edit the model-pricing alias table near line 340 (net -1 line); normalize_usage, the producer and the parser are untouched; 0 commits touch .github/workflows (PROOF/r20261001-03, raw/r3/merge_tree.txt)"

[upstream]
issues = ["NousResearch/hermes-agent#84460 (aider4ryder, open: durable log conflates reported zero with unavailable telemetry)",
          "NousResearch/hermes-agent#103563 (teknium1, closed 2026-09-08: postmortem harness tracking issue)"]
harness_pr = "NousResearch/hermes-agent#103756 (teknium1, merged 2026-09-06: the postmortem harness itself)"
eval_prs = []
carrier = { pr = 121135, author = "Wenfengcheng (commits authored as funky-xamarin)", head = "dd4a0ca4cf3345702eb7be95e11873308d3015b5" }
line_shape_dependency = { pr = 119713, author = "teknium1", head = "7471d9915d7d1ce3e94f9d18c9d775461d269815" }
competitors = []
close_after = []
demand = { score = 0, source = "no demand-report entry; judges: missing:logcalls-zero-hit-coverage-fix 9, postmortem-logcalls-zero-hit-fix 4" }
maintainer_signal = "teknium1 on #119713: ttfb= appended last 'so the forensics parser's latency=..s cache= adjacency ... keep matching'. Automated review on #121135 (issuecomment-5854199241): 'Blocker 1 - the new state reaches no consumer' naming logcalls.py:27, cache_prefix_live.py:44, cache_prefix_wire.py:61."

[[donors]]
sha = "dd4a0ca4cf3345702eb7be95e11873308d3015b5"
author = "Wenfengcheng / funky-xamarin"
role = "carrier (cache_state= on the log line); no code reused, so no Co-authored-by on our commit"

[[donors]]
sha = "dd4dd10611e8c23c7579a4ddb95655abebbaca27"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "fold-in (parser + live-probe regexes + 2 harness tests)"
trailer = "Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>   # if folded into #121135"

[ownership]
searched_at = "2026-10-01T09:00Z"
queries = ["logcalls", "forensics logcalls cache", "usage=unavailable", "cache_state", "zero-hit cache log", "postmortem forensics", "logcalls (closed)"]
recheck = "2026-10-01T18:34Z (round 3, gh read-only): open PRs matching logcalls / cache_state / usage=unavailable / cache_prefix_live: still only #121135 and #119713 touch the line or its readers; both open, heads unchanged; #84460 open, #103563 closed, #103756 merged"
open_external = [121135, 119713]
merged_overlap = ["NousResearch/hermes-agent#103756 (teknium1, harness, merged 2026-09-06)", "NousResearch/hermes-agent#104568 (teknium1, write=/id=/upstream=, merged 2026-09-06)"]
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # all TUI/HUD perf; no overlap (gh, 2026-10-01)
hard_hold = [69, 70]                                         # kvnloo/hermes-agent#69 and kvnloo/hermes-agent#70 (state-db docs/doctor); no overlap
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]   # none apply
hermes_lane_overlap = "NOT CHECKED: the Hermes-lane PLAN lives under ~/.hermes/profiles/..., which this worker may not read"
verdict = "EXTERNAL carrier (#121135) -> fold-in/support first; no one else changes these parsers"

excluded_paths = []

[evidence]
receipts = [   # round 1: r01 receipts completed to xf.receipt.v1 + absolute paths redacted (harness/receipts_r1.py). Round 3: env.host scrubbed and inputs.scripts_published added (harness/r3/receipts_r3.py), so the six r01/r02 hashes changed again; measurements unchanged; superseded bytes kept privately (private/superseded-receipts-r2/)
  { id = "PROOF/r20261001-01",  path = "receipts/PROOF_r20261001-01.json",  sha256 = "f3395ee6a93ebe06ab324216e50b4d9a7f503dfa18a498af20f93a521cb9accd" },
  { id = "F06RT/r20261001-01",  path = "receipts/F06RT_r20261001-01.json",  sha256 = "2dd8206b43e5363994bed7d7ad1ca21dadc5dc88ae2fe010c6b3fd06097cad90" },
  { id = "F06SYN/r20261001-01", path = "receipts/F06SYN_r20261001-01.json", sha256 = "d7d27185727df7ccc19beecb858c2d9f4a2e3d29e714cff36d7cae2161e59116" },
  { id = "E19SYN/r20261001-01", path = "receipts/E19SYN_r20261001-01.json", sha256 = "72e36943e5424cbeb19cfd77333b33050d6e86e5d442da7d9227babf72b52b3e" },
  { id = "CARRIER/r20261001-01", path = "receipts/CARRIER_r20261001-01.json", sha256 = "88c85a7f868c57053058982114a329603b44f993a97c784e43247250b5d8ae22" },
  { id = "PROOF/r20261001-02",  path = "receipts/PROOF_r20261001-02.json",  sha256 = "d62ad6a3bfaeccb06f89dae7cc2dc0a4bbe18e5c138e65ac70477b09feeb4011" },
  { id = "F14/r20261001-01",    path = "receipts/F14-r20261001-01.json",    sha256 = "26d2b140e6e9483132c25e1d2c9510f4c6b08e713efe77e7d930f90c1221a52c" },
  { id = "PROOF/r20261001-03",  path = "receipts/PROOF_r20261001-03.json",  sha256 = "1cc44075691ddf3aedeb6fca77bb9ced4391596ce9892e0a0123f33451c655d6" },
]
red = { test = "evals/postmortem/tests/test_postmortem_harness.py::test_logcalls_counts_zero_hit_and_usage_unavailable_calls + ::test_logcalls_reads_cache_state_and_tolerates_trailing_fields", main = "234badf401; re-run on aea969677c and on 34f8ec3b40 (sandboxed)", marker = "assert 2 == 3 / assert (2 == 4) on coverage.calls_found", receipt = "PROOF/r20261001-01, PROOF/r20261001-02, PROOF/r20261001-03" }
green = { reps = "3/3 (8 passed: harness 5 + tests/agent/test_turn_usage_log_line.py 3) on the head; 3/3 again on main aea969677c + head (tree f388caeb37) and on main 34f8ec3b40 + head (tree c7460b5c53, sandboxed)", receipt = "PROOF/r20261001-01, PROOF/r20261001-02, PROOF/r20261001-03" }
negative_control = { mutation = "per-hunk, 6 logcalls hunks -> 6/6 RED again; probe regex hunks RED offline (1/4 rows). Unpinned: early-exit guard (`if not scored` -> `if not calls` stays GREEN; ZeroDivisionError on only-no_field input), coverage print line, docstring", result = "RED (6 pinned hunks)", receipt = "PROOF/r20261001-01, PROOF/r20261001-02" }
adjacent = { identical = true, pre_existing = [], files = ["tests/agent/test_turn_usage_log_line.py", "evals/postmortem/tests/test_postmortem_harness.py"], recheck = "34f8ec3b40: test_turn_usage_log_line.py 3 passed on main and on main + head; the harness file's 3 existing tests pass on both (PROOF/r20261001-03)" }
guards = { F14 = "EQUAL", receipt = "F14/r20261001-01", arm = "42b7748969 (dd4dd10611 cherry-picked clean onto main 34f8ec3b40, same patch-id; refs/xf/w0/postmortem-logcalls-zero-hit)", set_sha256 = "aba79fe8f09d", detail = "2 runs x 40 verdict ids, both equal to the base baseline and to each other (36 PASS, the same 4 FAIL as base); 0 INFRA, 0 flaky. No F14 probe reaches the 4 changed files, so this guards neighbours, not the parser" }
quantitative = []                  # no real-run numbers; synthetic numbers are MODELED and not claimed
cache_read_ratio = { status = "N_A" }
route_scope = "n/a"
not_tested = ["real agent.log / state.db (OD-7)", "live probes end-to-end (paid, owner-launched)", "combined #121135+#119713 producer (carriers conflict)", "CI (evals/ outside testpaths)", "real-run size of the legacy-line behaviour change (routes with no cache counter now read as zero-hit; disclosed in PR_BODY.md)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-postmortem-logcalls-zero-hit", commit = "" }

[gates]
P1 = "PASS"       # RED on main 234badf401, re-run RED on aea969677c and on 34f8ec3b40 (2026-10-01T18:37Z, PROOF r03); the only invalidate_on change since the base is the usage_pricing.py alias table; re-check within 24 h of queueing
P2 = "PENDING"    # upstream dedupe PASS; Hermes-lane PLAN overlap not checkable by this worker
P3 = "PASS"       # one invariant, 4 files (+79/-18), no env vars, no hooks
P4 = "PASS"       # real record_response_usage + real agent.log formatter -> parser; live probes NOT_TESTED
P5 = "PASS"       # RED marker matched, GREEN 3/3, per-hunk NEG 6/6 with 3 unpinned hunks listed, ADJ identical, flaky=false (PROOF r01/r02); F14 EQUAL (F14/r20261001-01)
P6 = "N_A"        # body makes no real-run value claim
P7 = "PASS"       # one commit on 234badf401 (not rebased; 74 commits behind 34f8ec3b40, none on its files), author ok; merge-tree clean vs declared main 34f8ec3b40 (c7460b5c53), #121135, #119713; a push of staged/<id> matches 0 workflows
P8 = "PENDING"    # receipts local + sha256, full xf.receipt.v1 shape, host and paths scrubbed in round 3 (as-run harness private, cited by sha256); spec NOT_PREREGISTERED (pre-Wave-0); not frozen to z0evals
P9 = "PENDING"    # PR_BODY.md: AI use disclosed for code and description, no @mentions, legacy-line behaviour change disclosed, test-coverage claim narrowed, probe 10.0% vs 13.3% stated; round-3 mechanical jargon + privacy lint clean; tone gate by owner
P10 = "PENDING"   # round-0 blind verifier on dd4dd10611: CHANGES_REQUIRED (text only); round-1 re-verify on dd4dd10611: accept, 4 non-blocking advisories (handled in round 3). No APPROVE_EXACT_HEAD / QA CLEAN recorded, and the texts and receipts changed after that read: needs a fresh exact-head read
P11 = "PENDING"   # eval-only: must ride #121135 (fold-in) or show real-log bias via F06/E19 (OD-7)
P12 = "PENDING"   # staging cap / promotion_freeze: owner

[verification]
verifier = "phase-3 blind verifier: round 0 (frontier-2026-10-01/phase3_results.json) and round-1 re-verify (frontier-2026-10-01/phase3_fix_results.json)"
provenance = "independent"
exact_head = "dd4dd10611e8c23c7579a4ddb95655abebbaca27"
inputs = "raw diff + repo + oracle block only"
verdict = "round-1 re-verify: accept"   # round 0 CHANGES_REQUIRED (text only) -> round 1 accept with 4 non-blocking advisories (harness/ paths, fallback precondition, probe no_field nit, declared-main lag), all handled in round 3. Not an APPROVE_EXACT_HEAD record; the round-3 texts/receipts are unread
qa_class = ""

[merge_check]
main_sha = "34f8ec3b407e50bad3ae27e4cd79d65212061356"
checked_at = "2026-10-01T18:34Z"
clean = true
tree = "c7460b5c539e76cff2dbe5cdb7961cec1334a892"   # = git write-tree of main + the head's 4 files, where RED/GREEN/ADJ ran (PROOF/r20261001-03)
recheck = "git merge-tree --write-tree main staging/postmortem-logcalls-zero-hit   (or: bash harness/r3/mt_r3.sh <h.git> <main sha>)"
also = ["#121135 x staging: CLEAN tree 2e7d28d7d3", "#119713 x staging: CLEAN tree 97793e195c", "main x #121135: CLEAN tree a40a4c7890", "main x #119713: CLEAN tree 18821688bd", "#121135 x #119713: CONFLICT agent/turn_usage.py (theirs, not ours)"]
invalidate_on_changed = "234badf401..34f8ec3b40: agent/usage_pricing.py only (e2d311e5e6, 5bb6127c5b: model alias table, not normalize_usage); evals/postmortem, agent/turn_usage.py, hermes_logging.py, tests/agent/test_turn_usage_log_line.py, .github/workflows unchanged"
previous = ["2026-10-01T11:05Z on aea969677c: CLEAN tree f388caeb37 (main x #121135 798e76b64d, main x #119713 1f2049ee49)", "2026-10-01T09:10Z on 234badf401: CLEAN tree 9f262517dd", "round-1 close, informational: e8c97320ac CLEAN tree 5335078cd2 (an ancestor of 34f8ec3b40)"]

[push]
no_follow_tags = true
remote_ref = "kvnloo/hermes-agent refs/heads/staged/postmortem-logcalls-zero-hit"
workflow_push_matches = 0     # for staged/postmortem-logcalls-zero-hit, workflow files at dd4dd10611 (PROOF/r20261001-02)
pushed_at = ""

[body]
path = "PR_BODY.md"
kind = "pr-body"
fold_in_comment = "see 'Origin action' below"
tone_gate = { peer = false, no_labor = false, no_internal_leak = false, smallest_ask = false, self_service = false, local_voice = false, easy_decline = false }
jargon_lint = "PENDING (owner). Round-3 mechanical grep of PR_BODY.md and the fold-in draft for P1-P12, OD-n, xf, F##/E##, D#, receipts, envelope, wave, staging, factory, OBSERVED/MODELED, @mentions: clean; upstream items appear only as #N"
privacy_scan = "CLEAN at round 3 (2026-10-01T18:49Z) for the publishable set (STAGING.md, PR_BODY.md, the patch, receipts/, receipts/raw/, harness/): no absolute local paths, host name, user name, session id, email other than the public noreply addresses (author, Claude co-author trailer), secret or bytecode. Remaining ~/.hermes strings are upstream code or owner-only commands; one generic pytest tmp-root regex remains in harness/receipts_r1.py (a redaction pattern, not a path); the 2 binary files are the synthetic F06 state.db fixtures. private/ is excluded; owner to confirm"
template_attestations = "The PR template boxes 'I've read the Contributing Guide' and 'I've tested on my platform' are the owner's attestations at posting time; the factory read CONTRIBUTING.md (blob b0baa59b50) and ran the tests; no owner review is recorded"

[queue]
board = "kvnloo/hermes-agent#404"   # staged-PR queue: 39 rows, none for this id (re-read 2026-10-01T18:40Z; board last updated 08:11Z)
position = "after existing rows"
slot_claimed = false
waves = "not part of NousResearch/hermes-agent#130139 (salvage wave, was kvnloo/hermes-agent#402) or NousResearch/hermes-agent#130140 (close wave, was kvnloo/hermes-agent#403)"

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# staging/postmortem-logcalls-zero-hit

**Promotion form:** eval-contribution. It goes first as a fold-in offered on NousResearch/hermes-agent#121135. It becomes a standalone PR only if #121135 merges without it **and** F06/E19 on real logs show the bias (OD-7), because an eval-only change cannot go upstream alone (P11, D5).

**RFC / issue links:**
- Upstream:
  - NousResearch/hermes-agent#121135 (carrier)
  - NousResearch/hermes-agent#84460 (issue that #121135 fixes)
  - NousResearch/hermes-agent#119713 (line shape: trailing `ttfb=`)
  - NousResearch/hermes-agent#103563 (closed; tracking issue for the postmortem harness)
  - NousResearch/hermes-agent#103756 (merged 2026-09-06; the PR that landed the harness)
- Fork: no campaign thread for this id yet (OD-9). The staged-PR queue kvnloo/hermes-agent#404 has 39 rows and none for this id. The wave issues kvnloo/hermes-agent#402 and kvnloo/hermes-agent#403 were closed and posted upstream as NousResearch/hermes-agent#130139 and NousResearch/hermes-agent#130140. This id is in neither.
- Fork branch name: `staged/postmortem-logcalls-zero-hit`. The fork already has a legacy `refs/heads/staging`, so `staging/<id>` cannot exist there. OD-0 is resolved by this rename. The local ref in h.git keeps the name `staging/postmortem-logcalls-zero-hit`.

## Member branches

Declared main for round 3: upstream `34f8ec3b40`, read 2026-10-01T18:34Z (round 1 used `aea969677c`). The commit stays on `234badf401`. Of the 74 commits in between, only two touch an `invalidate_on` path: `agent/usage_pricing.py`, in its model alias table only. RED, GREEN 3/3 and ADJACENT were re-run on `34f8ec3b40` (PROOF/r20261001-03).

| Ref | SHA | Role | Merge status on main `34f8ec3b40` (PROOF/r20261001-03) |
|---|---|---|---|
| `staging/postmortem-logcalls-zero-hit` (local, h.git; fork name `staged/postmortem-logcalls-zero-hit`) | `dd4dd10611` | Our one commit: logcalls parser, both live-probe regexes, 2 harness tests | Parent `234badf401`. merge-tree clean vs `34f8ec3b40` (tree `c7460b5c53`). |
| `refs/pr/121135` (h.git; head unchanged per gh, 2026-10-01T18:34Z) | `dd4a0ca4cf` | Carrier (Wenfengcheng): `cache_state=` / `cache_read=` / `cache_write=` on the log line | Clean vs main (tree `a40a4c7890`). Clean vs staging (tree `2e7d28d7d3`). |
| `refs/pr/119713` (h.git; head unchanged per gh, 2026-10-01T18:34Z) | `7471d9915d` | teknium1's trailing `ttfb=`; the parser must tolerate it | Clean vs main (tree `18821688bd`). Clean vs staging (tree `97793e195c`). **Conflicts with #121135** in `agent/turn_usage.py`, which is outside our files. |

Patch: `postmortem-logcalls-zero-hit.patch` (sha256 `3290c8c1…c844`).

## Invariant

Every reader of the per-call `API call #N` line counts a zero-hit call instead of dropping it, and reports `usage=unavailable` lines separately. A zero-hit call is one whose line has no `cache=`. When `cache_state=no_field` is present, that call stays out of the hit ratio.

Real call path exercised:
1. `agent.turn_usage.record_response_usage` (real AIAgent, no network) writes through `hermes_logging._LOG_FORMAT`.
2. `logcalls.parse_logs` / `logcalls.main` read that output, with `Run.open` on a synthetic `state.db`.
3. The live probes are not imported. Their exact `re.findall` literal is replayed on the same lines.

## Route and carrier choice

The defect is real on current main. `_LINE` in `logcalls.py:27-30` requires `cache=(\d+)/(\d+)`. `turn_usage.py` writes `cache=` only when `cache_read_tokens > 0` (around line 192), and its usage-less line is `in=? … usage=unavailable` (line 96). #121135 is the open carrier: it adds `cache_state=hit|miss|cold_write|no_field`, but `cache=` stays positive-only. Its own automated review flags "Blocker 1: the new state reaches no consumer", naming all three parsers this commit fixes.

Per D5 (eval-only changes never go upstream alone), the natural form is a fold-in on #121135 with a `Co-authored-by` trailer. #119713 is not a carrier. It only fixes a line shape the parser must accept, and the harness fixture plus the round trip on the #119713 arm cover it.

A/B line in WAVE.md row form, real producer lines matched:

| Arm | main parser | patched parser | Carrier tests + harness |
|---|---|---|---|
| main | 1/5 | 5/5 | 8 passed |
| main + #121135 | 1/5 | 5/5 | 126 passed |
| main + #119713 | 1/5 | 5/5 | 10 passed |

## Evidence

| Experiment | Receipt | Verdict | Label | n | Result |
|---|---|---|---|---|---|
| RED / GREEN / NEG / ADJ | `receipts/PROOF_r20261001-01.json` | KEEP | OBSERVED | 3 GREEN reps, 6 sabotage hunks | RED: 2 failed (`assert 2 == 3`, `assert (2 == 4)`). GREEN: 8/8 ×3. Sabotage: 6/6 RED again. Probe regexes RED offline. Adjacent: `test_turn_usage_log_line.py` 3/3. ruff clean. footguns `--all` clean. |
| Producer → parser round trip (closest $0 form of F06) | `receipts/F06RT_r20261001-01.json` | KEEP | OBSERVED | 5 lines × 3 arms | Old parser 1/5, new 5/5 on every arm. `upstream=` still parsed before trailing `cache_state=`/`ttfb=`. Probe regexes: old 1/4 rows (arm hit 40.0%), new 4/4 (10.0%, the true value). 0 egress attempts. |
| F06 on synthetic corpora | `receipts/F06SYN_r20261001-01.json` | KEEP | OBSERVED (parser) / MODELED (magnitudes) | 420 calls per corpus | E19-shaped corpus: coverage 94.2% → 100%; hit ratio 98.0% → 93.1%, exactly the corpus truth. The 24 dropped calls are exactly the zero-hit calls. All-hit corpus: `observed` and `modeled` blocks identical, which satisfies gate 3. |
| E19 baseline vs rerun, synthetic | `receipts/E19SYN_r20261001-01.json` | KEEP | OBSERVED (parser) / MODELED (magnitudes) | 1 switch, k=5 | Old parser never sees the switch's first call (#61, a full miss) and shows the post-switch hit ratio at 98.8%. New parser: 79.5%. |
| Carrier compatibility | `receipts/CARRIER_r20261001-01.json` | KEEP | OBSERVED | 6 merge pairs, 2 arms | Clean except #121135 × #119713 (their conflict). Carrier suites pass on the arms (126 and 10). |
| Round-1 re-measure on main `aea969677c` | `receipts/PROOF_r20261001-02.json` | KEEP | OBSERVED | 15 cells | 36 drift commits, 0 on relevant paths. merge-tree matrix on `aea969677c` as in `[merge_check].previous` (all clean except #121135 × #119713). RED 2 failed (same assertions). GREEN 8/8 ×3 on tree `f388caeb37`. Carrier arms again 126 and 10 passed. Early-exit guard unpinned: `if not scored` → `if not calls` stays 8/8 green, and on only-`no_field` input it raises `ZeroDivisionError` where the commit returns 1. A push of `staged/<id>` matches 0 workflows. Source lines behind the legacy-line disclosure are in `raw/r1/source_facts.txt`. |
| F14 standing guards, arm vs base | `receipts/F14-r20261001-01.json` | EQUAL | OBSERVED | 2 runs × 19 cells / 40 verdict ids | Arm `42b7748969` is `dd4dd10611` cherry-picked clean onto main `34f8ec3b40` (same patch-id). Both runs: 36 PASS / 4 FAIL, the same 4 FAIL as the base baseline (cache_estimator, notice_delivery, context_cap, readtool lying_extension). `compare` EQUAL vs baseline on both runs and r1 vs r2. 0 INFRA, 0 blocked exec, 0 flaky. Set `aba79fe8f09d`; runner, sandbox and helper hashes equal to the baseline. No F14 probe reaches the 4 changed files. |
| Round-3 freshness on upstream main `34f8ec3b40` | `receipts/PROOF_r20261001-03.json` | KEEP | OBSERVED | 11 cells | 74 commits since the base; among `invalidate_on` only the `usage_pricing.py` alias table changed. merge-tree: 5 of 6 pairs clean (main × staging tree `c7460b5c53`), the conflict is #121135 × #119713 again. In the bwrap sandbox: RED 2 failed (same assertions), GREEN 8/8 ×3 on tree `c7460b5c53`, ADJACENT `test_turn_usage_log_line.py` 3/3 on main and arm. 0 blocked exec. Carrier suites, round trip and synthetic F06/E19 not re-run (carried by the unchanged paths). |

Raw outputs are in `receipts/raw/` (round 1: `receipts/raw/r1/`, round 3: `receipts/raw/r3/`). The scripts that produced them are in `harness/`: `prove.sh`, `roundtrip.py`, `arms.sh`, `mt.sh`, `sibling_regex.py`, `f06_synth.py`, `e19_switch.py`, `mutate.py` and `mk_receipts.py`. Round 1 added `harness/r1/` (`mt_r1.sh`, `arms_r1.sh`, `wf_push.py`, `only_nofield.py`) and `harness/receipts_r1.py`. That script completed the r01 receipts to the FACTORY §9.2 shape and replaced absolute local paths in `receipts/` with placeholders (`$S`, `$W`, `<pytest-tmp>`, `$HERMES_PYTHON`). Round 3 added `harness/r3/mt_r3.sh` (merge-tree matrix and `invalidate_on` drift) and `harness/r3/receipts_r3.py` (host scrub, `inputs.scripts_published`, PROOF r03, INDEX). Six harness scripts ran with local paths inline (`mt.sh`, `prove.sh`, `arms.sh`, `r1/arms_r1.sh`, `mk_receipts.py`, `receipts_r1.py`). Their published copies now take the paths from the environment (`S`, `W`, `HERMES_PYTHON`) or carry `<placeholders>` (the two receipt generators). The as-run bytes are kept in `private/harness-as-run/` (`MANIFEST.sha256`); the receipts keep citing the as-run sha256 under `inputs` and list the published copies' sha256 under `inputs.scripts_published`. A rerun of `mk_receipts.py` would regenerate the r01 receipts without the round-1 and round-3 fields; run `harness/receipts_r1.py .` and `harness/r3/receipts_r3.py .` after it.

## Gate checklist (P1-P12)

- **P1 PASS.** RED on main `234badf401` (PROOF r01), again on `aea969677c` (PROOF r02), and again on upstream main `34f8ec3b40` in the sandbox (PROOF r03, 2026-10-01T18:37Z). The only `invalidate_on` change since the base is the `usage_pricing.py` alias table. The 24 h freshness rule applies at queue time, so re-check then.
- **P2 PENDING.** Upstream dedupe is clean: no other open PR changes these parsers, the claimant lanes and kvnloo/hermes-agent#69 / kvnloo/hermes-agent#70 are unrelated, and #121135 is treated as the carrier. The Hermes-lane PLAN could not be read under the isolation rules, so that check is undone.
- **P3 PASS.** One invariant, 4 files, +79/-18. No env vars, hooks or shims.
- **P4 PASS.** Real producer to real parser (F06RT). The live probes are NOT_TESTED end-to-end.
- **P5 PASS.** RED with the marker matched (`assert 2 == 3` / `assert (2 == 4)`), GREEN 3/3, per-hunk NEG 6/6, ADJ identical and `flaky = false` are recorded in PROOF r01 and re-run in r02. Three hunks are not pinned by any test, and both the receipt and the PR body list them: the early-exit guard, the coverage print line and the docstring. F14 guards are EQUAL to the base baseline on two runs (F14/r20261001-01). No F14 probe reaches the changed files, so F14 covers the code around the change, not the parser itself; the parser evidence is the PROOF receipts.
- **P6 N_A.** The body makes no claim about any real run. Synthetic numbers are labelled.
- **P7 PASS.** One commit on `234badf401` (not rebased; none of the 74 later commits touch its files). Author Kevin Rajan. merge-tree is clean vs the declared main `34f8ec3b40` and vs both carriers (PROOF r03; earlier PROOF r02, CARRIER). A push of `staged/postmortem-logcalls-zero-hit` matches 0 workflow push triggers. Push only with `--no-follow-tags`.
- **P8 PENDING.** Receipts are written with sha256 and carry the full xf.receipt.v1 field set. Round 3 scrubbed the host name from them and moved the six as-run harness scripts that held local paths to `private/harness-as-run/`, cited by sha256. `spec` is NOT_PREREGISTERED because the build predates Wave 0 and the ledger. The receipts are not frozen to z0evals.
- **P9 PENDING.** `PR_BODY.md` follows the template and has no @mentions. It discloses the legacy-line behaviour change and limits the test-coverage claim to the six pinned changes. Since round 3 the AI disclosure covers the code, the tests and the description, step 4 states that the probes count a `no_field` row as 0 cached (10.0%, versus 13.3% without it), and a mechanical jargon and privacy lint is clean. The owner runs the tone gate.
- **P10 PENDING.** The round-0 blind verifier on `dd4dd10611` returned CHANGES_REQUIRED for text only. The round-1 re-verify on the same head accepted it with 4 non-blocking advisories, all handled in round 3. That output records no APPROVE_EXACT_HEAD verdict or QA class, and the texts and receipts changed after it, so a fresh exact-head read is still needed.
- **P11 PENDING.** This is eval-only and must ride #121135 (fold-in). A standalone PR needs both #121135 merged without it and F06/E19 on real logs showing the bias (OD-7).
- **P12 PENDING.** Owner (staging cap, OD-8).
- **Global precondition:** Wave 0 (F15, F14, E48, F11) must pass before any PROMOTION_READY. F14 now has a base baseline and this item's arm run (EQUAL). This manifest does not record a Wave 0 pass, so no PROMOTION_READY is possible yet.

## Acceptance gates (from the selection)

| Gate | Status | Where |
|---|---|---|
| Harness self-test RED on main for the miss and unavailable lines, GREEN when patched | met | PROOF |
| Negative control: re-requiring `cache=` makes it fail again | met | PROOF, N1 |
| Hit ratio on an all-hit synthetic DB unchanged | met | F06SYN `all_hit`: `observed` and `modeled` blocks identical |
| F06 reports the coverage delta with an OBSERVED label | not met for real logs (needs OD-7). The synthetic closest form is done: parser behaviour OBSERVED, magnitudes MODELED. | F06SYN, F06RT |
| Fixtures confirm the parser accepts both the #121135 and #119713 line shapes | met | Harness test 2, plus real-producer round trip on both arms (F06RT) |
| Offered as a fold-in on #121135; standalone only if #121135 merges without it | pending (owner action) | Origin action below |

## Experiments queued

All need the owner. None was run by this worker.

**F06 (T0 priv, needs OD-7).** Coverage recount on real copies, old vs new parser. Results stay local (K1). Only aggregates with n ≥ 5 per bucket are published.
```bash
S=<scratch dir holding h.git>; X=<factory-xf-dir>
P=$X/private/F06/$(date +%Y%m%d); mkdir -p $P/logs
sqlite3 ~/.hermes/state.db ".backup '$P/state_copy.db'" && cp ~/.hermes/logs/agent.log* $P/logs/   # owner only; copies, never in place
git -C $S/h.git worktree add --detach $X/wt/f06-main main
git -C $S/h.git worktree add --detach $X/wt/f06-fix staging/postmortem-logcalls-zero-hit
for arm in main fix; do (cd $X/wt/f06-$arm && mkdir -p $P/home-$arm/.hermes && env -i PATH=/usr/bin:/bin HOME=$P/home-$arm HERMES_HOME=$P/home-$arm/.hermes \
  python3 -m evals.postmortem.forensics.logcalls --db $P/state_copy.db --logs "$P/logs/agent.log*" --out $P/out-$arm); done
# publish only: coverage.fraction, cache_hit_ratio_overall, zero_hit, usage_unavailable per arm (OBSERVED)
```

**E19 baseline vs rerun (T0 priv, after F06, needs OD-7).**
```bash
H=<xf-root>/staging/postmortem-logcalls-zero-hit/harness
for arm in main fix; do env -i PATH=/usr/bin:/bin PYTHONPATH=$X/wt/f06-$arm HOME=$P/home-$arm HERMES_HOME=$P/home-$arm/.hermes \
  python3 $H/e19_switch.py $X/wt/f06-$arm/evals/postmortem/forensics/logcalls.py $P/state_copy.db "$P/logs/agent.log*" 5 > $P/e19-$arm.json; done
git -C $S/h.git worktree remove --force $X/wt/f06-main; git -C $S/h.git worktree remove --force $X/wt/f06-fix
```

**F14 adjacent guard (T1, $0). Done:** the factory standing set ran on the arm, with result EQUAL (F14/r20261001-01, see Evidence). The command below is the older plan and is kept for reference only. HERMES_HOME must be explicit because `run.py:47` uses `setdefault`.
```bash
env -i PATH=/usr/bin:/bin HOME=$(mktemp -d -p <scratch-tmp>) HERMES_HOME=$(mktemp -d -p <scratch-tmp>) \
  /path/to/disposable-venv/bin/python -m evals.postmortem.run --repo $X/wt/f06-main --compare $X/wt/f06-fix
```

**T2 (local GPU).** None applies, because the parser path calls no model.

**T3 (paid, owner launches, cents).** End-to-end live probes on the branch. The probes default HERMES_HOME to `~/.hermes` and read `~/.hermes/logs/agent.log`, so this is owner-only.
```bash
cd <checkout at staging/postmortem-logcalls-zero-hit>
python evals/postmortem/live_ab/cache_prefix_live.py . A; python evals/postmortem/live_ab/cache_prefix_live.py . B
python evals/postmortem/live_ab/cache_prefix_wire.py . B
# parser A/B offline on the same captured lines: harness/sibling_regex.py (old vs new regex)
```

## NOT_TESTED

- Real `agent.log` / `state.db`. The bias on any real run is NOT_MEASURED (OD-7). The README's #102117 reference output (coverage 24.1%, hit 93.9%) was computed with the old regex and is PRIOR only.
- The live probes `cache_prefix_live.py` / `cache_prefix_wire.py` end-to-end: real provider, credentials, paid. Only their regex literals were replayed offline.
- A producer with both #121135 and #119713. The carriers conflict, so the combined shape is covered only by the harness fixture (MODELED shape).
- Usage shapes other than OpenAI-style `prompt_tokens_details` in the round trip. #121135's own suite covers its normalizer paths.
- CI: `evals/` is outside `testpaths`, so the harness tests never run in CI. The `tests/agent/test_turn_usage_log_line.py` parser test does run in CI and still passes.
- Legacy lines (before #121135) cannot tell a reported zero from a route that reports no cache counter, because neither has `cache=`. In F06RT `raw/rt_main.json`, the miss line and the no-field line are identical apart from the call number and `id=`. On such routes every call now counts as zero-hit and pulls `cache_hit_ratio_overall` down; before, those calls were invisible. Source on main `aea969677c` (`raw/r1/source_facts.txt`) shows two ways this happens:
  - `normalize_usage` reads an absent usage field as 0. Any OpenAI-compatible endpoint that leaves out `prompt_tokens_details` is affected, for example a local server that sends no cache counter.
  - The Bedrock and native Gemini adapters write an absent cache count as an explicit 0. #121135's automated review covers this under Blocker 2.

  The new `logcalls.py` docstring states the rule: a line without `cache=` is a zero-hit call, and `cache_state=no_field` stays out of the ratio. It does **not** say that legacy lines cannot separate the two cases, or that such routes read as 0% hit. As of round 1, `PR_BODY.md` discloses this ("One behaviour change") and offers to add a docstring sentence. Separating the two needs #121135, and for Bedrock and Gemini also the adapter change that review suggests. The size of the effect on a real run is NOT_MEASURED (OD-7).

## Next steps

1. Owner: decide the form. Default: the fold-in comment on #121135 below.
2. Owner: OD-7. Then run the queued F06 and E19 on copies, and attach only the aggregates.
3. Factory: a fresh blind read of the exact head `dd4dd10611` against the round-3 manifest, body and receipts, returning APPROVE_EXACT_HEAD and a QA class (P10). Wave 0 must pass before any PROMOTION_READY.
4. Re-check freshness within 24 h of any origin action: refresh main, run `bash harness/r3/mt_r3.sh <h.git> <new main sha>` (merge-tree matrix plus `invalidate_on` drift), and if any `invalidate_on` path changed, re-run RED/GREEN as in PROOF r03 (`receipts/PROOF_r20261001-03.json` `command`).
5. Later commits, separate from this slice and per the selection:
   - `evals/postmortem/run.py:47`: always use a fresh temp HERMES_HOME, never `env.setdefault`.
   - `run.py:41`: give `cache_prefix_wire` a non-empty pass marker. `''` passes vacuously.
   - The live probes' `~/.hermes` defaults. These are eval-only and ride with a real fix (D5).
6. OD-0 is resolved: the fork name is `staged/postmortem-logcalls-zero-hit`. The owner pushes it, with `--no-follow-tags`, when acting on the origin action. Until then the ref stays local in h.git.

## Origin action (owner only)

The smallest ask is one comment on #121135. Draft:

> The parser side of the "no consumer" point above: `evals/postmortem/forensics/logcalls.py` and the two `live_ab/cache_prefix_*` probes require `cache=`, so miss / cold_write / no_field lines are dropped. A 4-file patch makes `cache=` optional, reports `usage=unavailable` separately, and keeps `cache_state=no_field` out of the hit ratio. It also accepts the trailing `ttfb=` from #119713. It merges cleanly on this branch. With it applied, your `test_cache_log_states.py` plus `test_turn_usage_log_line.py` and the harness give 126 passed. One side effect: on lines without `cache_state=`, a route that reports no cache counter now reads as zero-hit instead of being dropped. With `cache_state=no_field` it stays out of the ratio. Happy for you to fold it in (with a Co-authored-by) if it's useful: https://github.com/kvnloo/hermes-agent/commit/dd4dd10611e8c23c7579a4ddb95655abebbaca27 (branch `staged/postmortem-logcalls-zero-hit` on kvnloo/hermes-agent). The patch and this comment were written with Claude Code (AI assistance).

The link resolves once the owner pushes `staged/postmortem-logcalls-zero-hit` (with `--no-follow-tags`). The 126-passed count was observed on `aea969677c` × #121135 + this commit (PROOF r02); on `34f8ec3b40` only the merges were re-checked (PROOF r03).

Fallback, only if #121135 merges without it **and** the queued F06/E19 on real logs show the bias (OD-7; an eval-only change cannot go upstream alone, P11/D5). NOT run by the factory:
`gh pr create -R NousResearch/hermes-agent --head kvnloo:staged/postmortem-logcalls-zero-hit --base main --title "fix(evals): postmortem log parsers count zero-hit and usage-unavailable calls" --body-file PR_BODY.md`

## History

| Timestamp | Status | Worker | Reason |
|---|---|---|---|
| 2026-10-01T08:40Z | CANDIDATE | builder (Claude Code, Opus 5.5) | Selection entry read. Defect re-verified on main `572e4f4fad`. |
| 2026-10-01T08:55Z | EVIDENCED | builder | RED/GREEN/NEG on `391af8cd81`. Sibling regexes in the live probes added after reading the #121135 review (`c4d0b37465`). utf-8-sig footgun fix (`1cab2898b5`). |
| 2026-10-01T09:10Z | STAGED | builder | Rebased to main `234badf401` as `dd4dd10611`. Full proof, round trips, carriers, F06/E19 synthetic re-run. Local branch created. Worktree removed. |
| 2026-10-01T11:20Z | STAGED | round-1 fixer (Claude Code, Opus 5.5) | Phase-3 verifier round 0 returned CHANGES_REQUIRED, text only. Fixes: (1) PR_BODY.md now discloses the legacy-line behaviour change, where routes with no cache counter read as zero-hit; (2) the NOT_TESTED docstring claim is corrected; (3) How-to-Test step 2 is limited to the six pinned changes and names the unpinned early-exit guard; (4) the harness is cited as #103756 (tracking issue #103563); (5) the r01 receipts are completed to xf.receipt.v1, absolute paths are redacted, and the sha256 values are updated. Re-measured on main `aea969677c` (PROOF/r20261001-02). OD-0 is resolved by the fork name `staged/<id>`. Commit unchanged at `dd4dd10611`. Form unchanged: eval-contribution, fold-in first. |
| 2026-10-01T18:28Z | STAGED | Wave 0 F14 worker (Claude Code, Opus 5.5) | F14 guard comparison. `dd4dd10611` was cherry-picked clean onto main `34f8ec3b40` as `42b7748969` (same patch-id, author kept), ref `refs/xf/w0/postmortem-logcalls-zero-hit`. Two F14 runs (19 cells, 40 verdict ids each) were both EQUAL to the base baseline and to each other: 36 PASS and the same 4 FAIL as base, 0 INFRA, 0 flaky (F14/r20261001-01). `guards.F14 = EQUAL`, and P5 PENDING → PASS, because every other P5 part was already recorded in PROOF r01/r02. Informational: no F14 probe reaches the changed files. Between the proof main `aea969677c` and `34f8ec3b40` (38 commits), only `agent/usage_pricing.py` changed among the `[base]` paths, and only in the model alias table, not `normalize_usage`; P1 and declared main are unchanged. The absolute paths in the queued F06/E19/F14 commands were replaced with placeholders. Commit, branch and status unchanged; worktree removed; nothing pushed. |
| 2026-10-01T18:50Z | STAGED | round-3 polish (Claude Code, Opus 5.5) | Handled the 4 non-blocking advisories of the round-1 re-verify (phase3_fix_results.json, accept). (1) Privacy: the six harness scripts that held local paths (`mt.sh`, `prove.sh`, `arms.sh`, `r1/arms_r1.sh`, `mk_receipts.py`, `receipts_r1.py`) now take them from the environment or carry `<placeholders>`; the as-run bytes are in `private/harness-as-run/`. The host name was scrubbed from the six r01/r02 receipts, which now also list the published scripts' sha256 (`harness/r3/receipts_r3.py`); their hashes changed, measurements did not; superseded bytes are in `private/superseded-receipts-r2/`. (2) The fallback `gh pr create` line, the promotion-form line and the route comment now carry the OD-7 precondition. (3) PR_BODY.md step 4 states that the probes count a `no_field` row as 0 cached (10.0%, versus 13.3% without it). (4) Declared main moved to upstream `34f8ec3b40`: merge-tree clean (tree `c7460b5c53`), only the `usage_pricing.py` alias table changed among `invalidate_on`, and RED / GREEN 3/3 / ADJACENT re-run in the bwrap sandbox (PROOF/r20261001-03). Also: the PR body's AI disclosure now says Claude Code wrote the code, tests and description and ran the checks, and its freshness sentence names `34f8ec3b40`; the fold-in draft got its commit link and an AI disclosure; `[verification]` and P10 record the round-1 accept. The commit message was re-read and left unchanged, so no `-v2` ref was created. Commit `dd4dd10611`, branch and status unchanged; worktree removed and pruned; nothing pushed. |
