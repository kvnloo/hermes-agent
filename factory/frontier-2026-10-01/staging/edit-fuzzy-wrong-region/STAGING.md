+++
xf_staging = 1
id = "edit-fuzzy-wrong-region"
title = "Patch fuzzy fallback fails loud on wrong-region matches: A/B the external carriers and offer a reviewer's fold-in (NousResearch/hermes-agent#54572)"
version = 3
promotion_form = "salvage-support"
branch = "staging/edit-fuzzy-wrong-region"          # logical id and local ref in the scratch bare repo h.git
fork_branch = "staged/edit-fuzzy-wrong-region"      # physical name when pushed to kvnloo/hermes-agent
branch_physical = "local-only in h.git; not pushed. It will be pushed to kvnloo/hermes-agent as staged/edit-fuzzy-wrong-region, because the fork's legacy refs/heads/staging blocks staging/<id>. OD-0 is resolved by that rename (FACTORY §15 option b)."
branch_sha = "fdaaf5b7295125dd2c38bf66980e4016ce3bfb09"
naming_exception = "FACTORY §10 names a rebuild staging/<id>-vN and says never force-push and never delete an earlier version. The fixer task names the local branch staging/edit-fuzzy-wrong-region (and the fork name staged/edit-fuzzy-wrong-region) as the newest version, so that local ref was force-moved in place: in round 1 (ea25f06132 -> c3af284031) and in round 4 (c3af284031 -> fdaaf5b729). Nothing was ever pushed, so no published history changed. Round 1 left ea25f06132 with no ref (the round-3 re-verifier's process finding); round 4 repairs that. Every earlier commit is now kept under refs/archive/staging/ in h.git (outside refs/heads, so no branch push picks them up), and the v1 and v2 format-patches sit next to this manifest. This is a recorded deviation from the §10 naming rule; the owner has not accepted it yet."
versions = [
  { v = 0, sha = "01bf8d379edc480765c53c087735e09be7798140", ref = "refs/archive/staging/edit-fuzzy-wrong-region-v0-build", base = "572e4f4fad", note = "first build, the head tested in F01/r20261001-01; never staged as the branch head" },
  { v = 0, sha = "8375dc3ccae5e7d32f2d9be43792e85936d560e1", ref = "refs/archive/staging/edit-fuzzy-wrong-region-v0-cherry", base = "234badf401", note = "cherry-pick of the first build onto 234badf401; never staged as the branch head" },
  { v = 1, sha = "ea25f06132c81ef18f44f160b7a278770ac59586", ref = "refs/archive/staging/edit-fuzzy-wrong-region-v1", base = "234badf401", note = "round 0 staged head (phase-3 verdict head); patch edit-fuzzy-wrong-region.v1-ea25f06132.patch" },
  { v = 2, sha = "c3af284031fcdf95e0f0a05d872d25d84ad45039", ref = "refs/archive/staging/edit-fuzzy-wrong-region-v2", base = "aea969677c", note = "rounds 1-3 head (round-1 test rename, Enough1122 trailer); patch edit-fuzzy-wrong-region.v2-c3af284031.patch" },
  { v = 3, sha = "fdaaf5b7295125dd2c38bf66980e4016ce3bfb09", ref = "refs/heads/staging/edit-fuzzy-wrong-region", base = "44a1ce9724", note = "round 4: v2 cherry-picked onto main 44a1ce9724; same test blob e059b025c8 and same message and trailers; patch edit-fuzzy-wrong-region.patch" },
]
superseded_shas = ["ea25f06132c81ef18f44f160b7a278770ac59586 (v1)", "c3af284031fcdf95e0f0a05d872d25d84ad45039 (v2)"]
status = "STAGED"        # receipts exist, branch + body staged locally; blind verifier, F14 guards and z0evals freeze still pending; round 4 rebased the commit onto main 44a1ce9724 and re-proved every gate there (F01/r20261001-04)
route = "salvage-row"
feature = "edit-tool-fail-loud-and-meter"
invariant = "When old_string is not in the file, the patch tool must not overwrite a region whose text differs from it (block_anchor or context_aware); it must return an error and leave the file byte-identical, while near misses on the same text still apply."

[base]
repo = "NousResearch/hermes-agent"
sha = "44a1ce9724502b9c692faaef00af3054bf11f1a6"     # parent of branch_sha; RED/GREEN 3/3, per-arm A/B, sabotage, adjacent, coverage, E01, M01 and probes re-proven here (F01/r20261001-04)
previous_staged_on = ["aea969677c60a1bb72fe227fdfb98f196a2092cc (v2, F01/r20261001-02)", "234badf4012af380d23c91eae55d045a69c69ffb (v1)"]
first_tested_on = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0"
factory_base = "e496ccc7d7e0ca885041e69223683d7739123ff9"
edit_path_blobs_identical_on_all = { "tools/fuzzy_match.py" = "a6a439d70e", "tools/file_operations.py" = "cc028e89f1", "tools/patch_parser.py" = "8e6ce92ed7" }   # e496, 572e, 234b, aea9, e8c9, 44a1
fetched_at = "2026-10-01T16:34Z (git ls-remote: main 44a1ce9724, 29 commits after aea969677c; the commit was rebased onto it at 16:37Z and every gate re-run there, F01/r20261001-04). Rechecked 16:56Z: main aaa863f7ff, 4 commits later, none touching the edit path, the invalidate_on paths or the 13 adjacent files; merge-tree clean (tree 8f651c0238); 1 RED + 1 GREEN spot-check run there, same counts (F01/r20261001-04 freshness_after_proof)"

[upstream]
issues = ["NousResearch/hermes-agent#54572", "NousResearch/hermes-agent#93698", "NousResearch/hermes-agent#111116 (ours)"]
fork_threads = ["kvnloo/hermes-agent#311 (RFC-3 track 3, harness cross-pollination)"]
eval_prs = [{ pr = "NousResearch/hermes-agent#111127", author = "KoNit-K", head = "5444b1a2a8" }]
carrier = { prs = ["NousResearch/hermes-agent#54575", "NousResearch/hermes-agent#125376 (fix commit 5f3f5896a4 only)"], authors = ["MaxFreedomPollard", "Finn763"], heads = ["e28d7c772d", "5f3f5896a4"] }
reviews = [{ ref = "NousResearch/hermes-agent#125376 (issue comment, 2026-09-29T16:38:28Z)", author = "Enough1122", used = "the stripped-pattern guard line, word for word (the fold-in), and the trailing-newline case from its table (contract-test fixture)" }]
competitors = [
  { pr = "NousResearch/hermes-agent#54575", author = "MaxFreedomPollard", head = "e28d7c772d", result = "contract: 6 of 10 cases fail, 4 pass (block cases fixed; the 6 single-line cases still land); adjacent identical; CARRIER (block)" },
  { pr = "NousResearch/hermes-agent#125376", author = "Finn763", head = "5f3f5896a4", result = "fix commit: 4 of 10 cases fail, 6 pass (single-line fixed; the 2 block cases and the 2 trailing-newline cases still land); full head CONFLICTING (bundled bot_relay); CARRIER (single-line) + the reviewer's fold-in" },
  { pr = "NousResearch/hermes-agent#126502", author = "Finn763", head = "6d4fbff950", result = "contract: 6 of 10 cases fail, 4 pass (block cases fixed; single-line cases still land); 2 existing escape-drift tests fail on main's tests; not chosen", note = "found by the dedupe search; not in the selection" },
  { pr = "NousResearch/hermes-agent#93717", author = "fangliquanflq", head = "3c4c81f706", result = "CONFLICTING in tools/fuzzy_match.py; not run", note = "found by the dedupe search; same flat 0.70 core as #126502 plus a diagnostic-preserving hunk" },
]
related_not_arms = [
  { pr = "NousResearch/hermes-agent#128138", author = "elisam0", head = "83401c2591", note = "adds a 'Non-exact match (strategy: ...)' note to similarity-strategy patch results; complementary, not evaluated" },
  { pr = "NousResearch/hermes-agent#129645", author = "Froraut", head = "29789718ff", note = "found by the round-4 dedupe re-search (opened 2026-09-30T20:45Z): V4A Add File newline, @@ hint validation and line endings; touches fuzzy_find_and_replace's signature and _apply_replacements, not block_anchor or context_aware matching. Not a wrong-region fix and not evaluated. merge-tree clean on 44a1ce9724, and c54575-rebased-on-main.diff and 5f3f5896a4's fuzzy_match.py hunk both still apply on main + #129645 (git apply --check)" },
]
close_after = ["NousResearch/hermes-agent#126502", "NousResearch/hermes-agent#93717"]
demand = { score = 30, source = "demand reader 2026-10-01; #54572 has 7 comments, P2, type/bug" }
maintainer_signal = "teknium1 automated hermes-sweeper review on #54575 (2026-07-15): keep_open, salvageability=high; asked for a live patch_replace regression, which likivik supplied"

