+++
xf_staging = 1
id = "compaction-anchor-retention"
title = "Extend the compaction anchor index to the identifier classes the recall exam loses"
version = 1
branch = "staging/compaction-anchor-retention"
branch_physical = "local-only in scratch h.git (OD-0 pending: fork refs/heads/staging blocks staging/<id>; fallback frontier/<slug>)"
branch_sha = "6e0fa629a0f6227b03417d1d6ff7f7d81208346a"
status = "STAGED"          # ceiling at $0: LIMITED (exam gates need OD-1 or OD-3)
route = "core-leaf"        # promotion_form = core-pr; coordinate with NousResearch/hermes-agent#117462 (same function, different classes)
feature = "compaction-identifier-anchor-retention"
invariant = "When an identifier of the classes 'delegation/kanban task id', 'dotted config key' or 'CLI error line' appears in the compacted region, the lean anchor index carries it verbatim, inside per-class caps and the unchanged 7,000-char budget, without changing any existing section's line."

[base]
repo = "NousResearch/hermes-agent"
sha = "234badf4012af380d23c91eae55d045a69c69ffb"
first_built_on = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0"   # rebased by cherry-pick; the 11 commits between touch no relevant file
fetched_at = "2026-10-01T04:13-05:00"

[upstream]
issues = [
  "NousResearch/hermes-agent#116246 (teknium1, merged: adds evals/compaction/results/SCORECARD-2026-09-19-jev.md, which names this target)",
  "NousResearch/hermes-agent#87326 (teknium1, merged 2026-08-16: lean tail + recall exam harness)",
  "c4bbb14e52 (teknium1, 2026-08-15: mechanical anchor index + region-scoping tripwire)",
  "NousResearch/hermes-agent#122274 (teknium1, open: summary_source=original; different mechanism)",
  "NousResearch/hermes-agent#78457 (akivavh, open: user-demand signal, r=1)",
]
eval_prs = []
carrier = { pr = 0, author = "", head = "" }   # own leaf; no external carrier for these classes
competitors = [
  { pr = 117462, author = "Seldash", head = "2c19948e15d68492d048250bae7707ca77063db5", result = "complementary: our tests RED on it, 3/5 of its tests RED on us, both GREEN on the fold-in", note = "same function and table: harvest tool-call args, cheap-first order, per-section truncation, session/todo ids, path extensions" },
]
adjacent = [
  { pr = 122522, author = "Nagisa-3000", head = "f596584b017694bf123d746a87740f58a2db15c1", role = "adjacent carrier (opt-in summary_source=original); coordinate, not a member", merge_tree_vs_main = "clean", merge_tree_vs_branch = "clean" },
  { pr = 109980, author = "Finn763", head = "82cb05f119a66d5cbe53dde8a5cc064ba2a9139a", role = "handoff block re-derivation; reads _LEAN_ANCHOR_HEADING, does not touch the table", merge_tree_vs_main = "CONFLICT (its own drift)" },
]
close_after = []
demand = { score = 0, source = "user demand thin (#78457 r=1); maintainer signal strong" }
maintainer_signal = "SCORECARD-2026-09-19-jev.md: 'the facts our summary loses (delegation ids, root causes, config keys, exact error strings) sat in assistant text. That is a summariser-retention target (anchor index / identifier capture)'"

[[donors]]
sha = "6e0fa629a0f6227b03417d1d6ff7f7d81208346a"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "leaf commit (rows + tests); no third-party code reused, so no Co-authored-by"

[[members]]
ref = "refs/heads/staging/compaction-anchor-retention"
sha = "6e0fa629a0"
role = "the staging commit (core-pr head candidate)"
rebase = "on 234badf401; merge-tree clean vs main"

[[members]]
ref = "refs/pr/117462"
sha = "2c19948e15"
role = "coordination carrier (Seldash) on the same function; fold-in patch foldin-on-117462.patch applies to its head (offset -105)"
rebase = "merge-tree clean vs main 234badf401; CONFLICT vs our branch (both edit the table)"

