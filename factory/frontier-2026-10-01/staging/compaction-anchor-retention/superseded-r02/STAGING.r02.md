+++
xf_staging = 1
id = "compaction-anchor-retention"
title = "Extend the compaction anchor index to the identifier classes the recall exam loses"
version = 2
branch = "staging/compaction-anchor-retention"          # local name in the scratch h.git
branch_fork = "staged/compaction-anchor-retention"      # name it gets on kvnloo/hermes-agent (not pushed yet)
branch_physical = "local-only in scratch h.git; will be pushed to kvnloo/hermes-agent as staged/compaction-anchor-retention. OD-0 is resolved by that rename (the fork's legacy refs/heads/staging blocks staging/<id>)."
branch_sha = "b11e27d5f9c60a420cbbe94fa967fc1454df92a6"
previous_sha = "6e0fa629a0f6227b03417d1d6ff7f7d81208346a"   # round 1; replaced locally (never pushed)
status = "STAGED"          # class ceiling at $0: LIMITED (P6: exam gates need OD-1 or OD-3); P10 must re-run on the new head
route = "support-note"     # on NousResearch/hermes-agent#117462 (fold-in offer). Fallback: core-leaf after #117462 lands or closes AND P6 is met
promotion_form = "support-note"   # changed in round 2 from core-pr (see "Route and carrier choice")
feature = "compaction-identifier-anchor-retention"
invariant = "When an identifier of the classes 'delegation/kanban task id', 'dotted config key' or 'CLI error line / Hermes tool refusal' appears in the compacted region, the lean anchor index carries it verbatim, inside per-class caps and the unchanged 7,000-char budget, without changing any existing section's line, and without capturing Python annotations or log format strings as error lines."

[base]
repo = "NousResearch/hermes-agent"
sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"        # every round-2 number was measured on this main
fetched_at = "2026-10-01T06:05-05:00"
recheck = { main = "e8c97320ac8691d4de92af49f98459f9ef9ddb08", at = "2026-10-01T06:30-05:00", commits_since_base = 6, relevant_paths_changed = 0, merge_tree = "clean" }

[upstream]
issues = [
  "NousResearch/hermes-agent#116246 (teknium1, merged: adds evals/compaction/results/SCORECARD-2026-09-19-jev.md, which names this target)",
  "NousResearch/hermes-agent#87326 (teknium1, merged 2026-08-16: lean tail + recall exam harness)",
  "c4bbb14e52 (teknium1, 2026-08-15: mechanical anchor index + region-scoping tripwire)",
  "NousResearch/hermes-agent#122274 (teknium1, open: summary_source=original; different mechanism)",
  "NousResearch/hermes-agent#78457 (akivavh, open: user-demand signal, r=1)",
]
eval_prs = []
carrier = { pr = 117462, author = "Seldash", head = "2c19948e15d68492d048250bae7707ca77063db5" }   # owns the _build_anchor_index rework; our rows ride as a fold-in
competitors = []
adjacent = [
  { pr = 122522, author = "Nagisa-3000", head = "f596584b017694bf123d746a87740f58a2db15c1", role = "adjacent (opt-in summary_source=original, carrier for teknium's #122274); different mechanism; coordinate, not a member", merge_tree_vs_main = "clean", merge_tree_vs_branch = "clean" },
  { pr = 109980, author = "Finn763", head = "82cb05f119a66d5cbe53dde8a5cc064ba2a9139a", role = "handoff block re-derivation; reads _LEAN_ANCHOR_HEADING, does not touch the table", merge_tree_vs_main = "CONFLICT (its own drift)" },
]
close_after = []
demand = { score = 0, source = "user demand thin (#78457 r=1); maintainer signal strong" }
maintainer_signal = "SCORECARD-2026-09-19-jev.md:28-30: 'the facts our summary loses (delegation ids, root causes, config keys, exact error strings) sat in assistant text. That is a summariser-retention target (anchor index / identifier capture)'; :107-108 asks to 'check its coverage on these three banks before touching anything else' (banks not committed; see NOT_TESTED)"

[[donors]]
sha = "b11e27d5f9c60a420cbbe94fa967fc1454df92a6"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "rows + tests (standalone commit and the content of foldin-on-117462.patch); no third-party code reused"
trailer = "Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"   # requested in body.md if Seldash folds the patch in

[[members]]
ref = "refs/pr/117462"
sha = "2c19948e15"
role = "carrier (Seldash): same function and table; foldin-on-117462.patch applies to its head exactly (no offset)"
rebase = "merge-tree clean vs main aea969677c (tree 8d48e1bbf2); CONFLICT vs our standalone branch (both edit the table)"

