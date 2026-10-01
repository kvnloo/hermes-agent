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
status = "STAGED"        # commit + self-evidence done; round-0 verifier: CHANGES_REQUIRED (text only), fixed in round 1, re-verify pending; P11 needs OD-7 or the #121135 fold-in route
route = "eval-fix"       # offered first as a ride-along fold-in on #121135 (D5); standalone only if #121135 merges without it
feature = "postmortem-logcalls-zero-hit-fix"
invariant = "Every reader of the per-call 'API call #N' log line counts a call whose line has no cache= (a zero-hit call) and accounts for usage=unavailable lines separately, instead of silently dropping them."

[base]
repo = "NousResearch/hermes-agent"
sha = "234badf4012af380d23c91eae55d045a69c69ffb"
fetched_at = "2026-10-01T08:51Z (main @ 2026-10-01 03:50:55 -0500)"
first_built_on = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0 (rebased to 234badf401; the 11 intervening commits touch none of evals/postmortem, agent/turn_usage.py, agent/usage_pricing.py, hermes_logging.py, tests/agent/test_turn_usage_log_line.py)"
declared_main = "aea969677c60a1bb72fe227fdfb98f196a2092cc"   # round 1: fetched 2026-10-01T11:04Z (commit date 10:56:05Z); commit stays on 234badf401
declared_main_drift = "36 commits 234badf401..aea969677c; 0 touch evals/postmortem, agent/turn_usage.py, agent/usage_pricing.py, hermes_logging.py, tests/agent/test_turn_usage_log_line.py or .github/workflows (PROOF/r20261001-02)"

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
open_external = [121135, 119713]
merged_overlap = ["NousResearch/hermes-agent#103756 (teknium1, harness, merged 2026-09-06)", "NousResearch/hermes-agent#104568 (teknium1, write=/id=/upstream=, merged 2026-09-06)"]
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # all TUI/HUD perf; no overlap (gh, 2026-10-01)
hard_hold = [69, 70]                                         # kvnloo/hermes-agent#69 and kvnloo/hermes-agent#70 (state-db docs/doctor); no overlap
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]   # none apply
hermes_lane_overlap = "NOT CHECKED: the Hermes-lane PLAN lives under ~/.hermes/profiles/..., which this worker may not read"
verdict = "EXTERNAL carrier (#121135) -> fold-in/support first; no one else changes these parsers"

excluded_paths = []