[[members]]
ref = "refs/pr/122522"
sha = "f596584b01"
role = "adjacent carrier (Nagisa-3000, opt-in summary_source=original); coordinate, not a member"
rebase = "merge-tree clean vs main 234badf401 and vs our branch"

[ownership]
searched_at = "2026-10-01T04:20-05:00"
queries = ["_ANCHOR_PATTERNS", "anchor index", "_build_anchor_index", "anchor_index", "anchor ledger", "identifier capture compaction", "compaction identifier", "summary_source"]
open_external = [117462]
merged_overlap = []
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # all TUI/HUD perf; no overlap
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found; staging/compressor-media-extraction (sibling worker) must not move context_compressor.py lines ~1040-1110 concurrently"
verdict = "OWN LEAF, coordinate with #117462 (complementary, not duplicate)"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
receipts = [
  { id = "RG01/r20261001-01", path = "receipts/RG01-redgreen.json", sha256 = "540a06d0f2d88658d45b1a49894ded53bfee7dcf99edcd97e59dc19e0d173135" },
  { id = "E03p/r20261001-01", path = "receipts/E03p-gold-reachability.json", sha256 = "2651baed2a425204a0818f6d033725b0f6ac78fa8c7ea0de306d7841f0eb9f08" },
  { id = "E03s/r20261001-01", path = "receipts/E03s-synthetic-survival.json", sha256 = "b6286c0f1f4c0b27ffaebde76f4b67a5cf9120932cfb1fa468d183945c911781" },
  { id = "F02s/r20261001-01", path = "receipts/F02s-budget-audit.json", sha256 = "ee4770c761c13233cb5a1226df3fd8d69253715d059656adbae93cfdb00631fc" },
  { id = "N01/r20261001-01", path = "receipts/N01-noise-audit.json", sha256 = "09bf76d8b9ce744d2b18ab0939cb4867cee7e9804ea879d038a7201a7bcba296" },
  { id = "AB117462/r20261001-01", path = "receipts/AB117462-carrier-compat.json", sha256 = "e36bf4511dc4d30a873ec0ebd02ebdfa8f2eefd1a94273e44bd79a7f2d263f98" },
]
patches = [
  { path = "compaction-anchor-retention.patch", sha256 = "26f8485aa9c538a2f7c8ca64b6903f711ca428b932e97b6a9ff902773f9ac5a8" },
  { path = "foldin-on-117462.patch", sha256 = "2b32d18636cb60f86c54bbc1c31f42ae062df48e13876edc34a01ae5b33c0224" },
]
red = { test = "tests/agent/test_context_compressor_anchor_index.py", main = "234badf401", marker = "AssertionError: 'sa-2-7318d0ba' missing from anchor index", receipt = "RG01/r20261001-01" }
green = { reps = "3/3", receipt = "RG01/r20261001-01" }
negative_control = { mutation = "drop each new row (3/3 re-RED) + dotted-keys precision sabotage (re-RED)", result = "RED", receipt = "RG01/r20261001-01" }
adjacent = { identical = true, base = "365 passed (6 files)", head = "367 passed (7 files)", pre_existing = [] }
guards = { region_scoping = "ALL PASS base and head", replay_gates = "11/11 PASS base and head, result dicts equal" }
quantitative = []                  # no OBSERVED recall number exists yet
cache_read_ratio = { status = "N_A", why = "summary text changes only at a compaction event (already a cache break); cadence unchanged" }
route_scope = "local-compressor (lean tail mode); native compaction summaries are opaque"
not_tested = ["recall exam (E05/E04): aux LLM needed", "real lineages / state.db copies (forbidden in this run; OD-7)", "native compaction routes", "legacy tail mode (index not built there)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-compaction-anchor-retention", commit = "" }