[[members]]
ref = "refs/heads/staging/compaction-anchor-retention"
sha = "b11e27d5f9"
role = "standalone commit: fallback core-leaf head, and the source of the fold-in rows/tests"
rebase = "on aea969677c; merge-tree clean vs aea969677c and vs e8c97320ac"

[[members]]
ref = "refs/pr/122522"
sha = "f596584b01"
role = "adjacent (Nagisa-3000, opt-in summary_source=original); coordinate, not a member"
rebase = "merge-tree clean vs main aea969677c and vs our branch"

[ownership]
searched_at = "2026-10-01T04:20-05:00 (round 1); PR heads and comments re-read 2026-10-01T06:20-05:00"
queries = ["_ANCHOR_PATTERNS", "anchor index", "_build_anchor_index", "anchor_index", "anchor ledger", "identifier capture compaction", "compaction identifier", "summary_source"]
open_external = [117462]
merged_overlap = []
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # all TUI/HUD perf; no overlap
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found; sibling staging/compressor-media-extraction @ c5e8be14b4 now exists and merge-tree vs our branch is clean (2026-10-01T06:38)"
verdict = "EXTERNAL -> support: #117462 (open, Seldash) owns the _build_anchor_index rework; our classes are complementary and ride on it as a fold-in. Own core-leaf only as a fallback."

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
receipts = [
  { id = "RG01/r20261001-02", path = "receipts/RG01-redgreen.json", sha256 = "0b3c59366cc99360d9888bc244e1d03ff18e864da6f040000188c7a3f22a3acf" },
  { id = "E03p/r20261001-02", path = "receipts/E03p-gold-reachability.json", sha256 = "2a26d159d47eb95fb115fc75a03498b296fbbe9f22513646742695953101474c" },
  { id = "E03s/r20261001-02", path = "receipts/E03s-synthetic-survival.json", sha256 = "f0e1af13be517f4b44df26880df45ab6ab9b62628f4ae15ac94a8d4da7044952" },
  { id = "F02s/r20261001-02", path = "receipts/F02s-budget-audit.json", sha256 = "57b54353b2d3707c894624ad0cc8b589fa49fc14cc21d760f310d2b52559594b" },
  { id = "N01/r20261001-02", path = "receipts/N01-noise-audit.json", sha256 = "dddcbfdbe442540451430b649527fafab962304ba5215b822813c63f919e29d9" },
  { id = "AB117462/r20261001-02", path = "receipts/AB117462-carrier-compat.json", sha256 = "0c92a8d546a34fd7f55a14d8158e9ecd215c498abbef1c4e5b81b0328d553d8e" },
]
patches = [
  { path = "compaction-anchor-retention.patch", sha256 = "90bea6dba82605dd49b94230b387b57dcba6da532e8bfa9cc76818146b1fa214", note = "git format-patch -1 of b11e27d5f9" },
  { path = "foldin-on-117462.patch", sha256 = "06369375643c1233d72e7f7a705f150c9909a9d906aa8bcf19215ffab6ef6228", note = "git diff of #117462's tree + our rows (its order) + our test file" },
]
superseded = "superseded-r01/ (round-1 receipts, raw, harness, patches, STAGING and PR body; absolute paths replaced by placeholders; nothing there is cited)"
red = { test = "tests/agent/test_context_compressor_anchor_index.py", main = "aea969677c", marker = "AssertionError: 'sa-2-7318d0ba' missing from anchor index", receipt = "RG01/r20261001-02" }
green = { reps = "3/3", receipt = "RG01/r20261001-02" }
negative_control = { mutation = "drop each new row (3/3) + dotted-keys precision sabotage + 6 error-row sabotages (anchor, escaped-\\n anchor, quote/backtick anchor, re.M, placeholder guard, escaped-\\n stop): 10/10 re-RED", result = "RED", receipt = "RG01/r20261001-02" }
adjacent = { identical = true, base = "365 passed (6 files)", head = "367 passed (7 files)", pre_existing = [] }
guards = { region_scoping = "ALL PASS base and head (2 fresh-home runs each)", replay_gates = "11/11 PASS base and head; result dicts equal apart from compressor_sha256" }
egress = "region_scoping: 2 DNS lookups of openrouter.ai per run (model-metadata fetch), blocked, on base and head alike; 0 connect attempts. replay_gates and the coverage harness: 0 attempts."
quantitative = []                  # no OBSERVED recall number exists yet
cache_read_ratio = { status = "N_A", why = "summary text changes only at a compaction event (already a cache break); cadence unchanged" }
route_scope = "local-compressor (lean tail mode); native compaction summaries are opaque"
not_tested = ["recall exam (E05/E04): aux LLM needed", "the 09-19 prreview/sysprompt/sigsegv banks the maintainer asked about (not committed)", "real lineages / state.db copies (forbidden in this run; OD-7)", "native compaction routes", "legacy tail mode (index not built there)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-compaction-anchor-retention", commit = "" }

