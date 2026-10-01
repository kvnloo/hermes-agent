+++
xf_staging = 1
id = "memory-prefetch-metric"
title = "Record external memory prefetch outcome and latency in opt-in shared metrics"
version = 3
branch = "staging/memory-prefetch-metric"            # logical id and local ref in the scratch h.git
branch_fork = "staged/memory-prefetch-metric"        # push name on kvnloo/hermes-agent (OD-0 resolved by this rename)
branch_physical = "local-only in scratch h.git at 569ad4d84b, not pushed. The fork's legacy refs/heads/staging (@28790e597c) blocks staging/*, so the fork branch is staged/memory-prefetch-metric (FACTORY OD-0 option b: different physical prefix, staging/<id> stays the logical id). ls-remote 2026-10-01T16:52Z (OWNERSHIP r04) and again in its final check at 2026-10-01T17:06Z: staged/memory-prefetch-metric is absent on the fork (5 other staged/* refs exist), name free."
branch_sha = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
superseded_heads = [
  { sha = "c815543bc2504eccaae9f6adce5046f41710f38c", base = "572e4f4fad", patch = "memory-prefetch-metric.v1-c815543bc2.patch", why = "v1 head; cherry-picked onto aea969677c as 519876fa02 (diff byte-identical)" },
  { sha = "519876fa02f5e5812f5763cef03c5fed054d6cf7", base = "aea969677c", patch = "memory-prefetch-metric.v2-519876fa02.patch", why = "v2 head; its contract test pinned sub-2 s wall-clock buckets and its caller computed success/empty outside the metric guard (round-1 re-verifier). Cherry-picked onto e8c97320ac and amended (an intermediate amend 61fc6ea62d was proven, then reworded for an overclaiming test comment; never published), then cherry-picked onto 040b6df2c4 as 569ad4d84b; the local ref was force-moved to the new commit" },
]
status = "STAGED"        # RED/GREEN/sabotage/stall/adjacent re-proved on 569ad4d84b and replayed on main aaa863f7ff (F08 r04); blind verifier (P10), F14 guard (P5), freeze (P8), queue (P12) and an owner ruling on the hot-path gate are pending
route = "core-leaf"      # promotion_form = "core-pr" (unchanged: no open PR adds a prefetch counter; #124151/#120042/#87028 are demand, #65329/#92118/#125881 touch the same code without a shared counter; #98045 closed 2026-10-01T12:51Z as a duplicate of #87028; #126457 closed unmerged by its author 2026-10-01T16:23:32Z, no replacement)
feature = "memory-prefetch-telemetry-and-probe (catalog), counter half only"
invariant = "Every exit of MemoryManager._prefetch_provider for an external provider records exactly one hermes.memory.prefetch.count row (bounded provider, outcome, wait bucket) on the caller's thread when shared metrics are on, and nothing when they are off."
invariant_gap = "One exit is not covered: if thread.start() itself raises (for example RuntimeError: can't start new thread), the exception propagates exactly as on main (prefetch_all logs it as a non-fatal prefetch failure) and no row is written. Disclosed in PR_BODY.md; not fixed (round-3 re-verifier code nit (a), see manifest r5)."

[base]
repo = "NousResearch/hermes-agent"
sha = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5"
fetched_at = "2026-10-01T12:33Z"     # git ls-remote refs/heads/main; main commit dated 2026-10-01T12:03:56Z
freshness_recheck = { main = "aaa863f7ff2dec1821be1652b5d15ad14ecea70b", checked_at = "2026-10-01T16:52Z", commits_since_base = 25, invalidate_on_changed = false, invalidate_on_blobs_equal_base = "all 8", merge_tree_clean = true, tree = "21c423feb3", f08_replay = "F08/r20261001-04: the head's diff replayed on aaa863f7ff (tree 21c423feb3 = the merge-tree result): RED, GREEN 3/3, 10/10 sabotage, stall cells, adjacent 330 -> 331, all as on 040b6df2c4", final_check = { at = "2026-10-01T17:06Z", main = "aaa863f7ff (unchanged)", merge_tree_clean = true, tree = "21c423feb3", cited_state_changes = 0, query_total_changes = 0, record = "OWNERSHIP/r20261001-04 results.final_state_check" }, record = "OWNERSHIP/r20261001-04 results.main_recheck and results.final_state_check (ls-remote, git log -- <invalidate_on>, merge-tree); MERGE/r20261001-03 has the 040b6df2c4 check; the previous recheck (44a1ce9724, 16:14Z, reconfirmed 16:28Z, 21 commits, tree 675e1aa029, OWNERSHIP r03) is replaced" }
invalidate_on = ["agent/memory_manager.py", "hermes_cli/observability/shared_metrics_loop.py", "hermes_cli/observability/shared_metrics_contract.py", "hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json", "tests/hermes_cli/test_shared_metrics_loop.py", "website/docs/developer-guide/relay-shared-metrics.md", "agent/memory_provider.py", "agent/turn_context.py"]
rebase = { from_base = "aea969677c60a1bb72fe227fdfb98f196a2092cc", commits_between = 8, invalidate_on_changed = false, method = "cherry-pick 519876fa02 onto e8c97320ac (clean); amend: the contract test drops its sub-2 s wall-clock buckets and success/empty moves into the guarded builder; then a clean cherry-pick onto 040b6df2c4; author and author date kept", receipt = "MERGE/r20261001-03" }

[upstream]
issues = [
  "NousResearch/hermes-agent@25c1b008c8 (teknium1, 2026-09-27: wires memory/curator/delegation/backend call sites; prefetch left unmetered) and @2e56f40c16 (the loop metric contract this extends)",
  "NousResearch/hermes-agent#124151 (kweez007, OPEN, head 3ee6189dba: raises the Hindsight prefetch bound to 20 s after timing it by hand; demand signal 1)",
  "NousResearch/hermes-agent#120042 (Navlem, OPEN since 2026-09-23, head 641f6b94c5: raises the default external prefetch bound to 12 s after a production audit of 18-27 s recalls and about 53 dropped prefetches in one day; demand signal 2)",
  "NousResearch/hermes-agent#87028 (richardclawbot, OPEN, head f63bfa2a5c, conflicts with main: makes the external prefetch timeout configurable; Navlem named it the keeper when closing #98045. rodrigogs's field evidence there, 2026-09-06: 8 s timeouts coinciding with 18.4-47.1 s embeds, and 101 of 197 agent starts with no injected recall that he could not all attribute; he argues a tunable bound matters more than more logging; demand signal 3)",
  "NousResearch/hermes-agent#98045 (Navlem, CLOSED unmerged 2026-10-01T12:51:06Z by Navlem as a duplicate of #87028: 'This is not fixed on main') - no longer a demand signal or an open overlap",
  "NousResearch/hermes-agent#47119 (jbienz, OPEN: memory provider tools sometimes not injected) - listed by the selection; tangential, not cited as Fixes",
  "NousResearch/hermes-agent#21566 (pikos-apikos, OPEN: aux LLM 30 s timeout on local endpoints) - listed by the selection; tangential, not cited as Fixes",
]
fork_refs = ["kvnloo/hermes-agent#404 (staged-PR board, 39 rows; queue position after them)", "kvnloo/hermes-agent#322 (factory thread)"]
eval_prs = []
carrier = { pr = 0, author = "", head = "" }   # own core leaf, no carrier
competitors = []
# merge-tree results measured 2026-10-01T12:34Z against main 040b6df2c4 and the staging head 569ad4d84b (MERGE/r20261001-03, with the
# merged-tree tests); re-run at 16:15Z against main 44a1ce9724 (OWNERSHIP/r20261001-03) and at 16:52-16:57Z against main aaa863f7ff
# (OWNERSHIP/r20261001-04) with every open PR head unchanged and the same results. r04 merge-tested all 50 open prefetch-search hits that touch
# the watched files (r03: 51; only #126457 left, closed): 38 already conflict with main, 11 merge cleanly with main and the head, and 1 open PR
# conflicts with the head only (#92118).
adjacent_open_prs = [
  { pr = 124151, author = "kweez007", head = "3ee6189dba", touches = "agent/memory_manager.py per-provider prefetch bound (Hindsight 20 s)", result = "clean on main and with the head; merged tree passes test_shared_metrics_loop + test_memory_provider (74 passed); semantics compatible", receipt = "MERGE/r20261001-03" },
  { pr = 120042, author = "Navlem", head = "641f6b94c5", touches = "agent/memory_manager.py default prefetch bound 8 s -> 12 s", result = "clean on main and with the head; merged tree passes the same two files (72 passed); demand signal, not a counter", receipt = "MERGE/r20261001-03" },
  { pr = 92118, author = "seradin", head = "2ad5cc73fa", touches = "agent/memory_manager.py _prefetch_provider return path (str or MemoryPrefetchResult)", result = "clean on main; CONFLICTS with the head in agent/memory_manager.py on the line after the success/empty record call. The v2 head computed the outcome in the caller, so a keep-both resolution raised AttributeError and dropped that provider's recalled context (probe: context ''); v3 passes the raw value to the guarded builder, so the same resolution keeps the context (probe: '- prefers tabs', row ('honcho','empty')). Remaining: a structured result counts as empty until the builder reads .context (one-line follow-up for whichever lands second)", receipt = "MERGE/r20261001-03" },
  { pr = 87028, author = "richardclawbot", head = "f63bfa2a5c", touches = "agent/memory_manager.py _prefetch_provider (honor external prefetch timeout)", result = "already CONFLICTS with main on its own (agent/agent_init.py, agent/memory_manager.py); same two files with the head; adds no record/metric lines. OPEN; the keeper for the configurable timeout since #98045 closed; carries rodrigogs's field evidence (demand signal 3)", receipt = "MERGE/r20261001-03; state OWNERSHIP/r20261001-04" },
  { pr = 86948, author = "V0v1kkkAssistant", head = "cc1c2a1f2c", touches = "agent/memory_manager.py (configurable provider timeouts)", result = "already CONFLICTS with main on its own (agent/memory_manager.py, plugins/memory/byterover/__init__.py); same with the head; adds no record/metric lines", receipt = "MERGE/r20261001-03" },
  { pr = 65329, author = "Soju06", head = "c868eaaa02", touches = "agent/turn_context.py opt-in local turn trace with a prologue.memory_prefetch span around prefetch_all (hit/empty tag)", result = "not a shared metric, so not a competitor; overlaps the latency half on one machine. Already CONFLICTS with main on its own in 11 files (last update 2026-07-30); same with the head", receipt = "OWNERSHIP/r20261001-02" },
  { pr = 125802, author = "Finn763", head = "543af5de19", touches = "agent/turn_context.py prefetch delivery channel (does not edit this PR's files)", result = "already CONFLICTS with main on its own (agent/turn_context.py and 2 test files); same with the head", receipt = "MERGE/r20261001-03" },
  { pr = 125881, author = "pstarkgit", head = "d3fdffcf82", touches = "agent/memory_manager.py _prefetch_provider: a fail-closed memory-admission check after the provider returns", result = "clean on main and with the head. In the merged tree its check sits right after the success/empty record call and can return '' (5 returns vs 4), so there is still one row per exit, but a context the check blocks is recorded as success. Read from the merged tree, not run", receipt = "OWNERSHIP/r20261001-03; re-confirmed on aaa863f7ff in OWNERSHIP/r20261001-04" },
  { pr = 108965, author = "jonpol01", head = "39dd41fe68", touches = "agent/memory_manager.py recalled-context sanitizer (outside _prefetch_provider)", result = "clean on main and with the head; _prefetch_provider unchanged in the merged tree", receipt = "OWNERSHIP/r20261001-03; re-confirmed on aaa863f7ff in OWNERSHIP/r20261001-04" },
  { pr = 15412, author = "tabtablabs-dev", head = "69c5a41321", touches = "agent/memory_manager.py prefetch_all (2026-07-19, draft)", result = "stale, different purpose (Discord preview); already CONFLICTS with main on its own (8 files)", receipt = "OWNERSHIP/r20261001-03; re-confirmed in OWNERSHIP/r20261001-04" },
]
adjacent_closed_prs = [
  { pr = 98045, author = "Navlem", head = "77f018b7db", touches = "agent/agent_init.py + config: configurable prefetch timeout (does not edit memory_manager.py)", result = "CLOSED unmerged 2026-10-01T12:51:06Z by Navlem as a duplicate of #87028 ('This is not fixed on main'). Its head merged cleanly on main and with the head (MERGE/r20261001-03, 12:34Z, before the close). Dropped from the demand signals", receipt = "OWNERSHIP/r20261001-03" },
  { pr = 126457, author = "mozhongzhou", head = "822f7b2835", touches = "agent/memory_manager.py _prefetch_provider timeout exit (CLI health indicator; not a shared metric)", result = "CLOSED unmerged 2026-10-01T16:23:32Z by its author, with no comment and the head unchanged; the author has no other PR (open or closed), so no replacement. While open it was clean on main and CONFLICTED with the head at the timeout exit (both add a line before return \"\"); the keep-both resolution passed test_shared_metrics_loop + test_memory_provider + test_memory_health (115 of 115, MERGE/r20261001-03, 12:34Z). OWNERSHIP r03 recorded it as open at 16:14:25Z, nine minutes before the close; manifest r4 (16:35Z) and PR_BODY.md kept it as an open conflict until this round", receipt = "OWNERSHIP/r20261001-04" },
]
close_after = []
demand = { score = 24, source = "catalog.json memory-prefetch-telemetry-and-probe (impact 2, evidence moderate); selection combined 4.76", signals = ["#124151 (kweez007: timed Hindsight by hand)", "#120042 (Navlem: production audit, ~53 dropped prefetches/day)", "#87028 (richardclawbot: configurable timeout; rodrigogs's field evidence there: 101 of 197 agent starts with no injected recall, not all attributable to the 8 s cap. He argues for a tunable bound over more logging, so this is demand for visibility of the drop, not for a counter as such)"], dropped = ["#98045 (closed 2026-10-01T12:51Z as a duplicate of #87028)"] }
maintainer_signal = "teknium1 is actively extending the same shared-metrics series (2e56f40c16, 25c1b008c8, f7b5ea6f7a, d8d9639d8e all 2026-09-27)"