[gates]
P1 = "PASS"       # RED on 234badf401 (2026-10-01)
P2 = "PASS"       # #117462 complementary (AB117462); claimant lanes clear
P3 = "PASS"       # +5 prod lines, one test file, no env/config/hook
P4 = "PASS"       # production _build_anchor_index called directly, no mocks; compress() path exercised by region_scoping + test_lean_single_aux_call
P5 = "PASS"       # RED, GREEN 3/3, per-row sabotage 3/3 + precision sabotage, ADJ identical, guards equal
P6 = "PENDING"    # body makes no recall claim; selection gate needs exam (OD-1 or OD-3)
P7 = "PASS"       # one commit on 234badf401, author ok, merge-tree clean, workflow push matches = 0
P8 = "PENDING"    # receipts hashed locally; not frozen to z0evals / ledger
P9 = "PASS"       # PR_BODY.md self-checked (tone, no jargon, AI disclosed); verifier to confirm
P10 = "PENDING"   # blind verifier not run
P11 = "RECORDED"  # maintainer-named target; user demand thin
P12 = "PENDING"   # staging cap / OD-8; Wave 0 not passed

[verification]
verifier = ""
provenance = "independent"
exact_head = "6e0fa629a0f6227b03417d1d6ff7f7d81208346a"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""

[merge_check]
main_sha = "234badf4012af380d23c91eae55d045a69c69ffb"
checked_at = "2026-10-01T04:13-05:00"
clean = true
recheck = "git merge-tree --write-tree main staging/compaction-anchor-retention"

[push]
no_follow_tags = true
workflow_push_matches = 0
pushed_at = ""

[body]
path = "PR_BODY.md"
kind = "pr-body"
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
jargon_lint = "PASS (self)"
privacy_scan = "PASS (self): no session ids, no private paths beyond committed scorecard text"

[queue]
board = "kvnloo/hermes-agent#404"
position = "after existing rows"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# staging/compaction-anchor-retention

Promotion form: **core-pr** (FACTORY route `core-leaf`). Current status **STAGED**. The best class reachable at $0 is **LIMITED**, because the exam gates need an aux LLM.

## Invariant

If a delegation or kanban task id (`sa-2-7318d0ba`, `t_4f9c2a1e`), a dotted config key (`plugins.stream_reasoning_deltas`) or a CLI error line (`GraphQL: … (mergePullRequest)`, `Blocked: …`, `fatal: …`, `error TS2741: …`) appears in the compacted region, the lean anchor index keeps it verbatim. The index stays inside per-class caps and the unchanged 7,000-char budget, and no existing section's line changes.

Call path: `ContextCompressor.compress()` calls `_augment_summary_lean()` (lean mode only), which calls `_redact_compaction_text(_build_anchor_index(turns_to_summarize))` (`agent/context_compressor.py:3645`). The contract tests call the production `_build_anchor_index` directly, without mocks. `evals/compaction/test_region_scoping.py` and `tests/agent/test_lean_single_aux_call.py` exercise the full `compress()` path.

## Premise re-check on current main

- **Still needed.** The `_ANCHOR_PATTERNS` table at `agent/context_compressor.py:1057` on `234badf401` is unchanged since `c4bbb14e52`. No row matches subagent ids (the commits row needs 9+ hex chars), dotted keys, or error lines that lack an exception class name.
- **Open upstream overlap: NousResearch/hermes-agent#117462** (Seldash, opened 2026-09-20, P2, one positive bot review, no maintainer review).
  - It changes the same function: it harvests tool-call arguments, puts cheap ids first, truncates per section instead of using `break`, and adds session ids, todo ids and more path extensions.
  - It does **not** add any of our three classes. The A/B receipt shows this: our tests are RED on #117462, and 3 of its 5 tests are RED on our branch. Both suites are GREEN on the fold-in (`foldin-on-117462.patch`).
  - Verdict: complementary, not a duplicate. Coordinate, don't compete. Whichever PR lands second needs a small table rebase.