[gates]
P1 = "PASS"       # RED on aea969677c (2026-10-01)
P2 = "PASS"       # route now matches ownership: external #117462 -> support note with fold-in (round 1 recorded core-leaf; corrected)
P3 = "PASS"       # +9 prod lines (3 rows, 4 comment lines, 2 continuation lines), one test file, no env/config/hook
P4 = "PASS"       # production _build_anchor_index called directly, no mocks; compress() path exercised by region_scoping + test_lean_single_aux_call
P5 = "PASS"       # RED, GREEN 3/3, 10/10 per-hunk sabotage, ADJ identical, guards equal
P6 = "PENDING"    # bodies make no recall claim; selection gate needs exam (OD-1 or OD-3) -> class LIMITED
P7 = "PASS"       # one commit on aea969677c, author ok, merge-tree clean (also on e8c97320ac), workflow push matches for staged/compaction-anchor-retention = 0
P8 = "PENDING"    # receipts hashed locally; not frozen to z0evals / ledger
P9 = "PASS"       # body.md and PR_BODY.md self-checked (tone, no jargon, AI disclosed, no absolute paths); verifier to confirm
P10 = "PENDING"   # round-1 verifier ran on 6e0fa629a0; the new head b11e27d5f9 needs a fresh blind read
P11 = "RECORDED"  # maintainer-named target; user demand thin
P12 = "PENDING"   # staging cap / OD-8; Wave 0 not passed

[verification]
verifier = ""
provenance = "independent"
exact_head = "b11e27d5f9c60a420cbbe94fa967fc1454df92a6"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""
previous = { head = "6e0fa629a0", verdict = "accept=false (7 problems; all addressed in round 2, see 'Round 2 changes')" }

[merge_check]
main_sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
checked_at = "2026-10-01T06:20-05:00"
clean = true
recheck = "git merge-tree --write-tree main staging/compaction-anchor-retention   # clean again on e8c97320ac at 06:30"

[push]
no_follow_tags = true
workflow_push_matches = 0          # push triggers on main: main, wine2e/**, wine2e-install/**, tags v*; none match staged/compaction-anchor-retention
pushed_at = ""

[body]
path = "body.md"
kind = "support-note"
fallback_pr_body = "PR_BODY.md"    # core-leaf body; not usable while the class is LIMITED or while #117462 is open
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
jargon_lint = "PASS (self)"
privacy_scan = "PASS (self): no session ids, no local paths; gold strings quoted only from committed scorecard text"

[queue]
board = "kvnloo/hermes-agent#404"
position = "after existing rows (39 at 2026-10-01); a support note takes no PR slot"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# staging/compaction-anchor-retention (fork branch: `staged/compaction-anchor-retention`)

Promotion form: **support-note** on NousResearch/hermes-agent#117462 (route `support-note`), changed in round 2 from core-pr. Status **STAGED**. The best class reachable at $0 is **LIMITED**, because the exam gates need an aux LLM. FACTORY §11.2 lets a LIMITED item ship only as a support note or a decision request.

## Round 2 changes (2026-10-01, fixes for the phase-3 verifier)

