+++
xf_staging = 1
id = "compaction-anchor-retention"
title = "Extend the compaction anchor index to the identifier classes the recall exam loses"
version = 3
branch = "staging/compaction-anchor-retention"          # local name in the scratch h.git
branch_fork = "staged/compaction-anchor-retention"      # name it gets on kvnloo/hermes-agent (not pushed yet)
branch_physical = "local-only in scratch h.git; will be pushed to kvnloo/hermes-agent as staged/compaction-anchor-retention. OD-0 is resolved by that rename (the fork's legacy refs/heads/staging blocks staging/<id>)."
branch_sha = "30a746f7920c2b4101f121353778d94f5ce001b5"
naming_exception = "FACTORY §10 names a rebuild staging/<id>-vN and forbids force-push; S7 forbids deleting or renaming refs. The orchestrator fixes the local name staging/compaction-anchor-retention (and the fork name staged/compaction-anchor-retention) to the newest version, so that local ref was moved in place for v2 (round 2) and v3 (round 3). Nothing was ever pushed and no ref was deleted or renamed. Round 2 moved the ref without keeping the old head (the phase-3 re-verifier's process finding); round 3 repairs that: v1 and v2 now sit at refs/archive/staging/compaction-anchor-retention-v1 / -v2 in h.git (outside refs/heads, so no branch push picks them up), and their format-patches are kept in superseded-r01/ and superseded-r02/. This is a recorded deviation from the §10 naming rule, pending owner acceptance; it is not owner-accepted yet, and it must be accepted before the push to staged/compaction-anchor-retention."
versions = [
  { v = 1, sha = "6e0fa629a0f6227b03417d1d6ff7f7d81208346a", ref = "refs/archive/staging/compaction-anchor-retention-v1", base = "234badf401", note = "round 1; phase-3 verdict head (accept=false, 7 problems); patch superseded-r01/compaction-anchor-retention.patch, sha256 26f8485aa9c538a2f7c8ca64b6903f711ca428b932e97b6a9ff902773f9ac5a8 = git format-patch -1 --stdout 6e0fa629a0" },
  { v = 2, sha = "b11e27d5f9c60a420cbbe94fa967fc1454df92a6", ref = "refs/archive/staging/compaction-anchor-retention-v2", base = "aea969677c", note = "round 2; round-1 re-verifier head (3 problems); patch superseded-r02/compaction-anchor-retention.patch, sha256 90bea6dba82605dd49b94230b387b57dcba6da532e8bfa9cc76818146b1fa214 = git format-patch -1 --stdout b11e27d5f9" },
  { v = 3, sha = "30a746f7920c2b4101f121353778d94f5ce001b5", ref = "refs/heads/staging/compaction-anchor-retention", base = "040b6df2c4", note = "round 3 (current); patch compaction-anchor-retention.patch. Round 4 changed text and receipts only (new N02); round 5 changed text, the fold-in patch and the receipts that measure it. The head did not move" },
]
status = "STAGED"          # class ceiling at $0: LIMITED (P6: exam gates need OD-1 or OD-3); P5 PENDING (F14 not run); P9 and P10 PENDING until a blind read of the round-5 texts and fold-in patch
route = "support-note"     # on NousResearch/hermes-agent#117462 (fold-in offer). Fallback: core-leaf after #117462 lands or closes AND P6 is met
promotion_form = "support-note"   # unchanged in rounds 3, 4 and 5 (changed in round 2 from core-pr; see "Route and carrier choice")
feature = "compaction-identifier-anchor-retention"
invariant = "When an identifier of the classes 'delegation/kanban task id', 'dotted config key whose last segment is snake_case' (compression.tail_mode; not terminal.backend) or 'CLI error line / Hermes tool refusal' appears in the compacted region, the lean anchor index carries it verbatim, inside per-class caps and the unchanged 7,000-char budget, without changing any existing section's line (standalone commit on main: 180 of 180 synthetic regions; fold-in on #117462, rows appended after its last row: 180 of 180 synthetic and 3 of 3 real-text regions; the new sections only get the budget the existing ones leave), without capturing Python annotations or log format strings as error lines, and without capturing a mid-name fragment of a longer dotted name as a dotted key. Dotted keys whose last segment is one word are not captured: 270 of the 996 dotted DEFAULT_CONFIG paths (27.1%, N02)."

[base]
repo = "NousResearch/hermes-agent"
sha = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5"        # every round-3 number was measured on this main
fetched_at = "2026-10-01T07:20-05:00"
recheck = { main = "aaa863f7ff2dec1821be1652b5d15ad14ecea70b", at = "2026-10-01T11:55-05:00", commits_since_base = 25, files_changed = 64, relevant_note = "agent/context_compressor.py, hermes_cli/config_defaults.py, evals/ and the six neighbouring compressor test files are byte-identical to base; under agent/ and tests/agent/ only agent/kanban_stop.py, agent/model_metadata.py, agent/transports/hermes_tools_mcp_server.py, tests/agent/test_kanban_stop.py and tests/agent/test_model_metadata.py changed (none is a compressor file); main+#117462 merges clean (tree ee14a0acac) with the same compressor file as the c117462 arm", merge_tree = "clean (tree e2c14b39ee)" }
recheck_prev = [
  { main = "44a1ce9724502b9c692faaef00af3054bf11f1a6", at = "2026-10-01T11:10-05:00 (and 11:40 for the round-5 runs)", commits_since_base = 21, files_changed = 60, merge_tree = "clean (tree 337833232d)" },
  { main = "a3b56cac95488242856b6fb1f121842a38c3e391", at = "2026-10-01T07:41-05:00", commits_since_base = 4, relevant_paths_changed = 0, merge_tree = "clean" },
]

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
  { pr = 122522, author = "Nagisa-3000", head = "f596584b017694bf123d746a87740f58a2db15c1", role = "adjacent (opt-in summary_source=original, carrier for teknium's #122274); different mechanism; coordinate, not a member", merge_tree_vs_main = "clean (040b6df2c4; again on 44a1ce9724 and aaa863f7ff)", merge_tree_vs_branch = "clean (30a746f792)" },
  { pr = 109980, author = "Finn763", head = "82cb05f119a66d5cbe53dde8a5cc064ba2a9139a", role = "handoff block re-derivation; reads _LEAN_ANCHOR_HEADING, does not touch the table", merge_tree_vs_main = "CONFLICT on 040b6df2c4, 44a1ce9724 and aaa863f7ff (its own drift)" },
]
states_rechecked = "2026-10-01T11:53-05:00 (gh, read-only; ls-remote heads at 11:55): #117462, #122522, #109980 open with heads unchanged (2c19948e15, f596584b01, 82cb05f119); #117462 has 0 formal reviews and 2 issue comments (last update 2026-09-22); issues #122274 and #78457 open; #116246 merged 2026-09-19; #87326 merged 2026-08-16"
close_after = []
demand = { score = 0, source = "user demand thin (#78457 r=1); maintainer signal strong" }
maintainer_signal = "SCORECARD-2026-09-19-jev.md:28-30: 'the facts our summary loses (delegation ids, root causes, config keys, exact error strings) sat in assistant text. That is a summariser-retention target (anchor index / identifier capture)'; :107-108 asks to 'check its coverage on these three banks before touching anything else' (banks not committed; see NOT_TESTED)"

[[donors]]
sha = "30a746f7920c2b4101f121353778d94f5ce001b5"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "rows + tests (standalone commit and the content of foldin-on-117462.patch); no third-party code reused"
trailer = "Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"   # requested in body.md if Seldash folds the patch in

[[members]]
ref = "refs/pr/117462"
sha = "2c19948e15"
role = "carrier (Seldash): same function and table; foldin-on-117462.patch (round 5: the rows appended after its last row, errors) applies to its head exactly (no offset) and 7 of 7 tests in the two files pass there"
rebase = "merge-tree clean vs main 040b6df2c4 (tree f4139cef66), 44a1ce9724 (tree 7beb2da248) and aaa863f7ff (tree ee14a0acac); CONFLICT vs our standalone branch (both edit the table)"

[[members]]
ref = "refs/heads/staging/compaction-anchor-retention"
sha = "30a746f792"
role = "standalone commit: fallback core-leaf head, and the source of the fold-in rows/tests"
rebase = "on 040b6df2c4; merge-tree clean vs a3b56cac95, 44a1ce9724 (tree 337833232d) and aaa863f7ff (tree e2c14b39ee); no rebase needed (compressor and config_defaults byte-identical)"