[[donors]]
sha = "e28d7c772d"
author = "MaxFreedomPollard"
role = "carrier (block_anchor / context_aware content-divergence floor); reported #54572 and wrote its repro (handler / audit_log; also `TestContentDivergenceGuard::test_block_anchor_partial_middle_does_not_overwrite` in f13fb31050), reused as the block_anchor_middle contract case; wrote the original drift near-miss fixture (`test_genuine_single_line_drift_still_matches` in f13fb31050: 4-space indentation, only the value drifted), which likivik's live variant extends"
trailer = "Co-authored-by: Max Freedom Pollard <272618364+MaxFreedomPollard@users.noreply.github.com>"

[[donors]]
sha = "dbc91693bb"
author = "likivik"
role = "live patch_replace regression inside #54575. Gave the block_drift near-miss fixture, byte-identical to `test_legitimate_rescue_still_applies` (old_string with 2-space drift and `y = 9`, new `def foo():\\n    return 0\\n`, must land `return 0`), and the live-path pattern the contract test follows (drive `ShellFileOperations.patch_replace` on a real file, assert an error and a byte-identical file). Credited in our test commit"
trailer = "Co-authored-by: likivik <address withheld here; the commit uses the author address of dbc91693bb, see edit-fuzzy-wrong-region.patch>"

[[donors]]
sha = "5f3f5896a4"
author = "Finn763"
role = "carrier (single-line context_aware refusal); single_line_wrong_token fixture reused in the contract test"
trailer = "Co-authored-by: finn763 <165816600+finn763@users.noreply.github.com>"

[[donors]]
sha = "5444b1a2a8"
author = "KoNit-K"
role = "oracle battery (evals/edittool); missing_anchor and indentation_drift trap fixtures reused in the contract test"
trailer = "Co-authored-by: KoNit-K <address withheld here; the commit uses the author address of 5444b1a2a8, see edit-fuzzy-wrong-region.patch>"

[[donors]]
sha = ""                 # no commit: a review comment
ref = "NousResearch/hermes-agent#125376 issue comment 2026-09-29T16:38:28Z"
author = "Enough1122"
role = "proposed the fold-in line `if len(pattern.strip().split('\\n')) == 1:` (foldin-125376-stripped-guard.diff is that line, word for word) and the trailing-newline case (single_line_trailing_newline fixture in the contract test)"
trailer = "Co-authored-by: Enough1122 <10966420+Enough1122@users.noreply.github.com>"

[[donors]]
sha = "fdaaf5b729"       # v3; the same commit content as c3af284031 (v2) and ea25f06132 (v1)
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "author of the contract test commit; verified the reviewer's line in the A/B and packaged it as foldin-125376-stripped-guard.diff (the line itself is Enough1122's)"
trailer = "Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"

[ownership]
searched_at = "2026-10-01T09:05Z; re-searched 2026-10-01T16:45Z for open PRs created since 2026-09-30 (gh api search, read-only): one hit, NousResearch/hermes-agent#129645 (related, not a competitor; see related_not_arms)"
queries = ["fuzzy_match", "block_anchor", "context_aware", "wrong region", "fuzzy wrong anchor", "fuzzy_find_and_replace"]
open_external = [54575, 125376, 126502, 93717, 111127]
merged_overlap = ["c0b0c88626 (teknium1, on main): context_aware requires every non-blank line >= 0.80; closes the half-block variant, not the block_anchor or single-line cases"]
claimant_lanes = "clear: NousResearch/hermes-agent#127373/#127374/#127375 (TUI perf), #127332 (composer), #127228 (HUD), all OPEN issues, do not touch tools/fuzzy_match.py"
hard_hold = "clear: kvnloo/hermes-agent#69 and kvnloo/hermes-agent#70 are state-db/doctor"
design_holds = "none apply"
hermes_lane_overlap = "none found"
heads_rechecked_at = "2026-10-01T16:37Z-16:44Z (git ls-remote refs/pull/<n>/head + gh api, read-only): e28d7c772d, 5f3f5896a4, 6d4fbff950, 3c4c81f706, 5444b1a2a8, 83401c2591 unchanged; all six PRs OPEN, none merged; issues #54572, #93698, #111116 OPEN; NousResearch/hermes-agent#130139 OPEN (its body has no AI disclosure; 1 comment, the owner's); kvnloo/hermes-agent#402 CLOSED, kvnloo/hermes-agent#404 and kvnloo/hermes-agent#311 OPEN. No new comments on #125376 (last: Enough1122, 2026-09-29), #54575 (last: 2026-08-13) or #111127 (last: 2026-09-16)"
verdict = "EXTERNAL -> salvage-support; no competing PR"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
receipts = [
  { id = "E01/r20261001-01", path = "receipts/E01-r20261001-01.json", sha256 = "9d5a8e164b428d24baf36047e9e34745ebacfe064c719ed0b5a8f972e303c553" },
  { id = "F01/r20261001-01", path = "receipts/F01-r20261001-01.json", sha256 = "cd29f42b0b724d61f70127bba15ebddf73cb813985f9be27d3651af78ef2b6ec" },
  { id = "F01/r20261001-02", path = "receipts/F01-r20261001-02.json", sha256 = "5b5f70ecf8469b362f236aabf4e7d711b50ac49fc8a2ec587a2cc27b26f9e166" },
  { id = "F01/r20261001-03", path = "receipts/F01-r20261001-03.json", sha256 = "ca83409e178a529a019662f3bb0fb6a387c56d4389049bdd67f96242d8e294e9" },
  { id = "F01/r20261001-04", path = "receipts/F01-r20261001-04.json", sha256 = "6066f93a2069916fc031e288454c99f5e7fa95eb1d57a72ed53d9f0ef13954aa" },
  { id = "M01/r20261001-01", path = "receipts/M01-r20261001-01.json", sha256 = "0e7eeadf658a09292dbcd5e9d5b360baae23940d22a9ee6d72586ec2e6f320f2" },
]
red = { test = "tests/tools/test_fuzzy_match_wrong_region.py", main = "44a1ce9724 (r04, on head fdaaf5b729); earlier aea969677c (r02), 234badf401 and 572e4f4fad (r01)", observed = "8 of 10 cases fail, 2 pass, in 4 of 4 runs on fdaaf5b729 (1 commit-only + 3 with carrier tests cross-applied); with carrier tests, 3 carrier tests also fail on main and are listed separately. Same counts as r02 on c3af284031", marker = "wrong region replaced via block_anchor|context_aware: count=1, error=None", receipt = "F01/r20261001-04" }
green = { arm = "main + #54575 (c54575-rebased-on-main.diff) + 5f3f5896a4 + fold-in", reps = "3 of 3 on fdaaf5b729 / 44a1ce9724 (r04); earlier 3 of 3 on c3af284031 / aea969677c (r02), 3 of 3 on ea25f06132 and on the first head (r01)", observed = "contract: 10 of 10 cases pass (0 fail); carrier tests 61 of 61 and 16 of 16 pass", receipt = "F01/r20261001-04" }
negative_control = { mutation = "per-hunk revert on the GREEN arm", result = "RED each, counted as contract cases failing of 10: #54575 floor -> 2 fail (block cases); #125376 guard -> 6 fail (single-line cases); fold-in line -> 2 fail (trailing-newline cases; carrier tests still all pass)", receipt = "F01/r20261001-04 (same as r02)" }
adjacent = { identical = true, files = 13, observed = "284 passed / 8 skipped / 0 failed on main, #54575, #125376 fix and the GREEN arm (44a1ce9724); #126502: 282 passed / 8 skipped / 2 failed", pre_existing = [], receipt = "F01/r20261001-04 (same as r02 on aea969677c)" }
coverage = { tool = "stdlib sys.settrace line coverage (coverage.py is not installed in the test interpreter; nothing installed)", result = "base: every wrong-region cell reaches the block_anchor or context_aware match and the write (patch_replace write_file / V4A _apply_update write_file) through the seam; GREEN: the floor 'continue' and the stripped-pattern guard 'return []' execute through the seam, then the no-match path", receipt = "F01/r20261001-04 gates.coverage_P4 (identical to r02)" }
guards = { F14 = "NOT_RUN (factory-replay-gate harness not built)" }
quantitative = []
cache_read_ratio = { status = "N_A" }
route_scope = "n/a"
not_tested = ["model behaviour after refusal (E02 deferred: needs >=64K local or paid, plus OD-2)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-edit-fuzzy-wrong-region", commit = "" }