1. **F02s claim corrected.** The old "0/720 regions" spanned 4 arms. This PR's arm is 180 regions; its index peaks at **7,190** chars (sections 6,998). The 7,193 figure was the fold-in arm. Staying under 7,000 section chars is guaranteed by the loop, so it is no longer reported as a finding. PR_BODY.md and the F02s receipt say this now.
2. **09-19 check stated as not run.** SCORECARD-2026-09-19-jev.md:107-108 asks for a coverage check on its prreview/sysprompt/sigsegv banks. Those banks are not committed: `jev-cycles-2026-09-19/*.json` contain no golds. Both bodies now say the check could not be run, and why.
3. **Circularity disclosed.** The 24 → 31 gold count is in-sample: the rows were written after reading those golds. The 5 new error-line golds are only **2 distinct strings**: Hermes's own `Blocked: \`git …\` would rewrite …` guard refusal (3 golds) and one gh `GraphQL: … (mergePullRequest)` error (2 golds). `Blocked:` is labelled as a Hermes tool-refusal prefix, not a CLI error line. The prefix opens about 30 refusal messages across 15 files in `tools/`, `cron/`, `plugins/` and `agent/`.
4. **Error row tightened (code change).** `fatal:`/`error:` now count only where a line starts, or after a quote, a backtick or a JSON-escaped `\n`. The row skips `%s`/`{}` placeholders, and a value stops at an escaped newline. On public `agent/*.py` (251 files) the row now matches **2** strings, both real messages. Before it matched 80, nearly all annotations or log formats. On the docs it matches 9 instead of 24. The precision test now pins this: annotations and `"error: %s"` must stay out. The verbatim test adds a JSON terminal-output case and a backtick-quoted case. The cost: the MODELED emitter-line column drops 35 → 34, and sparse synthetic survival drops 100 → 90 of 110. Both losses are the GNU as `Fatal error: error writing …` line, where `error:` does not start a line. **Dotted-keys limitation stated, not changed:** on `agent/*.py`, 9 of the 40 most frequent values are `self.*` and none is a DEFAULT_CONFIG key.
5. **Provenance.** Every receipt was re-measured on one declared main, **aea969677c**. The harness ran on a checkout of the new head, which differs from that main only in the two files of the commit. The round-1 claim that "the 11 commits between touch no relevant file" was wrong, and it is gone. Receipts no longer contain absolute local paths.
6. **Route and ownership.** #117462 is an open external PR on the same function and table, so FACTORY P2 calls for support, not a competing PR. The route is now `support-note`, and the origin action is a single fold-in offer on #117462 (`body.md`). The standalone `gh pr create` option is removed. Core-leaf stays recorded only as a fallback (see Origin action).
7. **Minor fixes.**
   - replay_gates results are "equal apart from compressor_sha256".
   - Egress was re-measured with a socket/DNS logger in fresh homes: region_scoping makes 2 blocked openrouter.ai lookups per run on base and head alike, with 0 connects. replay_gates and the harness make 0 attempts.
   - The reconstruct_lineage command is now one invocation per root.
   - On #117462, the positive "review" is a plain issue comment from a User account (kyssta-exe, signed "Reviewed using Hermes-Agent"). The PR has 0 formal reviews.
8. **OD-0 resolved** by the rename: the fork branch will be `staged/compaction-anchor-retention`.

## Invariant

If a delegation or kanban task id (`sa-2-7318d0ba`, `t_4f9c2a1e`), a dotted config key (`plugins.stream_reasoning_deltas`) or an error line appears in the compacted region, the lean anchor index keeps it verbatim. Error lines include CLI errors (`fatal: …`, `error: …`, `error TS2741: …`, `GraphQL: … (mergePullRequest)`) and Hermes tool refusals (`Blocked: …`). The index stays inside per-class caps and the unchanged 7,000-char budget, and no existing section's line changes. Python annotations (`error: Exception)`) and log format strings (`"error: %s"`) are not captured as error lines.

Call path: `ContextCompressor.compress()` calls `_augment_summary_lean()` (lean mode only), which calls `_redact_compaction_text(_build_anchor_index(turns_to_summarize))` (`agent/context_compressor.py:3645` on main, `:3654` on the branch). The contract tests call the production `_build_anchor_index` directly, without mocks. `evals/compaction/test_region_scoping.py` and `tests/agent/test_lean_single_aux_call.py` exercise the full `compress()` path.

## Route and carrier choice

- **Carrier: NousResearch/hermes-agent#117462** (Seldash, opened 2026-09-20, labels P2 / area/compression, 0 formal reviews). It has one issue comment from kyssta-exe, a User account, signed "Reviewed using Hermes-Agent", with the verdict "Looks good to merge". Seldash pushed follow-ups in `2c19948` on 2026-09-22. The PR reworks `_build_anchor_index`: it harvests tool-call arguments, puts cheap ids first, truncates per section instead of using `break`, and adds session ids, todo ids and more path extensions.
- **Why support, not a separate PR.** Both PRs edit the same table, so they conflict, and #117462 owns the rework. Our three classes are complementary: our tests are RED on #117462, and 3 of its 5 tests are RED on our branch. With `foldin-on-117462.patch` applied, both suites are GREEN, and the 8-file adjacent suite gives 372 passed. Its per-section truncation also helps our rows in medium-density regions (fold-in 20/110 vs 17/110 on main, MODELED). Under FACTORY P2, an external owner means support. Under FACTORY §11.2, a LIMITED item ships only as a support note.
- **#122522 / #122274** (`summary_source=original`): a different mechanism. Merge-tree is clean in both directions. FACTORY §11.4 had pencilled #122522 as the support target. That was re-checked: it does not touch the anchor table, so it is adjacent only.
- **Fallback (not an origin action today).** If #117462 lands without the rows, or closes, *and* P6 is met (E05 → E04), re-stage the standalone commit as core-leaf. Rebase the table first if #117462 landed. PR_BODY.md is the draft for that case.
- **Sibling dependency.** `staging/compressor-media-extraction` now exists (`c5e8be14b4`), and `git merge-tree --write-tree staging/compressor-media-extraction staging/compaction-anchor-retention` is clean (2026-10-01T06:38). Recheck if either moves.