- **#122274 / #122522** (`summary_source=original`) is a different mechanism. Merge-tree is clean in both directions. Recorded as adjacent only, not cited as a carrier.
- **Sibling dependency.** `compressor-media-extraction` must not move lines ~1040-1110 at the same time. Its worktree exists, but it had no staging ref when this was written. Recheck with `git merge-tree --write-tree staging/compressor-media-extraction staging/compaction-anchor-retention` once that branch exists.

## First slice: committed

`6e0fa629a0` "fix(compression): anchor index keeps task ids, dotted keys and CLI error lines". Author Kevin Rajan, on `234badf401`, 2 files, +70.

| row (appended after `urls`) | regex | cap |
|---|---|---|
| `task ids` | `\b(?:sa-\d+-[0-9a-f]{8}\|t_[0-9a-f]{8})\b` (from `tools/delegate_tool.py:195`, `hermes_cli/kanban_db.py:1089`) | 40 |
| `dotted keys` | dotted lowercase name whose **last** segment is snake_case. This excludes file names, hosts and `e.g`. | 40 |
| `error messages` | `\b(?:fatal\|[Ee]rror(?: TS\d{4,5})?\|GraphQL\|Blocked): [^\n]{8,110}` | 20 |

Rows were chosen from the evidence:

- Error lines: 9 golds across 3 lineages.
- Task id: 1 gold, plus the maintainer naming "delegation ids".
- Config key: 1 gold, plus the maintainer naming "config keys".
- **Env-var names: no row.** There are 0 golds and the maintainer did not name them.
- **Bare symbols: no row.** This is the largest remaining class (6 golds, 4 lineages), but a bare identifier row would be dominated by frequent code tokens.

**Placement.** On main, `_build_anchor_index` `break`s at the first section that overflows the budget. A new row placed before `files` could therefore delete the whole `files` line in dense regions. So the rows are **appended**. Existing lines are byte-identical: 180/180 synthetic regions (F02s). The cost is that new sections only get leftover budget on main. In the fold-in for #117462, the rows follow that PR's cheap-first order instead: `task ids` after `todo ids`, `dotted keys` before `files`, `error messages` last.

Label honesty: `dotted keys`, not `config keys`. On the docs corpus, 29.7% of distinct dotted-key values are `DEFAULT_CONFIG` keys. The rest are dotted API identifiers such as `ctx.register_hook`.

## Evidence (experiments run, all $0)

Receipts are under `$STAGING/receipts/`. Inputs are pinned by SHA and sha256 inside each receipt. The harness is `harness/anchor_coverage.py` (sha256 inside the receipts). Every run used bwrap with no network (a connect probe returns ENETUNREACH), the live home masked except the venv, and isolated HOME/HERMES_HOME. Egress attempts: the region-scoping guard tries one OpenRouter model-metadata fetch, which is blocked on both base and head.