[evidence]
receipts = [   # round 1: r01 receipts completed to xf.receipt.v1 + absolute paths redacted (harness/receipts_r1.py), so their sha256 changed
  { id = "PROOF/r20261001-01",  path = "receipts/PROOF_r20261001-01.json",  sha256 = "54d97f8e9036335f577fb4b7b1b36b09dfcf2ce4cca4a019c7ead07d24562116" },
  { id = "F06RT/r20261001-01",  path = "receipts/F06RT_r20261001-01.json",  sha256 = "405b09859f9d0416205052a52d8ba5594a35eb09d01ee4fc1948b5c181a7e714" },
  { id = "F06SYN/r20261001-01", path = "receipts/F06SYN_r20261001-01.json", sha256 = "caf296a4d5ffd738925a634d6c6618f6039e5b0dfc142d73452aa1bbaaf2a684" },
  { id = "E19SYN/r20261001-01", path = "receipts/E19SYN_r20261001-01.json", sha256 = "40c53149e6a83d20b41da91c4650bb0a992cabc1b32bf72af4dc2cd8375578c1" },
  { id = "CARRIER/r20261001-01", path = "receipts/CARRIER_r20261001-01.json", sha256 = "c653b35e41ea90343a9fc89acfd9979cb7cf521e997183f62dc8f2671896d851" },
  { id = "PROOF/r20261001-02",  path = "receipts/PROOF_r20261001-02.json",  sha256 = "aa48e790d70c443e3659ac7d7d3b33f4edfadba593ccb447f3ce21e4e561bace" },
]
red = { test = "evals/postmortem/tests/test_postmortem_harness.py::test_logcalls_counts_zero_hit_and_usage_unavailable_calls + ::test_logcalls_reads_cache_state_and_tolerates_trailing_fields", main = "234badf401; re-run on aea969677c", marker = "assert 2 == 3 / assert (2 == 4) on coverage.calls_found", receipt = "PROOF/r20261001-01, PROOF/r20261001-02" }
green = { reps = "3/3 (8 passed: harness 5 + tests/agent/test_turn_usage_log_line.py 3) on the head; 3/3 again on main aea969677c + head (tree f388caeb37)", receipt = "PROOF/r20261001-01, PROOF/r20261001-02" }
negative_control = { mutation = "per-hunk, 6 logcalls hunks -> 6/6 RED again; probe regex hunks RED offline (1/4 rows). Unpinned: early-exit guard (`if not scored` -> `if not calls` stays GREEN; ZeroDivisionError on only-no_field input), coverage print line, docstring", result = "RED (6 pinned hunks)", receipt = "PROOF/r20261001-01, PROOF/r20261001-02" }
adjacent = { identical = true, pre_existing = [], files = ["tests/agent/test_turn_usage_log_line.py", "evals/postmortem/tests/test_postmortem_harness.py"] }
guards = { F14 = "NOT RUN (factory standing set not built)" }
quantitative = []                  # no real-run numbers; synthetic numbers are MODELED and not claimed
cache_read_ratio = { status = "N_A" }
route_scope = "n/a"
not_tested = ["real agent.log / state.db (OD-7)", "live probes end-to-end (paid, owner-launched)", "combined #121135+#119713 producer (carriers conflict)", "CI (evals/ outside testpaths)", "real-run size of the legacy-line behaviour change (routes with no cache counter now read as zero-hit; disclosed in PR_BODY.md)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-postmortem-logcalls-zero-hit", commit = "" }

[gates]
P1 = "PASS"       # RED on main 234badf401, re-run RED on aea969677c (2026-10-01)
P2 = "PENDING"    # upstream dedupe PASS; Hermes-lane PLAN overlap not checkable by this worker
P3 = "PASS"       # one invariant, 4 files (+79/-18), no env vars, no hooks
P4 = "PASS"       # real record_response_usage + real agent.log formatter -> parser; live probes NOT_TESTED
P5 = "PENDING"    # RED/GREEN 3/3/NEG 6/6/ADJ PASS; 3 unpinned hunks named (early-exit guard, print line, docstring); F14 guards not built
P6 = "N_A"        # body makes no real-run value claim
P7 = "PASS"       # one commit on 234badf401, author ok; merge-tree clean vs declared main aea969677c (f388caeb37), #121135, #119713; a push of staged/<id> matches 0 workflows
P8 = "PENDING"    # receipts local + sha256, full xf.receipt.v1 shape (spec NOT_PREREGISTERED, pre-Wave-0); not frozen to z0evals
P9 = "PENDING"    # PR_BODY.md: AI disclosed, no @mentions, legacy-line behaviour change disclosed, test-coverage claim narrowed; tone gate + jargon lint by owner
P10 = "PENDING"   # round-0 blind verifier on dd4dd10611: CHANGES_REQUIRED, text only (code/merge/proof/privacy/policy passed); round-1 text fixes applied; re-verify pending
P11 = "PENDING"   # eval-only: must ride #121135 (fold-in) or show real-log bias via F06/E19 (OD-7)
P12 = "PENDING"   # staging cap / promotion_freeze: owner

[verification]
verifier = "phase-3 blind verifier, round 0 (frontier-2026-10-01/phase3_results.json verdicts[id])"
provenance = "independent"
exact_head = "dd4dd10611e8c23c7579a4ddb95655abebbaca27"
inputs = "raw diff + repo + oracle block only"
verdict = "CHANGES_REQUIRED"       # round 0: manifest/PR-body text only; fixed in round 1 without changing the commit; needs a re-verify
qa_class = ""