## Premise re-check on current main

- **Still needed.** The `_ANCHOR_PATTERNS` table at `agent/context_compressor.py:1057` on `aea969677c` is unchanged since `c4bbb14e52`. No row matches subagent ids (the commits row needs 9+ hex chars), dotted keys, or error lines that lack an exception class name.
- **Main drift.** `aea969677c` → `e8c97320ac` is 6 commits, and none touches `agent/context_compressor.py`, `tests/agent/`, `evals/compaction/` or `evals/token_accounting/`. Merge-tree is clean on both.

## The commit

`b11e27d5f9` "fix(compression): anchor index keeps task ids, dotted keys and CLI error lines". Author Kevin Rajan, on `aea969677c`, 2 files, +98 (9 production lines, 89 test lines).

| row (appended after `urls`) | regex | cap |
|---|---|---|
| `task ids` | `\b(?:sa-\d+-[0-9a-f]{8}\|t_[0-9a-f]{8})\b` (from `tools/delegate_tool.py:195`, `hermes_cli/kanban_db.py:1089`) | 40 |
| `dotted keys` | dotted lowercase name whose **last** segment is snake_case. This excludes file names, hosts and `e.g`. | 40 |
| `error messages` | `fatal:`/`[Ee]rror:` only at a line start, after a quote or backtick, or after a JSON-escaped `\n` (`re.M`); `\berror TS\d{4,5}:`, `\bGraphQL:` and `\bBlocked:` anywhere; then not `%`/`{`, 8-110 chars, stopping at a real or escaped newline | 20 |

Rows were chosen from the evidence (in-sample, see Round 2 item 3):

- Error lines: 9 golds across 3 lineages, 0 of them reachable on main. The rows reach 5, which are 2 distinct strings.
- Task id: 1 gold, plus the maintainer naming "delegation ids".
- Config key: 1 gold, plus the maintainer naming "config keys".
- **Env-var names: no row.** There are 0 golds and the maintainer did not name them.
- **Bare symbols: no row.** This is the largest remaining class (6 golds, 4 lineages), but a bare identifier row would be dominated by frequent code tokens.

**Placement.** On main, `_build_anchor_index` `break`s at the first section that overflows the budget. A new row placed before `files` could therefore delete the whole `files` line in dense regions. So the rows are **appended**, and existing lines stay byte-identical in 180/180 synthetic regions (F02s). The cost is that new sections only get leftover budget on main. In the fold-in for #117462, the rows follow that PR's cheap-first order instead: `task ids` after `todo ids`, `dotted keys` before `files`, `error messages` last.

Label honesty: `dotted keys`, not `config keys`. On the docs corpus, 29.7% of distinct values are `DEFAULT_CONFIG` keys. On Python source it is mostly attribute access (N01).

## Evidence (experiments run, all $0)

Receipts are in `receipts/` (r20261001-02). Every number was measured on main `aea969677c` and head `b11e27d5f9`. Inputs are pinned by SHA and sha256 inside each receipt. The harness is `harness/anchor_coverage.py`; `harness/build_receipts.py` writes the receipts from `raw/`. Guard and harness runs used `harness/sandbox.sh`, which applies:

- bwrap with no network: connect returns ENETUNREACH, and the systemd-resolved socket is masked, so DNS fails.
- The live Hermes install masked except the venv, and a fresh HOME/HERMES_HOME per run.
- An egress logger (`harness/egress_sitecustomize.py`) that records every non-loopback lookup or connect.

Tests ran with `HOME=$S/testhome-sf-compaction-anchor-retention`.