| experiment | receipt | verdict | label | n | result |
|---|---|---|---|---|---|
| RG01 red/green | `RG01-redgreen.json` | KEEP | OBSERVED | 2 tests | RED on main: 2 failed (`'sa-2-7318d0ba' missing from anchor index`). GREEN 3/3. Removing any of the 3 rows re-REDs. Precision sabotage re-REDs (`config.yaml` leaks). Adjacent: 365 passed on base vs 365+2 on head (6 files). `test_region_scoping` ALL PASS on both. `replay_gates` 11/11 PASS on both with equal result dicts. |
| E03p gold reachability (stands in for E03) | `E03p-gold-reachability.json` | KEEP | OBSERVED (emitter-line column MODELED) | 90 golds, 49 identifier | Identifier golds the rows can capture: main **24/49**, branch **31/49**, #117462 24/49, fold-in 31/49. The 7 new ones are 5 error lines (sweep, gui, acp), 1 subagent id (gui) and 1 config key (prmerge). Error lines: 0/9 reachable on main, across 3 lineages. With the emitter line (MODELED): 25 → 35. |
| E03s synthetic survival | `E03s-synthetic-survival.json` | PARTIAL | MODELED | 180 regions/arm | Needles in the new classes that survive: sparse main 0/110, branch 100/110. Medium branch 17/110, fold-in 20/110 (error lines 0/90 on both). Dense: almost no once-mentioned needle of any class survives on any arm (main 13/570). Frequency-first ranking plus the 7K budget is the binding limit, not the row set. |
| F02s budget audit (stands in for F02) | `F02s-budget-audit.json` | KEEP | OBSERVED (tokens MODELED) | 720 regions | 0/720 over the 7,000-char section budget. Index max 7,193 chars including heading, about 1,798 tokens (chars/4), against the 32,000-token `RETAINED_SUMMARY_TOKEN_BUDGET`. Base sections are a prefix of branch sections in 180/180. Index build on a 443K-char region: 0.030 s main vs 0.029 s branch (single run). |
| N01 noise audit | `N01-noise-audit.json` | KEEP | OBSERVED | 448 files, 7.8M chars | Task ids: 4 matches, 2 distinct (doc examples). Dotted keys: 1,032 distinct, 306 of them in `DEFAULT_CONFIG`, and all of the top 15 are real dotted identifiers. Error messages: 24 matches, mostly doc prose. |
| AB117462 carrier compatibility | `AB117462-carrier-compat.json` | KEEP | OBSERVED | 3 arms × 2 suites | On #117462: ours 0/2, theirs 5/5. On fold-in: ours 2/2, theirs 5/5, adjacent 8 files 372 passed. On branch: ours 2/2, theirs 2/5. The fold-in patch applies to the #117462 head. |

Raw outputs (synthetic or public only) are in `raw/`. Arm sources are in `raw/arms/` (base, branch, c117462, c117462_foldin).

## Acceptance gates (from selection.json)

| gate | status | evidence |
|---|---|---|
| E03 shows ≥1 missing class with frequency evidence on ≥3 frozen **local** lineages | **pending** (proxy met) | Local lineages are not allowed in this run (state.db) and need OD-7. On the committed banks, the error-line class is missing on 3 lineages (9 golds). |
| Unit tests RED on main, GREEN with the rows | **met** | RG01 |
| Negative control: dropping a row re-REDs | **met** | RG01 (3/3 rows, plus precision sabotage) |
| Index ≤7,000 chars and summary <32k tokens on every frozen lineage | **pending** (synthetic met) | F02s: 0/720 over budget and index ≤ about 1.8k tokens. Real lineages need OD-7. Whole-summary tokens are NOT_MEASURED. |
| Exam: anchor-v2 beats current+recovery on a frozen mix, n≥3 reps per lineage, by more than the E05 SD, with no lineage regressing beyond the SD | **not-met** (queued) | E05, then E04 below. Needs OD-1 or OD-3. |
| `evals/compaction/test_region_scoping.py` and `token_accounting/replay_gates.py` unchanged | **met** | Files untouched. Verdicts equal on base and head (RG01). |
| PR body states local-route-only scope | **met** | PR_BODY.md |
| Only aggregate receipts published; lineages never pushed (K1) | **met** | No lineages were used. Inputs are committed upstream text plus seeded synthetic data. |

## Gate checklist (P1-P12)