[ownership]
searched_at = "2026-10-01T16:53Z"   # OWNERSHIP/r20261001-04, after #126457's close at 16:23:32Z; the previous search (16:14Z, OWNERSHIP r03) predates that close, as r02's 12:15Z search predated #98045's
queries = ["prefetch metric", "prefetch telemetry", "memory prefetch", "prefetch_provider", "prefetch shared metrics", "memory.prefetch", "record_memory_prefetch", "external prefetch", "prefetch timeout", "prefetch latency", "every result page (since r03; r02 kept only the first 100 of 152 'memory prefetch' hits): 177 unique open PRs at 16:53Z (r03: 178; only #126457 left, nothing added), all file-scanned; 50 touch the watched files, all merge-tested against aaa863f7ff and the head; none adds a prefetch record call", "teknium1 open PRs: 260, the same set as r01's full scan (titles for prefetch|telemetry|metric: 0; that scan's 2871 changed files for memory_manager|shared_metrics stand)", "git log -i --grep=prefetch on main aaa863f7ff (16:52Z): none in the 25 commits since the base; the 15 earlier commits since 2026-09-20 (r03) do not meter prefetch (closest: d1267d8045 runs prefetch on multimodal turns, cbe23de61a dedups recalled lines)", "kvnloo/hermes-agent issues and PRs matching prefetch: 0 at 16:52Z (#404's 39 rows do not mention prefetch)"]
teknium1_open_prs = { count = 260, scanned = 260, same_set_as = "OWNERSHIP/r20261001-01", title_hits = [], file_hits = [113678], note = "#113678 (OPEN) changes inject_memory_provider_tools (disabled tools), not _prefetch_provider; the same 260 again at 16:53Z", receipt = "OWNERSHIP/r20261001-04" }
open_external = []            # no open PR adds a prefetch counter; see adjacent_open_prs for the same-code PRs
merged_overlap = []
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # TUI/HUD lanes, no overlap
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none known (PLAN.txt lives under ~/.hermes and is off limits; not checked)"
verdict = "OURS (no external owner); demand from #124151, #120042 and the field evidence on #87028 (#98045 closed as its duplicate); one open PR conflicts with the head (#92118); #126457 closed unmerged by its author; risk: teknium1 may land the same row himself"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]   # not touched

[[donors]]
sha = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "own leaf (production + tests + schema + doc row), one commit"
trailer = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
credit_check = "no external contributor's code or idea is used: the counter follows teknium1's in-tree pattern (25c1b008c8, 2e56f40c16) and the catalog's own unified-memory proposal; #124151 and #120042 are cited as demand signals in PR_BODY.md; #87028/rodrigogs's evidence is a demand signal in this manifest only and is not cited in PR_BODY.md; classifying inside the guarded builder was the round-1 re-verifier's suggestion (internal review, no external credit)"