[gates]
P1 = "PASS"       # RED on 44a1ce9724 (4 of 4 runs, r04); invalidate_on paths unchanged since e496ccc7d7; < 24 h old
P2 = "PASS"       # external carriers; salvage route; no competing PR (dedupe re-searched 16:45Z); lanes and holds clear
P3 = "PASS"       # one test file, +106, no env vars, no hooks
P4 = "PASS"       # real ShellFileOperations.patch_replace and patch_v4a through LocalEnvironment (bash); nothing faked. Coverage proof: per-test line coverage tagged by call path (F01/r20261001-04 gates.coverage_P4, identical to r02). Done with stdlib sys.settrace because coverage.py is not in the test interpreter; if the factory requires coverage.py itself, this returns to PENDING
P5 = "PENDING"    # RED 4/4, GREEN 3/3, every A/B arm 3/3, SABOTAGE and ADJACENT re-done on fdaaf5b729 / 44a1ce9724 (r04), flaky=false; F14 guards not run, so not PASS
P6 = "N_A"        # no value claim
P7 = "PASS"       # locally: one commit on main 44a1ce9724 (upstream main when rebased at 16:37Z; main moved 4 commits to aaa863f7ff by 16:56Z, none on the edit path, merge-tree clean there, tree 8f651c0238), author/subject/trailers unchanged from v2, merge-tree clean on 44a1ce9724 (tree f23cd04b5d); rebase again at push time, workflow push-trigger scan = 0 (.github unchanged since 234badf401). Push name staged/<id> (OD-0 resolved); not pushed; OD-4 open
P8 = "PENDING"    # 6 receipts hashed (receipts/SHA256SUMS.json); no emails, host name or local paths in them, but the K1 validator has not been run; not frozen to z0evals
P9 = "PENDING"    # body.md drafted, tone gate self-checked again in round 4 (the section 3 diff is now inline, so self_service holds), AI-assistance line in all 4 quoted blocks, no @mentions, no owner notes inside the quotes, reviewer and test-case authors credited; independent read pending
P10 = "PENDING"   # blind verifier not run on fdaaf5b729
P11 = "RECORDED"  # demand 30; maintainer keep_open/high on #54575; test-only content rides two real fixes (D5 satisfied)
P12 = "PENDING"   # A5 sweep not run; staging cap (OD-8); venue: NousResearch/hermes-agent#130139 delta or next wave (owner)

[verification]
verifier = ""
provenance = "independent"
exact_head = "fdaaf5b7295125dd2c38bf66980e4016ce3bfb09"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""

[merge_check]
main_sha = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
checked_at = "2026-10-01T16:40Z"   # the head's parent; merge tree = the head's own tree f23cd04b5d
newer_main = { sha = "aaa863f7ff2dec1821be1652b5d15ad14ecea70b", checked_at = "2026-10-01T16:56Z", commits_after_main_sha = 4, clean = true, tree = "8f651c0238f0aec4ed1a34b5411264a1e19fb80d", edit_path_changed = false }
clean = true
proof_main_sha = "44a1ce9724502b9c692faaef00af3054bf11f1a6"   # where RED/GREEN/A-B/sabotage/adjacent/coverage/E01/M01 ran for v3 (F01/r20261001-04)
recheck = "git merge-tree --write-tree main staging/edit-fuzzy-wrong-region"

[push]
remote_branch = "staged/edit-fuzzy-wrong-region"
no_follow_tags = true
workflow_push_matches = 0
pushed_at = ""
publishes = "the commit's six trailers as written: four noreply addresses (MaxFreedomPollard, finn763, Enough1122, Claude) and the public commit-author addresses of KoNit-K (from 5444b1a2a8) and likivik (from dbc91693bb), checked against those upstream commits with gh in round 3. GitHub needs those addresses to attribute the co-authors, and any salvage cherry-pick of their work publishes them the same way. Receipts and this manifest name handles only."

[body]
path = "body.md"
kind = "wave-row"
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
tone_gate_provenance = "self (author worker), re-run in round 4 after the section 3 diff was inlined; not yet independent"
jargon_lint = "PASS (self)"
posting_rule = "body.md top note: post each quoted block after removing the leading '> ' from each line; nothing to paste or fill in. Round 4 removed the one paste instruction that sat inside a quoted block (section 3) by inlining c54575-rebased-on-main.diff byte for byte (round-trip sha256 e8da4410..., the file's)"
privacy_scan = "PASS (self): synthetic fixtures only, no home paths in body; receipts use $S/$WT/<venv-python>/<pytest-tmp> placeholders; round 3 removed the host name from all receipts and make_receipts.py, the commit-trailer emails from F01/r20261001-02, the two personal addresses from the donors table and a private endpoint IP from the E02 recipe; round 4's receipt and raw files were scanned for local paths, the host name and email addresses (none). The format-patches (*.patch) carry the commit's full trailers, as the commit itself does (see [push].publishes)"

[queue]
board = "NousResearch/hermes-agent#130139 (OPEN; salvage wave posted from the closed kvnloo/hermes-agent#402; 9 rows, this one not included). Owner picks: delta comment there (body.md section 1, which carries its own AI disclosure), or the next wave. Not a kvnloo/hermes-agent#404 row (that queue holds 39 PR-form branches)."
position = "after existing rows"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# Patch fuzzy fallback fails loud on wrong-region matches

Promotion form: **salvage-support**. The deliverable is not a new PR. It is a contract test (one commit) plus a one-line fold-in that a reviewer already proposed on #125376, offered to the two external carriers that already fix the two halves of the defect.

## Invariant

When `old_string` is not in the file, the `patch` tool must not overwrite a region whose text differs from it. It must return an error and leave the file byte-identical, so the model re-reads instead of silently corrupting code. Near misses on the same text must still apply. For those, the matcher (`fuzzy_find_and_replace`) names the non-exact strategy that matched, and the edit meter records it as the `hermes.file_edit.count` strategy label (M01). The patch tool's own result does not carry the strategy on main: `patch_replace` discards it (`_strategy`, `tools/file_operations.py:1583`), and main deleted `TestStrategyNameSurfaced`. So the test checks the matcher's return value, not the tool result.