[[members]]
ref = "refs/pr/122522"
sha = "f596584b01"
role = "adjacent (Nagisa-3000, opt-in summary_source=original); coordinate, not a member"
rebase = "merge-tree clean vs main 040b6df2c4 and vs our branch"

[ownership]
searched_at = "2026-10-01T04:20-05:00 (round 1); PR heads, states and comments re-read 2026-10-01T07:25-05:00, 11:10-05:00 and 11:53-05:00 (unchanged: #117462 open, head 2c19948e15, 0 formal reviews, 2 issue comments: kyssta-exe's review-style comment and Seldash's reply)"
queries = ["_ANCHOR_PATTERNS", "anchor index", "_build_anchor_index", "anchor_index", "anchor ledger", "identifier capture compaction", "compaction identifier", "summary_source"]
open_external = [117462]
merged_overlap = []
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # all TUI/HUD perf; no overlap
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found; siblings staging/compressor-media-extraction @ c5e8be14b4 (tree 74b5eb832e) and staging/compaction-hook-salvage @ 111f361fb0 (tree 78e8df607f; it was de819a7d06 at the 07:40 check) both merge-tree clean vs our branch (2026-10-01T11:10-05:00; same SHAs and trees again at 11:55)"
verdict = "EXTERNAL -> support: #117462 (open, Seldash) owns the _build_anchor_index rework; our classes are complementary and ride on it as a fold-in. Own core-leaf only as a fallback."

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
receipts = [
  { id = "RG01/r20261001-03", path = "receipts/RG01-redgreen.json", sha256 = "7d5d7073106720cbac0887d93ce351182dc91b974015d0ba67b3186669315db4" },
  { id = "E03p/r20261001-05", path = "receipts/E03p-gold-reachability.json", sha256 = "ac860565c1028ebbe3c96fe55e16fd9ae723996dd4745ea73a9609d481559ac7", note = "round 5: fold-in arm re-measured (identical per gold)" },
  { id = "E03s/r20261001-05", path = "receipts/E03s-synthetic-survival.json", sha256 = "61f6b9b9c5d44a4622b195c7280aaeec5c15bdbd722ab60aba0d6cc222493255", note = "round 5: fold-in arm re-measured; round-3 order kept as c117462_foldin_r03" },
  { id = "F02s/r20261001-05", path = "receipts/F02s-budget-audit.json", sha256 = "93066049d9c2d3d316bd4fcf04b29a13ef669369bd3f97cfa5e529a45a8eae63", note = "round 5: adds foldin_order (synthetic + real-text line comparison vs #117462) and build_cost_443k_char_region" },
  { id = "T01/r20261001-05", path = "receipts/T01-dot-chain-cost.json", sha256 = "89f2a3c0e2ca78773a8d1efb9e6a7a1865e403ff09ad71168ec2a629fd253e1d", note = "round 5: fold-in arm timing from the round-5 run" },
  { id = "N01/r20261001-03", path = "receipts/N01-noise-audit.json", sha256 = "abf0ad64e58866e8f2a44cf57f4d6e13c0a35f2d7e4c7b11f305d07f6d47004e", note = "unchanged; its arms block names the round-3 fold-in arm, whose N01 output is identical to the round-5 arm (reproduction_checks in the r05 receipts)" },
  { id = "AB117462/r20261001-05", path = "receipts/AB117462-carrier-compat.json", sha256 = "e2ff1e9a80bf216dc29ae762cc4defdd6ba342910bcd095b0f748a576dc0d14f", note = "round 5: new fold-in tests on 2c19948e15, 44a1ce9724 and aaa863f7ff; 12 of 12 fold-in sabotages re-RED" },
  { id = "N02/r20261001-04", path = "receipts/N02-config-key-coverage.json", sha256 = "9bb8d980e4b66861d9823aa7522ebbe27b1de24f37e3545bd3b62b66944d73f3", note = "round 4; built by harness/build_receipt_n02.py from raw/config_key_coverage.json (harness/config_key_coverage.py, sandboxed, 0 egress)" },
]
patches = [
  { path = "compaction-anchor-retention.patch", sha256 = "e6afea19bd5bb43a658cf3c9f6d63be5031bddb4f6701b8868c024baa8114709", note = "git format-patch -1 --stdout 30a746f792" },
  { path = "foldin-on-117462.patch", sha256 = "f2db42bef2c90360beb775de62f1bc4c2c944dea2fbab5672610dbcd957ceb8d", note = "round 5: git diff of #117462's head tree + our rows appended after errors (the standalone commit's rows block, byte-identical) + our test file; embedded verbatim in body.md. The round-3 patch (cheap-first order, sha256 3713e44b...) is in superseded-r04/" },
]
superseded = "superseded-r01/ (round 1) and superseded-r02/ (round 2): receipts, raw, harness, patches, STAGING and bodies; superseded-r03/ (round 3): STAGING and bodies only; superseded-r04/ (round 4): STAGING, bodies, the round-3 fold-in patch, the five r20261001-03 receipts replaced in round 5 and the round-3 fold-in test outputs; placeholders only; nothing there is cited"
red = { test = "tests/agent/test_context_compressor_anchor_index.py", main = "040b6df2c4", marker = "AssertionError: 'sa-2-7318d0ba' missing from anchor index", receipt = "RG01/r20261001-03" }
red_prev_rows = { rows = "b11e27d5f9 (round 2)", marker = "AssertionError: 'router.add_post' leaked into dotted keys", receipt = "RG01/r20261001-03" }
green = { reps = "3/3", receipt = "RG01/r20261001-03" }
negative_control = { mutation = "drop each new row (3/3) + 3 dotted-keys sabotages (mid-name guard, word-start guard, snake_case last segment) + 6 error-row sabotages (anchor, escaped-\\n anchor, quote/backtick anchor, re.M, placeholder guard, escaped-\\n stop): 12/12 re-RED", result = "RED", receipt = "RG01/r20261001-03", foldin = "the same 12 on 2c19948e15 + foldin-on-117462.patch: 12/12 re-RED (AB117462/r20261001-05)" }
adjacent = { identical = true, base = "365 passed (6 files)", head = "367 passed (7 files)", foldin = "372 passed, 0 failed (8 files) on 44a1ce9724 + #117462 + patch and again on aaa863f7ff + #117462 + patch", head_on_latest_main = "367 passed, 0 failed (7 files) on the merge of the branch into aaa863f7ff (tree e2c14b39ee; raw/r05/adjacent_branch_main_aaa863f7ff.full)", pre_existing = [] }
guards = { F14 = "NOT_RUN (the factory standing set is not built; it lives on staging/factory-replay-gate)", region_scoping = "ALL PASS base and head (2 fresh-home runs each); one F14 member, not the set", replay_gates = "11/11 PASS base and head; result dicts equal apart from compressor_sha256 (checkout path placeholder ignored); one F14 member, not the set" }
egress = "region_scoping: 2 DNS lookups of openrouter.ai per run (model-metadata fetch), blocked, on base and head alike; 0 connect attempts. replay_gates and the coverage harness: 0 attempts."
quantitative = []                  # no OBSERVED recall number exists yet
cache_read_ratio = { status = "N_A", why = "summary text changes only at a compaction event (already a cache break); cadence unchanged" }
route_scope = "local-compressor (lean tail mode); native compaction summaries are opaque"
not_tested = ["recall exam (E05/E04): aux LLM needed", "the 09-19 prreview/sysprompt/sigsegv banks the maintainer asked about (not committed)", "real lineages / state.db copies (forbidden in this run; OD-7)", "native compaction routes", "legacy tail mode (index not built there)", "precision on real transcripts (N01 used docs and agent/*.py)", "dotted keys whose last segment is one word (terminal.backend): not captured by design, 270 of 996 dotted DEFAULT_CONFIG paths (N02); how often such a key is the fact a real summary loses is not measured", "F14 standing guard set (only its region_scoping and replay_gates members were run)", "placement is measured (F02s foldin_order), not pinned by a unit test: moving the rows earlier would not turn a test red"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-compaction-anchor-retention", commit = "" }

[gates]
P1 = "PASS"       # RED on 040b6df2c4 (2026-10-01)
P2 = "PASS"       # route matches ownership: external #117462 -> support note with fold-in
P3 = "PASS"       # +10 prod lines (3 rows, 5 comment lines, 2 continuation lines), one test file, no env/config/hook
P4 = "PASS"       # production _build_anchor_index called directly, no mocks; compress() path exercised by region_scoping + test_lean_single_aux_call
P5 = "PENDING"    # RED, GREEN 3/3, 12/12 per-hunk sabotage, ADJ identical all pass; F14 standing guards NOT_RUN (only region_scoping and replay_gates, both equal), so not PASS. Was PASS in rounds 2-3 (overstated)
P6 = "PENDING"    # bodies make no recall claim; selection gate needs exam (OD-1 or OD-3) -> class LIMITED
P7 = "PASS"       # one commit on 040b6df2c4, author ok, merge-tree clean (also on a3b56cac95, 44a1ce9724 and aaa863f7ff), workflow push matches for staged/compaction-anchor-retention = 0
P8 = "PENDING"    # receipts hashed locally; not frozen to z0evals / ledger
P9 = "PENDING"    # round 4 self-marked PASS while body.md left out the fold-in's cost to #117462 (round-3 re-verifier); round 5 moved the rows so that cost is gone and states the remaining trade, but only a blind read can re-pass it
P10 = "PENDING"   # round-3 re-verifier read 30a746f792 + round-4 texts: 1 blocking + 5 advisory findings (fixed in round 5); needs a fresh blind read of the round-5 texts and fold-in patch
P11 = "RECORDED"  # maintainer-named target; user demand thin
P12 = "PENDING"   # staging cap / OD-8; Wave 0 not passed

[verification]
verifier = ""
provenance = "independent"
exact_head = "30a746f7920c2b4101f121353778d94f5ce001b5"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""
previous = [
  { head = "6e0fa629a0", verdict = "accept=false (7 problems; all addressed in round 2)" },
  { head = "b11e27d5f9", verdict = "round-1 re-verifier: 3 problems (error-row precision wording, dotted-keys quadratic backtracking, ref kept for the round-1 head); all addressed in round 3, see 'Round 3 changes'. All other numbers reproduced exactly." },
  { head = "30a746f792", verdict = "round-2 re-verifier: accept=false, 3 text problems (dotted-key invariant and bodies overstated config-key coverage; round-3 file list for aea969677c..040b6df2c4 incomplete; stale compaction-hook-salvage SHA); all addressed in round 4, see 'Round 4 changes'. Head unchanged." },
  { head = "30a746f792", verdict = "round-3 re-verifier: 1 blocking finding (the fold-in's cheap-first order took budget from #117462's files and errors lines, undisclosed in body.md, the invariant and Route; P9 self-marked PASS) and 5 advisories (first-person voice vs AI disclosure; 'applied on top of current main'; naming_exception needs owner acceptance; record current main; error-string coverage wording). All addressed in round 5 (option b: rows appended after errors), see 'Round 5 changes'. Head unchanged." },
]

[merge_check]
main_sha = "aaa863f7ff2dec1821be1652b5d15ad14ecea70b"
checked_at = "2026-10-01T11:55-05:00"
clean = true
tree = "e2c14b39eefd2c90edfdd75e40baf91d82a017d1"
recheck = "git merge-tree --write-tree main staging/compaction-anchor-retention   # clean on 040b6df2c4 (base), a3b56cac95 (07:41), 44a1ce9724 (11:10, tree 337833232d) and aaa863f7ff (11:55, tree e2c14b39ee); no rebase needed"

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

Promotion form: **support-note** on NousResearch/hermes-agent#117462 (route `support-note`), unchanged in rounds 3, 4 and 5. Status **STAGED**. The best class reachable at $0 is **LIMITED**, because the exam gates need an aux LLM. FACTORY §11.2 lets a LIMITED item ship only as a support note or a decision request. None of the re-verifiers' findings changes ownership or form.

## Round 5 changes (2026-10-01, fixes for the round-3 re-verifier on `30a746f792`)

The head did not move (`30a746f792`, v3). The standalone commit, its rows and the RG01, N01 and N02 receipts are unchanged. The fold-in patch was rebuilt, and the receipts that measure it were re-run (E03p, E03s, F02s, T01 and AB117462, now r20261001-05, built by `harness/build_receipts_r05.py` from `raw/coverage.json` and `raw/r05/`). Round-4 texts, the round-3 fold-in patch, the five replaced receipts and the round-3 fold-in test outputs are kept in `superseded-r04/`.

1. **Fold-in rows moved after `errors` (the blocking finding; option b).** In #117462, sections fill one shared 7,000-char budget in table order. The round-3 fold-in followed that PR's cheap-first order (`task ids` after `todo ids`, `dotted keys` before `files`), so #117462's own lines lost budget, and neither body.md, the invariant nor Route said so. Re-measured in round 5 on the same 180 synthetic regions (sandboxed, 0 egress; the round-3 arm reproduces its round-3 output exactly apart from timings):
   - Round-3 order: a #117462 line changed in 101 of 180 regions. In dense regions `files` went from a median 1,274 chars to its bare label in 59 of 60 and was removed in the 60th. In medium regions `errors` got shorter in 41 of 60. One planted existing-class needle was lost: `ModuleNotFoundError: No module named 'hermes_cli.dashboard_auth'` (medium, seed 1; 279 vs 280 of 460). On 3 regions built from `agent/*.py` at main `44a1ce9724` as read_file traffic (new `harness/foldin_order_check.py`), `dotted keys` took 1,020-1,088 chars of attribute access, and `errors` shrank from 2,334 to 1,321 chars (40 files) and from 1,318 to 308 (120 files).
   - Round-5 order: the three rows are appended after `errors`, #117462's last row, with the standalone commit's rows block byte for byte. The arm `raw/arms/c117462_foldin.py` (sha256 `35bb31c8…`) equals `git apply foldin-on-117462.patch` on main+#117462. No #117462 line changes: 180 of 180 synthetic regions and 3 of 3 real-text regions (F02s `foldin_order`). Existing-class survival equals #117462 in every density (280, 280 and 25 of 460).
   - New-class survival is the same as with the round-3 order: sparse 90/110, medium 20/110, dense 0/110 (E03s). E03p is identical per gold (31/49).
   - **The trade that remains.** The new sections only get what #117462 leaves. In the 60 dense synthetic regions, `task ids` keeps at least one value in 16 (31 bare labels, 13 absent), `dotted keys` appears only as a bare label in 2, and `error messages` appears in none. In medium regions `error messages` keeps a value in 7 of 60. In the real-text regions only `dotted keys` gets in, with 1-3 values. The round-3 order emitted these sections in every dense region, at #117462's expense. Once-mentioned needles rank last in both orders, so E03s cannot show this. What the appended order gives up is a new-class value that is repeated often in a dense region.
   - **Cost.** The three patterns take about 0.045 s together on the 443K-char synthetic region. #117462 runs every row, so its build goes from 0.037 s to 0.082 s (median of 7, new `harness/index_cost.py`). On main the loop stops at `errors` on that region, before the rows, so main and branch both stay at 0.029 s there. PR_BODY.md said "about 0.03 s with or without the new rows", which hid this; it is corrected.
   - **Tests.** 7 of 7 tests pass on `2c19948e15` + patch (no offset). On main `44a1ce9724` + #117462 + patch (offset +105): ours 2 of 2, theirs 5 of 5, and 372 of 372 across the 8 files. Again 372 of 372 on main `aaa863f7ff` + #117462 + patch. The 12 RG01 sabotages re-run on `2c19948e15` + patch: 12 of 12 re-RED.
   - Option (a), keeping the order and disclosing the cost, was not taken. The appended order keeps the same new-class survival and costs #117462 nothing, so there is no reason to ask Seldash to accept an emptied `files` line.

   body.md now says the rows come last and that no #117462 line changes, and it gives the trade and the cost one limits bullet each. The invariant (front matter and `## Invariant`) now holds for both the standalone commit and the fold-in, and says the new sections only get leftover budget. Placement, Route, NOT_TESTED (placement is measured, not unit-tested) and the evidence table are updated. P9 is back to PENDING: it was self-marked PASS while the fold-in's cost was undisclosed.
2. **Voice vs AI disclosure (advisory).** body.md and PR_BODY.md no longer say "I wrote the rows" or "Other checks I ran". Work Claude Code did is described neutrally ("The rows were written after reading those golds"). First person stays only for the offer, the credit request and the owner's own actions.
3. **"Applied on top of current main" (advisory).** body.md now says "With your PR merged into current main and this patch applied", which is what was run.
4. **Error-string coverage wording (advisory).** Both bodies now say that delegation ids and config keys have no row, and that exact error strings are only partly covered, because the `errors` row catches lines that contain an exception name.
5. **naming_exception (advisory).** Unchanged and still not owner-accepted. The front matter and Next steps now say it must be accepted before the push to `staged/compaction-anchor-retention`.
6. **Main recorded (advisory).** Upstream main moved to `aaa863f7ff` during this round. `[merge_check]` records it (11:55): 25 commits and 64 files past `040b6df2c4`. `agent/context_compressor.py`, `hermes_cli/config_defaults.py`, `evals/` and the six neighbouring test files are byte-identical. Merge-tree of the branch is clean (tree `e2c14b39ee`), and main+#117462 is clean (tree `ee14a0acac`) with the same compressor file as the c117462 arm, so no rebase is needed. The 8-file fold-in suite was re-run there (item 1), and so was the branch's own 7-file suite on that merge (tree `e2c14b39ee`): 367 of 367 pass, as on the head (`raw/r05/adjacent_branch_main_aaa863f7ff.full`). `agent/model_metadata.py` changed since `44a1ce9724`; the real-text corpus is declared at `44a1ce9724`.
7. **Pass/fail wording.** Both bodies now give counts as "N of M pass".

## Round 4 changes (2026-10-01, text and receipts only, fixes for the round-2 re-verifier on `30a746f792`)

The head did not move (`30a746f792`, v3). The patches and the r20261001-03 receipts are unchanged. Round-3 texts are kept in `superseded-r03/`.

1. **Dotted-key coverage limit stated (new receipt N02).** Round 3's invariant said any dotted config key in the compacted region is carried verbatim. The row only matches keys whose **last** segment is snake_case. Re-measured on the head (N02/r20261001-04, sandboxed, 0 egress): flattening `hermes_cli.config_defaults.DEFAULT_CONFIG` gives 1,095 key paths, of which 996 contain a dot. The row captures 726 of the 996 verbatim (72.9%) and misses 270 (27.1%). Every miss has a one-word last segment: `terminal.backend`, `compression.threshold`, `compression.enabled`, `browser.backend`, `checkpoints.enabled`. No path is partly matched. Counting leaf settings only (no section names), it misses 212 of 870 (24.4%). `config_defaults.py` is byte-identical on `040b6df2c4`, the head and main `44a1ce9724`, so the figures hold on all three. The front-matter invariant, the `## Invariant` section, the row table, "Label honesty", NOT_TESTED, body.md and PR_BODY.md now say "dotted keys whose last segment is snake_case" and state the miss rate. The code is unchanged. Allowing one-word last segments would let `config.yaml`, `api.openai.com` and `e.g` back in (that is what the rule is for), and nothing measures whether those keys matter more than the noise they would add.
2. **Round 3 item 4 file list corrected.** `git diff --name-only aea969677c 040b6df2c4` lists 37 files in 8 commits. Round 3 listed only the two `agent/` files, "one test file" and the docs page; there are three test files and 31 `apps/desktop/` files as well. Item 4 now gives the full breakdown. No conclusion changes, because every receipt was re-measured on `040b6df2c4` anyway.
3. **Sibling SHA refreshed.** `staging/compaction-hook-salvage` moved from `de819a7d06` to `111f361fb0`. Re-checked at 2026-10-01T11:10-05:00: `git merge-tree --write-tree 30a746f792 staging/compaction-hook-salvage` is clean (tree `78e8df607f`). `staging/compressor-media-extraction` is still `c5e8be14b4` and still clean (tree `74b5eb832e`).
4. **P5 PASS → PENDING.** FACTORY P5 requires the F14 standing guard set to be equal. Only two of its members ran (`test_region_scoping` and `replay_gates`, both equal on base and head). The set itself is not built yet, so P5 is PENDING, as on the sibling items. Rounds 2 and 3 marked it PASS, which overstated it.
5. **Main re-checked.** Current main is `44a1ce9724`, 21 commits and 60 files past `040b6df2c4`. `agent/context_compressor.py`, `hermes_cli/config_defaults.py`, `evals/` and `website/docs` are unchanged. In the round-3 relevant set only `tests/agent/test_kanban_stop.py` changed. `agent/kanban_stop.py` (+1 line) is in N01's `agent/*.py` corpus, but N01 was not re-run; its figures stay declared on `040b6df2c4`. Merge-tree of the branch is clean on `44a1ce9724` (tree `337833232d`). #117462 (head `2c19948e15`), #122522 and #109980 are open with unchanged heads, and #117462 still has 0 formal reviews. The fold-in patch therefore still targets the same head.
6. **AI disclosure in both bodies made exact.** They now say what Claude Code did (the rows, the tests, the checks and the text). The old wording, "I reviewed the patch and ran the tests above", claimed an owner review that has not happened yet.

## Round 3 changes (2026-10-01, fixes for the round-1 re-verifier on `b11e27d5f9`)

1. **Error-row precision wording corrected.** Round 2 said the row's 2 matches on `agent/*.py` were "both real messages". Re-measured on `040b6df2c4`, they are one error-message template, the f-string `Error: Invalid JSON arguments. {err}. "` at `agent/turn_tool_validation.py:217`, and one docstring line, `Blocked: internal skill-hub caches (prompt-injection carriers), credential` at `agent/file_safety.py:368` (`get_read_block_error`). The docstring line is prose. It shows that the unanchored `Blocked:` alternative catches any prose or docstring line containing `Blocked: `, and that limit is now stated in the `Blocked:` caveat (Round 2 item 3), the row table, N01, PR_BODY.md and body.md. `Blocked:` stays unanchored. Anchoring it like `fatal:`/`error:` would drop refusals that assistant text quotes mid-sentence, so this round states the limit and leaves the code as it is. The docs figure is also itemised now: 9 matches, of which 7 are quoted messages or message examples, 1 is a code example and 1 is a type annotation in a table (`error: str | None`).
2. **Dotted-keys backtracking fixed (code change).** The round-2 row could start a match after every `.` (it used `\b`), and each failing start re-scanned the rest of the chain. On a long unbroken `a.a.a…` chain that is quadratic: 6.2 s for the row alone on 40K chars. The row now begins with `(?<!\w)(?<!\w\.)` instead of `\b`, so a match starts only where a dotted name starts: not after a word character, and not after `x.`. Each chain is scanned from its first segment only, so the cost is linear: 1.3 ms on 40K chars and 6.9 ms on 200K chars (T01). Precision also improves. On the same corpora the guard removes 1 docs match and 2 code matches, all fragments of longer names (`router.add_post` from `self._app.router.add_post`, `wait_notice.should_emit`, `tb_frame.f_code.co_filename`). Nothing else changes (N01), and E03p and E03s are identical to round 2. A timing-free test pins the guard: `self._app.router.add_post(...)` must not yield `router.add_post`. That assertion is RED on the round-2 rows, and dropping either lookbehind re-REDs it (RG01, 12/12 sabotages). Main's own `files` row has the same kind of cost on that input (2.55 s on 40K chars). This slice doesn't touch it, and on that input the index takes the same time with or without the new rows.
3. **Earlier heads kept.** Round 2 moved the local ref from `6e0fa629a0` to `b11e27d5f9` and kept no ref to the old head. Now `refs/archive/staging/compaction-anchor-retention-v1` points at `6e0fa629a0`, and `-v2` points at `b11e27d5f9`. The local branch was then moved to `30a746f792`, as the orchestrator directs. Neither branch was ever pushed. The superseded format-patches are in `superseded-r01/` (sha256 `26f8485a…`, which equals `git format-patch -1 --stdout 6e0fa629a0`) and `superseded-r02/` (sha256 `90bea6db…`, which equals the same for `b11e27d5f9`). The front-matter `naming_exception` records the in-place update as a deviation from the FACTORY §10 naming rule, pending owner acceptance.
4. **Rebased and re-measured.** The commit now sits on main `040b6df2c4`, 8 commits past `aea969677c`. Between the two, 37 files changed: `agent/model_metadata.py`, `agent/usage_pricing.py`, three test files (`tests/agent/test_credential_pool_codex_quota_probe_rotation.py`, `tests/hermes_cli/test_auth_codex_quota_probe.py`, `tests/hermes_cli/test_gpt6_tiers_registration.py`), `website/docs/developer-guide/context-compression-and-caching.md` and 31 files under `apps/desktop/`. (Corrected in round 4. Round 3 said "one test file" and left out the desktop files.) Every receipt was re-measured on `040b6df2c4` (r20261001-03). Six arms were measured: base, branch, #117462, the fold-in, round-1 rows and round-2 rows. The fold-in patch was rebuilt and now also passes both test files on #117462's own head (7 passed). The former NOT_TESTED line "fold-in not tested on #117462's own base" is gone.

## Round 2 changes (2026-10-01, fixes for the phase-3 verifier; kept for history)

1. **F02s claim corrected.** The old "0/720 regions" spanned 4 arms. This PR's arm is 180 regions; its index peaks at **7,190** chars (sections 6,998). The 7,193 figure was the fold-in arm. Staying under 7,000 section chars is guaranteed by the loop, so it is no longer reported as a finding.
2. **09-19 check stated as not run.** SCORECARD-2026-09-19-jev.md:107-108 asks for a coverage check on its prreview/sysprompt/sigsegv banks. Those banks are not committed: `jev-cycles-2026-09-19/*.json` contain no golds. Both bodies say the check could not be run, and why.
3. **Circularity disclosed.** The 24 → 31 gold count is in-sample: the rows were written after reading those golds. The 5 new error-line golds are only **2 distinct strings**: Hermes's own ``Blocked: `git …` would rewrite …`` guard refusal (3 golds) and one gh `GraphQL: … (mergePullRequest)` error (2 golds). `Blocked:` is labelled as a Hermes tool-refusal prefix, not a CLI error line. The prefix opens about 30 refusal messages across 15 files in `tools/`, `cron/`, `plugins/` and `agent/` (32 quoted literals in 15 files on `040b6df2c4`). **`Blocked:` is matched anywhere in a line, so it also catches prose and docstrings that use `Blocked: ` that way (added in round 3; one of the 2 `agent/*.py` matches is such a docstring line).**
4. **Error row tightened (code change).** `fatal:`/`error:` count only where a line starts, or after a quote, a backtick or a JSON-escaped `\n`. The row skips `%s`/`{}` placeholders, and a value stops at an escaped newline. On public `agent/*.py` (251 files) the row matches **2** strings: one error-message template and one docstring line (wording corrected in round 3; round 2 said "both real messages"). Before tightening it matched 80, nearly all annotations or log formats. On the docs it matches 9 instead of 24. The precision test pins this: annotations and `"error: %s"` must stay out. The verbatim test adds a JSON terminal-output case and a backtick-quoted case. The cost: the MODELED emitter-line column drops 35 → 34, and sparse synthetic survival drops 100 → 90 of 110. Both losses are the GNU as `Fatal error: error writing …` line, where `error:` does not start a line. **Dotted-keys limitation stated, not changed:** on `agent/*.py`, 9 of the 40 most frequent values are `self.*` and none is a DEFAULT_CONFIG key.
5. **Provenance.** Every receipt was re-measured on one declared main, **aea969677c** (round 3 re-measured them all again on **040b6df2c4**). The harness ran on a checkout of the new head, which differs from that main only in the two files of the commit. The round-1 claim that "the 11 commits between touch no relevant file" was wrong, and it is gone. Receipts no longer contain absolute local paths.
6. **Route and ownership.** #117462 is an open external PR on the same function and table, so FACTORY P2 calls for support, not a competing PR. The route is `support-note`, and the origin action is a single fold-in offer on #117462 (`body.md`). Core-leaf stays recorded only as a fallback (see Origin action).
7. **Minor fixes.** replay_gates results are "equal apart from compressor_sha256". Egress is measured with a socket/DNS logger in fresh homes. The reconstruct_lineage command is one invocation per root. On #117462, the positive "review" is a plain issue comment from a User account (kyssta-exe, signed "Reviewed using Hermes-Agent"); the PR has 0 formal reviews.
8. **OD-0 resolved** by the rename: the fork branch will be `staged/compaction-anchor-retention`.

## Invariant

If a delegation or kanban task id (`sa-2-7318d0ba`, `t_4f9c2a1e`), a dotted config key whose last segment is snake_case (`plugins.stream_reasoning_deltas`, `compression.tail_mode`) or an error line appears in the compacted region, the lean anchor index keeps it verbatim. Dotted keys whose last segment is one word (`terminal.backend`, `compression.enabled`) are **not** kept: that is 270 of the 996 dotted paths in `DEFAULT_CONFIG` (27.1%; 212 of 870 leaf settings), measured in N02. Error lines include CLI errors (`fatal: …`, `error: …`, `error TS2741: …`, `GraphQL: … (mergePullRequest)`) and Hermes tool refusals (`Blocked: …`). The index stays inside per-class caps and the unchanged 7,000-char budget, and no existing section's line changes. That holds for the standalone commit on main (180 of 180 synthetic regions, F02s) and for the fold-in on #117462, where the rows are appended after that PR's last row (180 of 180 synthetic and 3 of 3 real-text regions, F02s `foldin_order`). The price is that the new sections only get the budget the existing ones leave, so in dense regions they are mostly cut. Python annotations (`error: Exception)`) and log format strings (`"error: %s"`) are not captured as error lines. A fragment of a longer dotted name (`router.add_post` inside `self._app.router.add_post`) is not captured as a dotted key.

Call path: `ContextCompressor.compress()` calls `_augment_summary_lean()` (lean mode only), which calls `_redact_compaction_text(_build_anchor_index(turns_to_summarize))` (`agent/context_compressor.py:3645` on main, `:3655` on the branch). The contract tests call the production `_build_anchor_index` directly, without mocks. `evals/compaction/test_region_scoping.py` and `tests/agent/test_lean_single_aux_call.py` exercise the full `compress()` path.

## Route and carrier choice

- **Carrier: NousResearch/hermes-agent#117462** (Seldash, opened 2026-09-20, labels P2 / area/compression, 0 formal reviews). It has one review-style issue comment from kyssta-exe, a User account, signed "Reviewed using Hermes-Agent", with the verdict "Looks good to merge", and Seldash's reply. Seldash pushed follow-ups in `2c19948` on 2026-09-22. The PR reworks `_build_anchor_index`: it harvests tool-call arguments, puts cheap ids first, truncates per section instead of using `break`, and adds session ids, todo ids and more path extensions.
- **Why support, not a separate PR.** Both PRs edit the same table, so they conflict, and #117462 owns the rework. Our three classes are complementary: our tests are RED on #117462, and 3 of its 5 tests are RED on our branch. With `foldin-on-117462.patch` applied, both suites are GREEN: on #117462's own head (7 of 7) and on main+#117462, where the 8-file adjacent suite gives 372 of 372 (on `44a1ce9724` and again on `aaa863f7ff`). Since round 5 the fold-in appends the rows after `errors`, #117462's last row, so no #117462 line changes (180 of 180 synthetic and 3 of 3 real-text regions). The new sections only get what #117462 leaves and are mostly cut in dense regions (see Placement). In medium-density synthetic regions, 20/110 once-mentioned new-class needles survive on the fold-in vs 17/110 for the standalone commit on main (MODELED). The round-3 fold-in used #117462's cheap-first order and took budget from its `files` and `errors` lines; that cost was not disclosed (round-3 re-verifier) and is gone now. Under FACTORY P2, an external owner means support. Under FACTORY §11.2, a LIMITED item ships only as a support note.
- **#122522 / #122274** (`summary_source=original`): a different mechanism. Merge-tree is clean in both directions. FACTORY §11.4 had pencilled #122522 as the support target. That was re-checked: it does not touch the anchor table, so it is adjacent only.
- **Fallback (not an origin action today).** If #117462 lands without the rows, or closes, *and* P6 is met (E05 → E04), re-stage the standalone commit as core-leaf. Rebase the table first if #117462 landed. PR_BODY.md is the draft for that case.
- **Sibling dependency.** `staging/compressor-media-extraction` (`c5e8be14b4`) and `staging/compaction-hook-salvage` (`111f361fb0`; it was `de819a7d06` at the 07:40 check) both merge-tree clean against `staging/compaction-anchor-retention` (re-checked 2026-10-01T11:10-05:00 and again at 11:55 with the same SHAs and trees). Recheck if any of them moves.

## Premise re-check on current main

- **Still needed.** The `_ANCHOR_PATTERNS` table at `agent/context_compressor.py:1057` on `040b6df2c4` is unchanged since `c4bbb14e52`. No row matches subagent ids (the commits row needs 9+ hex chars), dotted keys, or error lines that lack an exception class name.
- **Main drift.** `040b6df2c4` → `a3b56cac95` is 4 commits, and none touches `agent/context_compressor.py`, `tests/agent/`, `evals/compaction/`, `evals/token_accounting/`, `website/docs`, `AGENTS.md` or `hermes_cli/config_defaults.py`. Re-checked in round 4 on `44a1ce9724` (21 commits, 60 files past `040b6df2c4`): of that set only `tests/agent/test_kanban_stop.py` changed, and it is not a compressor test. `agent/kanban_stop.py` changed by one line; it is in N01's `agent/*.py` corpus, and N01 was not re-run. Merge-tree is clean on all three mains. Round 5 re-checked on `aaa863f7ff` (25 commits, 64 files past `040b6df2c4`): under `agent/` and `tests/agent/` only `agent/kanban_stop.py`, `agent/model_metadata.py`, `agent/transports/hermes_tools_mcp_server.py`, `tests/agent/test_kanban_stop.py` and `tests/agent/test_model_metadata.py` changed, none of them a compressor file; merge-tree is clean (tree `e2c14b39ee`).

## The commit

`30a746f792` "fix(compression): anchor index keeps task ids, dotted keys and CLI error lines". Author Kevin Rajan, on `040b6df2c4`, 2 files, +100 (10 production lines, 90 test lines). The commit message ends with the `Co-Authored-By: Claude Opus 5.5` trailer. No third-party code or idea is reused, so no other credit is due.

| row (appended after `urls`) | regex | cap |
|---|---|---|
| `task ids` | `\b(?:sa-\d+-[0-9a-f]{8}\|t_[0-9a-f]{8})\b` (from `tools/delegate_tool.py:195`, `hermes_cli/kanban_db.py:1089`) | 40 |
| `dotted keys` | dotted lowercase name whose **last** segment is snake_case, which excludes file names, hosts and `e.g`. The same rule drops config keys whose last segment is one word (`terminal.backend`): 270 of the 996 dotted `DEFAULT_CONFIG` paths, 27.1% (N02). It starts only where a dotted name starts: `(?<!\w)(?<!\w\.)`, so not after a word character and not after `x.`. That keeps fragments out and the scan linear. | 40 |
| `error messages` | `fatal:`/`[Ee]rror:` only at a line start, after a quote or backtick, or after a JSON-escaped `\n` (`re.M`). `\berror TS\d{4,5}:`, `\bGraphQL:` and `\bBlocked:` anywhere, so `Blocked:` also matches prose and docstrings. Then not `%`/`{`, 8-110 chars, stopping at a real or escaped newline. | 20 |

Rows were chosen from the evidence (in-sample, see Round 2 item 3):

- Error lines: 9 golds across 3 lineages, 0 of them reachable on main. The rows reach 5, which are 2 distinct strings.
- Task id: 1 gold, plus the maintainer naming "delegation ids".
- Config key: 1 gold, plus the maintainer naming "config keys".
- **Env-var names: no row.** There are 0 golds and the maintainer did not name them.
- **Bare symbols: no row.** This is the largest remaining class (6 golds, 4 lineages), but a bare identifier row would be dominated by frequent code tokens.

**Placement.** On main, `_build_anchor_index` `break`s at the first section that overflows the budget. A new row placed before `files` could therefore delete the whole `files` line in dense regions. So the rows are **appended**, and existing lines stay byte-identical in 180/180 synthetic regions (F02s). The cost is that new sections only get leftover budget on main. Since round 5 the fold-in for #117462 uses the same placement: the rows go after `errors`, that PR's last row. #117462 has no `break`, but its sections share the budget in table order, so a row placed early takes budget from every row after it. The round-3 fold-in followed #117462's cheap-first order (`task ids` after `todo ids`, `dotted keys` before `files`). That changed a #117462 line in 101 of 180 synthetic regions and emptied its `files` line in all 60 dense ones (F02s `foldin_order`). With the rows appended, no #117462 line changes (180/180 synthetic, 3/3 real-text), new-class survival is the same (E03s), and the new sections are mostly cut in dense regions instead: in the 60 dense regions `task ids` keeps a value in 16, `dotted keys` and `error messages` in none.

Label honesty: `dotted keys`, not `config keys`. On the docs corpus, 29.7% of distinct values are `DEFAULT_CONFIG` keys. On Python source it is mostly attribute access (N01). Nor does it cover all config keys: it captures 726 of the 996 dotted `DEFAULT_CONFIG` paths, and every miss has a one-word last segment (N02).

## Evidence (experiments run, all $0)

Receipts are in `receipts/`: RG01 and N01 at r20261001-03, N02 at r20261001-04, and E03p, E03s, F02s, T01 and AB117462 at r20261001-05 (round 5, the fold-in arm re-measured). Every number was measured on main `040b6df2c4` and head `30a746f792`, with these round-5 exceptions: the fold-in tests ran on `2c19948e15`, on `44a1ce9724` + #117462 and on `aaa863f7ff` + #117462, and the real-text regions use `agent/*.py` at `44a1ce9724`. Inputs are pinned by SHA and sha256 inside each receipt. The harness is `harness/anchor_coverage.py` (plus `harness/foldin_order_check.py` and `harness/index_cost.py` in round 5); `harness/build_receipts.py` wrote the r20261001-03 receipts from `raw/`, and `harness/build_receipts_r05.py` writes the r20261001-05 receipts from `raw/coverage.json` and `raw/r05/`. Guard and harness runs used `harness/sandbox.sh`, which applies:

- bwrap with no network: connect returns ENETUNREACH, and the systemd-resolved socket is masked, so DNS fails.
- The live Hermes install masked except the venv, and a fresh HOME/HERMES_HOME per run. Homes sit on a non-/tmp disk, because the sandbox mounts `<home>/tmp` over `/tmp`.
- An egress logger (`harness/egress_sitecustomize.py`) that records every non-loopback lookup or connect.

Tests ran with `HOME=$S/testhome-sf-compaction-anchor-retention` (round 5: `$S/testhome-sf3-compaction-anchor-retention`).

| experiment | receipt | verdict | label | n | result |
|---|---|---|---|---|---|
| RG01 red/green | `RG01-redgreen.json` | KEEP | OBSERVED | 2 tests | RED on main: 2 failed (`'sa-2-7318d0ba' missing from anchor index`; `assert 'compression.tail_mode' in ''`). The round-2 rows fail 1 of 2 (`'router.add_post' leaked into dotted keys`). GREEN 3/3. All 12 single mutations re-RED. Adjacent: 365 passed on base vs 365+2 on head (6 files). `test_region_scoping` ALL PASS on both, 2 runs each. `replay_gates` 11/11 PASS on both; result dicts are equal apart from `compressor_sha256`. Egress: 2 blocked openrouter.ai lookups per region_scoping run on both arms, 0 elsewhere. |
| E03p gold reachability (stands in for E03) | `E03p-gold-reachability.json` | KEEP (in-sample) | OBSERVED (emitter-line column MODELED) | 90 golds, 49 identifier | Identifier golds the rows can capture: main **24/49**, branch **31/49**, #117462 24/49, fold-in 31/49 (round-5 order; identical per gold to the round-3 order, since order does not enter this measure). The 7 new ones are 5 error lines (3× the `Blocked:` git-guard refusal, 2× one gh GraphQL merge-conflict error), 1 subagent id and 1 config key. Rows were written from these golds. With the emitter line (MODELED): 25 → 34. Per gold identical to the round-2 rows. |
| E03s synthetic survival | `E03s-synthetic-survival.json` | PARTIAL | MODELED | 180 regions/arm | Needles in the new classes that survive: sparse main 0/110, branch 90/110, fold-in 90/110. Medium branch 17/110, fold-in 20/110 (round-3 order also 20/110; error lines 0/90 on every arm). Existing classes on the fold-in equal #117462 in every density (280, 280, 25 of 460); the round-3 order lost one (medium 279/460). Dense: almost no once-mentioned needle of any class survives on any arm (main 13/570, #117462 and fold-in 25/570; new classes 0/110 everywhere). Frequency-first ranking plus the 7K budget is the binding limit, not the row set. Branch identical to the round-2 rows. |
| F02s budget audit (stands in for F02) | `F02s-budget-audit.json` | KEEP | OBSERVED (tokens MODELED) | 180 regions per arm | Branch index max **7,190** chars including heading (sections 6,998), about 1,797 tokens (chars/4), against the 32,000-token `RETAINED_SUMMARY_TOKEN_BUDGET`. Other arms: base 6,451, #117462 7,186, fold-in 7,193. Section chars ≤ 7,000 holds by construction on every arm. Base sections are a prefix of branch sections in 180/180. #117462 sections are a prefix of fold-in sections in 180/180 synthetic and 3/3 real-text regions (round-3 order: 0/180; a #117462 line changed in 101). Index build on a 443K-char region (median of 7): main 0.029 s, branch 0.029 s (the loop stops at `errors` there, before the rows), #117462 0.037 s, fold-in 0.082 s; the three patterns take 0.045 s together wherever they run. |
| T01 dot-chain cost (new) | `T01-dot-chain-cost.json` | KEEP | OBSERVED | 3-5 sizes × 5 arms, single runs | `dotted keys` row alone on `'a.'*20000` (40K chars): branch 0.0013 s vs round-2 row 6.15 s, which grows about 4× per doubling. Branch on `'a.'*100000` (200K chars): 0.0069 s, linear. Whole index on 40K chars: main 2.58 s, branch 2.56 s, round-2 rows 8.71 s; #117462 2.58 s (round-3 run), fold-in 2.76 s (round-5 run); single runs on a shared host. Main's time is its existing `files` row (2.55 s alone), which this slice doesn't change. Pinned by the timing-free mid-name assertion. |
| N01 noise audit | `N01-noise-audit.json` | KEEP | OBSERVED | docs 448 files / 7.8M chars; `agent/*.py` 251 files / 5.9M chars | Docs: task ids 4 matches, 2 distinct (doc examples). Dotted keys 1,031 distinct, 306 in `DEFAULT_CONFIG`. Error messages 9 matches (round-1 rows: 24): 7 quoted messages or message examples, 1 code example, 1 type annotation in a table. Code: error messages **2 matches: one error-message template (`agent/turn_tool_validation.py:217`) and one docstring line (`agent/file_safety.py:368`)**. The unanchored `Blocked:` also matches prose (round-1 rows: 80, nearly all annotations or log formats). Dotted keys: 1,955 distinct; top 40 = 9 `self.*`, 0 config keys (**limitation**). The mid-name guard removes 1 docs and 2 code matches vs round 2, all fragments. |
| N02 config-key coverage (round 4) | `N02-config-key-coverage.json` | KEEP (limit disclosed) | OBSERVED | 996 dotted `DEFAULT_CONFIG` paths (870 leaf) | The `dotted keys` row captures 726 of 996 verbatim (72.9%) and misses 270 (27.1%). Leaf settings only: 658 of 870 captured, 212 missed (24.4%). Every miss has a one-word last segment (`terminal.backend`, `compression.threshold`, `compression.enabled`, `browser.backend`, `checkpoints.enabled`), and no path is partly matched. Sandboxed, 0 egress. `config_defaults.py` is byte-identical on base, head, `44a1ce9724` and `aaa863f7ff`. |
| AB117462 carrier compatibility | `AB117462-carrier-compat.json` | KEEP | OBSERVED | 3 arms × 2 suites, plus #117462's own head | On main+#117462: ours 0 of 2 pass, theirs 5 of 5. Fold-in (round 5, on `44a1ce9724` + #117462 + patch): ours 2 of 2, theirs 5 of 5, adjacent 8 files 372 of 372; again 372 of 372 on `aaa863f7ff`. On #117462's head + fold-in patch: 7 of 7. On branch: ours 2 of 2, theirs 2 of 5. 12 of 12 sabotages re-RED on #117462's head + patch. The fold-in patch applies to the #117462 head exactly, and to main+#117462 at offset +105, giving the tested arm. |

Raw outputs (synthetic or public only) are in `raw/` (round 5 in `raw/r05/`). Arm sources are in `raw/arms/`: base, branch, c117462, c117462_foldin (round-5 order), and c117462_foldin_r03 (round-3 order), branch_r01 and branch_r02 for comparison. Egress logs are in `raw/egress/` and `raw/r05/egress/` (all three round-5 runs: 0 attempts).

## Acceptance gates (from selection.json)

| gate | status | evidence |
|---|---|---|
| E03 shows ≥1 missing class with frequency evidence on ≥3 frozen **local** lineages | **pending** (proxy met, in-sample) | Local lineages are not allowed in this run (state.db) and need OD-7. On the committed banks, the error-line class is missing on 3 lineages (9 golds). |
| Unit tests RED on main, GREEN with the rows | **met** | RG01 |
| Negative control: dropping a row re-REDs | **met** | RG01 (3/3 rows, plus 9 precision/anchor/guard sabotages); the same 12 on the fold-in, 12/12 (AB117462) |
| Index ≤7,000 chars and summary <32k tokens on every frozen lineage | **pending** (synthetic: sections ≤7,000 by construction; branch index ≤7,190 chars) | Real lineages need OD-7. Whole-summary tokens are NOT_MEASURED. |
| Exam: anchor-v2 beats current+recovery on a frozen mix, n≥3 reps per lineage, by more than the E05 SD, with no lineage regressing beyond the SD | **not-met** (queued) | E05, then E04 below. Needs OD-1 or OD-3. |
| `evals/compaction/test_region_scoping.py` and `token_accounting/replay_gates.py` unchanged | **met** | Files untouched. Verdicts equal on base and head (RG01). |
| Body states local-route-only scope | **met** | body.md and PR_BODY.md |
| Only aggregate receipts published; lineages never pushed (K1) | **met** | No lineages were used. Inputs are committed upstream text plus seeded synthetic data. |

## Gate checklist (P1-P12)

- P1 Need: PASS. RG01 RED on `040b6df2c4`, 2026-10-01.
- P2 Ownership: PASS. The route matches ownership: #117462 is external and open, so this ships as a support note with a fold-in. Claimant lanes #127373/#127374/#127375/#127332/#127228 are all TUI or HUD perf.
- P3 Shape: PASS. +10 production lines and one test file. No env var, config key, hook or prompt change.
- P4 Real path: PASS. The production function runs with no mocks.
- P5 Proof: PENDING. RED, GREEN 3/3, 12/12 sabotages re-RED with no hunk unpinned, and ADJACENT identical all pass (RG01). FACTORY P5 also needs the F14 standing guards equal. Only two F14 members ran (`test_region_scoping` and `replay_gates`, equal on base and head), and the set is not built yet. Rounds 2 and 3 said PASS, which was overstated (corrected in round 4).
- P6 Numbers: PENDING. Neither body makes a recall claim. The selection's exam gate needs E05 then E04, so the class is LIMITED.
- P7 Package: PASS. One commit, merge-tree clean on `040b6df2c4`, `a3b56cac95`, `44a1ce9724` and `aaa863f7ff`, 0 workflow push matches for `staged/compaction-anchor-retention`. Push triggers are only `main`, `wine2e/**`, `wine2e-install/**` and tags `v*`.
- P8 Freeze: PENDING. Receipts are hashed here but not frozen to z0evals or the ledger.
- P9 Text: PENDING. Round 4 self-marked it PASS while body.md left out the fold-in's cost to #117462's lines. Round 5 removed that cost (rows appended) and states the remaining trade and the build-time cost, but only a blind read can re-pass it.
- P10 Independent read: PENDING. The round-3 re-verifier read `30a746f792` and the round-4 texts and returned 1 blocking finding and 5 advisories, all addressed in round 5. A fresh blind read of the round-5 texts and the rebuilt `foldin-on-117462.patch` is needed.
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
- **Arms.** Worktrees `$WT/base` @ `040b6df2c4` (or the then-current main) and `$WT/branch` @ `30a746f792`. Optionally add `$WT/c117462` (main + #117462) and `$WT/foldin` (c117462 + `foldin-on-117462.patch`). The fold-in arm is the one that matters for the support route.
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
- Precision on real transcripts. N01 used docs and `agent/*.py`, not sessions. The dotted-keys row is known to fill with attribute accesses on Python source, and the unanchored `Blocked:` alternative also catches prose and docstrings.
- Config keys whose last segment is one word (`terminal.backend`, `compression.enabled`). The row does not capture them by design: 270 of the 996 dotted `DEFAULT_CONFIG` paths (N02). How often such a key is the fact a real summary loses has not been measured; the one config-key gold (`plugins.stream_reasoning_deltas`) is snake_case.
- The F14 standing guard set. Only its `test_region_scoping` and `replay_gates` members were run (P5 PENDING).
- Native compaction routes (`codex_responses_native` and others): summaries are opaque. The index adds at most about 1.8k tokens (MODELED) against the 32k retained-summary carrier.
- Legacy tail mode: `_augment_summary_lean` is a no-op there.
- Whole-suite `pytest tests/`: only targeted files were run.
- Interplay with #109980 (handoff block), which conflicts with main on its own.
- Row placement is measured (F02s `foldin_order`, 180 synthetic and 3 real-text regions), not pinned by a unit test: moving the rows earlier in either table would not turn a test red.
- Regex cost beyond dot chains: T01 covers only long `a.a.a…` runs. A `dotted keys` value also has no length cap (neither does main's `files` directory part), so one value longer than the 7,000-char budget would end the index at that section through main's existing `break`. Not changed here.

## Origin action (owner only)

One comment on NousResearch/hermes-agent#117462, with the text in `body.md`. It offers `foldin-on-117462.patch` (three rows appended after that PR's last row, plus one test file) to Seldash, asks for credit as `Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>`, and gives an easy decline. The factory does not post it.

There is no standalone PR while the class is LIMITED. If #117462 lands without the rows, or closes, and E05/E04 meet the exam gate, re-stage the standalone commit as core-leaf (rebasing the table first if #117462 landed) and use PR_BODY.md as the draft.

## Next steps

1. Blind verifier on exact head `30a746f792`, the round-5 texts and the round-5 `foldin-on-117462.patch` (P9, P10). The oracle is the RG01 commands, `foldin-on-117462.patch` on `refs/pr/117462`, `harness/foldin_order_check.py` (placement), `harness/index_cost.py` and `harness/config_key_coverage.py` (N02).
2. F14 standing guard set on base vs head once `staging/factory-replay-gate` provides the runner (P5).
3. Owner: decide whether to post `body.md` on #117462, and whether to accept the `naming_exception` (in-place local ref, earlier heads under `refs/archive/`). The exception must be accepted before the push to `staged/compaction-anchor-retention`.
4. OD-1 or OD-3, then E05, then E04 (on the fold-in arm while #117462 is open). OD-7, then E03-local and F02-local (harness extension above).
5. Daily drift check: `git diff --name-only 040b6df2c4..main -- agent/context_compressor.py tests/agent/test_lean_single_aux_call.py evals/compaction/` plus `git merge-tree --write-tree main staging/compaction-anchor-retention`. Re-run if #117462, compressor-media-extraction or compaction-hook-salvage moves.
6. Follow-up candidates (not in this slice): a recency or diversity tie-break for count-1 values, since once-mentioned needles die in dense regions on every arm (E03s). Separately, a guard against attribute-access domination in `dotted keys`, and whether one-word-leaf config keys (N02) deserve a narrower row, both of which need real-transcript precision data first.

## History

- 2026-10-01T03:55-05:00 | CANDIDATE | builder (Claude Code) | Premise re-checked. #117462 found to be complementary.
- 2026-10-01T04:00-05:00 | EVIDENCED | builder | RED/GREEN/NEG/ADJ on 572e4f4fad. E03p/E03s/F02s/N01/AB117462 run.
- 2026-10-01T04:13-05:00 | STAGED | builder | Rebased to 234badf401 as 6e0fa629a0. Local branch `staging/compaction-anchor-retention` set.
- 2026-10-01T06:02-05:00 | STAGED (verifier: accept=false) | phase-3 verifier | 7 problems: F02s arm count, 09-19 check unstated, in-sample gold count, error-row precision, receipt provenance, route/ownership, minor accuracy.
- 2026-10-01T06:36-05:00 | STAGED (round 2) | staging fixer (Claude Code) | Error row tightened and tests extended. New head b11e27d5f9 on aea969677c. All receipts re-measured on that main (r20261001-02, no local paths). Route changed to support-note on #117462 (body.md); PR_BODY.md kept as the core-leaf fallback. OD-0 resolved by the `staged/<id>` fork name. Local branch forced to b11e27d5f9, with no ref kept for 6e0fa629a0 (repaired in round 3); round-1 material moved to `superseded-r01/`.
- 2026-10-01T07:45-05:00 | STAGED (round 3) | staging fixer (Claude Code) | Fixes for the round-1 re-verifier on b11e27d5f9 (3 problems). Error-row precision wording corrected (one template + one docstring line; unanchored `Blocked:` limit stated). Dotted-keys row given a mid-name guard: linear on long dot chains, pinned by a timing-free test (12/12 sabotages). Earlier heads kept as `refs/archive/staging/compaction-anchor-retention-v1`/`-v2`; naming deviation recorded. New head 30a746f792 on 040b6df2c4; all receipts re-measured there (r20261001-03, new T01); fold-in patch rebuilt and passing on #117462's own head. Local branch moved to 30a746f792; round-2 material moved to `superseded-r02/`. Form unchanged (support-note).
- 2026-10-01 (results file written 11:00-05:00) | STAGED (verifier: accept=false) | round-2 re-verifier | 3 text problems on 30a746f792: dotted-key invariant and bodies overstated config-key coverage (270 of 996 dotted DEFAULT_CONFIG paths missed); round-3 file list for aea969677c..040b6df2c4 incomplete; stale compaction-hook-salvage SHA.
- 2026-10-01T11:25-05:00 | STAGED (round 4, text and receipts only) | staging fixer (Claude Code) | Head unchanged (30a746f792). Invariant narrowed to dotted keys whose last segment is snake_case; miss rate stated in the row table, NOT_TESTED, body.md and PR_BODY.md, backed by new receipt N02/r20261001-04 (726 of 996 captured; every miss has a one-word last segment). Round 3 item 4 file list corrected (37 files). Sibling compaction-hook-salvage refreshed to 111f361fb0, merge-tree clean. P5 PASS → PENDING (F14 not run). Main re-checked on 44a1ce9724 (clean; compressor and config_defaults unchanged); cited PR/issue states re-read. AI disclosure in both bodies made exact. Round-3 texts kept in `superseded-r03/`. Form unchanged (support-note).
- 2026-10-01 (after round 4) | STAGED (verifier: accept=false) | round-3 re-verifier | 1 blocking finding on 30a746f792 + round-4 texts: the fold-in's cheap-first order took budget from #117462's `files` and `errors` lines (101 of 180 regions changed; dense `files` emptied in 60 of 60), undisclosed in body.md, the invariant and Route; P9 self-marked PASS. 5 advisories: first-person voice vs the AI disclosure, 'applied on top of current main', naming_exception owner acceptance, record current main, error-string coverage wording.
- 2026-10-01T12:05-05:00 | STAGED (round 5: fold-in patch, texts and fold-in receipts) | staging fixer (Claude Code) | Head unchanged (30a746f792). Fold-in rows moved after #117462's last row (`errors`), the same block as the standalone commit: no #117462 line changes (180/180 synthetic, 3/3 real-text regions), new-class survival unchanged (sparse 90, medium 20, dense 0 of 110), remaining trade (new sections mostly cut in dense regions) and build cost (+0.045 s on 443K chars) disclosed in body.md. Fold-in tests 7 of 7 on #117462's head, 372 of 372 on 44a1ce9724 and aaa863f7ff with #117462 merged; 12/12 fold-in sabotages re-RED. E03p/E03s/F02s/T01/AB117462 rebuilt as r20261001-05 (new harness/foldin_order_check.py, harness/index_cost.py, harness/build_receipts_r05.py). Voice, 'current main' and error-coverage wording fixed in both bodies; P9 PASS -> PENDING; main recorded as aaa863f7ff (merge-tree clean, no rebase). Round-4 material in `superseded-r04/`. Form unchanged (support-note).