[merge_check]
main_sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
checked_at = "2026-10-01T11:05Z"
clean = true
tree = "f388caeb37c573dcd1dfb1211526f32b0c7abdc6"
recheck = "git merge-tree --write-tree main staging/postmortem-logcalls-zero-hit"
also = ["#121135 x staging: CLEAN tree 2e7d28d7d3", "#119713 x staging: CLEAN tree 97793e195c", "main x #121135: CLEAN tree 798e76b64d", "main x #119713: CLEAN tree 1f2049ee49", "#121135 x #119713: CONFLICT agent/turn_usage.py (theirs, not ours)"]
previous = "2026-10-01T09:10Z on 234badf401: CLEAN tree 9f262517dd"
post_check = "informational, not the declared main: h.git main moved to e8c97320ac (another worker's fetch, observed at round-1 close): +6 commits, merge-tree CLEAN tree 5335078cd2; 2 of the 6 touch agent/usage_pricing.py, but only the model-pricing alias table at line ~340, not normalize_usage (its lines shift by -1)"

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
jargon_lint = "PENDING"
privacy_scan = "PENDING (body has no paths, session ids or emails by construction; owner to confirm)"

[queue]
board = "kvnloo/hermes-agent#404"   # staged-PR queue: 39 rows as of 2026-10-01T11:05Z, none for this id
position = "after existing rows"
slot_claimed = false
waves = "not part of NousResearch/hermes-agent#130139 (salvage wave, was kvnloo/hermes-agent#402) or NousResearch/hermes-agent#130140 (close wave, was kvnloo/hermes-agent#403)"

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# staging/postmortem-logcalls-zero-hit

**Promotion form:** eval-contribution. It goes first as a fold-in offered on NousResearch/hermes-agent#121135, and becomes a standalone PR only if #121135 merges without it.

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

Declared main for round 1: `aea969677c`, fetched 2026-10-01T11:04Z. The commit stays on `234badf401`. None of the 36 commits in between touch the files listed in `[base]`.

| Ref | SHA | Role | Merge status on main `aea969677c` (PROOF/r20261001-02) |
|---|---|---|---|
| `staging/postmortem-logcalls-zero-hit` (local, h.git; fork name `staged/postmortem-logcalls-zero-hit`) | `dd4dd10611` | Our one commit: logcalls parser, both live-probe regexes, 2 harness tests | Parent `234badf401`. merge-tree clean vs `aea969677c` (tree `f388caeb37`). |
| `refs/pr/121135` (h.git; head unchanged per gh, 2026-10-01T11:05Z) | `dd4a0ca4cf` | Carrier (Wenfengcheng): `cache_state=` / `cache_read=` / `cache_write=` on the log line | Clean vs main (tree `798e76b64d`). Clean vs staging (tree `2e7d28d7d3`). |
| `refs/pr/119713` (h.git; head unchanged per gh) | `7471d9915d` | teknium1's trailing `ttfb=`; the parser must tolerate it | Clean vs main (tree `1f2049ee49`). Clean vs staging (tree `97793e195c`). **Conflicts with #121135** in `agent/turn_usage.py`, which is outside our files. |

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
| Round-1 re-measure on main `aea969677c` | `receipts/PROOF_r20261001-02.json` | KEEP | OBSERVED | 15 cells | 36 drift commits, 0 on relevant paths. merge-tree matrix as in the table above. RED 2 failed (same assertions). GREEN 8/8 ×3 on tree `f388caeb37`. Carrier arms again 126 and 10 passed. Early-exit guard unpinned: `if not scored` → `if not calls` stays 8/8 green, and on only-`no_field` input it raises `ZeroDivisionError` where the commit returns 1. A push of `staged/<id>` matches 0 workflows. Source lines behind the legacy-line disclosure are in `raw/r1/source_facts.txt`. |