[evidence]   # local durable paths; claude/ledger:factory/xf/... copies pending. Receipts hold repo-relative paths and placeholders only.
receipts = [
  { id = "F08/r20261001-03", path = "receipts/F08-r20261001-03.json", sha256 = "db62e9cd548d23f3d53072656350ee69a6aa7fbad2bd5a40d08a625ec4fd12fa", sha256_as_written = "4323bde09499ef17763de15d8ea4f24ebea74721ed479eb9394b0c3704506cb0" },
  { id = "E17/r20261001-04", path = "receipts/E17-r20261001-04.json", sha256 = "1196c730a3440bfa868cd44b6e54e2d9a947af7473a3f256f5c00a6444eb8411", sha256_as_written = "58db7e0af63eeeda1923daa446870f53d9d400751741f53b0f4eb1c9070af110" },
  { id = "E17d/r20261001-02", path = "receipts/E17d-r20261001-02.json", sha256 = "04dbbb6b554b73767a596abdc706bf42bea10de94b5c9fe8f46eae3f7ca2feeb", sha256_as_written = "3365dcb103a0397ebba9dde9a0e3e9f3b33bb9e233f681fe20846cdfae6fba63" },
  { id = "T0-SCHEMA/r20261001-03", path = "receipts/T0-SCHEMA-r20261001-03.json", sha256 = "99a348d1f6d05fa9f9a912ec8ba1a167a91b0ccfe74a899497427968886cb91a" },
  { id = "MERGE/r20261001-03", path = "receipts/MERGE-r20261001-03.json", sha256 = "2e3cecb22c777f7e05e8e2e137e2dc51860dcbb7e4911e6cb6fbf5d4cea78c48" },
  { id = "OWNERSHIP/r20261001-04", path = "receipts/OWNERSHIP-r20261001-04.json", sha256 = "09b8c11d703112d8aff0810cbe671859f58dd458b15ba00fefb15d1b833a62d8" },
  { id = "F08/r20261001-04", path = "receipts/F08-r20261001-04.json", sha256 = "35bb1491acd4714e173436cd28325b63199ba8382f0307459747ba89d2ac2c84", note = "replay of the head's diff on main aaa863f7ff; complements F08/r20261001-03, does not replace it" },
]
# Superseded receipts stay in place unchanged apart from redaction. sha256 is the file as it is now; sha256_as_written is the hash
# as first written, before the 2026-10-01 in-place redactions: local paths (round 1 of stfix) and the "env.host" machine name,
# replaced by "<host>" in 9 F08/E17/E17d receipts (round 3 of stfix; work/r4/host_redaction_r4.json). Receipts that cite a
# superseded receipt cite its sha256_as_written.
superseded_receipts = [
  { id = "OWNERSHIP/r20261001-03", path = "receipts/OWNERSHIP-r20261001-03.json", sha256 = "3f1372957a4472436fda2d26b4fc8dc26f4ca1d3fd15371701a5321c3d319102", by = "OWNERSHIP/r20261001-04", why = "recorded #126457 as open (correct at its 16:14:25Z check; its author closed it unmerged at 16:23:32Z), so its head-only conflict count (2: #92118, #126457) is now 1 open PR (#92118)" },
  { id = "OWNERSHIP/r20261001-02", path = "receipts/OWNERSHIP-r20261001-02.json", sha256 = "55f264ebbbf9c0f6482a28d4222c8433ba5bfa00663fda1c9942aaedfdd1a055", by = "OWNERSHIP/r20261001-03", why = "recorded #98045 as OPEN (correct at its 12:15Z search; closed 12:51Z as a duplicate of #87028); kept only 100 of 152 'memory prefetch' hits; did not merge-test the hits that touch the watched files" },
  { id = "F08/r20261001-02", path = "receipts/F08-r20261001-02.json", sha256 = "69059635c89e3cf281e3a9e78ea16e4c4c59469c8deaf885e3d3f7415ce97392", sha256_as_written = "160bd52592adbd0a06b8687903f4db88d5b9b55620e16d3cc50b0174c9fcc13f", by = "F08/r20261001-03", why = "head 519876fa02; its contract test asserted sub-2 s wall-clock buckets (flake risk listed under limitations while flaky=false)" },
  { id = "E17/r20261001-03", path = "receipts/E17-r20261001-03.json", sha256 = "4b6bbdf3a00fdfda618ad6942fe2c0aa27f4ab1f52bd27e33635d2d9eb1a3c9b", sha256_as_written = "c0e152d4f9123bac071bf1dd05a8e88b5172076def0c6827cde26b99731d761d", by = "E17/r20261001-04", why = "measured at c815543bc2; the amended success/empty call was rerun" },
  { id = "E17d/r20261001-01", path = "receipts/E17d-r20261001-01.json", sha256 = "c1ccd6a462c5227919c116b99c2634cec89607e768b8530f489d48aaf6498689", sha256_as_written = "7e3a8638ab38c5cff3ec137cb2f5e2941d2df40297a44feaf3c6eabd29a897ba", by = "E17d/r20261001-02", why = "measured at 519876fa02" },
  { id = "T0-SCHEMA/r20261001-02", path = "receipts/T0-SCHEMA-r20261001-02.json", sha256 = "c333b0e7c47e55ffd4f7ef6078e6c63c24a71f692995283d22065c948da1ecf8", by = "T0-SCHEMA/r20261001-03", why = "builder changed; schema/contract/doc blobs identical" },
  { id = "MERGE/r20261001-02", path = "receipts/MERGE-r20261001-02.json", sha256 = "5d721ad49a573add9373a7fd7b0a473dc0e43c908a7b03906f2bde6b36882fa1", by = "MERGE/r20261001-03", why = "old head/base; no merge test against #87028, #86948, #92118 (the #92118 conflict and hazard were missed); missed #120042, #98045, #126457, #65329" },
  { id = "OWNERSHIP/r20261001-01", path = "receipts/OWNERSHIP-r20261001-01.json", sha256 = "07b1659df318b5517772105c5e2b84f054516aa4b81ef3b7057d2e3d37a1869d", by = "OWNERSHIP/r20261001-02", why = "missed #120042 (second demand signal) and #65329, #126457, #98045" },
  { id = "F08/r20261001-01", path = "receipts/F08-r20261001-01.json", sha256 = "5487bc4af0dbca569deee80c5566412cd055a541e24ad2a89c348a03b249253e", sha256_as_written = "aeee1549bcc8e0668699abacb94002e6bdcb0b1541d11f9846433db0a6763bc6", by = "F08/r20261001-02", why = "head c815543bc2; command held a scratch path" },
  { id = "E17/r20261001-02", path = "receipts/E17-r20261001-02.json", sha256 = "5924512df0f14d1e379392f608d4e37477377a5428be90adb15081dc13fad03a", sha256_as_written = "e56f44b7bae8282e428e13b3eb6ef3890d96f5ba9273aacb052863fe810655e3", by = "E17/r20261001-03", why = "A/A stated as +/-8 and +/-30 us; unestablished enabled()-check attribution; local paths" },
  { id = "E17/r20261001-01", path = "receipts/E17-r20261001-01.json", sha256 = "1040c74021ada4177aa8ef323a06125f7a2bc869dd19822466266d4b143e20b3", sha256_as_written = "0cc477b9907d49569fe747448445029cd91aa5288ae9f00bc9551306c53ecd6f", by = "E17/r20261001-02", why = "env label said the Relay binding was the shipped runtime; it is nemo-relay 0.8.4" },
  { id = "T0-SCHEMA/r20261001-01", path = "receipts/T0-SCHEMA-r20261001-01.json", sha256 = "ff94835af0ca0ae58c7fc29d48e08ae1359181b9e76ecaf7834730810a8a51d5", sha256_as_written = "ad89767764a9aeaf0d792fd7797f549c5ff693983ba304cdf8715c0e3a08f722", by = "T0-SCHEMA/r20261001-02", why = "overstated the schema's provider bound; local paths" },
  { id = "MERGE/r20261001-01", path = "receipts/MERGE-r20261001-01.json", sha256 = "95e81c42398cb6fa4fea8aaef7c67a028d9b513379b13ab60ba1256bf2f71a22", sha256_as_written = "95e81c42398cb6fa4fea8aaef7c67a028d9b513379b13ab60ba1256bf2f71a22", by = "MERGE/r20261001-02", why = "old base; derived semantics read as observed" },
]
patch = { path = "memory-prefetch-metric.patch", sha256 = "2cbe69a2387ecea2bda1b272a9ab5f5f534d8ba74721100e8dd33b52e76fdc36", head = "569ad4d84b" }
superseded_patches = [
  { path = "memory-prefetch-metric.v2-519876fa02.patch", sha256 = "ff6031101153d7b9de80f34944c76b90b0a884ee196079545c3de277e06cf6c9", note = "v2 head (the file previously named memory-prefetch-metric.patch)" },
  { path = "memory-prefetch-metric.v1-c815543bc2.patch", sha256 = "dfa9fff6445c6214a5899834ef6e2eb6d070e21864e1dc0e2416550a81578801", note = "v1 head; identical to v2 except the From <sha> line" },
]
red = { test = "tests/hermes_cli/test_shared_metrics_loop.py::test_external_prefetch_records_each_exit_with_how_long_the_turn_waited", main = "040b6df2c4", marker = "AssertionError: assert [] == [('honcho', '... 'failed', 1)] (Right contains 5 more items, first extra item: ('honcho', 'success', 1))", receipt = "F08/r20261001-03" }
green = { reps = "3/3 (16/16 tests each)", receipt = "F08/r20261001-03" }
replay_on_current_main = { main = "aaa863f7ff", replay_commit = "27d0a5e42f (temporary, unreferenced; same patch-id and the same 6 blobs as 569ad4d84b)", tree = "21c423feb3 (= merge-tree of main and the head)", red = "15 of 16 pass, the contract test fails with the same marker", green = "3/3, 16 of 16 pass each", negative_control = "10/10 re-RED on exactly the contract test", stall = "1.5 s stall passes; round-2 test with a 0.15 s stall fails", adjacent = "12 files: 330 of 330 pass on main, 331 of 331 with the replay", receipt = "F08/r20261001-04" }
negative_control = { mutation = "10 single-hunk reverts: skip/timeout/error/success record calls, mark projection, provider rule, outcome typo, empty rule (new), latency 0, constant latency above the timeout (new)", result = "10/10 re-RED on exactly the contract test", receipt = "F08/r20261001-03" }
stall_tolerance = { amended_test = "PASS with every fake provider stalled 1.5 s", round2_test = "FAIL with a 0.15 s stall (success/empty/failed rows in 100ms_to_250ms), the flake the re-verifier named", receipt = "F08/r20261001-03" }
adjacent = { identical = true, observed = "12 files: base 040b6df2c4 330 passed / 0 failed; head 569ad4d84b 331 passed / 0 failed (+1 = new test)", pre_existing = [] }
guards = { F14 = "PENDING (factory standing set not built yet)" }
quantitative = []             # no value claim in the body; E17/E17d numbers are mechanism and cost evidence
cache_read_ratio = { status = "N_A", why = "no prompt/prefix change: returned context byte-identical across arms (E17 r04)" }
route_scope = "n/a"
not_tested = ["py3.14 + nemo-relay 0.9 (the shipped shared-metrics runtime; runs used py3.11 + nemo-relay 0.8.4)", "hosted memory backends over a real network", "package send (send: false throughout)", "Windows/macOS", "full test suite", "#124151's 20 s path (the 10s_to_30s / plugin row is derived, not run)", "a real merge of #92118 beyond the keep-both resolution probe; #87028, #86948, #65329 and #125802 already conflict with main on their own", "tests on the clean merges (#125881, #108965 and 9 others, re-confirmed clean on aaa863f7ff); only merge-tree and a reading of the merged _prefetch_provider", "E17/E17d/T0 on main aaa863f7ff (they ran on 569ad4d84b; the 6 changed blobs are identical in the replay)", "a thread.start() failure inside _prefetch_provider (the uncovered exit in invariant_gap)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "", commit = "" }

[gates]
P1 = "PASS"        # RED on 040b6df2c4 (the commit's parent, current main at fetch)
P2 = "PASS"        # no external owner (OWNERSHIP r04, 16:52-16:57Z, after #126457's close): 260 teknium1 PRs (same set as the full scan); 10 prefetch queries re-run with every page, 177 hits file-scanned, 50 merge-tested against aaa863f7ff; #124151/#120042/#87028 demand; #65329/#92118/#125881 same code without a shared counter; 1 open PR conflicts with the head (#92118); #98045 closed as a duplicate of #87028; #126457 closed unmerged by its author (16:23:32Z), no replacement
P3 = "PASS"        # one invariant, 6 files +145/-6, no env var, no hook, extends the existing contract pattern
P4 = "PASS"        # real MemoryManager.prefetch_all/_prefetch_provider path; only the provider is faked; E17 r04 drives _memory_turn_start_and_prefetch on the real Relay binding
P5 = "PENDING"     # RED/GREEN 3/3/SABOTAGE 10/10/STALL/ADJACENT identical all pass on 569ad4d84b (F08 r03) and again with its diff replayed on main aaa863f7ff (F08 r04), flaky=false with no sub-2 s wall-clock bound; F14 was not run (guard map not available yet), so P5 cannot be PASS
P6 = "N_A"         # no value claim
P7 = "PASS"        # one commit on 040b6df2c4, author correct, merge-tree clean on aaa863f7ff (25 commits later, 16:52Z; tree 21c423feb3, reproduced by the F08 r04 replay) and in the final check (main still aaa863f7ff, clean); workflow push-trigger scan 0/52 for staged/ and staging/ names (no .github change since the base); not pushed; not rebased (optional per the round-3 re-verifier; no invalidate_on path moved)
P8 = "PENDING"
P9 = "PASS"        # self-check after the r5 correction: PR_BODY.md names one open conflicting PR (#92118; #126457 dropped, closed) and discloses the thread.start() gap; AI assistance disclosed; no @mentions; no factory jargon
P10 = "PENDING"    # round-3 re-verifier read 569ad4d84b and rejected on manifest and PR text only (#126457 stale, 1 blocking finding), fixed in manifest r5; its re-check is still needed
P11 = "RECORDED"
P12 = "PENDING"

[selection_gates]
redgreen_per_outcome = "MET (F08 r03: each of the 4 exit record calls reverted alone re-REDs, and so does the new empty rule; GREEN 3/3)"
disabled_records_nothing = "MET (pytest collection-off test extended with a prefetch; E17 r04: 0 rows and no store created with collection off)"
no_prompt_prefix_change = "MET (E17 r04: returned context identical base vs head for all 7 faults; diff touches no prompt code)"
hot_path_below_noise_microbench = "NOT MET as worded; needs an owner ruling (re-word or waive) before PROMOTION_READY. Re-measured on 569ad4d84b (host load1 about 2.5-3). E17 r04: median delta +37.77 us/call collection off (p05..p95 +34.71..+40.11), +111.45 us on (+107.49..+120.04); A/A p05..p95 -2.78..+1.39 off, -3.40..+10.96 on. E17d r02: head - base +37.17 us off (A/A -3.95..+0.38); with the record call swapped for a no-op the delta is +1.80 us (-2.70..+3.04, just above A/A), so the record call is essentially the whole cost: about 35 us in place against 21.3 us measured alone (enabled() alone 12.7 us; record_execution_backend alone 22.2 us). Round-2 values on 519876fa02 were +47.05/+158.76 (E17 r03) and +44.12 (E17d r01) at higher host load. The in-place cost of the existing record_* sites was not measured."
labels_bounded_provider_rule = "MET (T0 r03: 450/450 contract combinations pass both the schema and the contract check. The schema types provider as vocabulary_identifier and checks the pattern only: a lowercase raw name such as `hindsight` validates. The closed set is enforced by the contract (counter_dimensions_are_valid at the mark projection and the store write) and the builder's provider rule, which S6 sabotage pins. Of 6 out-of-contract rows, the schema rejects 5 and the contract rejects 6. Builder samples 9/9, including '  ', None and a non-str value giving `empty` without raising)"
doc_row_enumerates_values = "MET (outcomes enumerated; latency given as the tool-call bucket range lt_100ms ... gte_30s, matching the doc's style for bucket ranges)"

[verification]
verifier = ""
provenance = "independent"
exact_head = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""
previous = [
  { head = "c815543bc2", accept = false, findings = 7, fixed_in = "v2", source = "phase3_results.json verdicts[memory-prefetch-metric]" },
  { head = "519876fa02", round = "stfix round-1 re-verifier", findings = 4, fixed_in = "v3", note = "1 blocking (timing test vs AGENTS.md:384-385), 2 manifest gaps (#92118 conflict and hazard; #120042 and #65329 missing), 1 disclosed open item (hot-path gate)" },
  { head = "569ad4d84b", round = "stfix round-2 re-verifier", accept = false, findings = 2, fixed_in = "manifest r4 (this file; no code change)", note = "1 manifest error (#98045 still treated as open in four places and in OWNERSHIP r02; it closed at 12:51Z as a duplicate of #87028), 1 restated non-blocking open item (hot-path gate NOT MET as worded; STAGING/PR numbers confirmed against E17 r04 and E17d r02)" },
  { head = "569ad4d84b", round = "stfix round-3 re-verifier", accept = false, findings = 5, fixed_in = "manifest r5 (this file) + PR_BODY.md; no code change", note = "1 BLOCKING text finding (#126457 closed unmerged by its author at 16:23:32Z, before manifest r4's 16:35Z entry, but still listed as an open conflict in PR_BODY.md and in nine places here); 4 advisories: hot-path gate NOT MET as worded (unchanged, status stays STAGED), commit 21 behind main (merge-tree clean; rebase optional, not done; replayed on the newer main instead), gates reported honestly (P5/P8/P10/P12 PENDING, P6 N_A), code nits (a) thread.start() raising leaves no row (disclosed, not fixed), (b) empty provider name maps to builtin (teknium1's existing memory_provider_name rule, not changed), (c) the collection-off test is a guard, not a red test (as recorded)" },
]

[merge_check]
main_sha = "aaa863f7ff2dec1821be1652b5d15ad14ecea70b"
checked_at = "2026-10-01T16:52Z"
final_check = { at = "2026-10-01T17:06Z", main = "aaa863f7ff (unchanged)", merge_tree_clean = true, tree = "21c423feb3", cited_state_changes = 0, query_total_changes = 0, record = "OWNERSHIP/r20261001-04 results.final_state_check" }
clean = true
tree = "21c423feb3"
recheck = "git -C <h.git> merge-tree --write-tree <current main> staging/memory-prefetch-metric"

[push]
remote_branch = "staged/memory-prefetch-metric"
no_follow_tags = true
workflow_push_matches = 0
pushed_at = ""

[body]
path = "PR_BODY.md"
kind = "pr-body"
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
jargon_lint = "PASS (self-check)"
privacy_scan = "PASS (synthetic fixtures only; no local paths, no session ids, noreply emails only)"
pr_create_command = "gh pr create -R NousResearch/hermes-agent --base main --head kvnloo:staged/memory-prefetch-metric --title 'feat(telemetry): count external memory prefetch outcomes and wait' --body-file PR_BODY.md   # NOT run by the factory"

[queue]
board = "kvnloo/hermes-agent#404"
position = "after the 39 existing rows"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

## Invariant

Every exit of `MemoryManager._prefetch_provider` for an external provider records exactly one `hermes.memory.prefetch.count` row when shared metrics are on, and nothing when they are off. The row has a bounded provider, outcome and wait bucket and is written on the caller's thread.

Known gap (round-3 re-verifier nit (a), disclosed in PR_BODY.md, not fixed): if `thread.start()` itself raises, for example `RuntimeError: can't start new thread`, `_prefetch_provider` exits by that exception exactly as on main, and no row is written. `prefetch_all` then logs it as a non-fatal prefetch failure. Covering it would need a try/except around `thread.start()` inside `_external_prefetch_lock`, plus a flag so the record call still runs outside the lock, plus a test that fakes a start failure. That is more code and another test for a rare case, so it is left as a stated gap.

Real call path exercised:
- pytest: `MemoryManager.prefetch_all` → `_prefetch_provider` → `record_memory_prefetch` → `shared_metrics_events._emit` → `memory_prefetch_fields` (success/empty decided here, inside the guard) → Relay mark → `_DECISION_MARK_METRICS` projection → `SharedMetricsStore`, read back from SQLite. Relay is the `direct_runtime` fake.
- E17 r04: `agent.turn_context._memory_turn_start_and_prefetch` → the same chain on the real nemo-relay 0.8.4 native binding, with a `MemoryProvider` subclass doing HTTP against a loopback fault backend. Also bundled `holographic`.

## Premise re-check (current main)

- **Still needed.** On `040b6df2c4` and on current main `aaa863f7ff` (2026-10-01T16:52Z, 25 commits later), `_prefetch_provider` records nothing on any exit. All 8 `invalidate_on` files have the same blobs on both; `agent/memory_manager.py` is blob `d023a57f8b`, as on the v1 and v2 bases.
- **Nobody else is doing it.** Receipt: OWNERSHIP/r20261001-04 (16:52-16:57Z, plus a final state check at 2026-10-01T17:06Z; supersedes r03, whose 16:14Z check came before #126457 closed, as r02's came before #98045 closed).
  - No open upstream PR adds a prefetch counter. The 10 queries in `[ownership]` were re-run with every result page: 177 unique open PRs (r03: 178; only #126457 left), all file-scanned. The 50 that touch the watched files were merge-tested against current main and the head: 38 already conflict with main, 11 merge cleanly with both, and 1 open PR conflicts with the head only (#92118, below).
  - teknium1 still has the same 260 open PRs that the full scan covered (no title matches prefetch, telemetry or metric; only #113678 touches `agent/memory_manager.py`, outside prefetch).
- **Demand.**
  - #124151 (kweez007) timed Hindsight by hand.
  - #120042 (Navlem, open since 2026-09-23) raises the default bound to 12 s after a production audit: 18–27 s recalls and about 53 dropped prefetches in one day.
  - #87028 (richardclawbot, open) makes the timeout configurable. On it, rodrigogs posted field evidence on 2026-09-06: the 8 s join fired 4 times in about an hour, coinciding with 18.4–47.1 s embeds, and 101 of 197 agent starts injected no external memory, which he could not all pin on the 8 s cap. He also argues that a tunable bound matters more than more logging. So this is demand for seeing the drop, not a request for a counter as such.
  - All three fix or tune the bound; none adds a way to see the drop rate.
  - #98045 (Navlem) is no longer a signal: Navlem closed it unmerged at 2026-10-01T12:51Z as a duplicate of #87028 ("This is not fixed on main").
- **Same code, not a counter.**
  - #65329 (Soju06) adds an opt-in local JSONL turn trace with a `prologue.memory_prefetch` span around the `prefetch_all` call in `agent/turn_context.py`, tagged hit/empty. It overlaps the latency half on one machine, records nothing shared, and already conflicts with main in 11 files (last updated 2026-07-30). A maintainer may ask about it; the answer is that the trace times all providers together for one user, and this counter gives each exit's outcome across opted-in installs.
  - #92118 (seradin) is a structured observation side channel that says it adds no telemetry.
  - #125881 (pstarkgit) adds a fail-closed memory-admission check. It merges cleanly, but in the merged tree the check runs right after the success/empty record call and can return `""`. Each exit still writes one row, but a context the check blocks is recorded as `success`. This was read from the merged tree, not run (Next steps 6).
- **Closed since manifest r4.** #126457 (mozhongzhou) marked the provider unavailable at the same timeout exit for a CLI status-bar indicator and conflicted with the head there. Its author closed it unmerged at 2026-10-01T16:23:32Z, with no comment and the head unchanged, and has no other PR, so there is no replacement (OWNERSHIP r04). OWNERSHIP r03 had recorded it as open at 16:14:25Z, and manifest r4 (16:35Z) and PR_BODY.md still listed it as an open conflict; both are corrected in r5.
- **No origin dimension needed.** The background review, curator and delegate children run with `skip_memory=True`, so their prefetches never reach this code. Unlike `memory.op.count`, this metric does not need an `origin` dimension.
- **Outcome names.** The selection proposed {ok, empty, timeout, inflight_skip, error}. The commit uses the series' existing vocabulary instead: `success`, `empty`, `timed_out`, `skipped`, `failed`. This matches `TASK_OUTCOMES`, `CURATOR_OUTCOMES` and `memory.op.count`.

## Route and carrier choice

`core-leaf`: our own single commit, with no carrier and no competitor. The refreshed ownership scan (OWNERSHIP r04) found no open PR that adds a prefetch counter. #124151, #120042 and #87028 are demand. #65329, #92118 and #125881 touch the same code without a shared counter, and only #92118 conflicts with the head. #98045 has closed as a duplicate of #87028, and #126457 was closed unmerged by its author with no replacement. So the promotion form stays `core-pr`; no salvage-support or HOLD form applies. It follows teknium1's 2e56f40c16 + 25c1b008c8 pattern:
- the contract, schema and doc row as in 2e56f40c16;
- the call sites and read-back tests as in 25c1b008c8.

The selection deferred the evals/memory probe half (maintainer-fit: lead with the counter). The probe stays a local receipt (E17) and is not part of the commit.

## What changed in v3 (round-1 re-verifier)

1. **Timing test (blocking).** AGENTS.md:384-385 (Teknium, 2026-09-04) says "Timing tests must not assume a quiet runner: wall-clock bounds >= 2s, event-based sync". The v2 test asserted `lt_100ms` for four rows and `250ms_to_500ms` at a 0.3 s timeout (200 ms of headroom). F08 r02 listed that risk under limitations but still recorded `flaky = false`.
   - **Fix.** The test now uses a 2.0 s timeout. It asserts the exact (provider, outcome, count) rows, the timed-out row in the timeout's own bucket (`tool_latency_bucket(2000)` = `2s_to_5s`; at least 2 s is guaranteed by `Thread.join`, with 3 s of slack), and every other row in a bucket that a wait shorter than the timeout can produce.
   - **Bounds.** No bound in the test is below 2 s.
   - **Sabotage.** S8 (latency 0) still re-REDs, and so does the new S10 (constant 2500 ms): no constant latency satisfies both bounds.
   - **Stall check.** The new test passes with every fake provider stalled 1.5 s. The v2 test fails with a 0.15 s stall.
   - **Cost.** The test now takes about 2 s.
2. **#92118 conflict and hazard.** The v2 head computed `"success" if result and result.strip() else "empty"` in the caller, outside `_emit`'s guard. #92118 lets `result` be a `MemoryPrefetchResult`, so a keep-both resolution raised `AttributeError` inside `_prefetch_provider`, and #92118's per-provider `except` dropped that provider's recalled context (probe: context `''`).
   - **Fix.** v3 passes the raw value (`record_memory_prefetch(provider.name, "success", started, recalled=result)`), and `memory_prefetch_fields` classifies it inside the guard with an `isinstance` check. The same resolution now keeps the context (probe: `'- prefers tabs'`, one `('honcho', 'empty')` row).
   - **Remaining.** The textual conflict is still there, and a structured result counts as `empty` until the builder reads `.context`. Recorded in Next steps 6.
3. **Missing overlaps.**
   - Added #120042 (second demand signal; merges cleanly, merged tree 72 of 72 pass), #98045 (closed since, see below) and #126457 (same timeout exit; keep-both resolution 115 of 115 pass; closed since, see manifest r5). Added #65329 (local trace; not a competitor).
   - Recorded that #87028, #86948, #65329 and #125802 already conflict with main on their own.
4. **Hot-path gate.** Still not met; re-measured on the new head (see `[selection_gates]`); owner ruling still needed.

## What changed in manifest r4 (round-2 re-verifier; no code change)

The branch is still `569ad4d84b`. What changed: this manifest, the PR_BODY.md wording, one new receipt (OWNERSHIP r03), and a host-name redaction in nine existing receipts.

1. **#98045 is closed.** Navlem closed it unmerged at 2026-10-01T12:51:06Z as a duplicate of #87028. This manifest's 12:57Z recheck and 13:00Z History entry came after the close but still listed it as open.
   - It is now in `adjacent_closed_prs` and `demand.dropped`, and out of the Premise, Route, P2 and P11 wording.
   - OWNERSHIP/r20261001-03 supersedes r02, which recorded it as OPEN at 12:15Z, before the close.
   - PR_BODY.md never cited #98045.
2. **Replacement demand signal.** #87028 (open) with rodrigogs's field evidence: 101 of 197 agent starts with no injected recall. His comment argues for a tunable bound over more logging, and the manifest says so.
3. **Every cited PR and issue re-checked at 16:14Z.** At that time all were open except #98045. The fork's #404 was open with 39 rows, #322 open, and #402 and #403 closed. *Corrected in r5:* #126457 closed at 16:23:32Z, nine minutes after this check and twelve minutes before the r4 History entry, and nothing re-checked it in between (the 16:28Z reconfirmation covered main only). So "all open except #98045" was already false when r4 was written.
4. **Ownership scan widened.** r02 stored only the first 100 of 152 `memory prefetch` hits. r03 lists every page (178 unique open PRs), file-scans all of them, and merge-tests the 51 that touch the watched files. No new conflict with the head was found. One new semantic overlap turned up: #125881 merges cleanly, but a context its check blocks would be recorded as `success`. #108965 and #125881 were added to `adjacent_open_prs`.
5. **Freshness.** Main is now `44a1ce9724` (21 commits after the base, with no `invalidate_on` path changed), merge-tree is clean, and the workflow scan stands because nothing under `.github/` changed. The same 10 PR heads give the same merge results.
6. **Hot-path gate.** Unchanged and still NOT MET as worded; see `[selection_gates]`. The verifier confirmed the numbers against E17 r04 and E17d r02.
7. **PR_BODY.md wording.** Counts are now stated as "N of M pass", the AI-assistance line covers the description and the measurements too, the conflict sentence names exactly the two PRs that conflict, and one line about #125881 was added. *(Corrected in r5: by 16:35Z only #92118 was still open; PR_BODY.md now names one conflicting PR.)*
8. **Host name redacted.** Nine F08/E17/E17d receipts (three of them cited) carried the machine name in `env.host`. It was replaced by `<host>` in place, following the round-1 path-redaction precedent. Nothing else in them changed. `[evidence]` now lists each file's new sha256 next to its `sha256_as_written`. The receipts that cite a superseded receipt cite its as-written hash, so they still match.

## What changed in manifest r5 (round-3 re-verifier; no code change)

The branch is still `569ad4d84b`. What changed: this manifest, PR_BODY.md, and two new receipts (OWNERSHIP r04, which supersedes r03, and F08 r04, a replay on current main). No existing receipt was edited.

1. **#126457 is closed (the blocking finding).** Its author, mozhongzhou, closed it unmerged at 2026-10-01T16:23:32Z. He left no comment; the only review activity is Copilot bot reviews from 2026-09-28. The head is unchanged (`822f7b2835`). He has no other PR in the repo, open or closed, so there is no replacement.
   - OWNERSHIP r03 recorded it as open at 16:14:25Z, nine minutes before the close. Manifest r4 was written at 16:35Z, but its 16:28Z reconfirmation covered main only. This is the same mistake as round 2's #98045 finding.
   - Moved to `adjacent_closed_prs`. Dropped from the route comment, P2 (front matter and checklist), the Premise "Same code, not a counter" bullet, the Route section, NOT_TESTED and Next steps 6.
   - The head-only conflict count is now 1 open PR (#92118), in the merge comment, the Premise, the Ownership evidence row and P2. The manifest-r4 item 3 and the 16:35Z History entry are corrected in place, with a note.
   - PR_BODY.md now says "One open PR, #92118, conflicts with this one", and the #126457 sub-bullet is gone.
2. **Every cited PR and issue re-checked after the close.** OWNERSHIP r04 re-checked all 33 upstream numbers this manifest, PR_BODY.md and OWNERSHIP r03 cite, at 16:52Z. Only #98045 and #126457 are closed; the other 31 are open, and the 10 open adjacent heads are unchanged. A final state check at 2026-10-01T17:06Z found no change: main still aaa863f7ff, merge-tree clean, none of the 33 states or heads changed, the 10 query totals unchanged, the fork branch name still free. The same receipt re-ran the 10 queries with every page (177 hits; nothing added, only #126457 gone) and the teknium1 set (the same 260). It file-scanned all 177 hits: 50 touch the watched files and none adds a prefetch record call. It merge-tested those 50 against main `aaa863f7ff` and the head: 38 already conflict with main, 11 are clean with both, and 1 conflicts with the head only (#92118). No class or head changed since r03. The fork's #404 is open with 39 rows, #322 is open, #402 and #403 are closed, and `staged/memory-prefetch-metric` is still absent on the fork.
3. **Freshness, and the rebase advisory.** Main is now `aaa863f7ff`, 25 commits after the base. No `invalidate_on` path and nothing under `.github/` changed. merge-tree is clean (tree `21c423feb3`).
   - The re-verifier called rebasing optional. It was not done: moving the branch would change the exact head that P10 reads, and no watched path has moved.
   - Instead, F08 r04 replays the head's diff on that main as a temporary, unreferenced commit, `27d0a5e42f`. It has the same patch-id and the same 6 blobs, and its tree equals the merge-tree result.
   - Every F08 cell gives the same result as on `040b6df2c4`: RED (15 of 16 pass, the contract test fails with the same marker); GREEN 3/3 (16 of 16 pass each); 10/10 sabotage re-RED on exactly the contract test; the 1.5 s stall cell passes and the round-2 test fails at 0.15 s; and the 12 adjacent files go from 330 of 330 passing to 331 of 331.
   - This replaces the NOT_TESTED item "F08 on main 44a1ce9724". The worktree is removed.
4. **Hot-path gate (advisory).** Unchanged, and still NOT MET as worded (`[selection_gates]`). Status stays STAGED until the owner re-words or waives it.
5. **Gate honesty (advisory).** No gate changed state. P5 stays PENDING because F14 was not run, and that holds even though F08 r04 passed. P8, P10 and P12 stay PENDING. P6 stays N_A, because the body discloses the cost and makes no value claim.
6. **Code nits (advisory; no code change).**
   - (a) If `thread.start()` raises, no row is written. Disclosed, not fixed: see `invariant_gap` and the Invariant section. PR_BODY.md now says the five exits are covered and this case is not.
   - (b) `memory_provider_name` maps an empty provider name to `builtin`. That is teknium1's existing rule from 2e56f40c16, shared with `memory.op.count`. The `MemoryProvider` ABC requires a name, so it is left alone; changing it would alter the existing metric too.
   - (c) The extended collection-off test cannot fail on base. It is recorded as a guard, not a red test, as F08 r03 already says; the new contract test is the red test.

## Evidence

| Experiment | Receipt | Verdict | Label | n | Result |
|---|---|---|---|---|---|
| F08 RED on base | F08/r20261001-03 | PASS | OBSERVED | 1 | new test fails on `040b6df2c4`: `assert [] == [...]` (no rows) |
| F08 GREEN | F08/r20261001-03 | PASS | OBSERVED | 3 | 16/16 each rep, no FLAKY retry |
| F08 per-hunk sabotage | F08/r20261001-03 | PASS | OBSERVED | 10 | 10/10 re-RED on the contract test only (S9 empty rule and S10 constant latency are new) |
| F08 stall tolerance | F08/r20261001-03 | PASS | OBSERVED | 2 | amended test passes with a 1.5 s stall on every fake provider; v2 test fails with 0.15 s |
| F08 adjacent | F08/r20261001-03 | PASS | OBSERVED | 12 files | base 330/0, head 331/0 |
| F08 replay on current main | F08/r20261001-04 | PASS | OBSERVED | 1 + 3 + 10 + 2 + 2 runs | head's diff on main `aaa863f7ff` (temporary commit `27d0a5e42f`, tree `21c423feb3` = merge-tree result): RED 15 of 16 pass (contract test fails, same marker); GREEN 3/3, 16 of 16 each; 10/10 sabotage re-RED; 1.5 s stall passes, round-2 test at 0.15 s fails; adjacent 330 of 330 on main, 331 of 331 with the replay |
| E17 fault classes | E17/r20261001-04 | KEEP | OBSERVED | 12 per fault x 7 | outcome = expected for every fault. One row per turn on head, 0 rows on base. |
| E17 hang | E17/r20261001-04 | KEEP | OBSERVED | 4 turns | 1 `timed_out` (1s_to_2s) + 3 `skipped` (lt_100ms), then 1 `success` after release. 1 backend call while hung. Shipped 8 s bound → `5s_to_10s` (8001.75 ms). |
| E17 profile scope | E17/r20261001-04 | PASS | OBSERVED | 1 | row in owning profile 1, default home 0 |
| E17 collection off | E17/r20261001-04 | PASS | OBSERVED | 4 turns | 0 rows, no store file created |
| E17 prompt/prefix | E17/r20261001-04 | PASS | OBSERVED | 7 faults | returned context identical base vs head |
| E17 turn wait (p50 ms, base → head) | E17/r20261001-04 | report | OBSERVED | 12 | ok 0.53 → 0.63; delay_0.05 50.89 → 51.12; delay_0.4 400.86 → 401.09; slow_over_timeout(1 s) 1000.26 → 1000.49; empty 0.47 → 0.61; error 0.50 → 0.59; refused 0.21 → 0.39 |
| E17 microbench `_prefetch_provider` | E17/r20261001-04 | gate NOT MET as worded | OBSERVED | 12 blocks x 400 | median Δ +37.77 us off (p05..p95 +34.71..+40.11; A/A median +0.43, −2.78..+1.39); +111.45 us on (+107.49..+120.04; A/A +0.06, −3.40..+10.96) |
| E17d in-place attribution | E17d/r20261001-02 | report | OBSERVED | 16 blocks x 400 x 5 arms | Off: head − base +37.17 us (A/A −3.95..+0.38). Record call swapped for a no-op: +1.80 (−2.70..+3.04, just above A/A), so the record call in place is about 35 us. Import hoisted: +1.59 (−0.33..+4.42). On: +110.72; no-op +2.68; record call +108.29. Alone: record 21.28 us off (enabled() 12.67), 94.77 on; record_execution_backend 22.19 / 96.46. |
| E17c holographic (real bundled provider) | E17/r20261001-04 | KEEP | OBSERVED | 20 turns | 10 success + 10 empty rows, provider label `holographic`, all lt_100ms; rows = turns |
| T0 schema/contract/doc | T0-SCHEMA/r20261001-03 | KEEP | OBSERVED | 450 combos + 6 bad rows + 9 builder samples | 450/450 pass schema and contract. Bad rows: schema rejects 5/6 (a lowercase raw name `hindsight` passes the pattern), contract rejects 6/6. Builder samples 9/9 (`'  '`, None and a non-str value give `empty`, none raises); doc row enumerates outcomes |
| Freshness / overlap | MERGE/r20261001-03 | KEEP | OBSERVED | 10 PRs | moved onto `040b6df2c4` (8 commits after `aea969677c`, no `invalidate_on` path changed); #124151 / #120042 / #98045 clean (merged trees: 74 of 74 and 72 of 72 pass for #124151 and #120042; #98045 has closed since); #92118 and #126457 conflicted with the head only at 12:34Z (keep-both probes above; #126457 has closed since); #87028, #86948, #65329, #125802 already conflict with main; workflow push-trigger matches 0/52 |
| Freshness recheck | OWNERSHIP/r20261001-04 | KEEP | OBSERVED | 1 main + 10 open PR heads + final check | main `aaa863f7ff` at 16:52Z: 25 commits after the base, no `invalidate_on` path changed (all 8 blobs equal), merge-tree clean (tree `21c423feb3`); the 10 open adjacent heads unchanged with the same merge results; no `.github/` change; final check at 2026-10-01T17:06Z: main unchanged, merge-tree clean, no cited state or head changed, query totals unchanged (supersedes the r03 recheck on `44a1ce9724`) |
| #124151 20 s semantics | MERGE/r20261001-02 | report | DERIVED | - | a 20 s Hindsight timeout would land in `10s_to_30s` as provider `plugin`; from the bucket and provider rules, not run (unchanged by v3) |
| Ownership | OWNERSHIP/r20261001-04 | KEEP | OBSERVED | 260 PRs + 10 queries (177 hits) + 50 merge-tree pairs | no open prefetch counter; all 33 cited PRs/issues re-checked at 16:52Z, after #126457's close (31 open; #98045 closed as a duplicate of #87028; #126457 closed unmerged by its author at 16:23:32Z with no comment and no replacement PR); demand #124151, #120042, #87028; of the 50 hits that touch the watched files, 38 already conflict with main, 11 merge cleanly with main and the head, 1 open PR conflicts with the head only (#92118). Supersedes r03 (16:14Z: 51 hits, 2 head-only including #126457) |

All F08/E17/E17d/T0 numbers above were measured on `569ad4d84b`. Host load1 was about 8 to 10 during F08 and about 2.5 to 3 during E17/E17d (other agents share the host); round 1 ran at 5 to 17. Microsecond figures are inflated by the shared host, A/A included. An identical F08 run on the intermediate amend `61fc6ea62d` (same production code, test comment reworded since) gave the same results; it is kept under `work/r3/superseded-61fc6ea62d/` and not cited.

## Experiments run

- **F08** (round 3): per-outcome RED/GREEN with each `record_` call reverted, plus the stall cells.
  - Receipt: `receipts/F08-r20261001-03.json` (supersedes r02).
  - Driver: `work/r3/mpm_prove_r3.py`.
  - Command per cell: `HOME=<scratch>/testhome-sf-memory-prefetch-metric HERMES_HOME=$HOME/.hermes HERMES_PYTHON=<read-only py3.11 venv>/bin/python bash scripts/run_tests.sh -j 2 tests/hermes_cli/test_shared_metrics_loop.py -q`.
- **E17** (rerun): delay/hang/empty/error fault probe against a local fake provider, extending the `evals/memory/honcho_current_query.py` pattern. It uses the loopback guard and environment isolation lifted from `evals/provider_fallback/probe_104260.py:11-39`. It adds a profile-scope check, a collection-off check, a base-vs-head microbenchmark and a real bundled provider cell.
  - Receipt: `receipts/E17-r20261001-04.json` (supersedes r03, which ran on `c815543bc2`).
  - Scripts: `work/e17_prefetch_fault_probe.py`, `work/e17c_holographic_probe.py` (unchanged).
  - Command: `env -i PATH=/usr/bin:/bin <read-only py3.11 venv>/bin/python work/e17_prefetch_fault_probe.py --repo <worktree@569ad4d84b> --base-mm work/r3/base_memory_manager_d023a57f8b.py --out work/r3/e17_result_r3.json` (the base file is main's `agent/memory_manager.py`, blob `d023a57f8b`, unchanged since `572e4f4fad`).
- **E17d** (rerun): in-place attribution with arms base, base A/A, head, head with the record call swapped for a no-op, and head with the function-level import hoisted.
  - Receipt: `receipts/E17d-r20261001-02.json`.
  - Script: `work/r3/micro_attribution_r3.py` (the no-op takes the `recalled=` keyword).
  - Command: `env -i PATH=/usr/bin:/bin <read-only py3.11 venv>/bin/python work/r3/micro_attribution_r3.py --repo <worktree@569ad4d84b> --base-mm work/r3/base_memory_manager_d023a57f8b.py --sandbox-root <scratch> --out work/r3/micro_attribution_r3.json`.
- **T0-SCHEMA**: static schema ↔ contract ↔ doc agreement, which layer rejects each out-of-contract row, and 9 builder samples.
  - Receipt: `receipts/T0-SCHEMA-r20261001-03.json`.
- **MERGE**: the move to current main, the merge matrix over 10 open PRs, targeted tests on three merged trees, the #92118 keep-both probe, the workflow push-trigger scan and the fork-name check.
  - Receipt: `receipts/MERGE-r20261001-03.json`.
- **OWNERSHIP** (round 5): the same checks, taken after #126457's close against main `aaa863f7ff`, plus #126457's close details, its author's other PRs and a final state check just before this manifest was written.
  - Receipt: `receipts/OWNERSHIP-r20261001-04.json` (supersedes r03).
  - Scripts: `work/r5/recheck_r5.py`, `work/r5/final_state_r5.py`, `work/r5/make_receipts_r5.py`. They are read-only on GitHub (`gh api` GET). Main and the PR heads were fetched by SHA with `--no-write-fetch-head`, and no ref was written.
- **F08 replay** (round 5): the unchanged round-3 driver `work/r3/mpm_prove_r3.py`, run on a temporary commit that applies the head's diff onto main `aaa863f7ff`.
  - Receipt: `receipts/F08-r20261001-04.json`.
  - The commit was made in a detached worktree under the stfix3 worktree root, which is now removed. No ref points at `27d0a5e42f`.
  - Command per cell: as in F08 r03, with the test home `<scratch>/testhome-sf3-memory-prefetch-metric`.
- **OWNERSHIP** (round 4, superseded): state of every cited PR/issue, teknium1 recount (same 260 PRs), the 10 prefetch queries with every page, a changed-file scan of all 178 hits, a merge-tree matrix of the 51 that touch the watched files against main `44a1ce9724` and the head, and the freshness recheck.
  - Receipt: `receipts/OWNERSHIP-r20261001-03.json` (supersedes r02).
  - Scripts: `work/r4/recheck_r4.py`, `work/r4/fullscan_r4.py`, `work/r4/flagged_merge_r4.py`, `work/r4/clean_semantics_r4.py`, `work/r4/newhits_r4.py`, `work/r4/make_receipts_r4.py`. They are read-only on GitHub (`gh api` GET) and use `git merge-tree` on the local object store. PR heads were fetched with `--no-write-fetch-head` and no refs were written.

## Experiments queued (not run)

The selection lists only $0 experiments for this item (E17, F08). Both ran. These follow-ups are optional and none is needed for the PR's claim, since the PR makes no value claim.

1. **T1-env: rerun on the shipped runtime** ($0; blocked on a disposable Python 3.14 venv, which needs a networked build step).
   ```
   python3.14 -m pm.build_env --source <worktree@569ad4d84b> --out <factory venv dir>/py314-<uv.lock sha12> --group dev --group test
   HOME=<scratch>/testhome-sf-memory-prefetch-metric HERMES_HOME=$HOME/.hermes HERMES_PYTHON=<that venv>/bin/python bash scripts/run_tests.sh -j 2 tests/hermes_cli/test_shared_metrics_loop.py tests/hermes_cli/test_relay_shared_metrics_runtime.py -q
   env -i PATH=/usr/bin:/bin <that venv>/bin/python work/e17_prefetch_fault_probe.py --repo <worktree@569ad4d84b> --base-mm work/r3/base_memory_manager_d023a57f8b.py --out work/e17_py314.json
   ```
2. **T2: local-model turn share** (GPU lane, serial, flock). Gated by OD-1 (a preset of 64K or more, because `MINIMUM_CONTEXT_LENGTH` is 64000) and OD-2 (CLI entrypoint inside bwrap from the disposable venv). It measures prefetch's share of submit-to-first-token with holographic plus the slow fixture provider.
   ```
   # $RUN/.hermes/config.yaml:
   #   model: {default: qwen3-8b-64k, provider: custom, base_url: <local model host>/v1}
   #   memory: {provider: holographic}
   #   telemetry: {shared_metrics: {enabled: true, send: false}}
   flock <gpu lock> env -i PATH=<venv>/bin:/usr/bin:/bin HOME=$RUN HERMES_HOME=$RUN/.hermes <venv>/bin/hermes -z "What telescope do I own?"   # x30, then read rows with SharedMetricsStore(<HERMES_HOME>/telemetry/shared_metrics/metrics.sqlite3, .../outbox).counter_snapshot()
   ```
3. **T3: hosted-backend outcome mix** (paid). Gated by OD-3 and K3: the owner launches it with injected credentials, and no worker holds credentials. Each cell is one owner profile per hosted provider (honcho, hindsight via catalog, mem0, supermemory), with shared metrics on and `send: false`, run for N=50 real turns.
   ```
   HERMES_HOME=<owner throwaway profile> hermes -z "<turn prompt>"   # x50 per provider
   <venv>/bin/python -c "from hermes_cli.observability.shared_metrics import SharedMetricsStore as S; import sys; r=sys.argv[1]+'/telemetry/shared_metrics'; print([x for x in S(r+'/metrics.sqlite3', r+'/outbox').counter_snapshot() if x['metric_name']=='hermes.memory.prefetch.count'])" <owner throwaway profile>
   ```
   It reports the `timed_out` share per provider at the 8 s bound, which is the data #124151 and #120042 gathered by hand.

## Gate checklist (P1-P12)

- P1 Need: PASS. RED marker matched on `040b6df2c4`, the commit's parent (F08 r03).
- P2 Ownership: PASS. No external owner (OWNERSHIP r04, 16:52-16:57Z, after #126457's close; final state check at 2026-10-01T17:06Z). #124151, #120042 and #87028 are demand. #65329, #92118 and #125881 touch the same code without a shared counter; only #92118 conflicts with the head. #98045 closed at 12:51Z as a duplicate of #87028. #126457 was closed unmerged by its author at 16:23:32Z, with no replacement.
- P3 Shape: PASS.
  - One invariant; 6 files, +145/−6.
  - Adds no env var, no hook, no shim.
  - The `memory.op.count` contract pattern is reused.
- P4 Real path: PASS. Only the provider is faked (F08, E17 r04).
- P5 Proof: PENDING. RED, GREEN 3/3, SABOTAGE 10/10, STALL and ADJACENT identical all pass on `569ad4d84b` (F08 r03), and again with the same diff replayed on main `aaa863f7ff` (F08 r04). `flaky = false` now rests on the test having no wall-clock bound below 2 s and on the 1.5 s stall cell, not on a quiet runner. F14 was not run because the standing-set guard map does not exist yet (Wave 0), so P5 cannot be PASS.
- P6 Numbers: N_A. The body makes no value claim. The microbenchmark gate is reported as not met as worded.
- P7 Package: PASS.
  - One commit on `040b6df2c4`, author Kevin Rajan.
  - merge-tree clean on `aaa863f7ff`, current main at 2026-10-01T16:52Z (25 commits later, no `invalidate_on` path changed, tree `21c423feb3`), and in the final check at 2026-10-01T17:06Z (main still aaa863f7ff, clean). The F08 r04 replay reproduces that tree.
  - Not rebased. The round-3 re-verifier called it optional, and moving the branch would change the head that P10 reads.
  - `feat(telemetry):` subject.
  - Workflow trigger scan: 0 matches for `staged/memory-prefetch-metric` and `staging/memory-prefetch-metric` (nothing under `.github/` changed since the base).
- P8 Freeze: PENDING. No z0evals study yet, and receipts are not yet copied to `claude/ledger:factory/xf/`. All receipts hold placeholders instead of local paths and the host name (redacted in place in round 3; see `[evidence]`), so the S5 validator should not trip on them. The raw logs and result JSON under `work/` (cited only by sha256) still print local paths, so they stay local and are not copied.
- P9 Text: PASS (self-check). PR_BODY.md follows the template, deletes "For New Skills", lists what was not tested, discloses AI assistance, and has no @mentions and no factory jargon. It names the one open keep-both conflict (#92118; #126457 dropped in r5 because it closed) and the #125881 labelling overlap (read, not run) for the maintainer. It says which exits are recorded and that a `thread.start()` failure is not. It states counts as "N of M pass". Its AI-assistance line covers the code, the tests, the runs and the description. It does not cite #98045.
- P10 Independent read: PENDING. The round-1 re-verifier's 4 findings are fixed or carried in v3. The round-2 re-verifier rejected on manifest text only (#98045), fixed in r4. The round-3 re-verifier read `569ad4d84b` and rejected it on manifest and PR text only: #126457 had closed but was still listed as an open conflict. That is fixed in manifest r5, and its re-check is needed.
- P11 Demand: RECORDED. Catalog score 24. The concrete demand is #124151, #120042 and the field evidence on #87028. #98045 was dropped (closed as a duplicate of #87028). #47119 and #21566 are tangential.
- P12 Queue: PENDING. Goes behind the 39 existing #404 rows; staging cap of 5 (OD-8).
- Global: Wave 0 (F15, F14, E48, F11) has not passed, so no branch can be PROMOTION_READY yet.
- Selection gate "hot-path overhead stays below noise in a microbenchmark": NOT MET as worded. The owner must re-word or waive it before PROMOTION_READY (see Next steps 5).

## NOT_TESTED

- **Shipped runtime:** Python 3.14 with nemo-relay 0.9. All runs used the read-only Python 3.11 venv with nemo-relay 0.8.4. Under 0.8.4, Relay plugin activation logs a `TypeError` (`additional_plugins_toml`), but scope events, the subscriber and the store record normally.
- **Hosted memory backends over a real network:** Honcho cloud, Hindsight, mem0 and Supermemory. Their latency distributions and their failure modes, such as raising versus returning `""`, are not measured.
- **#124151's 20 s path:** the `10s_to_30s` / `plugin` row is derived from the bucket and provider rules. No run exercised it.
- **Merges beyond the probes:** #92118 (the one open PR that conflicts with the head) was checked only with a keep-both resolution (a probe test and the targeted files). #126457 got the same check while open and has closed since. #87028, #86948, #65329 and #125802 already conflict with main on their own, so no merge order was tried for them.
- **Clean merges (rounds 4 and 5):** #125881, #108965 and the other 9 clean pairs got merge-tree only, re-confirmed against `aaa863f7ff`. No tests ran on them. #125881's `success` labelling for a blocked context was read from the merged tree.
- **E17, E17d and T0 on current main `aaa863f7ff`:** not rerun. They ran on `569ad4d84b`. The 6 changed blobs are identical in the F08 r04 replay, and no `invalidate_on` path changed. (F08 itself was replayed there; see F08 r04.)
- **A `thread.start()` failure:** not exercised. It is the uncovered exit (`invariant_gap`).
- **Package export and send:** `send: false` throughout.
- **Platforms and suite scope:** Windows and macOS; the full test suite (only targeted files ran).
- **Desktop and TUI surfaces:** the TUI and Desktop drive the same `turn_context` path, but no TUI or Desktop turn was run.
- **Holographic failure mode:** holographic swallows its own errors, so its failures appear as `empty`.

## Origin action (owner only)

Push the branch to the fork as `staged/memory-prefetch-metric`, for example `git push --no-follow-tags <fork> 'refs/heads/staging/memory-prefetch-metric:refs/heads/staged/memory-prefetch-metric'` (zsh: keep the refspec quoted). OD-0 is resolved for this item by that rename. Then open the PR with the `pr_create_command` above and `--body-file PR_BODY.md`. The factory runs neither. The smallest alternative: a comment on #124151 or #120042 that offers the counter as a follow-up.

## Next steps

1. **Blind verification:** a different worker runs a blind exact-head read of `569ad4d84b` with the oracle block (P10).
2. **F14 guard map:** once `factory-replay-gate` Wave 0 exists, record the F14 guard map for this head (P5).
3. **Rebase only if needed:** before promotion, re-run the merge-tree recheck and the F08 GREEN on the newest main. Rebase only if `invalidate_on` paths moved.
4. **Freeze and copy:** freeze the cited receipts (z0evals) and copy them, this file and the patch to `claude/ledger:factory/xf/staging/memory-prefetch-metric/` (P8).
5. **Owner ruling on the microbenchmark gate:** the gate as worded is not met. The owner either waives it or re-words it, for example to "the record call costs no more than the existing record_* call sites". That comparison holds for the standalone cost only (E17d r02: 21.3 us vs record_execution_backend's 22.2 us off). In place the call costs about 35 us, and the in-place cost of the existing sites was not measured. If the per-call wording stands, E17d shows the cost is the record call itself (the other edits cost about 2 us), with enabled() about 13 us of it; the remedy would be a cheaper shared record path for every record_* site, which is out of scope for this PR.
6. **Watch the overlapping PRs** (MERGE r03 has the details):
   - **#124151 or #120042 lands first:** re-run F08 on the merged main. Both merged trees already pass.
   - **#92118 lands first:** resolve the `agent/memory_manager.py` conflict by keeping both lines: our `record_memory_prefetch(provider.name, "success", started, recalled=result)` and their `if isinstance(result, str) and result.strip():`. Then make `memory_prefetch_fields` read `.context` from a `MemoryPrefetchResult`, so a structured result is not counted as `empty`, and re-run F08. Do not move the success/empty decision back into the caller. With v2's caller-side expression, the keep-both resolution raised `AttributeError`, and #92118's per-provider `except` dropped that provider's recalled context.
   - **#125881 lands first (or second):** the merge is clean, but a context its admission check blocks is recorded as `success`. Decide whether that is right (the provider did return context) or whether the check should run before the record call. Then re-run F08.
   - **#87028 (the keeper for the configurable timeout since #98045 closed), #86948 or #65329 is rebased:** each already conflicts with main on its own, so its author rebases first. Then re-run the merge-tree check and F08.

## History

- 2026-10-01T08:52Z | CANDIDATE | memory-prefetch-metric builder (Claude Code) | premise re-checked on 572e4f4fad, no owner, worktree created
- 2026-10-01T08:59Z | EVIDENCED | builder | commit c815543bc2; RED/GREEN/sabotage/adjacent (F08) recorded
- 2026-10-01T09:12Z | STAGED | builder | E17, T0-SCHEMA, MERGE receipts; local branch staging/memory-prefetch-metric; worktree removed
- 2026-10-01 | VERIFYING → rejected | phase-3 verifier | accept=false, 7 findings: teknium1 PR count (40 → 260) and partial scan; A/A stated as ±8/±30 µs; #124151 20 s row stated as observed; hot-path gate not met and ~20 µs unattributed; T0 overstated the schema's provider bound; commit 11 commits behind main; local paths and an internal address in STAGING.md and receipts
- 2026-10-01T11:50Z | STAGED (v2) | stfix round 1 (Claude Code) | cherry-picked onto aea969677c as 519876fa02 (diff identical) and moved the local ref; F08 re-proved; all 260 teknium1 PRs scanned (OWNERSHIP r01); A/A ranges, the derived #124151 wording and the T0 provider wording corrected in STAGING.md, PR_BODY.md and new receipts; E17d attributes the per-call delta; local paths and the internal address replaced by placeholders, superseded receipts redacted in place; fork branch name staged/memory-prefetch-metric (OD-0 resolved by the rename); temp commits 3ed268422f (#124151 on main) and e5e0a7e336 (simulated merge) left unreferenced in h.git; worktree and scratch homes removed
- 2026-10-01 | re-verify → 4 findings | stfix round-1 re-verifier | BLOCKING: contract test asserted sub-2 s wall-clock buckets against AGENTS.md:384-385; #92118 conflict and caller-side AttributeError hazard unrecorded (and #87028/#86948 conflict with main); #120042 and #65329 missing; hot-path gate still needs an owner ruling
- 2026-10-01T13:00Z | STAGED (v3) | stfix round 2 (Claude Code) | cherry-picked 519876fa02 onto e8c97320ac and amended (2 s timeout with relational bucket asserts; success/empty classified inside the guarded builder); an intermediate amend 61fc6ea62d was fully proven, then its test comment was reworded (it claimed a busy runner 'cannot' move a row) and the commit cherry-picked onto 040b6df2c4 as 569ad4d84b; everything re-proved there: F08 r03 (RED, GREEN 3/3, 10/10 sabotage, stall cells, adjacent 330/331), E17 r04, E17d r02, T0 r03, MERGE r03 (10-PR matrix, #92118 keep-both probe old vs new head, merged-tree tests for #124151/#120042/#126457), OWNERSHIP r02 (#120042, #98045, #126457, #65329); local ref force-moved to 569ad4d84b; PR_BODY.md updated; v2 patch kept as memory-prefetch-metric.v2-519876fa02.patch; probe merges were --no-commit in the stfix worktree and aborted (no new refs; 61fc6ea62d and 751d592063 are unreferenced); freshness recheck on a3b56cac95 clean; worktree and scratch homes removed
- 2026-10-01 | re-verify → 2 findings | stfix round-2 re-verifier | accept=false: #98045 closed 12:51Z as a duplicate of #87028 but still treated as open in adjacent_open_prs, demand.signals, the Premise demand bullet and P2/route wording, and OPEN in OWNERSHIP r02; hot-path gate restated as NOT MET as worded (non-blocking, numbers confirmed)
- 2026-10-01T16:35Z | STAGED (v3 head, manifest r4) | stfix round 3 (Claude Code) | text and receipt fix, no code change, branch still 569ad4d84b, no worktree needed. #98045 moved to adjacent_closed_prs and dropped from demand; #87028 with rodrigogs's field evidence added as demand signal 3 (with his pro-bound caveat). OWNERSHIP r03 supersedes r02: 19 cited PRs/issues re-checked (only #98045 closed), teknium1 same 260, 10 queries with every page (178 hits), all file-scanned, 51 merge-tested against main 44a1ce9724 and the head (38 already conflict with main, 11 clean with both, 2 head-only: #92118, #126457 [r5 correction: #126457 had closed unmerged at 16:23:32Z, before this entry, so only 1 open PR (#92118) conflicted with the head when it was written]); new adjacent rows #125881 (clean; blocked context recorded as success, read not run) and #108965 (clean). Freshness: main 44a1ce9724, 21 commits after the base, no invalidate_on change, merge-tree clean, no .github change. PR_BODY.md: "N of M pass" counts, broader AI-assistance line, exact conflict wording, #125881 note. env.host machine name redacted to <host> in place in 9 F08/E17/E17d receipts (new sha256 + sha256_as_written recorded; work/r4/host_redaction_r4.json). PR heads fetched with --no-write-fetch-head (no refs written); a partial work/r4 left by an interrupted earlier attempt (freshness_1605/1606.txt, ownership_*.json/txt, tmp1.txt, empty filescan.log) is not cited
- 2026-10-01 | re-verify → 5 findings | stfix round-3 re-verifier | accept=false: BLOCKING #126457 closed unmerged by its author at 16:23:32Z (no comment, head unchanged, no replacement) but PR_BODY.md said "Two open PRs conflict" and STAGING.md listed it as open in nine places; OWNERSHIP r03 (16:14:25Z) was correct then, and nothing re-checked PR state before the 16:35Z entry. Advisories: hot-path gate NOT MET as worded (unchanged); 21 commits behind main 44a1ce9724, merge-tree clean, rebase optional; gates honest (P5/P8/P10/P12 PENDING, P6 N_A); code nits (a) thread.start() raising leaves no row, (b) empty provider name maps to builtin, (c) collection-off test is a guard
- 2026-10-01T17:12Z | STAGED (v3 head, manifest r5) | stfix round 4 (Claude Code) | text and receipt fix, no code change, branch still 569ad4d84b. #126457 moved to adjacent_closed_prs and dropped from the route comment, P2, the Premise, Route, NOT_TESTED and Next steps; head-only conflict count corrected to 1 open PR (#92118) everywhere, with the manifest-r4 item 3 and the 16:35Z entry annotated. PR_BODY.md: "One open PR, #92118, conflicts", the #126457 sub-bullet removed, and the thread.start() gap disclosed (five exits recorded, a start failure is not). OWNERSHIP r04 supersedes r03: 33 cited PRs/issues re-checked at 16:52Z (31 open; #98045 and #126457 closed), mozhongzhou has no other PR, teknium1 same 260, 10 queries with every page (177 hits; only #126457 gone), all file-scanned, 50 merge-tested against main aaa863f7ff (38 already conflict with main, 11 clean, 1 head-only: #92118; no head or class changed), final state check at 2026-10-01T17:06Z (no change: main still aaa863f7ff, merge-tree clean, none of the 33 states or heads changed, the 10 query totals unchanged, the fork branch name still free). Freshness: main aaa863f7ff, 25 commits after the base, no invalidate_on or .github change, merge-tree clean (tree 21c423feb3). Not rebased (optional; would change the head P10 reads); F08 r04 replays the diff there as unreferenced commit 27d0a5e42f (same patch-id and blobs, tree = merge-tree result): RED, GREEN 3/3, 10/10 sabotage, stall cells, adjacent 330 -> 331 all as on 040b6df2c4; worktree under wt/stfix3 removed, scratch test home removed. Code nits: (a) disclosed as invariant_gap, not fixed; (b) left (teknium1's existing rule); (c) already recorded as a guard. Hot-path gate still NOT MET as worded; status stays STAGED