- P1 Need: PASS. RG01 RED on `234badf401`, 2026-10-01.
- P2 Ownership: PASS. AB117462 shows the work is complementary. Claimant lanes #127373/#127374/#127375/#127332/#127228 are all TUI or HUD perf.
- P3 Shape: PASS. +5 production lines and one test file. No env var, config key, hook or prompt change.
- P4 Real path: PASS. The production function runs with no mocks.
- P5 Proof: PASS (RG01).
- P6 Numbers: PENDING. The body makes no recall claim. The selection's exam gate needs E05 then E04.
- P7 Package: PASS. One commit, merge-tree clean on `234badf401`, 0 workflow push matches (push triggers are only `main`, `wine2e/**`, `wine2e-install/**` and tags `v*`).
- P8 Freeze: PENDING. Receipts are hashed here but not frozen to z0evals or the ledger.
- P9 Text: PASS (self-checked). The verifier should re-check.
- P10 Independent read: PENDING.
- P11 Demand: RECORDED. The target is maintainer-named. User demand is thin (#78457).
- P12 Queue: PENDING. Wave 0 has not passed, and the staging cap is OD-8.

## Experiments queued (not run)

Shared setup, all owner-gated:

- **Private lineages (OD-7, owner-run, private store only):**
  ```
  cp ~/.hermes/state.db $PRIV/state_copy.db
  python evals/compaction/scripts/reconstruct_lineage.py $PRIV/state_copy.db <root_session_id> $PRIV/lineages/L{1,2,3}.json
  ```
  Freeze the 3-lineage mix: record the sha256 of each JSON.
- **Arms:** worktrees `$WT/base` @ `234badf401` and `$WT/branch` @ `6e0fa629a0`. Optionally add `$WT/c117462` (main + #117462) and `$WT/foldin` (c117462 + `foldin-on-117462.patch`).
- **Aux route.** Write it to `$RUN/home/.hermes/config.yaml`, not to env vars:
  ```yaml
  auxiliary:
    compression:
      base_url: "http://100.113.138.100:11530/v1"   # T2: llama.cpp router; or http://localhost:11434/v1 (ollama)
      model: "<preset with >=64K served context>"     # OD-1; an 8K preset is not allowed
      api_key: "local"
  ```
  For T3, drop `base_url`, set `provider`/`model` to the owner's paid route (09-19 used gemini-3.8-flash via Nous), and the owner launches it with injected credentials.
- **Sandbox.** bwrap with HOME/HERMES_HOME under `$RUN` (on /mnt, never /tmp) and `$HERMES_INSTALL` masked. T2 uses the router profile (allowlist only 127.0.0.1 and 100.113.138.100:11530, plus `flock $TMPROOT/gpu.lock`, strictly serial). `runner.py:241`'s OpenRouter pricing GET fails closed under that profile and only nulls the `$` column.
- **Question banks.** `runner.py` caches `questions-<md5(transcript@cap)[:10]>.json` per `--out`. Generate a bank once per lineage and question count, then copy it into every other out-dir before running, so every rep and arm answers the identical exam.

| id | tier | needs | exact command | decision rule |
|---|---|---|---|---|
| E05 | T2 (gpu) or T3 (paid) | OD-7 + (OD-1 or OD-3) | `for L in L1 L2 L3; do for Q in 15 30; do for rep in 1 2 3; do (cd $WT/base && $VENV/bin/python evals/compaction/runner.py --transcript $PRIV/lineages/$L.json --policies current+recovery --questions $Q --out $PRIV/E05/base/$L/q$Q/rep$rep); done; done; done` | SD of `recall_pct` across 3 reps per lineage, at 15q vs 30q. MDE = 2×SD. Pick the question count. |
| E04 | T2 or T3 | E05 done, plus OD-7 + (OD-1 or OD-3) | `for L in L1 L2 L3; do for rep in 1 2 3; do order="base branch"; [ $rep = 2 ] && order="branch base"; for ARM in $order; do (cd $WT/$ARM && $VENV/bin/python evals/compaction/runner.py --transcript $PRIV/lineages/$L.json --policies current+recovery --questions 30 --out $PRIV/E04/$ARM/$L/rep$rep); done; done; done; python evals/compaction/report.py $PRIV/E04/<arm>/<L>/rep<n>` (arm order alternates by rep: AB, BA, AB) | branch mean − base mean > E05 SD on the frozen mix, and no lineage regresses beyond the SD. Also read `after_tokens` and the anchor section length from the out JSON (real F02). |
| E03-local | T0 (priv) | OD-7 + a cached bank from E05 | Extend `harness/anchor_coverage.py` with `--lineage <json> --bank <questions-*.json>`: region = the messages `compress()` would summarize; count per-class gold needle survival in `_build_anchor_index` output on each arm. Not built yet. Output private; publish aggregates with n≥5 per bucket. | ≥1 class missing on main with frequency on ≥3 lineages (the selection gate). |
| F02-local | T0 (priv) | OD-7 | the same harness extension: index chars per lineage per arm, plus summary tokens from E04 | index ≤7,000 section chars and summary <32k tokens on every lineage |

Cost estimate for T3 (UNVERIFIED, MODELED from the 09-19 run: $33.6 / 634 calls ≈ $0.053 per call): E05 is about 1,200 calls, roughly $65. E04 is about 1,600 calls, roughly $85.

## NOT_TESTED

- Recall effect of the rows: no aux model was run. The E03s survival numbers are MODELED on synthetic regions.
- Real lineages and state.db: forbidden in this run, and they need OD-7. No question bank beyond the committed 08-15 golds.
- Native compaction routes (`codex_responses_native` and others): summaries are opaque. The index adds at most about 1.8k tokens (MODELED) against the 32k retained-summary carrier.
- Legacy tail mode: `_augment_summary_lean` is a no-op there.
- Precision on real transcripts. N01 used docs, not sessions.
- Whole-suite `pytest tests/`: only targeted files were run.
- Interplay with #109980 (handoff block), which conflicts with main on its own.

## Origin action (owner only)

The smallest ask has two options; pick one:

1. Preferred while #117462 is open: one comment on NousResearch/hermes-agent#117462 offering `foldin-on-117462.patch` (three rows in that PR's order) to Seldash, with credit as `Co-authored-by: Kevin Rajan`.
2. After #117462 merges, or if it is closed: open the PR with
   ```
   gh pr create -R NousResearch/hermes-agent --head <fork>:<physical branch> --base main --title "fix(compression): anchor index keeps task ids, dotted keys and CLI error lines" --body-file PR_BODY.md
   ```
   The factory does NOT run this. Rebase the table first if #117462 landed.

Either way, run E05/E04 first if the maintainer is expected to ask for exam numbers (his scorecards are the currency).

## Next steps

1. Owner: resolve OD-0 (branch namespace) and choose origin action 1 or 2.
2. Blind verifier on exact head `6e0fa629a0`, with the oracle being the RG01 commands.
3. OD-1 or OD-3, then E05, then E04. OD-7, then E03-local and F02-local (harness extension above).
4. Daily drift check: `git diff --name-only 234badf401..main -- agent/context_compressor.py tests/agent/test_lean_single_aux_call.py evals/compaction/` plus `git merge-tree --write-tree main staging/compaction-anchor-retention`. Re-run if #117462 or compressor-media-extraction moves.
5. Follow-up candidate (not in this slice): once-mentioned needles die in dense regions on every arm (E03s). A recency or diversity tie-break for count-1 values is a separate, measurable change for the maintainer to weigh.

## History

- 2026-10-01T03:55-05:00 | CANDIDATE | builder (Claude Code) | Premise re-checked. #117462 found to be complementary.
- 2026-10-01T04:00-05:00 | EVIDENCED | builder | RED/GREEN/NEG/ADJ on 572e4f4fad. E03p/E03s/F02s/N01/AB117462 run.
- 2026-10-01T04:13-05:00 | STAGED | builder | Rebased to 234badf401 as 6e0fa629a0. RED/GREEN/ADJ/guards re-run on the exact head. Local branch `staging/compaction-anchor-retention` set.