Raw outputs are in `receipts/raw/` (round 1: `receipts/raw/r1/`). The scripts that produced them are in `harness/`: `prove.sh`, `roundtrip.py`, `arms.sh`, `mt.sh`, `sibling_regex.py`, `f06_synth.py`, `e19_switch.py`, `mutate.py` and `mk_receipts.py`. Round 1 added `harness/r1/` (`mt_r1.sh`, `arms_r1.sh`, `wf_push.py`, `only_nofield.py`) and `harness/receipts_r1.py`. That script completed the r01 receipts to the FACTORY §9.2 shape and replaced absolute local paths in `receipts/` with placeholders (`$S`, `$W`, `<pytest-tmp>`, `$HERMES_PYTHON`). The harness scripts still reference scratch paths, so re-point `S=` and `W=` before re-running. A rerun of `mk_receipts.py` would regenerate the r01 receipts without the round-1 fields; run `harness/receipts_r1.py .` after it.

## Gate checklist (P1-P12)

- **P1 PASS.** RED on main `234badf401` (PROOF r01), and again on `aea969677c` (PROOF r02).
- **P2 PENDING.** Upstream dedupe is clean: no other open PR changes these parsers, the claimant lanes and kvnloo/hermes-agent#69 / kvnloo/hermes-agent#70 are unrelated, and #121135 is treated as the carrier. The Hermes-lane PLAN could not be read under the isolation rules, so that check is undone.
- **P3 PASS.** One invariant, 4 files, +79/-18. No env vars, hooks or shims.
- **P4 PASS.** Real producer to real parser (F06RT). The live probes are NOT_TESTED end-to-end.
- **P5 PENDING.** RED, GREEN 3/3, per-hunk NEG 6/6 and ADJ are done (PROOF r01, re-run in r02). Three hunks are not pinned by any test, and the PR body now says so: the early-exit guard, the coverage print line and the docstring. The F14 standing guards are not built.
- **P6 N_A.** The body makes no claim about any real run. Synthetic numbers are labelled.
- **P7 PASS.** One commit on `234badf401`. Author Kevin Rajan. merge-tree is clean vs the declared main `aea969677c` and vs both carriers (PROOF r02, CARRIER). A push of `staged/postmortem-logcalls-zero-hit` matches 0 workflow push triggers. Push only with `--no-follow-tags`.
- **P8 PENDING.** Receipts are written with sha256 and now carry the full xf.receipt.v1 field set. `spec` is NOT_PREREGISTERED because the build predates Wave 0 and the ledger. The receipts are not frozen to z0evals.
- **P9 PENDING.** `PR_BODY.md` follows the template, discloses AI use and has no @mentions. Since round 1 it also discloses the legacy-line behaviour change and limits the test-coverage claim to the six pinned changes. The owner runs the tone gate and jargon lint.
- **P10 PENDING.** The round-0 blind verifier on `dd4dd10611` returned CHANGES_REQUIRED for text only. The code, merge, proof, privacy and policy checks passed. Round 1 fixed the text without changing the commit, and a re-verify is pending.
- **P11 PENDING.** This is eval-only and must ride #121135 (fold-in). A standalone PR needs F06/E19 on real logs (OD-7).
- **P12 PENDING.** Owner (staging cap, OD-8).
- **Global precondition:** Wave 0 (F15, F14, E48, F11) has not run, so no PROMOTION_READY is possible yet.

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
S=<scratch dir holding h.git>; X=$ARTIFACTS/factory/xf
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
H=$ARTIFACTS/frontier-2026-10-01/staging/postmortem-logcalls-zero-hit/harness
for arm in main fix; do env -i PATH=/usr/bin:/bin PYTHONPATH=$X/wt/f06-$arm HOME=$P/home-$arm HERMES_HOME=$P/home-$arm/.hermes \
  python3 $H/e19_switch.py $X/wt/f06-$arm/evals/postmortem/forensics/logcalls.py $P/state_copy.db "$P/logs/agent.log*" 5 > $P/e19-$arm.json; done