Real call path exercised: `ShellFileOperations.patch_replace` and `ShellFileOperations.patch_v4a` (`tools/file_operations.py`, which goes to `tools/patch_parser.py` and then `tools/fuzzy_match.fuzzy_find_and_replace`), over a real `LocalEnvironment` bash in a temp directory. No model or provider is involved and nothing is mocked. Line coverage of that path is in F01/r20261001-04 (`gates.coverage_P4`; identical to F01/r20261001-02).

On main there are two live defects. c0b0c88626 (teknium1, already on main) closed the half-block `context_aware` case, but these remain:

1. `block_anchor` accepts a single candidate whose middle is only 0.50 similar. This is the #54572 repro (middle similarity 0.63).
2. A single line reaches `context_aware` and matches at 0.80 or above, for example `trim()` vs `strip()` at 0.923. A trailing newline (or CRLF, or a leading blank line) turns one line into two and gets past a guard that checks `n == 1`. The trailing-newline and CRLF bypass was found by Enough1122 in the 2026-09-29 review comment on #125376.

## Links

- Upstream issues: NousResearch/hermes-agent#54572 (block_anchor wrong region), NousResearch/hermes-agent#93698 (same defect, Markdown shape), NousResearch/hermes-agent#111116 (ours: edit-tool shape audit)
- Upstream carriers: NousResearch/hermes-agent#54575 (MaxFreedomPollard), NousResearch/hermes-agent#125376 (Finn763)
- Review that proposed the fold-in: the 2026-09-29 comment by Enough1122 on NousResearch/hermes-agent#125376
- Same-defect competitors: NousResearch/hermes-agent#126502 (Finn763), NousResearch/hermes-agent#93717 (fangliquanflq)
- Oracle: NousResearch/hermes-agent#111127 (KoNit-K, evals/edittool)
- Related, not evaluated: NousResearch/hermes-agent#128138 (strategy note on similarity matches)
- Salvage wave (venue candidate): NousResearch/hermes-agent#130139, posted from the closed kvnloo/hermes-agent#402
- Fork thread: kvnloo/hermes-agent#311

## Member branches

Rebase status re-measured on main `44a1ce9724` (2026-10-01T16:40Z, F01/r20261001-04 `member_heads_on_main`). It was first measured on `aea969677c` (11:21Z) and rechecked on `e8c97320ac` (11:35Z); none of the 29 commits from `aea969677c` to `44a1ce9724` touch the edit path. Tree SHAs change with every main commit, so each one below names the main it was measured on.