| experiment | receipt | verdict | label | n | result |
|---|---|---|---|---|---|
| RG01 red/green | `RG01-redgreen.json` | KEEP | OBSERVED | 2 tests | RED on main: 2 failed (`'sa-2-7318d0ba' missing from anchor index`; `assert 'compression.tail_mode' in ''`). The round-1 rows also fail the new tests: annotations leak, and an error after an escaped `\n` is missed. GREEN 3/3. All 10 single mutations re-RED. Adjacent: 365 passed on base vs 365+2 on head (6 files). `test_region_scoping` ALL PASS on both, 2 runs each. `replay_gates` 11/11 PASS on both; result dicts are equal apart from `compressor_sha256`. Egress: 2 blocked openrouter.ai lookups per region_scoping run on both arms, 0 elsewhere. |
| E03p gold reachability (stands in for E03) | `E03p-gold-reachability.json` | KEEP (in-sample) | OBSERVED (emitter-line column MODELED) | 90 golds, 49 identifier | Identifier golds the rows can capture: main **24/49**, branch **31/49**, #117462 24/49, fold-in 31/49. The 7 new ones are 5 error lines (3× the `Blocked:` git-guard refusal, 2× one gh GraphQL merge-conflict error), 1 subagent id and 1 config key. Rows were written from these golds. With the emitter line (MODELED): 25 → 34. |
| E03s synthetic survival | `E03s-synthetic-survival.json` | PARTIAL | MODELED | 180 regions/arm | Needles in the new classes that survive: sparse main 0/110, branch 90/110. Medium branch 17/110, fold-in 20/110 (error lines 0/90 on both). Dense: almost no once-mentioned needle of any class survives on any arm (main 13/570, #117462 25/570). Frequency-first ranking plus the 7K budget is the binding limit, not the row set. |
| F02s budget audit (stands in for F02) | `F02s-budget-audit.json` | KEEP | OBSERVED (tokens MODELED) | 180 regions per arm | Branch index max **7,190** chars including heading (sections 6,998), about 1,797 tokens (chars/4), against the 32,000-token `RETAINED_SUMMARY_TOKEN_BUDGET`. Other arms: base 6,451, #117462 7,186, fold-in 7,193. Section chars ≤ 7,000 holds by construction on every arm. Base sections are a prefix of branch sections in 180/180. Index build on a 443K-char region: 0.041 s main vs 0.033 s branch (single run). |
| N01 noise audit | `N01-noise-audit.json` | KEEP | OBSERVED | docs 448 files / 7.8M chars; `agent/*.py` 251 files / 5.9M chars | Docs: task ids 4 matches, 2 distinct (doc examples). Dotted keys 1,032 distinct, 306 in `DEFAULT_CONFIG`. Error messages 9 matches (round-1 rows: 24). Code: error messages 2 matches, both real messages (round-1 rows: 80, nearly all annotations or log formats). Dotted keys: 1,957 distinct; top 40 = 9 `self.*`, 0 config keys (**limitation**). |
| AB117462 carrier compatibility | `AB117462-carrier-compat.json` | KEEP | OBSERVED | 3 arms × 2 suites | On main+#117462: ours 0/2, theirs 5/5. On fold-in: ours 2/2, theirs 5/5, adjacent 8 files 372 passed. On branch: ours 2/2, theirs 2/5. The fold-in patch applies to the #117462 head exactly, and to main+#117462 at offset +105, giving the tested arm. |

Raw outputs (synthetic or public only) are in `raw/`. Arm sources are in `raw/arms/`: base, branch, c117462, c117462_foldin, and branch_r01 for comparison. Egress logs are in `raw/egress/`.

## Acceptance gates (from selection.json)

| gate | status | evidence |
|---|---|---|
| E03 shows ≥1 missing class with frequency evidence on ≥3 frozen **local** lineages | **pending** (proxy met, in-sample) | Local lineages are not allowed in this run (state.db) and need OD-7. On the committed banks, the error-line class is missing on 3 lineages (9 golds). |
| Unit tests RED on main, GREEN with the rows | **met** | RG01 |
| Negative control: dropping a row re-REDs | **met** | RG01 (3/3 rows, plus 7 precision/anchor sabotages) |
| Index ≤7,000 chars and summary <32k tokens on every frozen lineage | **pending** (synthetic: sections ≤7,000 by construction; branch index ≤7,190 chars) | Real lineages need OD-7. Whole-summary tokens are NOT_MEASURED. |
| Exam: anchor-v2 beats current+recovery on a frozen mix, n≥3 reps per lineage, by more than the E05 SD, with no lineage regressing beyond the SD | **not-met** (queued) | E05, then E04 below. Needs OD-1 or OD-3. |
| `evals/compaction/test_region_scoping.py` and `token_accounting/replay_gates.py` unchanged | **met** | Files untouched. Verdicts equal on base and head (RG01). |
| Body states local-route-only scope | **met** | body.md and PR_BODY.md |
| Only aggregate receipts published; lineages never pushed (K1) | **met** | No lineages were used. Inputs are committed upstream text plus seeded synthetic data. |

## Gate checklist (P1-P12)

- P1 Need: PASS. RG01 RED on `aea969677c`, 2026-10-01.
- P2 Ownership: PASS. The route now matches ownership: #117462 is external and open, so this ships as a support note with a fold-in. Claimant lanes #127373/#127374/#127375/#127332/#127228 are all TUI or HUD perf.
- P3 Shape: PASS. +9 production lines and one test file. No env var, config key, hook or prompt change.
- P4 Real path: PASS. The production function runs with no mocks.
- P5 Proof: PASS (RG01). 10/10 sabotages re-RED, and no hunk is unpinned.
- P6 Numbers: PENDING. Neither body makes a recall claim. The selection's exam gate needs E05 then E04, so the class is LIMITED.
- P7 Package: PASS. One commit, merge-tree clean on `aea969677c` and `e8c97320ac`, 0 workflow push matches for `staged/compaction-anchor-retention`. Push triggers are only `main`, `wine2e/**`, `wine2e-install/**` and tags `v*`.
- P8 Freeze: PENDING. Receipts are hashed here but not frozen to z0evals or the ledger.
- P9 Text: PASS (self-checked). The verifier should re-check.
- P10 Independent read: PENDING. A new blind read is needed on `b11e27d5f9`.
- P11 Demand: RECORDED. The target is maintainer-named. User demand is thin (#78457).
- P12 Queue: PENDING. Wave 0 has not passed, and the staging cap is OD-8.

## Experiments queued (not run)

Shared setup, all owner-gated:

- **Private lineages (OD-7, owner-run, private store only).** Run one invocation per root; the script takes exactly `<db> <root> <out>`:
  ```
  cp ~/.hermes/state.db $PRIV/state_copy.db
  python evals/compaction/scripts/reconstruct_lineage.py $PRIV/state_copy.db <root_session_id_1> $PRIV/lineages/L1.json
  python evals/compaction/scripts/reconstruct_lineage.py $PRIV/state_copy.db <root_session_id_2> $PRIV/lineages/L2.json
  python evals/compaction/scripts/reconstruct_lineage.py $PRIV/state_copy.db <root_session_id_3> $PRIV/lineages/L3.json
  ```
  Freeze the 3-lineage mix: record the sha256 of each JSON.
- **Arms.** Worktrees `$WT/base` @ `aea969677c` (or the then-current main) and `$WT/branch` @ `b11e27d5f9`. Optionally add `$WT/c117462` (main + #117462) and `$WT/foldin` (c117462 + `foldin-on-117462.patch`). The fold-in arm is the one that matters for the support route.
- **Aux route.** Write it to `$RUN/home/.hermes/config.yaml`, not to env vars:
  ```yaml
  auxiliary:
    compression:
      base_url: "http://<router-host>:<port>/v1"   # T2: llama.cpp router; or http://localhost:11434/v1 (ollama)
      model: "<preset with >=64K served context>"   # OD-1; an 8K preset is not allowed
      api_key: "local"
  ```
  For T3, drop `base_url`, set `provider`/`model` to the owner's paid route (09-19 used gemini-3.8-flash via Nous), and the owner launches it with injected credentials.
- **Sandbox.** bwrap with HOME/HERMES_HOME under `$RUN` (on /mnt, never /tmp) and the live install masked. T2 uses the router profile: allowlist only loopback and the router host, `flock` on the GPU lock, strictly serial. `runner.py:241`'s OpenRouter pricing GET fails closed under that profile and only nulls the `$` column.
- **Question banks.** `runner.py` caches `questions-<md5(transcript@cap)[:10]>.json` per `--out`. Generate a bank once per lineage and question count, then copy it into every other out-dir before running, so every rep and arm answers the identical exam.

| id | tier | needs | exact command | decision rule |
|---|---|---|---|---|
| E05 | T2 (gpu) or T3 (paid) | OD-7 + (OD-1 or OD-3) | `for L in L1 L2 L3; do for Q in 15 30; do for rep in 1 2 3; do (cd $WT/base && $VENV/bin/python evals/compaction/runner.py --transcript $PRIV/lineages/$L.json --policies current+recovery --questions $Q --out $PRIV/E05/base/$L/q$Q/rep$rep); done; done; done` | SD of `recall_pct` across 3 reps per lineage, at 15q vs 30q. MDE = 2×SD. Pick the question count. |
| E04 | T2 or T3 | E05 done, plus OD-7 + (OD-1 or OD-3) | `for L in L1 L2 L3; do for rep in 1 2 3; do order="base branch"; [ $rep = 2 ] && order="branch base"; for ARM in $order; do (cd $WT/$ARM && $VENV/bin/python evals/compaction/runner.py --transcript $PRIV/lineages/$L.json --policies current+recovery --questions 30 --out $PRIV/E04/$ARM/$L/rep$rep); done; done; done; python evals/compaction/report.py $PRIV/E04/<arm>/<L>/rep<n>` (arm order alternates by rep: AB, BA, AB) | branch mean − base mean > E05 SD on the frozen mix, and no lineage regresses beyond the SD. Also read `after_tokens` and the anchor section length from the out JSON (real F02). |
| E03-local | T0 (priv) | OD-7 + a cached bank from E05 | Extend `harness/anchor_coverage.py` with `--lineage <json> --bank <questions-*.json>`: region = the messages `compress()` would summarize; count per-class gold needle survival in `_build_anchor_index` output on each arm. Not built yet. Output private; publish aggregates with n≥5 per bucket. | ≥1 class missing on main with frequency on ≥3 lineages (the selection gate). This is also the first held-out test of the rows. |
| F02-local | T0 (priv) | OD-7 | the same harness extension: index chars per lineage per arm, plus summary tokens from E04 | index ≤7,000 section chars and summary <32k tokens on every lineage |

Cost estimate for T3 (UNVERIFIED, MODELED from the 09-19 run: $33.6 / 634 calls ≈ $0.053 per call): E05 is about 1,200 calls, roughly $65. E04 is about 1,600 calls, roughly $85.

## NOT_TESTED

- Recall effect of the rows: no aux model was run. The E03s survival numbers are MODELED on synthetic regions.
- The maintainer's requested coverage check on the 09-19 prreview/sysprompt/sigsegv banks: those banks and their golds are not committed (`jev-cycles-2026-09-19/*.json` carry no golds), so it was not run.
- Held-out validity: the 24 → 31 gold count is in-sample (rows written from those golds; error-line gain = 2 distinct strings).
- Real lineages and state.db: forbidden in this run, and they need OD-7.
- Precision on real transcripts. N01 used docs and `agent/*.py`, not sessions. The dotted-keys row is known to fill with attribute accesses on Python source.
- Native compaction routes (`codex_responses_native` and others): summaries are opaque. The index adds at most about 1.8k tokens (MODELED) against the 32k retained-summary carrier.
- Legacy tail mode: `_augment_summary_lean` is a no-op there.
- Whole-suite `pytest tests/`: only targeted files were run.
- The fold-in was tested on main+#117462, not on #117462's own (older) base.
- Interplay with #109980 (handoff block), which conflicts with main on its own.

## Origin action (owner only)

One comment on NousResearch/hermes-agent#117462, with the text in `body.md`. It offers `foldin-on-117462.patch` (three rows in that PR's order plus one test file) to Seldash, asks for credit as `Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>`, and gives an easy decline. The factory does not post it.

There is no standalone PR while the class is LIMITED. If #117462 lands without the rows, or closes, and E05/E04 meet the exam gate, re-stage the standalone commit as core-leaf (rebasing the table first if #117462 landed) and use PR_BODY.md as the draft.

## Next steps

1. Blind verifier on exact head `b11e27d5f9` (P10). The oracle is the RG01 commands plus `foldin-on-117462.patch` on `refs/pr/117462`.
2. Owner: decide whether to post `body.md` on #117462.
3. OD-1 or OD-3, then E05, then E04 (on the fold-in arm while #117462 is open). OD-7, then E03-local and F02-local (harness extension above).
4. Daily drift check: `git diff --name-only aea969677c..main -- agent/context_compressor.py tests/agent/test_lean_single_aux_call.py evals/compaction/` plus `git merge-tree --write-tree main staging/compaction-anchor-retention`. Re-run if #117462 or compressor-media-extraction moves.
5. Follow-up candidates (not in this slice): a recency or diversity tie-break for count-1 values, since once-mentioned needles die in dense regions on every arm (E03s). Separately, a guard against attribute-access domination in `dotted keys`, which would need real-transcript precision data first.

## History

- 2026-10-01T03:55-05:00 | CANDIDATE | builder (Claude Code) | Premise re-checked. #117462 found to be complementary.
- 2026-10-01T04:00-05:00 | EVIDENCED | builder | RED/GREEN/NEG/ADJ on 572e4f4fad. E03p/E03s/F02s/N01/AB117462 run.
- 2026-10-01T04:13-05:00 | STAGED | builder | Rebased to 234badf401 as 6e0fa629a0. Local branch `staging/compaction-anchor-retention` set.
- 2026-10-01T06:02-05:00 | STAGED (verifier: accept=false) | phase-3 verifier | 7 problems: F02s arm count, 09-19 check unstated, in-sample gold count, error-row precision, receipt provenance, route/ownership, minor accuracy.
- 2026-10-01T06:36-05:00 | STAGED (round 2) | staging fixer (Claude Code) | Error row tightened and tests extended. New head b11e27d5f9 on aea969677c. All receipts re-measured on that main (r20261001-02, no local paths). Route changed to support-note on #117462 (body.md); PR_BODY.md kept as the core-leaf fallback. OD-0 resolved by the `staged/<id>` fork name. Local branch forced to b11e27d5f9; round-1 material moved to `superseded-r01/`.