git -C $S/h.git worktree remove --force $X/wt/f06-main; git -C $S/h.git worktree remove --force $X/wt/f06-fix
```

**F14 adjacent guard (T1, $0, runs once Wave 0 exists).** The postmortem offline probes, main vs staging. HERMES_HOME must be explicit because `run.py:47` uses `setdefault`.
```bash
env -i PATH=/usr/bin:/bin HOME=$(mktemp -d -p <models-disk>/tmp) HERMES_HOME=$(mktemp -d -p <models-disk>/tmp) \
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
3. Factory: re-run the blind verifier on the exact head `dd4dd10611` against the round-1 manifest, body and receipts (P10). Wave 0 must run before any PROMOTION_READY.
4. Re-check freshness within 24 h of any origin action: refresh main, run `git merge-tree --write-tree main staging/postmortem-logcalls-zero-hit`, and re-run `harness/prove.sh` (or `harness/r1/mt_r1.sh` with the new main SHA).
5. Later commits, separate from this slice and per the selection:
   - `evals/postmortem/run.py:47`: always use a fresh temp HERMES_HOME, never `env.setdefault`.
   - `run.py:41`: give `cache_prefix_wire` a non-empty pass marker. `''` passes vacuously.
   - The live probes' `~/.hermes` defaults. These are eval-only and ride with a real fix (D5).
6. OD-0 is resolved: the fork name is `staged/postmortem-logcalls-zero-hit`. The owner pushes it, with `--no-follow-tags`, when acting on the origin action. Until then the ref stays local in h.git.

## Origin action (owner only)

The smallest ask is one comment on #121135. Draft:

> The parser side of the "no consumer" point above: `evals/postmortem/forensics/logcalls.py` and the two `live_ab/cache_prefix_*` probes require `cache=`, so miss / cold_write / no_field lines are dropped. A 4-file patch makes `cache=` optional, reports `usage=unavailable` separately, and keeps `cache_state=no_field` out of the hit ratio. It also accepts the trailing `ttfb=` from #119713. It merges cleanly on this branch. With it applied, your `test_cache_log_states.py` plus `test_turn_usage_log_line.py` and the harness give 126 passed. One side effect: on lines without `cache_state=`, a route that reports no cache counter now reads as zero-hit instead of being dropped. With `cache_state=no_field` it stays out of the ratio. Happy for you to fold it in (with a Co-authored-by) if it's useful: <link to kvnloo/hermes-agent branch staged/postmortem-logcalls-zero-hit>.

Fallback, only if #121135 merges without it. NOT run by the factory:
`gh pr create -R NousResearch/hermes-agent --head kvnloo:staged/postmortem-logcalls-zero-hit --base main --title "fix(evals): postmortem log parsers count zero-hit and usage-unavailable calls" --body-file PR_BODY.md`

## History

| Timestamp | Status | Worker | Reason |
|---|---|---|---|
| 2026-10-01T08:40Z | CANDIDATE | builder (Claude Code, Opus 5.5) | Selection entry read. Defect re-verified on main `572e4f4fad`. |
| 2026-10-01T08:55Z | EVIDENCED | builder | RED/GREEN/NEG on `391af8cd81`. Sibling regexes in the live probes added after reading the #121135 review (`c4d0b37465`). utf-8-sig footgun fix (`1cab2898b5`). |
| 2026-10-01T09:10Z | STAGED | builder | Rebased to main `234badf401` as `dd4dd10611`. Full proof, round trips, carriers, F06/E19 synthetic re-run. Local branch created. Worktree removed. |
| 2026-10-01T11:20Z | STAGED | round-1 fixer (Claude Code, Opus 5.5) | Phase-3 verifier round 0 returned CHANGES_REQUIRED, text only. Fixes: (1) PR_BODY.md now discloses the legacy-line behaviour change, where routes with no cache counter read as zero-hit; (2) the NOT_TESTED docstring claim is corrected; (3) How-to-Test step 2 is limited to the six pinned changes and names the unpinned early-exit guard; (4) the harness is cited as #103756 (tracking issue #103563); (5) the r01 receipts are completed to xf.receipt.v1, absolute paths are redacted, and the sha256 values are updated. Re-measured on main `aea969677c` (PROOF/r20261001-02). OD-0 is resolved by the fork name `staged/<id>`. Commit unchanged at `dd4dd10611`. Form unchanged: eval-contribution, fold-in first. |