| ref | SHA | role | rebase status on main 44a1ce9724 |
|---|---|---|---|
| `staging/edit-fuzzy-wrong-region` (local, h.git; pushed later as `staged/edit-fuzzy-wrong-region`) | `fdaaf5b729` (v3) | Our first slice: the contract test commit | One commit on `44a1ce9724` (tree `f23cd04b5d`) |
| `refs/archive/staging/edit-fuzzy-wrong-region-v2` / `-v1` / `-v0-cherry` / `-v0-build` | `c3af284031` / `ea25f06132` / `8375dc3cca` / `01bf8d379e` | Earlier versions of the same commit, kept (never deleted) | Superseded; not re-measured. v2 sits on `aea969677c`, v1 and v0-cherry on `234badf401`, v0-build on `572e4f4fad` |
| `refs/pr/54575` | `e28d7c772d` | Carrier A: content-divergence floor (block case), plus likivik's live test | Conflicts in tests only, mechanical: main deleted `TestStrategyNameSurfaced` and `TestTerminalOutputCleanliness` next to its additions (both classes exist at the PR's merge base `fa75692211`). `c54575-rebased-on-main.diff` (additions only: `tools/fuzzy_match.py` +30, `tests/tools/test_fuzzy_match.py` +58, `tests/tools/test_file_tools_live.py` +69; 0 removed) applies clean on `44a1ce9724`. `tools/fuzzy_match.py` merges clean (sha256 `fc55b3d0…`, same as the diff's) |
| `refs/pr/125376` | `5f3f5896a4` | Carrier B: single-line refusal in `context_aware` | Full branch CONFLICTING (`tui_gateway/methods_bot_relay.py`, from bundled bot_relay commit `1c890ae8d0`). Fix commit `5f3f5896a4` cherry-picks clean: tree `79e982be4d` on `44a1ce9724` (it was `38ff73b5da` on `aea969677c`, `b311275c1d` on `572e4f4fad`, `f9fb6640d2` on `234badf401`, `af624fea5e` on `bafb42b431`); the resulting `tools/fuzzy_match.py` blob is `e01522910c` on all five. `foldin-125376-stripped-guard.diff` applies to the head (offset -1) |
| `refs/pr/111127` | `5444b1a2a8` | Oracle battery (E01) | merge-tree clean |
| `refs/pr/126502` | `6d4fbff950` | Competitor (flat 0.70 block_anchor) | merge-tree clean; fails 2 existing escape-drift tests unless its own test edits are taken |
| `refs/pr/93717` | `3c4c81f706` | Competitor (flat 0.70 + diagnostic hunk) | CONFLICTING in `tools/fuzzy_match.py` (pre-refactor base) |
| `refs/pr/128138` | `83401c2591` | Related, not an arm | merge-tree clean |
| `refs/pr/129645` | `29789718ff` | Related, not an arm (line endings / @@ hints; found in round 4) | merge-tree clean; both carriers' fuzzy_match.py changes still apply on top of it |
| `refs/fork/fix/fuzzy-context-aware-correctness` | `9cdd813b64` | Reference only (mirror of c0b0c88626, already on main) | moot |

Read-only refs fetched earlier: `refs/pr/126502`, `refs/pr/93717`, `refs/pr/128138`; `refs/pr/129645` in round 4.

## First-slice status

**Committed.** `staging/edit-fuzzy-wrong-region` = `fdaaf5b729` (v3) on main `44a1ce9724`. The local branch was forced from `ea25f06132` to `c3af284031` in the phase-3 round-1 fix and from `c3af284031` to `fdaaf5b729` in round 4. It was never pushed, so no published history changed, and every earlier version is kept under `refs/archive/staging/` (front matter `versions`, `naming_exception`).

- `test(tools): pin the fail-loud contract for wrong-region fuzzy edits`. It adds `tests/tools/test_fuzzy_match_wrong_region.py` (+106, 1 file).
- Author is Kevin Rajan. The commit ends with six trailers:
  - `Co-authored-by` for MaxFreedomPollard, finn763, KoNit-K and likivik, whose repros, fixtures and live regression it reuses;
  - `Co-authored-by: Enough1122 <10966420+Enough1122@users.noreply.github.com>`, for the trailing-newline case taken from that review;
  - `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, which discloses the AI assistance.
- Two tests (10 cells):
  - `test_wrong_region_edit_fails_loud_and_leaves_file_untouched`: 4 cases × {replace, V4A}. The cases are the #54572 block repro, the #125376 single line, the #111127 missing_anchor anchor, and the trailing-newline case from Enough1122's review on #125376.
  - `test_near_miss_edit_still_applies_via_a_non_exact_strategy`: #54575's block drift (likivik's `test_legitimate_rescue_still_applies`, byte-identical; it extends MaxFreedomPollard's original 4-space drift fixture) and #111127's indentation_drift. Each must apply through `patch_replace`. Calling `fuzzy_find_and_replace` directly must return a non-exact strategy from the matcher's chain. Those strategy names are the meter's label set, because `FILE_EDIT_STRATEGIES` is derived from `STRATEGIES`. The tool result is not checked for a strategy, since it carries none.
- The missing_anchor case uses `new_string="return value.casefold()"`. The battery's own `"return value"` is a substring of the file, so it takes the already-applied path; see E01.
- Patch files:
  - `edit-fuzzy-wrong-region.patch` (sha256 `b8b0e3f1…`, format-patch of `fdaaf5b729`); the superseded versions are kept as `edit-fuzzy-wrong-region.v2-c3af284031.patch` (`bbfbee38…`) and `edit-fuzzy-wrong-region.v1-ea25f06132.patch` (`04fc9b9c…`)
  - the fold-in line, `foldin-125376-stripped-guard.diff` (`c0846607…`). This is Enough1122's proposed line, packaged as a diff against #125376's head.
  - the carrier A rebase hint, `c54575-rebased-on-main.diff` (`e8da4410…`), also inlined byte for byte in the `body.md` §3 comment
- History:
  - First built on main `572e4f4fad`, then cherry-picked onto `234badf401` (`ea25f06132`), both with zero edit-path drift.
  - Round-1 fix: cherry-picked onto `aea969677c`. The near-miss test was renamed and its docstring reworded so it no longer implies that the tool reports the strategy. The Enough1122 trailer was added.
  - Every gate was re-proven on `c3af284031` (F01/r20261001-02).
  - Round-4 fix: v2 cherry-picked onto `44a1ce9724` (clean) → `fdaaf5b729`, with the same test blob (`e059b025c8`), message, author, author date and trailers. Every gate was re-proven there (F01/r20261001-04), with the same counts as r02.

## Route and carrier choice

There are two independent defects, and no single open PR closes both. Each carrier closes one, and they compose cleanly. Neither closes the trailing-newline bypass. The one-line change to #125376's guard that Enough1122 proposed in review closes it. Our part is verifying that line in the A/B and writing the regression test.

- **Why both are needed.** #54575's content floor runs on every `block_anchor` and `context_aware` match, single-line ones included, but the single-line wrong token scores 0.923 against its 0.90 floor and still applies via `context_aware` (instrumented probe, F01/r20261001-03 `floor_reach_probe`, re-run identical in F01/r20261001-04; consistent with the c54575 arm, where the 6 single-line cells still land). #125376 refuses single-line patterns inside `context_aware` itself, before any similarity is scored.
- **Block case: #54575 over #126502 and #93717.**
  - All three refuse the #54572 repro.
  - #54575 also refuses #93717's and #126502's Markdown repros.
  - #54575 keeps the 13 adjacent files identical, because its floor runs after the escape-drift check, so both escape-drift diagnostics survive.
  - #126502's flat 0.70 turns both diagnostics into a plain "Could not find a match", and it has to edit two existing tests to pass.
  - #93717 conflicts with the refactored module.
  - #54575 is also the issue author's PR, and the maintainer sweeper marked it keep_open, salvageability high.
- **Single-line case: #125376's fix commit**, with the bundled bot_relay commit split off (as its reviewer already asked), plus the reviewer's fold-in `if len(pattern.strip().split('\n')) == 1:`.
- **The contract test stays optional (salvage bar).** Upstream AGENTS.md sets "≤ 2 tests is the salvage bar too". Each carrier already brings its own tests: #54575 adds 3 tests in `test_fuzzy_match.py` plus 2 live tests (5 `def test_` lines in `c54575-rebased-on-main.diff`), and #125376's fix commit adds 2. Folding our 2-test file into either carrier would take it past that bar. So the comments offer the test only as an option ("Take the line, the test, or neither" on #125376; the #54575 comment offers only the rebase). The fold-in line itself adds no test. If a maintainer wants the test, the smallest form is to swap it in for a carrier's own tests, not to add it on top; that call is theirs.

WAVE.md row form, as drafted in `body.md`:

> | #54572 (also #93698, single-line part of #111116) | #54575 (MaxFreedomPollard) + #125376 fix `5f3f5896` (Finn763) | main `44a1ce97`: FAIL, 8 of 10 cases fail; #54575: FAIL, 6 of 10 fail (block cases pass); `5f3f5896` alone: FAIL, 4 of 10 fail (block and trailing-newline cases); #126502: FAIL, 6 of 10 fail (block cases pass; +2 existing escape-drift tests fail); #93717: CONFLICTING, not run; #54575 + `5f3f5896`: FAIL, 2 of 10 fail (trailing newline); + fold-in: PASS, 10 of 10 pass (3 of 3 runs) | Enough1122 (review on #125376): stripped-pattern guard line; kvnloo: verification + `tests/tools/test_fuzzy_match_wrong_region.py` (cases from MaxFreedomPollard, likivik, Finn763, KoNit-K, Enough1122) | #126502, #93717 | per-hunk sabotage re-REDs each piece; 13 sibling files 284 passed / 8 skipped / 0 failed on every chosen arm; meter labels unchanged; wrong-region edits now return an error |
>
> (followed by the AI-assistance line; see `body.md` §1 for the exact text to post)

## Evidence

All results are OBSERVED, $0, local, with no CI involved: the carriers' check rollups are empty. Every count in the table was re-measured in round 4 on main `44a1ce9724` with head `fdaaf5b729` (F01/r20261001-04) and matches r02 (main `aea969677c`, head `c3af284031`) field by field; r02 matched r01. The E01 battery and M01 probe were re-run there too (reports and probe output byte-identical to r02).

| experiment | receipt | verdict | label | n | result |
|---|---|---|---|---|---|
| F01 carrier A/B (contract test, 10 cells) | `receipts/F01-r20261001-04.json` (`single_arm_ab`); earlier r02 on `aea969677c`, first run `receipts/F01-r20261001-01.json` | KEEP | OBSERVED | 3 reps/arm on `44a1ce9724` (r02: 3 reps/arm on `aea969677c`; r01: 3 reps/arm on `572e4f4fad`, +3 on `ea25f06132`) | contract cases passing of 10 (failing in brackets): base 2 (8 fail); c54575 4 (6 fail); c125376-leaf 6 (4 fail); both 8 (2 fail); leaf+fold 8 (2 fail); **both+fold 10 (0 fail)**; c126502 4 (6 fail); c126502+leaf+fold 10 (0 fail). Reps agree on every arm |
| F01 RED detail | r04 `gates.red` | PASS | OBSERVED | 4 runs on `fdaaf5b729` | contract 8 failed / 2 passed, every failure with the marker. When the carriers' tests are cross-applied, 3 of them also fail on main (`TestContentDivergenceGuard::test_block_anchor_partial_middle_does_not_overwrite`, `TestEdittoolShapeSingleLineFailLoud::test_wrong_token_single_line_refused`, `TestPatchReplaceWrongRegionRejected::test_block_anchor_wrong_region_is_rejected`), listed separately from the contract ids |
| F01 negative control | r04 `gates.sabotage` | RED each | OBSERVED | 1 per hunk on `fdaaf5b729` (r02 on `c3af284031`, r01 on each earlier head: same) | floor revert: 2 of 10 cases fail (the block cases; 8 pass); single-line revert: 6 of 10 fail (the single-line cases; 4 pass); fold-in revert: 2 of 10 fail (the trailing-newline cases; 8 pass) (carrier tests 61/61 + 16/16 still pass, so only the contract test pins that line) |
| F01 adjacent (13 files) | r04 `gates.adjacent` | identical | OBSERVED | 1 per arm on `44a1ce9724` | 284 passed / 8 skipped / 0 failed on base, c54575, c125376-leaf, both+fold; c126502 282 passed / 8 skipped / 2 failed (`TestEscapeDriftGuard::test_drift_blocked_apostrophe`, `..._double_quote`) |
| F01 coverage (P4) | r04 `gates.coverage_P4` (identical to r02) | seam executes | OBSERVED | 1 per arm | base: all 8 wrong-region cells reach the `block_anchor` ratio line or the `context_aware` all-lines accept, the matcher's applied return, and the write (`patch_replace` `write_file` / `_apply_update` `write_file`) through the seam. GREEN: the floor check and its `continue` (block cells) and the stripped-pattern guard and its `return []` (single-line cells, trailing newline included) run through the seam, then the matcher's no-match return and `patch_replace`'s `_no_match_result` (replace) or V4A validation (V4A) |
| F01 freshness spot check + floor probe (round 3; the spot check is superseded by r04, the probe was re-run identical in r04) | `receipts/F01-r20261001-03.json` | KEEP | OBSERVED | 1 per arm on main `44a1ce9724`, with v2 re-applied there | base: 8 of 10 cases fail, 2 pass, every failure with the marker; both+fold: 10 of 10 pass, carrier tests 61 of 61 and 16 of 16 pass; `tools/fuzzy_match.py` sha256 identical to r02 on both arms. Probe on main + #54575 only: the floor is called on each single-line match, scores 0.923 and keeps it (applied via `context_aware`, count=1, no error); on the block case it scores 0.851 and drops it |
| F01 cross-application | r01 `cross_application_block_anchor_carriers`; re-run identical in r02 `e01_m01_probes_rerun` and r04 `e01_m01_probes` | n/a | OBSERVED (direct calls) | 1 | #93717 and #126502 Markdown repros: refused on c54575, c126502, both+fold. Escape-drift diagnostics: kept on c54575/both+fold, lost on c126502 |
| F01 residual probe | r01 `residual_probe`; re-run identical in r02 and r04 | n/a | OBSERVED (direct calls) | 1 | both+fold also refuses the CRLF-terminated and leading-blank-line variants; a 2-line wrong-token anchor still applies via `context_aware` on every arm (out of scope) |
| E01 #111127 battery @ `5444b1a2a8` | `receipts/E01-r20261001-01.json` (on `572e4f4fad`); re-run in r02 on `aea969677c` and in r04 on `44a1ce9724`, reports byte-identical | KEEP | OBSERVED | 1 per arm | main: str_replace 6/6, hermes_patch 5/6 (missing_anchor applied via context_aware), the same as KeyArgo's run on `602e596389b`. The score stays at 5/6 on every fixed arm (missing_anchor becomes no_change through the already-applied check). The variant new_string `return value.casefold()` gives applied on main and rejected with #125376, checked by direct calls with the battery file unmodified |
| M01 meter labels | `receipts/M01-r20261001-01.json` (on `572e4f4fad`); re-run in r02 on `aea969677c` and in r04 on `44a1ce9724`, output identical | KEEP | OBSERVED | 1 per arm | `hermes.file_edit.count` label sets and strategy chain identical on every arm. Wrong-region cases go from `applied/block_anchor` or `applied/context_aware` on main to `no_match/none` on both+fold; near-miss labels unchanged |

Raw logs, scorecards, probes, coverage and scripts are in `receipts/raw/`. Round-1 outputs are in the `*-r02` directories; the round-3 spot check and probe are in `freshness-r3/` and `probes-r3/`; round-4 outputs are in `runs-r04/`, `e01-r04/`, `m01-r04/`, `probes-r04/` and `cov-r04/`, with their scripts (`*_v4.sh`, `make_receipt_r04.py`, `write_r04.py`) in `scripts/`. Receipt hashes are in `receipts/SHA256SUMS.json`. Absolute local paths in receipts and raw files are replaced by `$S`, `$WT`, `<venv-python>` and `<pytest-tmp>`, and the raw-file hashes cited inside the receipts were recomputed to match. The workstation name is withheld (`<local-workstation>`) and the receipts carry GitHub handles, not email addresses; the full commit trailers are in `edit-fuzzy-wrong-region.patch`. Round 4's receipt and raw files were scanned for local paths, the host name and email addresses before hashing (none found). Cost: $0.

## Acceptance gates (selection)

| gate | status | evidence |
|---|---|---|
| Contract test RED on main for the stated reason (wrong region replaced, count=1, error=None) | **met** | 8 of 10 cases fail on `44a1ce9724` (r04), also on `aea969677c` (r02), `572e4f4fad` and `234badf401` (r01); marker matched |
| GREEN on the chosen carrier, or carrier plus fold-in | **met** | #54575 + `5f3f5896a4` + fold-in: all 10 cases pass, 3 of 3 reps on `fdaaf5b729` (and on `c3af284031` in r02) |
| Negative control: reverting a carrier's floor or guard line fails the test again | **met** | each of the 3 hunks re-REDs alone |
| Legitimate near-miss edits still apply | **met** | 2/2 near-miss cells pass on every arm |
| Adjacent fuzzy_match, file_operations, patch_parser files keep identical pass counts | **met** | 284 passed / 8 skipped / 0 failed on base and every chosen arm (13 files) |
| Ownership: both carriers external, fold-in offered with credit to the reviewer who proposed it, no competing PR | **met** (no PR opened; comment drafts only) | `body.md` §1–§4 |
| hermes.file_edit.count outcome and strategy labels unchanged | **met** | M01 (re-run identical in r02 and r04) |
| One concrete comment per thread, passing the A4 tone gate | **pending** | drafted and self-checked; needs an independent read and the owner to post |

## Gate checklist (P1-P12)

- P1 Need: PASS. RED on `44a1ce9724`, 4 of 4 runs (F01/r04). The `invalidate_on` paths have been unchanged since `e496ccc7d7`.
- P2 Ownership: PASS. External carriers, salvage route; claimant lanes and holds are clear (front matter). The fold-in line is credited to its proposer, Enough1122.
- P3 Shape: PASS. One test file (+106), no production change in our commit; the fold-in is one line in someone else's PR.
- P4 Real path: PASS, with coverage proof. Live `patch_replace` and `patch_v4a` run over a real shell. Per-test line coverage, tagged by call path, shows the seam executing on base and GREEN (F01/r04 `gates.coverage_P4`, identical to F01/r02 `gates.coverage_P4`). It uses stdlib `sys.settrace`, because coverage.py is not installed in the test interpreter. If the factory accepts only coverage.py output, this gate goes back to PENDING.
- P5 Proof: PENDING. RED 4 of 4, GREEN 3 of 3, every A/B arm 3 of 3, SABOTAGE and ADJACENT were re-done on `fdaaf5b729` / `44a1ce9724` (F01/r04), flaky=false. The F14 standing guards have not been run, so this gate is not PASS.
- P6 Numbers: N_A. There is no value claim.
- P7 Package: PASS locally. One commit (`fdaaf5b729`) on `44a1ce9724`, which was upstream main when the commit was rebased (16:37Z, `git ls-remote`); merge-tree clean (tree `f23cd04b5d`). By 16:56Z main had moved 4 commits to `aaa863f7ff`, none on the edit path or the 13 adjacent files; merge-tree is clean there too (tree `8f651c0238`) and a 1-run RED/GREEN spot check gives the same counts (F01/r04 `freshness_after_proof`). Rebase once more at push time so "one commit on fresh main" stays literally true; `.github` unchanged since the push-trigger scan (0). Pushing publishes the six trailers as written, including KoNit-K's and likivik's public commit-author addresses (`[push].publishes`). OD-0 is resolved: the branch is pushed as `staged/edit-fuzzy-wrong-region`. Nothing is pushed yet. OD-4 (push the branch or keep the ledger patch only) is still the owner's call.
- P8 Freeze: PENDING. Six receipts are hashed but not frozen to z0evals. They carry no email addresses, host name or local paths (round 3 removed them from the older receipts; round 4's were scanned before hashing), but the K1 validator itself has not been run.
- P9 Text: PENDING. Self-checked only. All four quoted blocks in `body.md` end with an AI-assistance line naming what the assistant did (the §1 delta comment had none before round 3, and NousResearch/hermes-agent#130139's body has none to inherit). Round 4 removed the last owner instruction from inside a quoted block: §3 told the owner to paste the rebase diff, which the posting rule did not mention, so the comment would have gone up with a placeholder and no diff. The diff is now inline (byte for byte, round-trip checked), so the posted text needs no editing and the self_service claim holds. Every block names main `44a1ce97`, where all its counts were re-measured.
- P10 Independent read: PENDING, on exact head `fdaaf5b729`.
- P11 Demand: RECORDED. The test rides two real fixes, so D5 does not block it.
- P12 Queue: PENDING. The A5 sweep and OD-8 are outstanding. The venue is NousResearch/hermes-agent#130139 (delta) or the next wave; this is not a kvnloo/hermes-agent#404 row.

The global precondition also applies: Wave 0 (F15, F14, E48, F11) has not passed, so this branch cannot become PROMOTION_READY yet.

## Experiments queued (not run)

T2 and T3 must run serially and need owner decisions.

1. **E02-T2** (local GPU; needs OD-1 for a ≥64K-context preset and OD-2 for the `hermes chat` CLI inside bwrap from a disposable venv).
   - Prerequisite: add a wrong-region trap task to `evals/toolperf_abeval/ab_eval.py`, derived from the contract cases, because the stock 9 traps have none. Not authored here.
   - Trees:
     - `$RUN/wt/base` = main `44a1ce9724` (or the newest main at run time)
     - `$RUN/wt/fix` = that main + `git cherry-pick 5f3f5896a4` + `c54575-rebased-on-main.diff` + `foldin-125376-stripped-guard.diff`
   - `$RUN/home/.hermes/config.yaml` points `model.base_url` at the owner's local OpenAI-compatible endpoint (`<local-endpoint>/v1`, supplied at run time; or ollama `http://localhost:11434/v1`), with a served context of at least 64K.
   - Command:
     ```
     flock $GPU_LOCK env -i PATH=$VENV/bin:/usr/bin:/bin HOME=$RUN/home HERMES_HOME=$RUN/home/.hermes \
       ABEVAL_HOME=$RUN/home/.hermes ABEVAL_ROOT=$RUN/abeval PYTHON=$VENV/bin/python \
       bash $RUN/wt/base/evals/toolperf_abeval/run_all.sh $RUN/wt/base $RUN/wt/fix 3 <local-64k-model-id>
     ```
   - Metric: wrong-edit rate, turns, tool calls, errors, success, n≥3 (OBSERVED from ATOF traces). Scoring needs NeMo Relay ATOF on py≥3.14.
2. **E02-T3** (paid; OD-3, owner launches with injected credentials). Same trees and prerequisite, with `$RUN/home/.hermes/config.yaml` set to `model: {provider: openrouter}` and the key injected by the owner:
   ```
   env -i PATH=$VENV/bin:/usr/bin:/bin HOME=$RUN/home HERMES_HOME=$RUN/home/.hermes ABEVAL_HOME=$RUN/home/.hermes \
     ABEVAL_ROOT=$RUN/abeval PYTHON=$VENV/bin/python \
     bash $RUN/wt/base/evals/toolperf_abeval/run_all.sh $RUN/wt/base $RUN/wt/fix 3 qwen/qwen3-coder-30b-a3b-instruct
   ```
3. **F14 guards** ($0, blocked on the `staging/factory-replay-gate` harness). Run the standing regression set on `$RUN/wt/base` and `$RUN/wt/fix` and require equal verdict maps.
4. **Blind verifier** ($0, P10). Give a different worker exact head `fdaaf5b729` plus the two diffs plus the oracle (RED marker, the 10 case ids, the per-hunk sabotage expectation).

## NOT_TESTED

- Model behaviour after a refusal: does a refused wrong-region edit cut wrong edits, turns or errors (E02)?
- Files on disk with CRLF endings, Windows or macOS shells, and container backends. Only CRLF inside `old_string` was probed, by direct call.
- The #125376 full head and #93717 (both CONFLICTING, not run, not hand-ported).
- The ACP edit-approval path (`acp_adapter/edit_approval.py`) beyond its 6 existing tests; there is no wrong-region case there.
- A 2-line wrong-token anchor (`def normalize(value):` + `return value.trim()`) still applies via `context_aware` on every arm. #125376 scopes it out deliberately; recorded, not pursued.
- The already-applied check reports `no_change` when `new_string` is a substring of the file. This is deliberate maintainer design, out of scope, and noted only for the #111127 trap.
- The shared-metrics store end to end (Relay host on py3.14). Only the `file_edit_fields` mapping was exercised.
- Whether the strategy reaches the patch tool's result: it does not on main, and the test does not claim it (see Invariant). #128138 proposes surfacing it and was not evaluated.
- The F14 standing guards, the bwrap sandbox (isolation here was a scratch HOME/HERMES_HOME plus the clean env from `run_tests.sh`), and the blind verifier.

## Origin action (owner only)

The smallest asks, none of them run by the factory:

1. Post the wave row (`body.md` §1, the quoted block including its AI-assistance line) as a delta comment on NousResearch/hermes-agent#130139 (the salvage wave posted from the closed kvnloo/hermes-agent#402), or keep it for the next wave.
2. Post one comment each on NousResearch/hermes-agent#125376 (the reviewer's fold-in line, credited, plus the optional test), #54575 (A/B result plus the rebase diff, which is inline in the block) and #111127 (trap sensitivity), from `body.md` §2–§4.
3. Each quoted block is posted as it stands, after removing the leading `> ` from each line; nothing has to be pasted or filled in. Each block ends with "I checked the results myself". Post a block only after you have checked it; if you have not, change that line first.

No new upstream PR. If OD-4 allows a push, push the local `staging/edit-fuzzy-wrong-region` to kvnloo/hermes-agent as `staged/edit-fuzzy-wrong-region` with `--no-follow-tags`, so the comments can link the test instead of inlining it.

## Next steps

1. Owner decides OD-4: keep the ledger patch only, or push as `staged/edit-fuzzy-wrong-region` (OD-0 is resolved by that name). At push time, cherry-pick the commit onto the newest main first, keep `fdaaf5b729` under `refs/archive/staging/edit-fuzzy-wrong-region-v3`, and re-run RED/GREEN there.
2. Run the blind verifier on `fdaaf5b729` (P10). Run F14 once the factory-replay-gate harness exists (P5).
3. Before posting, check freshness: `git merge-tree --write-tree main staging/edit-fuzzy-wrong-region`, re-run RED on the newest main, confirm that the carrier heads (`e28d7c772d`, `5f3f5896a4`, `6d4fbff950`, `3c4c81f706`) have not moved, and, if main has moved, update the main SHA quoted in the `body.md` blocks (every count there was measured on `44a1ce97`) and check that `c54575-rebased-on-main.diff` still applies (`git apply --check`). Any carrier head drift invalidates F01.
4. Run the receipt validator, then freeze the six receipts to `kvnloo/z0evals` `study/hermes-edit-fuzzy-wrong-region` (P8).
5. If #125376's author declines the fold-in line, offer the same line (credited to Enough1122), and the test only as an option (salvage bar, see Route), on whichever carrier merges second. The test goes GREEN only when both fixes are present.
6. E02 when OD-1 or OD-3 (plus OD-2) are granted.

## History

- 2026-10-01T08:50Z | CANDIDATE | builder (Claude Code, Opus 5.5) | Selection entry read. Premise re-checked on main 572e4f4fad: both defects are live; c0b0c88626 covers only the half-block case.
- 2026-10-01T09:00Z | EVIDENCED | builder | F01, E01 and M01 run. Dedupe found #126502 and #93717, which were added as arms.
- 2026-10-01T09:37Z | STAGED (local) | builder | Commit `ea25f06132` on main `234badf401` re-proven (RED 3/3, GREEN 3/3, sabotage 3/3). Body drafted. Worktree removed.
- 2026-10-01T11:40Z | STAGED (local; round-1 fix) | fixer (Claude Code, Opus 5.5) | Phase-3 verifier findings addressed:
  - body §3 test count corrected to +127 (58 + 69; was +137).
  - Fold-in line and trailing-newline case credited to Enough1122 (review comment on #125376, 2026-09-29) in the donors, the wave row and the #125376 comment, with a `Co-authored-by` trailer on the commit.
  - Mislabelled cherry-pick tree replaced by per-main values; r01 merge-tree keys now name 572e4f4fad.
  - Trailers described in full, including the Claude disclosure.
  - Near-miss test renamed and docstring/invariant reworded (matcher and meter report the strategy, not the tool).
  - P4 backed by a line-coverage receipt.
  - r01 RED failed_ids split into 8 contract + 3 carrier.
  - Main refreshed: commit cherry-picked to `aea969677c` → `c3af284031`, all gates re-proven (F01/r20261001-02), merge-tree rechecked on `e8c97320ac`.
  - Receipts path-sanitized and rehashed.
  - Fork branch name set to `staged/<id>` (OD-0 resolved).
  - Venue updated: kvnloo/hermes-agent#402 → NousResearch/hermes-agent#130139.
  - Local branch forced to `c3af284031`; worktree removed.
- 2026-10-01T11:58Z | STAGED (local; round-2 fix, text only) | fixer (Claude Code, Opus 5.5) | Round-1 re-verifier findings addressed; branch, commit, patch files and receipts unchanged (`c3af284031`, receipt hashes as above):
  - A/B counts labelled everywhere. The body §1 wave row, its copy here (WAVE.md row form) and the competitors list mixed fail and pass counts in one cell ("main: FAIL, 8 of 10" next to "#54575: 4 of 10", which was a pass count). Every arm now says how many of the 10 cases fail, the way the rows posted in NousResearch/hermes-agent#130139 do: main 8, #54575 6, #125376 fix alone 4, #126502 6, #54575 + `5f3f5896` 2, + fold-in PASS 10/10. The evidence table, negative-control row, acceptance gates and the #125376 comment (§2) got the same labels. The numbers were read back from F01/r20261001-02 `gates.single_arm_ab` (per rep: passed 2/4/6/8/8/10/4/10 on base/c54575/c125376-leaf/both/leaf+fold/both+fold/c126502/c126502+leaf+fold).
  - Donor roles corrected. The block_drift near-miss fixture is byte-identical to likivik's `test_legitimate_rescue_still_applies` (dbc91693bb), so likivik is now credited with it and with the live-path pattern. MaxFreedomPollard is credited with the #54572 repro (issue body and f13fb31050) and the original 4-space drift fixture. Both already carry `Co-authored-by` trailers on `c3af284031`; the commit message names #54575, not a person, for the near miss, so it needed no change.
  - Freshness rechecked at 11:55Z: main still `e8c97320ac`, all six PR heads unchanged and OPEN, merge-tree clean. Nothing re-measured, because nothing moved.
- 2026-10-01T16:25Z | STAGED (local; round-3 fix, text and receipts only) | fixer (Claude Code, Opus 5.5) | Round-2 re-verifier findings addressed; branch and commit unchanged (`c3af284031` on `aea969677c`), patch files unchanged:
  - body §3 (comment for #54575) corrected. It said the single-line case was "a separate path that your floor doesn't reach". That was wrong: `context_aware` is in `SIMILARITY_STRATEGIES`, so #54575's floor runs on that match and keeps it at 0.923, above its 0.90 floor. Re-measured with an instrumented probe on main + `c54575-rebased-on-main.diff` (F01/r20261001-03 `floor_reach_probe`). The wave row and the route section now say the same.
  - AI disclosure added to the body §1 delta comment, which had none; NousResearch/hermes-agent#130139's body has none either. §1 is now a quoted block like §2–§4, with owner notes kept outside the quotes, and the other three disclosure lines now also say the assistant wrote the comment. The §1 row now names the authors of every reused test case.
  - Receipts: commit-trailer emails in F01/r20261001-02 `head_revision` replaced by GitHub handles plus a pointer to the patch. The workstation host name was removed from all four receipts and from `raw/scripts/make_receipts.py`. A private endpoint IP was removed from the E02 recipe, and the two personal addresses were removed from the donors table. All receipts rehashed (`SHA256SUMS.json`, `[evidence]`).
  - Counts in posting text made explicit ("N of 10 cases pass", "N of 6 tasks pass"; no bare `10/10` or `5/6`).
  - Freshness re-measured at 16:10Z on main `44a1ce9724` (29 commits after `aea969677c`): edit path and the 13 adjacent files byte-identical; merge-tree clean (tree `f23cd04b5d`); all six PR heads unchanged and OPEN; issues #54572, #93698, #111116 and NousResearch/hermes-agent#130139 OPEN; kvnloo/hermes-agent#402 CLOSED, kvnloo/hermes-agent#404 OPEN. One RED run (8 of 10 cases fail) and one GREEN run (10 of 10 pass) on that main, same `tools/fuzzy_match.py` hashes as r02 (F01/r20261001-03). Worktree removed.
  - Gates unchanged in status: P5, P8, P9, P10 and P12 stay PENDING (F14 not run, validator and freeze not run, no independent read).
- 2026-10-01T17:05Z | STAGED (local; round-4 fix, rebase + text + receipts) | fixer (Claude Code, Opus 5.5) | Round-3 re-verifier findings addressed:
  - BLOCKING, body §3: the quoted comment for #54575 held an owner instruction ("paste `c54575-rebased-on-main.diff` here …") that the posting rule did not mention, so the comment would have gone up with a placeholder, a local filename and "the diff below" with no diff. The diff is now inline in the `<details>` block, byte for byte (round-trip of the posted text gives sha256 `e8da4410…`, the file's), and `git apply --check` passes on `44a1ce9724` and `aaa863f7ff`. The posting rule now says each block is complete and nothing is pasted or filled in. A lint over the four blocks finds no HTML comments, placeholders or poster instructions. Tone gate re-run: self_service now holds (P9 and `[body].tone_gate` stay self-checked only).
  - "current main (`aea96967`)" in §1–§4: the commit was rebased onto `44a1ce9724` (then current) and every count in the blocks was re-measured there. Main moved to `aaa863f7ff` during the round, so the blocks now name the SHA (`44a1ce97`) and no longer call it current; the owner note gives the freshness facts and says to change the SHA if re-measured later.
  - Unreferenced `ea25f06132`: every earlier commit is now kept under `refs/archive/staging/edit-fuzzy-wrong-region-v0-build` (`01bf8d379e`), `-v0-cherry` (`8375dc3cca`), `-v1` (`ea25f06132`) and `-v2` (`c3af284031`), outside refs/heads. The v1 and v2 format-patches sit next to this manifest. The force-moves are recorded as a deviation from FACTORY §10 (`naming_exception`, `versions`).
  - Salvage bar: the Route section records that each carrier already adds its own tests (#54575: 5, #125376: 2), so the contract test stays an option and is never pushed on top; the comments' wording already says so.
  - Rebase: `c3af284031` cherry-picked onto `44a1ce9724` (clean) → `fdaaf5b729` (same test blob `e059b025c8`, message, author, author date and trailers). The local branch was force-moved to it; nothing pushed. Full re-proof there (F01/r20261001-04): RED 8 of 10 cases fail in 4 of 4 runs; GREEN 10 of 10 pass in 3 of 3 runs (carrier tests 61 of 61, 16 of 16); all 8 A/B arms 3 reps each; per-hunk sabotage; 13-file adjacent set 284 passed / 8 skipped on every chosen arm (#126502: 2 fail); coverage, E01, M01 and all probes. Every count equals r02 field by field; E01 reports and M01 output are byte-identical.
  - Trailer addresses: `[push].publishes` records that a push publishes KoNit-K's and likivik's public commit-author addresses (re-checked against 5444b1a2a8 and dbc91693bb), as any salvage cherry-pick would; receipts and this manifest keep handles only.
  - Freshness: carrier heads unchanged, all six PRs OPEN (16:37Z–16:44Z); dedupe re-search found NousResearch/hermes-agent#129645 (related, not a competitor; carriers still apply on top of it). Main `aaa863f7ff` at 16:56Z: 4 commits after `44a1ce9724`, edit path untouched, merge-tree clean, 1 RED + 1 GREEN spot-check run with the same counts.
  - Gates: P5, P8, P9, P10 and P12 stay PENDING (F14 not run; validator and freeze not run; no independent read; A5 sweep and OD-8 open). Status stays STAGED. Wave 0 is still the global precondition. Worktree removed.
