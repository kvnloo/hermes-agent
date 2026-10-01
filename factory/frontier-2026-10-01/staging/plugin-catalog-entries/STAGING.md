+++
xf_staging = 1
id = "plugin-catalog-entries"
version = 1
title = "Reshape third-party integrations into standalone repos with SHA-pinned plugin-catalog entries, PAW-PII first"
branch = "staging/plugin-catalog-entries"          # local name in the scratch bare mirror
branch_fork = "staged/plugin-catalog-entries"      # name it gets on kvnloo/hermes-agent
branch_physical = "staging/plugin-catalog-entries in the scratch bare mirror, and on kvnloo/hermes-agent as staged/plugin-catalog-entries at the same SHA 98c305b3ec (seen by gh api matching-refs at 2026-10-01T18:43:13Z, round 5; RECHECK/r20261001-06). Pushed by the factory before 17:40:49Z, when fork issue kvnloo/hermes-agent#412 was opened pointing at it; not pushed by any fixer round. OD-0 is resolved by that rename: the fork's legacy refs/heads/staging 28790e597c blocks refs/heads/staging/<id>. Earlier: no refs/heads/staged/* at 11:10Z; the name was still free at 16:17Z and 16:46Z (RECHECK/r20261001-04 and -05)"
branch_sha = "98c305b3ec8d03693f4dc94bade69035cb15ff7d"
commit_message = "unchanged in round 5, and no message-only v2 was made: v1 is never promoted, and the name staging/plugin-catalog-entries-v2 is reserved for the re-pin built on fresh main (owner fix item 7). The re-pin commit gets a new message written for the v2 entry. Known v1 message gaps it must not copy: 'The plugin redacts PII on the device ... before provider egress' is not true at d891ebdd when installed from the catalog subdir (T1-failopen: paw_pii not importable, payload passes through), and 'fail-open behaviour' and 'readme is off' describe the v1 entry only"
status = "HOLD"          # concrete blocker: the plugin at the pinned SHA fails catalog admission (see Evidence). v1 (98c305b3ec) must never be promoted as is: its entry description ships the MODELED "~600 MB" (owner fix item 7). Round 5: kvnloo/pii main is still d891ebdd, so the blocker stands; round 6 re-read it at 19:09Z: still d891ebdd
route = "plugin-catalog"
promotion_form = "plugin-catalog-entry"
feature = "third-party-plugin-repackaging"
invariant = "A catalog entry pins a 40-hex commit whose plugin passes `hermes plugins validate` and declares exactly what it registers; for paw-pii the pinned plugin must also import and redact when installed from its subdir, and must not report a redaction that did not happen."

[base]
repo = "NousResearch/hermes-agent"
sha = "234badf4012af380d23c91eae55d045a69c69ffb"     # parent of branch_sha; every count below is measured on this SHA unless labelled
fetched_at = "2026-10-01T09:05Z"
measured_on = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0 (F12 and T1); invalidate_on paths unchanged at 234badf401 (git diff --stat empty)"
declared_main = "1798b335c43d7e59066ad74a8c2d1d1c9fd537fe (declared in round 6: the upstream main gh api commits/main gave at 2026-10-01T19:08:41Z, committed 19:08:13Z; 137 commits after the base, 63 after the factory-given main 34f8ec3b40, 2 after 5d077106b8, which the round-6 verifier saw; object already in the scratch mirror, not fetched, no ref points at it). Measured on it in round 6, in the factory sandbox: merge-tree clean (tree 064f9e0c67), the 18 invalidate_on specs and the 14 adjacent files unchanged since 363e9d5f0a (where round 5 re-measured), paw-pii absent (loader 349/349), green 3 of 3 runs pass (validator OK 351 files, loader 350/350), the negative control RED ('assert 349 == 350'), 0 of 11 push workflows (RECHECK/r20261001-07). 5d077106b8 (committed 18:48:00Z) changed only agent/ and tests/agent/ after 105e876586, and 1798b335c4 only agent/, run_agent.py, tests/agent/, one e2e provider test and one developer-guide page after 5d077106b8. The scratch mirror's refs/heads/main stays 34f8ec3b40, the factory-given main, where F14 ran. Round 5 declared 34f8ec3b40 (given by the factory as upstream main; committed 2026-10-01T17:29:37Z; 74 commits after the base, 9 after 44a1ce9724). It replaced 44a1ce9724 (rounds 3 and 4). Measured on it in round 5: merge-tree clean (tree 47e2acb8c2, equal to the F14 arm tree), the 18 invalidate_on specs and the 14 adjacent files unchanged since the base, paw-pii absent (loader 348/348), green 3 of 3 runs pass and the negative control RED (RECHECK/r20261001-06). Upstream main kept moving while round 5 ran: gh api commits/main gave 363e9d5f0a at 18:32:47Z (committed 18:25:54Z) and 105e876586 at 18:40:55Z (committed 18:33:01Z). 363e9d5f0a changes 4 invalidate_on files (the validator, plugin-catalog/README.md, plugin-catalog-ci.yml and a new woof.yaml entry) and 1 adjacent test file, so round 5 re-measured need, green and the negative control there too; all hold. Nothing on those paths moved between 363e9d5f0a and 105e876586. Round 5 said to declare 105e876586 or a later main on the next touch; round 6 did (1798b335c4)"
rechecked_on = "1798b335c4 and 5d077106b8 (round 6, RECHECK/r20261001-07): merge-tree clean on both (trees 064f9e0c67 and 81e4690210), invalidate_on and adjacent files unchanged since 363e9d5f0a, paw-pii absent (349 entry files); need, green 3 of 3 and the negative control re-measured on 1798b335c4 in the factory sandbox; 0 of 11 push workflows match on 1798b335c4. Before that, 34f8ec3b40, 363e9d5f0a and 105e876586 (round 5, RECHECK/r20261001-06): see declared_main; merge-tree clean on all three (trees 47e2acb8c2, a997753eec, 47d51b343d); 0 of 11 push workflows match on 34f8ec3b40 and on 363e9d5f0a. Before that, 44a1ce9724 (round 3, RECHECK/r20261001-04): the 18 invalidate_on paths, the 7 other adjacent test files, tests/conftest.py, scripts/run_tests.sh, pyproject.toml, uv.lock, the PR template (blob 5496eb534f), CONTRIBUTING.md and AGENTS.md are unchanged since the base (plugin-catalog/README.md is inside plugin-catalog/); the 9 pinned hermes blobs other than paw-pii.yaml are identical; merge-tree clean (tree 60459843c2); paw-pii still absent (loader 348/348). Round 4 (RECHECK/r20261001-05), main unchanged: branch head, parent and tree unchanged, 65 commits after the base, merge-tree tree 60459843c2 again, paw-pii.yaml absent and 348 entry files. Earlier: aea969677c at 11:10Z, the same checks (RECHECK/r20261001-02)"

[upstream]
issues = ["NousResearch/hermes-agent#102922 (ours, open: plugin proposal; 2 comments, both by the author; re-read 2026-10-01T16:15Z, 16:41Z and 18:40Z; still open at 19:09Z, round 6)"]
fork_tracking = "kvnloo/hermes-agent#412 (open, created 2026-10-01T17:40:49Z by the factory; title '[staged · HOLD] ...'). It carries HOLD in its title, but its body says 'one commit on upstream main' (the parent is 74 commits behind 34f8ec3b40) and does not say 'not promotable at this pin'. Suggested edit for the owner, not made here (no GitHub writes): add 'v1 at d891ebdd is not promotable as is; the catalog PR comes from staged/plugin-catalog-entries-v2 after the re-pin' and replace 'one commit on upstream main' with 'one commit; merges cleanly on current main'"
closed_ours = ["NousResearch/hermes-agent#102924 (paw-pii plugin_index.json seed, closed by author 2026-09-30; route removed on main by 46ab5aa365 and still absent on 44a1ce9724, 34f8ec3b40 and 363e9d5f0a)", "NousResearch/hermes-agent#87495 (Spatial runtime plugin, closed by author 2026-08-25)", "NousResearch/hermes-agent#98105 (Groq Orpheus TTS, closed by author 2026-09-27)"]
eval_prs = []
carrier = { pr = 0, author = "", head = "" }
competitors = []          # no other PR adds paw-pii; adjacent PII work is listed under [ownership].adjacent
close_after = []
demand = { score = 2, source = "judges.json impact lens: niche, no measurable user pull" }
maintainer_signal = "weak, not none: one AI-assisted triage note on #102924 (2026-09-04) by alt-glitch, a human GitHub User account (profile company @NousResearch, commits on main; author_association NONE on that comment), marked 'This was generated by AI during triage'. It flagged whole-file reformat churn and an unrelated bundled kanban_db change, which the author then removed. It says nothing for or against the plugin. #102922 has no non-author comments. (RECHECK/r20261001-02). Round 5, adjacent but direct: on 2026-10-01 at 17:09-17:14Z teknium1 (author_association COLLABORATOR) reviewed the other local PII catalog entry, #129692 (privacy-gateway), CHANGES_REQUESTED, and listed what it needs before listing: fail closed when a dependency is missing, refuse a runtime model download (~560 MB, unpinned) with a clear error, declare provides_middleware in plugin.yaml, and add a requires_hermes floor for a newer API. paw-pii at d891ebdd fails open and does not declare its middleware (T1; owner fix items 1 and 3), and downloads its program and base model at first use (RECHECK/r20261001-02; whether those downloads are hash-pinned was not checked; owner fix item 3). Nothing was said about paw-pii itself (RECHECK/r20261001-06)"
policy = "plugin-catalog/README.md rules 2, 3, 5, 6, 7, 8, 9 and the Names section"

[[donors]]
sha = "cd7b9d3bcf0bf7373ab8b5893adceb7fda0ca8c6"
author = "Kevin Rajan (kvnloo)"
role = "metadata donor: name, subdir, pin and capability list from the obsolete plugin_index.json entry"
trailer = "none needed (same author as the staging commit)"

[[donors]]
sha = "d891ebdd3a3dab27a3451923eb56f955253a2782"
author = "kvnloo (Hermes integration); programasweights/da03 (model, paw_pii library, package name)"
role = "pinned plugin source (kvnloo/pii, fork of programasweights/pii, 1 commit ahead)"
trailer = "credited in the entry description, not a code reuse"

[ownership]
searched_at = "2026-10-01T11:05Z"
queries = ["gh search prs (open) 'PII', 'redact PII', 'anonymization', 'desensitize', 'privacy middleware', 'paw-pii', 'programasweights', 'pii plugin-catalog'", "gh search prs (merged) 'PII'", "plugin-catalog/*.yaml on main grepped for PII|redact|anonymi|desensiti|pseudonym", "gh issue view 102922", "gh pr view 102924/87495/98105/63917/129692/95186/102049/14624/122574/1542", "kvnloo repo list for orpheus|tinyfish|spatial|canvas|tts|browser", "round 2: gh search prs (open) 'PII' re-run with --limit 200 (111 hits), gh pr view and gh pr diff 17472", "round 3 (2026-10-01T16:15Z): gh search prs (open) 'PII' --limit 200 again (111 hits, the same 111 numbers as round 2); 'paw-pii', 'programasweights', 'pii plugin-catalog' and 'desensitize' still 0 open hits; state re-read for every PR and issue this manifest cites (RECHECK/r20261001-04)", "round 4 (2026-10-01T16:41Z): the same reads again; 'PII' open still the same 111 numbers, the four other searches still 0 open hits, every cited state unchanged (RECHECK/r20261001-05)", "round 5 (2026-10-01T18:40Z): the same reads again plus #129692 comments and reviews; 'PII' open still the same 111 numbers as round 2, the four other searches still 0 open hits; every cited state unchanged except new maintainer activity on #129692 (still open) (RECHECK/r20261001-06)"]
open_external = []        # nobody else claims a paw-pii entry
adjacent = [
  "NousResearch/hermes-agent#63917 (open, Micka420-collab, stale since 2026-07-16): in-tree regex prompt anonymization in agent/prompt_privacy.py behind privacy.* config. Different layer (core), no conflict",
  "NousResearch/hermes-agent#129692 (open, saiteja-madha, 2026-09-30): plugin-catalog/privacy-gateway.yaml, Presidio plus an encrypted alias vault. A different catalog key, no conflict; a reviewer may weigh two local PII plugins together. Maintainer review CHANGES_REQUESTED at 2026-10-01T17:14Z (see [upstream].maintainer_signal)",
  "NousResearch/hermes-agent#95186 (open, Ilannuko): host-side opt-in fail-closed contract for required LLM middleware. Complements owner fix item 3, no conflict",
  "NousResearch/hermes-agent#102049 (open): in-tree document PII anonymizer. No conflict",
  "NousResearch/hermes-agent#14624 (open): in-tree OpenRouter PII masking. No conflict",
  "NousResearch/hermes-agent#17472 (open, teodorofodocrispin-cmyk, stale since 2026-07-29): optional skill optional-skills/trustboost-pii-sanitizer that sends raw text to the hosted TrustBoost API (api.trustboost.dev) for redaction. A skill backed by a remote service, not a catalog entry or middleware, no conflict (added in round 2; RECHECK/r20261001-03)",
]
adjacent_rule = "Listed: open PRs whose main feature detects or redacts PII in content bound for a model or provider (plugin, skill, middleware or core), plus #95186, which changes the middleware contract such a plugin relies on. Round 2 re-ran gh search prs 'PII' (open) at 2026-10-01T11:36Z: 111 hits. Not listed: secret, log, export, telemetry, diagnostic or display redaction (e.g. #37833, #57741, #88608, #34693, #129805); secret-redactor tuning (e.g. #69890, #82196); the existing core redactor applied to one more egress path (#84611 MoA advisor input, #115109 memory-provider sync); a risk scorer that does not redact (#10730); a gateway text-filter hook seam (#125178); and hits with no privacy feature (gateway sender identity, session context, unrelated). RECHECK/r20261001-03. Round 3 re-ran the search at 16:15Z: the same 111 open hits (none new, none gone), and every PR named here is still open, so the list stands (RECHECK/r20261001-04). Round 4 at 16:41Z: the same 111, all still open (RECHECK/r20261001-05). Round 5 at 18:40Z: the same 111, all still open (RECHECK/r20261001-06)"
merged_overlap = [
  "plugin-catalog/desensitize.yaml (merged via NousResearch/hermes-agent#122574): Chinese-context reversible desensitization using hooks, a regex fallback and an optional LLM layer. Adjacent; a different key and engine, no conflict",
  "NousResearch/hermes-agent#1542: core privacy.redact_pii hashes platform user and chat IDs in the gateway system prompt only. Adjacent; a different scope, no conflict",
]
claimant_lanes = [127373, 127374, 127375, 127332, 127228]
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none"
verdict = "own: kvnloo owns kvnloo/pii and wrote integrations/hermes; no external owner (6 adjacent open PRs and 2 adjacent merged items, none adds paw-pii). Attribution with programasweights and use of their package name `paw-pii` as the catalog key are unconfirmed (rule 5, Names)"
excluded_paths = []

[evidence]
receipts = [
  { id = "SLICE/r20261001-01", path = "receipts/SLICE-proof-r20261001-01.json", sha256 = "ee97c00d324b553c9a0b011c298aa8766d75e200664ef7a6313cd35e2bda1c45" },
  { id = "F12/r20261001-01", path = "receipts/F12-r20261001-01.json", sha256 = "96d4108c09ef1b2d4fbabd46bbcb5f73fbb975a11e214fae62adb98e8acc2840" },
  { id = "T1-capability/r20261001-01", path = "receipts/T1-capability-probe-r20261001-01.json", sha256 = "1b1d5c1cfa0eb788cb33178d721c4f2d127042e14fcb1a63b93277cd2008e691" },
  { id = "T1-failopen/r20261001-01", path = "receipts/T1-failopen-r20261001-01.json", sha256 = "d31d5b102a902061d35e40c3690a3ed28f8d5397e35dbd0323178eb6e092fcff" },
  { id = "RECHECK/r20261001-02", path = "receipts/RECHECK-r20261001-02.json", sha256 = "90a4363d7886f9f2c4a1fd51748202494783014a641c8a7de7576d3aab694ece" },
  { id = "RECHECK/r20261001-03", path = "receipts/RECHECK-r20261001-03.json", sha256 = "591f645987dc5f30c253523a436e2e2fcf1eaf451d334e98465cb9bf614fbd9b" },
  { id = "RECHECK/r20261001-04", path = "receipts/RECHECK-r20261001-04.json", sha256 = "fbe43c3bddcb6ae4bb0287714a92e0a2e880fb0bebf66aaf98b4b66f809bbf7e" },
  { id = "RECHECK/r20261001-05", path = "receipts/RECHECK-r20261001-05.json", sha256 = "198693f3e697612a72bcbc901dbe1c03d5d900747bb8f35ffe7eb02052809e09" },
  { id = "F14/r20261001-01", path = "receipts/F14-r20261001-01.json", sha256 = "5920ad3e3dbe5549073f53ecd55c799aba5b6ed4b25be006627144a877f04599" },
  { id = "RECHECK/r20261001-06", path = "receipts/RECHECK-r20261001-06.json", sha256 = "6b9aa63362b8c924e13d597583c5ce21826b65ba465b73410b4ad7e0f6408e65" },
  { id = "RECHECK/r20261001-07", path = "receipts/RECHECK-r20261001-07.json", sha256 = "0614a8667b5652448649b72e5b0dcbaf83b46ca06fd553e0d3800b0728712d9e" },
]
private_moves = "Round 6 (the fresh verifier's blocking finding): the publishable set is everything in this directory outside private/, and local-only material sat in publishable locations. 169 files were moved byte-identical (a rename on the same filesystem) from <path> to private/<path>, keeping the relative path: the 41 raw/ outputs from r20261001-01 (every raw/ file whose name is not raw/r<round>_*; 27 of them hold absolute local paths and 6 the local login), tools/sandbox.sh (absolute paths), and the whole run/ tree (127 files: the pinned kvnloo/pii clone run/src/pii, whose .git/logs/HEAD, logs/refs/heads/main and logs/refs/remotes/origin/HEAD carry the host name and the local login in the reflog identity line and whose packs and index are binary; run/variants/; run/context_methods.json). Old to new: raw/<x> -> private/raw/<x> for those 41 names, tools/sandbox.sh -> private/tools/sandbox.sh, run/<y> -> private/run/<y>. private/MOVED-r6.tsv lists every moved path with its sha256 and size (TSV sha256 c0904e7ff0dea97c7d6b7830f929ae301554ab8004838da115b77d61ea81820b, local-only). All 169 re-hashed equal at the new path, and all 75 artifact hashes the receipts cite still match (30 cited paths now resolve under private/; 3 are F14 maps in the factory directory). No receipt changed, so every receipt sha256 above still matches. Where a receipt, an as-run command in Experiments run or a pinned tool names raw/<r01 name>, tools/sandbox.sh or run/..., the same bytes are now at private/<same path>; tools/build_receipts.py reads raw/ and tools/sandbox.sh at their old paths, so a rebuild check copies them back into a scratch copy first. private/ is never published or frozen (RECHECK/r20261001-07)"
receipt_privacy = "In the four r20261001-01 receipts, host paths are replaced by <staging>, <worktree>, <venv> and <testhome> (round 1), and the env.host hostname by <host> (round 2), all by tools/scrub_receipts.py; measurements unchanged. raw/ outputs from r01 stay local-only (public: false); since round 6 they are at private/raw/ (see private_moves). raw/r1_* to raw/r6_* carry no host paths. Kept on purpose (round 3): the F12 and both T1 receipts, and tools/build_receipts.py line 32, give the pinned kvnloo/pii commit's git display name next to the GitHub login kvnloo. The receipts call it the committer display name; it is also the author display name (round 5 checked by gh that the two names are equal, without copying the name; RECHECK/r20261001-06). That name is public on the commit itself (github.com/kvnloo/pii commit d891ebdd), so it is not private data, but it adds nothing to the evidence. Removing it would change the sha256 of three receipts cited above and of build_receipts.py, which RECHECK/r20261001-03 pins, so v1 keeps the bytes. The v2 receipts, rebuilt for the new pin, will name the GitHub login only"
public_scope = "Round 6 (current rule): everything in this directory outside private/ is publishable, and nothing else is. That is exactly STAGING.md, body.md, plugin-catalog-entries.patch, receipts/*.json, raw/r<round>_* (raw/r1_* to raw/r6_*) and tools/*.py (the .py files directly in tools/). Local-only (public: false) is private/ as a whole: private/raw/ (the 41 r01 raw outputs), private/tools/sandbox.sh, private/run/ (the pinned kvnloo/pii clone with its .git, the calibration variants and context_methods.json) and private/MOVED-r6.tsv. Correction: the round-4 text here called run/ 'working data, no host paths found'. That was incomplete. No scan ever walked run/ (tools/privacy_scan_r4.py skips it), and the clone's reflogs carry the host name and the local login (round-6 verifier; counted in RECHECK/r20261001-07 without printing either). Any file outside private/ that matches none of the publishable rules (a dotfile, a symlink, a subdirectory of tools/ or raw/, tools/sandbox.sh, a run/ tree) is unclassified and blocks publication; tools/privacy_scan_r6.py checks this, walking every file outside private/, and also checks the host name, the local login (whole word), a local list of private terms, binary files and bytecode. tools/privacy_scan_r4.py is superseded: it would now report every private/ file as unclassified, and it never walked run/. Every round-6 and later scan runs with python3 -B or PYTHONDONTWRITEBYTECODE=1. The scope history below is kept as written in rounds 1 to 5, with the old locations. Rounds 4 and 5 (superseded by round 6): Publishable (narrowed in round 4): STAGING.md, body.md, plugin-catalog-entries.patch, receipts/*.json, raw/r1_* to raw/r5_* (raw/r<round>_*; round 5 added raw/r5_*, which tools/privacy_scan_r4.py already classifies as publishable), and tools/*.py, meaning the .py files directly in tools/. Nothing in a subdirectory of tools/ is publishable, and tools/sandbox.sh is not a .py file. Local-only (public: false): raw/ outputs from r01; run/ (the kvnloo/pii clone and the calibration variants); and tools/sandbox.sh, whose as-run bytes (sha256 1f8f65ef..., pinned in the F12 and both T1 receipts and listed in RECHECK/r20261001-03) mask and re-bind host paths. Any other file in this directory is unclassified and blocks publication until it is removed or classified; tools/privacy_scan_r4.py checks this. Every file in tools/ is pinned by sha256 in at least one cited receipt, so none of them can be edited without breaking a cited hash; they stay byte-identical: catalog_probe.py (df35fe7c, SLICE/r20261001-01), f12_census.py (4f55ac29, F12/r20261001-01), t1_probe.py (ff594145, both T1 receipts), sandbox.sh (1f8f65ef, F12 and both T1; at private/tools/sandbox.sh since round 6), wf_scan.py (2c686f5d, RECHECK/r20261001-02), build_receipts.py (e6f34f85), scrub_receipts.py (f331a72b) and privacy_scan.py (c20c602b), all three in RECHECK/r20261001-03 'artifacts', privacy_scan_r3.py (6a578ec4, round 3, RECHECK/r20261001-04 'artifacts'), privacy_scan_r4.py (41abafaf, round 4, RECHECK/r20261001-05 'artifacts') and privacy_scan_r6.py (03e99afc, round 6, RECHECK/r20261001-07 'artifacts'). Round 2 removed every host path from build_receipts.py and scrub_receipts.py (locations now come from XF_WORKTREE, XF_VENV and XF_TESTHOME or the script's own directory); RECHECK/r20261001-03 pins those round-2 bytes. No r20261001-01 receipt pins build_receipts.py or scrub_receipts.py. Rebuilding the four r01 receipts from raw/ with them reproduces the published bytes (RECHECK/r20261001-03). Round 3 added tools/privacy_scan_r3.py, which runs privacy_scan.py unchanged with raw/r3_* added to the scanned set. Correction (round 4): the round-3 claim of a clean scan of the publishable set ('files_scanned 31, files_flagged 0', RECHECK/r20261001-04) covered 31 of the 32 files then in the declared set ('tools/ except sandbox.sh'). privacy_scan_r3.py loads privacy_scan.py through importlib exec_module, which wrote tools/__pycache__/privacy_scan.cpython-314.pyc at 16:21:49Z (5,384 bytes, sha256 0af2b07a..., pinned by no receipt), and privacy_scan.publishable() lists tools/ with iterdir() plus is_file(), which skips subdirectories. That .pyc embedded the absolute host path of privacy_scan.py as its co_filename. Round 4 deleted tools/__pycache__/, narrowed the scope to tools/*.py, and added tools/privacy_scan_r4.py. It loads privacy_scan.py unchanged with bytecode writing off, walks every file outside run/, runs privacy_scan.py's checks over the publishable and unclassified files, and fails on any unclassified, binary or bytecode file. Before the deletion it flagged the .pyc: unclassified, binary, 1 absolute path and 4 private-term hits. After the deletion: 38 publishable files, 0 unclassified, 0 binary, 0 bytecode, 0 of 38 flagged (RECHECK/r20261001-05). Every later scan must run with python3 -B or PYTHONDONTWRITEBYTECODE=1; privacy_scan_r3.py must not be rerun without them. Round 5 reran tools/privacy_scan_r4.py (unchanged) under python3 -B once every other round-5 edit was in place: PASS, 46 publishable files including raw/r5_privacy_scan.txt, 0 flagged, 0 unclassified, 0 binary, 0 bytecode, hostname check on, 8 local private terms (a new local list; the round-4 list was not available, and like it this one stays local). The output is raw/r5_privacy_scan.txt; a second run to stdout covered that file too. Round 6 moved the local-only files under private/ (private_moves) and added tools/privacy_scan_r6.py (it loads privacy_scan.py unchanged with bytecode writing off). Its negative control, on a scratch copy with five planted leaks (an r01 raw output back in raw/, tools/sandbox.sh, a clone reflog under run/, a .pyc in tools/__pycache__/ and a publishable-named file holding only the login), FAILs and flags each plant (raw/r6_privacy_scan_negative_control.txt). Its final run, once every other round-6 edit was in place, is raw/r6_privacy_scan.txt (written after the receipt, so no receipt pins it; see History for the counts). The round-6 local private-terms list has 9 terms; like the earlier lists it stays local"
red = { test = "need: paw-pii absent from load_catalog() on main", main = "234badf401 (SLICE); still absent on aea969677c (RECHECK/r20261001-02), 44a1ce9724 (loader 348/348, RECHECK/r20261001-04), the declared main 34f8ec3b40 (loader 348/348) and 363e9d5f0a (loader 349/349, after woof.yaml landed) (RECHECK/r20261001-06), and the round-6 declared main 1798b335c4 (loader 349/349, in the sandbox; RECHECK/r20261001-07)", marker = "348/348 entries, entry_present=false (349/349 on 363e9d5f0a and 1798b335c4)", receipt = "SLICE/r20261001-01" }
green = { reps = "3/3 (test_shipped_catalog_entries_are_all_valid_and_pinned on 572e4f4fad) + 1/1 on 234badf401; structural OK 350 files; loader 349/349. Round 3, on 44a1ce9724 plus the entry (index tree 60459843c2, equal to the merge-tree result): 3 of 3 runs pass, structural OK 350 files, loader 349/349 (RECHECK/r20261001-04). Round 5, in the factory sandbox: on 34f8ec3b40 plus the entry (index tree 47e2acb8c2 = merge-tree) 3 of 3 runs pass, structural OK 350 files, loader 349/349; on 363e9d5f0a plus the entry (index tree a997753eec = merge-tree) 3 of 3 runs pass, structural OK 351 files under the new subdir and repo rules, loader 350/350 (RECHECK/r20261001-06). Round 6, in the factory sandbox, on 1798b335c4 plus the entry (index tree 064f9e0c67 = merge-tree): 3 of 3 runs pass, structural OK 351 files, loader 350/350 (RECHECK/r20261001-07)", receipt = "SLICE/r20261001-01" }
negative_control = { mutation = "sha: main", result = "RED (validator rc=1; shipped test 'assert 348 == 349'); reproduced on 44a1ce9724 in round 3 (RECHECK/r20261001-04), and on 34f8ec3b40 ('assert 348 == 349') and 363e9d5f0a ('assert 349 == 350') in round 5 (RECHECK/r20261001-06), and on 1798b335c4 (validator rc=1, 'assert 349 == 350') in round 6 (RECHECK/r20261001-07)", receipt = "SLICE/r20261001-01" }
adjacent = { identical = true, base = "68 passed / 13 errors", branch = "68 passed / 13 errors", pre_existing = ["tests/hermes_cli/test_plugins_cmd_catalog.py: 13 setup errors (isolated_python: mandated venv is Python 3.11, main requires ==3.14.*)"] }
admission = { capability_probe = "FAIL 3/3 at d891ebdd (undeclared middleware llm_request, tool_execution); PASS 3/3 with provides_middleware added", security_scan = "safe, 0 findings (plugin-guard-v8)", receipt = "T1-capability/r20261001-01" }
behaviour = { failopen = "canary PII reaches the provider request and tool results in both install layouts, 3/3; full-clone layout trace says 'local PII redaction' with an unchanged payload", receipt = "T1-failopen/r20261001-01" }
disclosure = { source = "programasweights 0.4.10 wheel (sha256 7e82cb9364f0…, equal to the PyPI digest) and kvnloo/pii@d891ebdd", program_host = "programasweights.com (config.py:14) OBSERVED in code", base_model_host = "huggingface.co/programasweights (cache.py:36-37) OBSERVED in code", local_inference = "paw.function default remote=False (__init__.py:421); the plugin passes no remote argument (service.py:76-80) OBSERVED in code", base_model_size = "~600 MB (qwen3-0.6b-q6_k, 622733120 B) MODELED: the repo's frozen-programs.json and the wheel name that runtime, but the server picks the base model for program 73a0e38b at first use (the other option is gpt2-q8_0, 139804832 B); nothing was downloaded", receipt = "RECHECK/r20261001-02" }
guards = { F14 = "EQUAL", receipt = "F14/r20261001-01", arm = "dd185c1f84 (98c305b3ec cherry-picked cleanly onto upstream main 34f8ec3b40, patch byte-identical; local ref refs/xf/w0/plugin-catalog-entries, not pushed)", detail = "2 runs, each 36 PASS / 4 FAIL over 40 verdict ids, identical to the main baseline (verdict, marker, fingerprint) on every id; compare EQUAL baseline-r1, baseline-r2 and r1-r2; flaky excluded: none; set aba79fe8f09d. The 4 FAILs are the baseline's own. No F14 probe reads plugin-catalog/, so EQUAL is the expected result for a data-only entry and says nothing about the entry itself", notes = "Round 6: (1) the receipt's patch_sha256 091552753e... is the sha256 of 'git diff' with 10-hex index abbreviations; it reproduces with git -c core.abbrev=10 (the scratch mirror sets no core.abbrev, and its default gives 74f80da512... for both arms), so the patch-identity claim holds either way (RECHECK/r20261001-07). (2) The notice_delivery FAIL marker in the baseline map and in this receipt is \"KeyError: 'task_failure_notice'\"; the F14 harness summary's 'TypeError: missing overall_start' wording does not match it. This manifest cites the map's marker only" }
quantitative = []
cache_read_ratio = { status = "N_A" }
route_scope = "n/a"
not_tested = ["the catalog entry under F14: no F14 probe reads plugin-catalog/ (F14 itself ran: EQUAL, F14/r20261001-01); RED, GREEN and the negative control were re-run on 34f8ec3b40 and 363e9d5f0a outside F14 in round 5 (RECHECK/r20261001-06), and on 1798b335c4 in round 6 (RECHECK/r20261001-07)", "the reworked plugin-catalog-ci.yml admission job on 363e9d5f0a (pinned-clone confinement, data-only guard for entry PRs; unchanged through 1798b335c4); read, not run: it needs the CLI and a network clone", "adjacent test files on 34f8ec3b40, 363e9d5f0a and 1798b335c4 (unchanged on 34f8ec3b40; tests/scripts/test_validate_plugin_catalog.py gained 20 lines on 363e9d5f0a and is unchanged since)", "hermes plugins validate CLI with --install-deps (E52, needs OD-2)", "redaction with the PAW runtime installed and assets downloaded (T2)", "which base model the server assigns to program 73a0e38b, and its download size (T2)", "whether the programasweights runtime checks a hash on the program bundle and base model it downloads at first use", "whether redacting non-content fields (role, tool_call ids, function names, Responses item ids) breaks a provider request (T2)", "docs site README fetch (entry sets readme: false)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-plugin-catalog-entries", commit = "" }

[gates]
P1 = "PASS"       # need: entry absent on 234badf401, aea969677c, 44a1ce9724, 34f8ec3b40 and 363e9d5f0a (round 5, in the sandbox) and the round-6 declared main 1798b335c4 (in the sandbox, RECHECK/r20261001-07); invalidate_on unchanged from 363e9d5f0a to 1798b335c4; old route gone on 34f8ec3b40, 363e9d5f0a and 1798b335c4
P2 = "PENDING"    # attribution with programasweights + use of the `paw-pii` key; adjacent PRs listed, none conflicts
P3 = "PASS"       # one file, +20; no env vars, hooks or shims
P4 = "PASS"       # rests on production-path execution, not a coverage measurement (no receipt holds one; round-6 advisory): hermes_cli.plugin_catalog.load_catalog loaded the entry and read its capabilities (349/349, SLICE; 350/350 on 363e9d5f0a and 1798b335c4), scripts/validate_plugin_catalog.py and the shipped-entries test ran on the real plugin-catalog/, the production capability probe ran as a library call (T1) and the middleware chain ran the plugin's callbacks (T1-failopen). Accepted for a data-only entry; runtime-present path NOT_TESTED
P5 = "PENDING"    # RED with marker, GREEN 3/3, ADJ identical and F14 EQUAL (F14/r20261001-01) are recorded as met; round 5 re-measured RED, GREEN 3 of 3 and the negative control on 34f8ec3b40 and 363e9d5f0a (RECHECK/r20261001-06). Missing: (a) per-hunk SABOTAGE re-RED: FACTORY gives no N_A, and no receipt records the one hunk reverted alone with re-RED and unpinned hunks listed; (b) flaky = false is not recorded. ADJ was measured on 234badf401; one adjacent test file changed on 363e9d5f0a and was not re-run
P6 = "N_A"        # no value claim; the MODELED "~600 MB" in v1's description is why v1 must never be promoted as is
P7 = "PENDING"    # round 5: PASS changed to PENDING to follow FACTORY 11.1 literally ("one commit on fresh main"; round-4 advisory). The one commit sits on 234badf401, 137 commits behind the round-6 declared main 1798b335c4 (74 behind the factory main 34f8ec3b40). Every other P7 part holds: merge-tree clean on 1798b335c4 (tree 064f9e0c67 = main plus the entry, where round-6 green ran), on 34f8ec3b40 (tree 47e2acb8c2, also the F14 arm tree) and on 5d077106b8 (tree 81e4690210); author and subject correct; no contaminated paths; 0 of 11 push workflows match staged/plugin-catalog-entries on 34f8ec3b40, 363e9d5f0a and 1798b335c4; no_follow_tags. Closed by building v2 directly on fresh main
P8 = "PENDING"    # round 4 removed tools/__pycache__/ (a host path inside the declared publishable set) and narrowed public_scope; round 6 moved 169 local-only files (r01 raw outputs, tools/sandbox.sh, run/ with the host name and login in its clone reflogs) byte-identical under private/, so everything outside private/ is publishable and scans clean (private_moves); the receipts are not frozen yet
P9 = "PENDING"    # body.md drafted on the PR template; 8 distinct placeholders (11 occurrences), listed in [body].placeholders, stay until the re-pin; tone gate and independent lint not run
P10 = "PENDING"
P11 = "RECORDED"  # demand low; maintainer signal on paw-pii weak (AI-assisted triage note only); a maintainer review of the adjacent #129692 sets the bar a local PII plugin must meet (round 5); owner submission allowed (rule 5)
P12 = "PENDING"   # behind the 39 rows of kvnloo/hermes-agent#404 (re-counted 18:40Z); staging cap

[verification]
verifier = ""
provenance = "independent"
exact_head = ""
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""

[merge_check]
main_sha = "1798b335c43d7e59066ad74a8c2d1d1c9fd537fe"
checked_at = "2026-10-01T19:10Z"   # round 6 (RECHECK/r20261001-07); git write-tree of main plus the entry in the sandbox worktree gave the same tree
clean = true
tree = "064f9e0c6750e05e019129c5e954c4058c170bf4"
base_to_main = "137 commits; 4 invalidate_on files (the validator, plugin-catalog/README.md, plugin-catalog-ci.yml, the new woof.yaml entry) and 1 adjacent test changed, all at 363e9d5f0a and none since; need, green 3 of 3 and the negative control were re-measured on 1798b335c4 (RECHECK/r20261001-07)"
round5_main = "34f8ec3b40 (declared main in round 5, the factory-given main and the scratch mirror's refs/heads/main): clean, tree 47e2acb8c2, checked 18:40Z (RECHECK/r20261001-06); the F14 cherry-pick at 18:28Z gave the same tree (arm dd185c1f84, F14/r20261001-01); 74 commits after the base, none of the 18 invalidate_on specs or the 14 adjacent files changed"
round6_seen = "5d077106b8 (upstream main the round-6 verifier saw, committed 18:48:00Z, 33 after 105e876586): clean, tree 81e4690210; only agent/ and tests/agent/ changed after 105e876586 (RECHECK/r20261001-07)"
round3_main = "44a1ce9724 (declared main in rounds 3 and 4): clean, tree 60459843c2, checked 16:17Z and re-measured 16:46Z (RECHECK/r20261001-04 and -05)"
round1_main = "aea969677c (declared main in rounds 1 and 2): clean, tree 0f33a17f5c, checked 11:10Z and re-measured 11:35Z (RECHECK/r20261001-02 and -03)"
previous = "234badf401: clean, tree 3a91507507, re-measured on 98c305b3ec in round 2 at 2026-10-01T11:35Z (RECHECK/r20261001-03). The builder's run left no raw record. On 98c305b3ec it can only have run between the commit (committer date 2026-10-01T09:14:45Z) and 09:17:40Z, when tools/build_receipts.py was last written with this tree. The earlier '09:10Z' stamp predated the commit and is withdrawn (the pre-rebase commit 2b05ac2bb8 also gives tree 3a91507507 on 234badf401)"
later = "Round 5, newer upstream mains seen by gh while the round ran: 363e9d5f0a (committed 18:25:54Z, 23 commits after 34f8ec3b40): clean, tree a997753eec; 4 invalidate_on files and 1 adjacent test changed (validator subdir and repo shape rules, catalog README, plugin-catalog-ci.yml, new woof.yaml); need, green 3 of 3 and the negative control re-measured there and hold. 105e876586 (committed 18:33:01Z, 28 after 34f8ec3b40): clean, tree 47d51b343d; no invalidate_on or adjacent change since 363e9d5f0a (RECHECK/r20261001-06). Earlier: e8c97320ac (round 2, informational): clean, tree e84c527a14 (RECHECK/r20261001-03)"
recheck = "git -C <bare> merge-tree --write-tree 1798b335c43d7e59066ad74a8c2d1d1c9fd537fe staging/plugin-catalog-entries   # name the SHA: the mirror's main moves (its refs/heads/main is 34f8ec3b40)"

[push]
no_follow_tags = true
workflow_push_matches = 0      # 0 of 11 push workflows match branch staged/plugin-catalog-entries on 1798b335c4 (round 6) and on 34f8ec3b40 and 363e9d5f0a (round 5), tools/wf_scan.py under python3 -B -I; also 0 of 11 on 44a1ce9724 and aea969677c
pushed_at = "before 2026-10-01T17:40:49Z (by the factory, not by a fixer round; staged/plugin-catalog-entries at 98c305b3ec seen on the fork by gh api at 18:43:13Z; the exact push time is not recorded here)"

[body]
path = "body.md"
kind = "catalog-entry"
template = ".github/PULL_REQUEST_TEMPLATE.md blob 5496eb534f (all sections kept except 'For New Skills')"
tone_gate = { peer = false, no_labor = false, no_internal_leak = false, smallest_ask = false, self_service = false, local_voice = false, easy_decline = false }
jargon_lint = "PENDING (independent lint not run; round-5 self-check of body.md: 0 hits for P1-P12, OD-, xf, receipt, staging/staged, lane, envelope, E##/F##/T#, round, owner fix, @-mentions or host paths; upstream items are written #N, the plugin repo as kvnloo/pii)"
privacy_scan = "PENDING (independent scan not run; round-6 self-check with tools/privacy_scan_r6.py under python3 -B: body.md 0 host paths, 0 hostname hits, 0 login hits, 0 private-term hits, not binary; raw/r6_privacy_scan.txt. Round 5: the same with tools/privacy_scan_r4.py, raw/r5_privacy_scan.txt)"
placeholders = [   # body.md, round 5: 8 distinct, 11 occurrences; every one must be filled at the v2 re-pin before posting; test counts written as "N of M pass"
  "<new-sha> (lines 3, 33, 41; also inside <output at <new-sha>> on lines 68 and 71): the v2 40-hex pin",
  "<base-model size at the new pin> (line 35): the base-model download size T2 observes, or drop the number",
  "<when they download at the new pin> (line 35, added in round 5): when the program and base model download at the v2 pin, e.g. 'on first use' or 'during a one-time setup step, never at request time' (owner fix item 3)",
  "<behaviour at the new pin> (line 36): fail-closed or fail-open, as the v2 plugin behaves",
  "<N of M pass> (line 52): the targeted test result, written 'N of M pass'",
  "<platforms line at the new pin> (line 61): the platforms the v2 entry declares",
  "<output at <new-sha>> (lines 68, 71): the validator and 'hermes plugins validate' output",
  "<summary line> (line 74): the run_tests.sh summary line, consistent with line 52",
]
template_attestations = "Added in round 6 (verifier advisory). body.md keeps the template's pre-ticked boxes, and each is an owner attestation made at posting time, not a fact this staging round can prove: line 48 'I've read the Contributing Guide', line 49 Conventional Commits (it must hold for the v2 commit message, not yet written), line 50 the duplicate search (re-run the paw-pii and PII searches before posting), line 51 'only changes related to this feature', line 54 'tested on my platform: Linux (x86_64)', and the N/A boxes on lines 58, 59, 60 and 62. The owner confirms or unticks each one before posting. No owner attestation is claimed anywhere in this manifest"
ai_line_condition = "Added in round 6 (verifier advisory). body.md line 77 says Claude Code 'ran the checks listed above'. That becomes true only when every How to Test step has run at the v2 pin and its output fills the placeholders, including step 2, 'hermes plugins validate --install-deps' (E52), which has never run. Post only after E52 runs; otherwise narrow the line to the checks that did run"
filled_round5 = "Round 5 filled the two clone placeholders (line 41 '<clone of kvnloo/pii at <new-sha>>' and line 70 '<clone>') with a path-free 'git clone https://github.com/kvnloo/pii' and 'pii/integrations/hermes', and replaced the line-34 claim that the plugin's plugin.yaml declares the middleware (false at d891ebdd, round-4 advisory) with what is true at any pin: 'hermes plugins validate' (step 2) checks that plugin.yaml declares the same"

[queue]
board = "kvnloo/hermes-agent#404"
rows_at_check = 39             # re-counted 2026-10-01T18:40Z: open, 39 table rows plus a header (RECHECK/r20261001-06; also 39 at 16:15Z and 16:41Z, -04 and -05)
position = "after existing rows"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# plugin-catalog-entries

**Status: HOLD.** The staging commit is a correct catalog entry for its pin, but the plugin at that pin
does not pass catalog admission and does not redact when installed from the catalog. It needs one
commit in kvnloo/pii, then a re-pin (`staging/plugin-catalog-entries-v2` locally, pushed to the fork as
`staged/plugin-catalog-entries-v2`). The other three members have no standalone repos yet.

v1 (`98c305b3ec`) must never be promoted as is. Its entry description ships "~600 MB", which is
MODELED (see First slice), and owner fix item 7 drops or replaces that number at the re-pin. Its parent
is also 137 commits behind the declared main `1798b335c4` (round 6; 74 behind the factory main
`34f8ec3b40`), so P7 is PENDING (round 5) even though merge-tree is clean there; v2 is built directly
on fresh main. The branch is on the fork as
`staged/plugin-catalog-entries` (pushed by the factory) and is tracked by kvnloo/hermes-agent#412, whose
title carries HOLD; nobody should open a PR from it.

## Invariant

A catalog entry pins a 40-hex commit whose plugin passes `hermes plugins validate` and declares exactly
what it registers (README rules 2, 6, 7). For paw-pii, the plugin at the pin must also import and redact
when installed from its subdir, and must not report a redaction that did not happen.

Call paths exercised:
- catalog: `hermes_cli.plugin_catalog.load_catalog`, `scripts/validate_plugin_catalog.py` and
  `website/scripts/extract-plugins.py`, all on the real `plugin-catalog/`;
- admission: `hermes_cli.plugin_validate._run_capability_probe`, the production probe, called as a
  library function in bwrap (not the CLI);
- runtime: the plugin's callbacks driven through `hermes_cli.middleware.apply_llm_request_middleware`
  and `run_tool_execution_middleware`.

## Route and carrier choice

Route `plugin-catalog`. The policy (AGENTS.md and CONTRIBUTING) says third-party products ship as
standalone plugin repos. README rule 5 allows owner submissions. There is no carrier and no competitor:

- the only paw-pii PR upstream is our own NousResearch/hermes-agent#102924, closed by its author;
- its `hermes_cli/data/plugin_index.json` route no longer exists (removed on main by 46ab5aa365);
- no open PR adds a paw-pii entry.

Adjacent PII work exists. None of it conflicts with a separate `paw-pii` catalog key (RECHECK receipt):

| Item | What it is | Relation |
|---|---|---|
| `plugin-catalog/desensitize.yaml` (on main, merged via NousResearch/hermes-agent#122574) | Chinese-context reversible desensitization: hooks, regex fallback, optional LLM layer | Same catalog, different key and engine |
| NousResearch/hermes-agent#129692 (open, 2026-09-30) | `plugin-catalog/privacy-gateway.yaml`: Presidio plus an encrypted alias vault | Different key. A reviewer may weigh two local PII plugins together. Its author reported the same "redact every string" bug class (see owner fix item 4). A maintainer review (CHANGES_REQUESTED, 2026-10-01T17:14Z) asks it to fail closed, refuse a runtime model download, declare its middleware and add a `requires_hermes` floor (owner fix items 1 and 3) |
| NousResearch/hermes-agent#63917 (open, stale since 2026-07-16) | In-tree regex prompt anonymization (`agent/prompt_privacy.py`, `privacy.*` config) | Core, not catalog |
| NousResearch/hermes-agent#95186 (open) | Host-side opt-in fail-closed contract for required LLM middleware | Complements owner fix item 3 |
| NousResearch/hermes-agent#102049, NousResearch/hermes-agent#14624 (open) | In-tree document anonymizer; in-tree OpenRouter PII masking | Core, not catalog |
| NousResearch/hermes-agent#17472 (open, stale since 2026-07-29; added in round 2) | Optional skill `trustboost-pii-sanitizer`: sends raw text to the hosted TrustBoost API for redaction | A skill backed by a remote service, not catalog or middleware |
| NousResearch/hermes-agent#1542 (merged) | Core `privacy.redact_pii`: hashes platform user and chat IDs in the gateway system prompt | Different scope |

Which hits count as adjacent is set by `[ownership].adjacent_rule`. Round 2 re-ran the `PII` search
(111 open hits) and found #17472 missing from the list. The other hits are secret, log, export or
display redaction, or have no privacy feature. Round 3 re-ran it at 16:15Z and got the same 111 hits.
Every PR in the table still has the state shown (RECHECK/r20261001-04). Round 4 re-ran the search
and the state reads at 16:41Z: the same 111 hits and the same states (RECHECK/r20261001-05). Round 5
did the same at 18:40Z: the same 111 hits; every state unchanged except the new maintainer comment and
review on #129692, which is still open (RECHECK/r20261001-06).

`body.md` says how paw-pii differs from desensitize, privacy-gateway and #63917. It names #95186 as
complementary (round 3), and offers an easy decline.

PAW-PII goes first because it is the only member whose standalone repo and pin exist.

## Member branches

"Behind" counts are `git rev-list --count <ref>..234badf401`, measured on the declared base
(RECHECK receipt). The v1 manifest's counts were measured on `572e4f4fad`, 11 commits earlier. On
the round-6 declared main `1798b335c4` each count is 137 higher: 13,969 / 20,742 / 39,989 / 23,930
(RECHECK/r20261001-07). On `34f8ec3b40` they were 74 higher (RECHECK/r20261001-06), and on
`44a1ce9724` 65 higher (RECHECK/r20261001-04).

| Ref | SHA | Role | Rebase status |
|---|---|---|---|
| `staging/plugin-catalog-entries` (fork: `staged/plugin-catalog-entries`) | `98c305b3ec` | Staging commit: `plugin-catalog/paw-pii.yaml` (+20) pinned to kvnloo/pii `d891ebdd3a3dab27a3451923eb56f955253a2782`, subdir `integrations/hermes` | On main `234badf401`; merge-tree clean on `234badf401` (tree `3a91507507`) and on `aea969677c` (tree `0f33a17f5c`), both re-measured in round 2, on `44a1ce9724` (tree `60459843c2`, round 3), on `34f8ec3b40` (tree `47e2acb8c2`, round 5; also the F14 arm tree), and on the round-6 declared main `1798b335c4` (tree `064f9e0c67`). First built on `572e4f4fad` as `2b05ac2bb8` (committed 09:03:41Z), then rebased at 09:14:45Z (same blob `845dc6cc`) |
| `refs/fork/feat/paw-pii-plugin-index` | `cd7b9d3bcf` | Metadata donor; obsolete `plugin_index.json` route (NousResearch/hermes-agent#102924, closed by author) | n/a: content moved to the catalog YAML. 13,832 commits behind `234badf401` |
| `refs/fork/feat/groq-orpheus-tts` | `548df5dcc0` | In-tree diff (9 files, +404/-8) to port to a standalone `register_tts_provider` repo (`hermes_cli/plugins.py:1126`); NousResearch/hermes-agent#98105 closed by author | n/a: content leaves core. 20,605 behind `234badf401`. **No standalone repo exists** (kvnloo repo list checked) |
| `refs/fork/feat/tinyfish-browser-provider` | `739b30bc02` | In-tree diff (10 files, +214/-1) to port to a `register_browser_provider` repo (`hermes_cli/plugins.py:1106`) | n/a: content leaves core. 39,852 behind `234badf401`. **No standalone repo exists** |
| `refs/fork/feat/spatial-canvas-upstream` | `486a620b5a` | Desktop runtime plugin (`runtime-plugin/spatial/plugin.js`, 562 lines; 3 files +606/-1); needs the desktop-surface check (rule 8); NousResearch/hermes-agent#87495 closed by author | n/a: content leaves core. 23,793 behind `234badf401`. **No remote repo exists** |

## First slice

**Status: committed, not promotable at this pin.** It is one commit, `98c305b3ec`
(`feat(plugin-catalog): add paw-pii`), authored by Kevin Rajan <7121943+kvnloo@users.noreply.github.com>,
with a Claude co-author trailer. It refs NousResearch/hermes-agent#102922. The phase-3 verifier
reproduced it and found no change needed to the commit. Round 1 changed only this manifest, the
receipts and the PR body. Round 2 changed only this manifest, the receipts and `tools/`: the
findings were privacy and provenance text, with no code or test problem. Round 3 again left the
commit alone. It corrected the tool-pin text in `[evidence].public_scope` and the tools list, declared
the current upstream main `44a1ce9724` and re-measured on it, set P5 to PENDING because F14 was not
run, and edited `body.md` (#95186 named, AI-assistance line widened). It added
RECHECK/r20261001-04, `raw/r3_*` and `tools/privacy_scan_r3.py`. Round 4 also left the commit
alone; its findings were privacy and manifest text. It deleted `tools/__pycache__/`, which the round-3
scan had written, which held a host path, and which sat inside the declared publishable set. It narrowed
`[evidence].public_scope` to `tools/*.py` and corrected the round-3 scan claim. It added
`tools/privacy_scan_r4.py` (a completeness walk; never writes bytecode), RECHECK/r20261001-05 and
`raw/r4_*`, and listed the `body.md` placeholders. The F14 guard worker then ran F14 on the commit
cherry-picked onto `34f8ec3b40` (EQUAL). Round 5 (polish) also left the commit alone and made no
message-only v2 (see `commit_message`). It declared `34f8ec3b40` and re-measured need, green 3 of 3
and the negative control there and on the newer upstream main `363e9d5f0a` in the factory sandbox,
set P7 to PENDING (not on fresh main), fixed the false `plugin.yaml` claim and the two clone
placeholders in `body.md`, recorded the maintainer review on #129692 and the fork branch and issue,
and added RECHECK/r20261001-06 and `raw/r5_*`. Round 6 (fix after the fresh verifier) also left the
commit alone. Its blocking finding was privacy: local-only material sat in publishable locations, and
the clone under `run/` carried the host name in its git reflogs, which no scan had walked. It moved the
41 r01 raw outputs, `tools/sandbox.sh` and `run/` byte-identical under `private/`, added
`tools/privacy_scan_r6.py` (it walks every file outside `private/`) and rescanned. It declared the newest
upstream main `1798b335c4` and re-measured on it, recorded the template attestations and the AI-line
condition for `body.md`, and restated what P4 rests on. It added RECHECK/r20261001-07 and `raw/r6_*`.
The promotion form stays `plugin-catalog-entry` and the status stays HOLD.

- **Pin.** kvnloo/pii `main` is `d891ebdd3a` (re-read by gh in round 5), so this SHA is the intended head. It is 1 commit ahead
  of programasweights/pii `454b8df4e3`, and that commit is kvnloo's.
- **Capabilities.** Exactly what `register()` wires at the pin: tools `detect_pii` and `redact_pii`;
  middleware `llm_request` and `tool_execution`; no hooks, no required env. Both the ast census and
  the production probe confirm this.
- **Description.** Credits programasweights for the model and library. It discloses the first-use
  downloads, local inference, fail-open behaviour and per-string scan cost, in the same style as
  `desensitize.yaml`. The RECHECK receipt records where each disclosure comes from:
  - program bundle from programasweights.com (`config.py:14`): OBSERVED in the programasweights
    0.4.10 wheel (sha256 `7e82cb9364f0…`, equal to the PyPI digest);
  - base model from huggingface.co/programasweights (`cache.py:36-37`): OBSERVED in the same wheel;
  - local llama.cpp inference: `paw.function` defaults to `remote=False` (`__init__.py:421`), and the
    plugin passes no `remote` argument (`src/paw_pii/service.py:76-80`). OBSERVED in code;
  - **"~600 MB" is MODELED, not OBSERVED.** The pinned repo's `artifacts/frozen-programs.json` and the
    wheel both name `qwen3-0.6b-q6_k` (622,733,120 bytes). But the server chooses the base model for
    program `73a0e38b` at first use, and the other runtime the wheel knows is `gpt2-q8_0`
    (139,804,832 bytes). Nothing was downloaded here. The v2 re-pin must confirm the size with T2
    `prepare_program` or drop the number (owner fix item 7).
- **Docs.** `readme: false`, because the subdir README returns 404. `docs_url` points at the root
  README section at the pinned SHA (HTTP 200, anchor present).
- **Missing upstream.** No Groq-Orpheus, TinyFish or Spatial YAML was written: their standalone
  repos do not exist.

## Evidence

| Experiment | Receipt | Verdict | Label | n | Result |
|---|---|---|---|---|---|
| Slice proof (need, green, negative, adjacent, merge, workflows, link, dedupe) | `receipts/SLICE-proof-r20261001-01.json` | KEEP | OBSERVED | 3 reps (green) | Need: absent on main, 348/348. Green: 350 files valid, loader 349/349, page entry emitted. Negative: `sha: main` gives validator rc=1 and `assert 348 == 349`. Adjacent: 68 passed / 13 env errors on both arms. Workflow push matches: 0 |
| F12 offline census (T0, ast plus hermes static checks; plugin never imported) | `receipts/F12-r20261001-01.json` | KEEP / gate FAIL | OBSERVED counts, MODELED verdict | 1 plus 3 calibration variants | Manifest-vs-code mismatch 2 (middleware undeclared in `plugin.yaml`); catalog-vs-code 0; internal imports 0; self-updater 0; desktop bundles 0; `sys.path` mutation 1; imports unresolvable in the catalog install layout 1 (`paw_pii`); declared install deps 0; repo-root floors without upper bound 8/8; security scan `safe`, 0 findings; built-in collisions 0 of 89. Calibration: fixed-manifest PASS, sabotage flags every class, catalog drift flagged |
| T1 capability probe (production probe as a library call, bwrap, no egress) | `receipts/T1-capability-probe-r20261001-01.json` | KEEP | OBSERVED | 3 + 3 | As pinned: FAIL 3/3, `declared middleware` (undeclared `llm_request`, `tool_execution`). With `provides_middleware` added: PASS 3/3. Blocked exec/connect: 0 |
| T1 fail-open (real middleware chain, synthetic canary, runtime absent) | `receipts/T1-failopen-r20261001-01.json` | KEEP | OBSERVED | 3 | Full-clone: request payload keeps 3/3 canary markers, `changed=True`, trace "local PII redaction before provider egress", payload equal to original, `redact_pii` returns the original text, 0 log lines. Catalog-install: `paw_pii` not importable, payload keeps 3/3 markers, tools raise `ModuleNotFoundError`, 3 ERROR log lines, nothing blocked. Plugin exec/egress attempts: 0 |
| Round-1 recheck (git, gh read-only, PyPI wheel read; nothing executed from the plugin) | `receipts/RECHECK-r20261001-02.json` | KEEP | OBSERVED, except base-model size MODELED | 1 | On `aea969677c`: invalidate_on and adjacent files unchanged, merge-tree clean, need holds, 0 push matches for `staged/plugin-catalog-entries`, fork has no `staged/*` refs. Behind counts on `234badf401`: 13,832 / 20,605 / 39,852 / 23,793. #102924 note is AI-assisted from a human Nous-affiliated account. 5 adjacent open PRs and 2 adjacent merged items, none conflicting (round 2 adds a sixth). Wheel facts as above. `_redact_value` scans every string (`service.py:135`). 5 `PAW_PII_*` env toggles. #404 has 39 rows |
| Round-2 recheck (git, gh read-only, privacy scan; nothing executed from the plugin) | `receipts/RECHECK-r20261001-03.json` | KEEP | OBSERVED | 1 | `98c305b3ec` committed 09:14:45Z (author date 09:03:41Z). Merge-tree re-measured: `3a91507507` on `234badf401`, `0f33a17f5c` on `aea969677c`. Informational: clean on the mirror's newer main `e8c97320ac` (tree `e84c527a14`), with invalidate_on unchanged. `PII` search: 111 open hits; #17472 added as the sixth adjacent PR. Privacy scan of the publishable set: 0 host paths, 0 hostname hits, 0 hits for a local list of private terms. Receipt rebuild from raw/ matches the published bytes |
| Round-3 recheck on the then-declared main `44a1ce9724` (git, gh read-only, catalog loader, validator and shipped test in an isolated HOME, privacy scan; nothing executed from the plugin) | `receipts/RECHECK-r20261001-04.json` | KEEP | OBSERVED | 3 reps (green) | Upstream main `44a1ce9724` by ls-remote, 65 commits after the base. invalidate_on, the adjacent test files, runner, lock, PR template and policy docs unchanged since the base; 9 pinned hermes blobs identical. Merge-tree clean (tree `60459843c2`). Need: loader 348/348, paw-pii absent, `plugin_index.json` absent. Main plus the entry: validator OK 350 files, loader 349/349, shipped test 3 of 3 runs pass. `sha: main`: validator rc=1 and `assert 348 == 349`. Push workflows: 0 of 11 match. Behind counts 13,897 / 20,670 / 39,917 / 23,858. `PII` search: the same 111 open hits; every cited PR and issue has the state stated. #404 open, 39 rows. Fork: `staged/plugin-catalog-entries` still free. Privacy scan: 0 of 31 scanned files flagged, but the declared set held 32 files: the scan missed `tools/__pycache__/privacy_scan.cpython-314.pyc`, which it had written itself and which held a host path (corrected by RECHECK/r20261001-05) |
| Round-4 recheck: privacy completeness and the declared main (git, gh read-only, privacy scan with a completeness walk; nothing executed from the plugin) | `receipts/RECHECK-r20261001-05.json` | KEEP | OBSERVED | 1 | `.pyc` recorded without printing its path (5,384 B, written 16:21:49Z, `co_filename` absolute, pinned by no receipt), then `tools/__pycache__/` deleted. `tools/privacy_scan_r4.py` before the deletion: FAIL (1 unclassified, 1 binary, 2 bytecode entries, the `.pyc` flagged with 1 absolute path and 4 private-term hits). After: 38 publishable files, 0 unclassified, 0 binary, 0 bytecode, 0 of 38 flagged; no bytecode written by the run. Upstream main still `44a1ce9724` (ls-remote 16:46:36Z); branch unchanged; merge-tree tree `60459843c2` again; paw-pii absent (348 entry files). `PII` search: the same 111 open hits; every cited state unchanged. #404 open, 39 rows. Fork name still free |
| F14 standing regression set, Wave 0 (staging commit cherry-picked onto upstream main `34f8ec3b40`; 19 probes, each in its own bwrap cell with loopback only and its own HOME and HERMES_HOME; no plugin code run) | `receipts/F14-r20261001-01.json` | KEEP / EQUAL | OBSERVED | 2 runs × 40 verdict ids | Cherry-pick clean, patch byte-identical; arm `dd185c1f84`, tree `47e2acb8c2` (= merge-tree of `98c305b3ec` on `34f8ec3b40`). Both runs: 36 PASS / 4 FAIL, identical to the main baseline in verdict, marker and fingerprint on 40 of 40 ids; compare EQUAL (baseline-r1, baseline-r2, r1-r2); no flaky exclusions; 0 blocked execs; worktree clean. The 4 FAILs are the baseline's own (cache_estimator, notice_delivery, context_cap, readtool lying_extension). No probe reads `plugin-catalog/`, so EQUAL is expected for a data-only entry |
| Round-5 recheck: freshness on the then-declared main `34f8ec3b40` and the newer upstream mains, advisory re-check (git and gh read-only; catalog loader, validator and shipped test in the factory bwrap sandbox, loopback only, isolated HOME; nothing executed from the plugin) | `receipts/RECHECK-r20261001-06.json` | KEEP | OBSERVED | 3 reps (green) per main | `34f8ec3b40`: 74 commits after the base; invalidate_on and the 14 adjacent files unchanged; merge-tree clean (tree `47e2acb8c2` = F14 arm tree = index tree of main plus the entry). Need: loader 348/348, paw-pii absent. Green: validator OK 350 files, loader 349/349, shipped test 3 of 3 runs pass. `sha: main`: validator rc=1, `assert 348 == 349`. `363e9d5f0a` (upstream main at 18:32Z): validator, catalog README, `plugin-catalog-ci.yml` and a new `woof.yaml` changed; merge-tree clean (`a997753eec`); need 349/349 absent; green: validator OK 351 files under the new subdir and repo rules, loader 350/350, 3 of 3 pass; `sha: main`: rc=1, `assert 349 == 350`. `105e876586` (upstream main at 18:40Z): merge-tree clean (`47d51b343d`), no invalidate_on change since `363e9d5f0a`. Push workflows: 0 of 11 on both measured mains. 0 blocked execs. kvnloo/pii main still `d891ebdd`; its `plugin.yaml` has no `provides_middleware`; author and committer display names are equal. `PII` search: the same 111; #129692 got a maintainer CHANGES_REQUESTED review. #404: 39 rows. Fork: `staged/plugin-catalog-entries` at `98c305b3ec`; tracking issue kvnloo/hermes-agent#412 |
| Round-6 fix: privacy move, completeness scan, freshness on the newest upstream main (byte-identical move under `private/`; scan with a negative control; git and gh read-only; catalog loader, validator and shipped test in the factory bwrap sandbox, loopback only, isolated HOME; nothing executed from the plugin) | `receipts/RECHECK-r20261001-07.json` | KEEP | OBSERVED | 3 reps (green) | Move: 169 files (41 r01 raw outputs, `tools/sandbox.sh`, 127 `run/` files) to `private/<same path>`, 169 of 169 re-hashed equal; before the move 27 raw files held absolute paths, `sandbox.sh` too, and 3 clone reflog files the host name; 75 of 75 receipt-cited hashes still match. Scan negative control: 5 planted leaks, FAIL, each flagged. `1798b335c4` (upstream main at 19:08Z): 137 commits after the base; invalidate_on and adjacent unchanged since `363e9d5f0a`; merge-tree clean (`064f9e0c67` = index tree of main plus the entry). Need: loader 349/349, absent. Green: validator OK 351, loader 350/350, shipped test 3 of 3 pass. `sha: main`: rc=1, `assert 349 == 350`. Push workflows 0 of 11. 0 blocked execs. `5d077106b8`: clean (`81e4690210`), only `agent/` and `tests/agent/` changed after `105e876586`. F14 `patch_sha256` reproduces with `core.abbrev=10`. gh: `paw-pii.yaml` 404 upstream, 0 open `paw-pii` PRs, 111 open `PII` hits, kvnloo/pii main still `d891ebdd`, fork ref unchanged, #129692 open with CHANGES_REQUESTED |

Raw outputs are under `raw/` (each sha256-pinned in its receipt). The `r20261001-01` raw files carry
host paths and stay local-only; since round 6 they are at `private/raw/` under their old names
(`[evidence].private_moves`). In the four `r20261001-01` receipts, round 1 replaced the host paths
with placeholders (`<staging>`, `<worktree>`, `<venv>`, `<testhome>`), and round 2 replaced the
`env.host` hostname with `<host>`. Their measurements did not change, but their sha256 values did
(updated in `[evidence]`). Rebuilding them from `raw/` with the round-2 `build_receipts.py` and
`scrub_receipts.py` reproduces the published bytes 4/4 (RECHECK/r20261001-03). What gets published
and what stays local is set by `[evidence].public_scope`.

The harnesses are under `tools/`. Each one is pinned by sha256 in the receipt named after it, so
each must stay byte-identical; editing one breaks that receipt's hash:
- `f12_census.py` sha256 `4f55ac29…`, pinned by F12/r20261001-01.
- `t1_probe.py` sha256 `ff594145…`, pinned by both T1 receipts.
- `sandbox.sh` sha256 `1f8f65ef…`, pinned by F12/r20261001-01 and both T1 receipts, and listed in
  RECHECK/r20261001-03. **Local-only (public: false):** its as-run bytes mask and re-bind host paths.
  Since round 6 it is at `private/tools/sandbox.sh` (same bytes). The sandbox profile is stated in each
  receipt's `env.sandbox`.
- `catalog_probe.py` sha256 `df35fe7c…`, pinned by SLICE/r20261001-01. Round 3 also ran it on the
  declared main.
- `build_receipts.py` sha256 `e6f34f85…`, pinned by RECHECK/r20261001-03 (round-2 bytes; no r01
  receipt pins it). Round 2 removed its host locations; they come from `XF_WORKTREE`, `XF_VENV`,
  `XF_TESTHOME` or the script's directory. Line 32 still carries the pinned commit's display name;
  see `[evidence].receipt_privacy` for why it stays.
- `wf_scan.py` sha256 `2c686f5d…`, pinned by RECHECK/r20261001-02 (push-trigger scan, round 1; rerun
  on the declared main in round 3).
- `scrub_receipts.py` sha256 `f331a72b…`, pinned by RECHECK/r20261001-03 (round-2 bytes; no r01
  receipt pins it). It is the host-path scrub from round 1; round 2 added the `<host>` placeholder
  and marked `sandbox.sh` local-only. It is idempotent and holds no host locations.
- `privacy_scan.py` sha256 `c20c602b…`, pinned by RECHECK/r20261001-03 (round 2). It scans the
  publishable set for absolute paths, the hostname and a local list of private terms, and never
  prints the hostname or the terms. Its `publishable()` lists `tools/` with `iterdir()` plus
  `is_file()`, so it never sees a subdirectory of `tools/`. That is the round-3 gap.
- `privacy_scan_r3.py` sha256 `6a578ec4…`, pinned by RECHECK/r20261001-04 (round 3). It loads
  `privacy_scan.py` unchanged and adds `raw/r3_*` to the scanned set. It does not turn off bytecode
  writing, so its round-3 run wrote `tools/__pycache__/privacy_scan.cpython-314.pyc`, which round 4
  deleted. Never rerun it without `python3 -B` or `PYTHONDONTWRITEBYTECODE=1`.
- `privacy_scan_r4.py` sha256 `41abafaf…`, pinned by RECHECK/r20261001-05 (round 4). It sets
  `sys.dont_write_bytecode` before loading `privacy_scan.py` unchanged. It walks every file outside
  `run/` and classifies each one as publishable or local-only by the `public_scope` rules, or else as
  unclassified. It runs `privacy_scan.py`'s checks over the publishable and unclassified files. It
  fails on any flag, any unclassified file, any binary file (NUL byte or invalid UTF-8) and any
  `__pycache__` or `.pyc`/`.pyo` outside `run/`. With `--out` it also checks the report file it wrote.
  **Superseded in round 6:** it never walked `run/`, and it would now report every `private/` file as
  unclassified.
- `privacy_scan_r6.py` sha256 `03e99afc…`, pinned by RECHECK/r20261001-07 (round 6). It sets
  `sys.dont_write_bytecode` before loading `privacy_scan.py` unchanged. It walks every file outside
  `private/` (nothing else is skipped). Each must match a publishable rule (`STAGING.md`, `body.md`,
  `*.patch`, `receipts/*.json`, `raw/r<round>_*`, `tools/*.py`), or it is unclassified. It runs
  `privacy_scan.py`'s checks over them and adds a whole-word local-login check, a binary check and a
  bytecode check. It fails on any hit, any unclassified file, any binary file and any bytecode outside
  `private/`. For the record only, it also counts `private/` files that hold an absolute path, the host
  name or the login. It never prints the host name, the login or the terms. Its negative control is
  `raw/r6_privacy_scan_negative_control.txt`.

## Experiments run

The commands below are written as they ran. Since round 6, `tools/sandbox.sh`, `run/...` and the r01
`raw/` outputs they name are at `private/tools/sandbox.sh`, `private/run/...` and `private/raw/...`
(`[evidence].private_moves`).

- **SLICE/r20261001-01** (T0): `receipts/SLICE-proof-r20261001-01.json`. Numbers are in the table above.
- **F12/r20261001-01** (T0, $0): `receipts/F12-r20261001-01.json`.
  - Command: `RUN=<staging>/run VENV=1 CHDIR=<worktree> tools/sandbox.sh <venv>/bin/python -I tools/f12_census.py --clone run/src/pii --repo https://github.com/kvnloo/pii --sha d891ebdd3a3dab27a3451923eb56f955253a2782 --subdir integrations/hermes --catalog-entry <worktree>/plugin-catalog/paw-pii.yaml --hermes-tree <worktree> --variant as-pinned`
  - Variants run the same command with `--plugin-dir-override run/variants/<fixed-manifest|sabotage>`.
- **T1-capability/r20261001-01** ($0): `receipts/T1-capability-probe-r20261001-01.json`.
  - Command: `tools/sandbox.sh <venv>/bin/python -I tools/t1_probe.py capability --hermes-tree <worktree> --plugin-dir <dir> --manifest-json "$MP"`, 3 reps per arm.
  - This is the closest runnable form of E52. It is **not** the CLI and does not satisfy the E52 gate.
- **T1-failopen/r20261001-01** ($0): `receipts/T1-failopen-r20261001-01.json`.
  - Command: `tools/sandbox.sh <venv>/bin/python -I tools/t1_probe.py failopen --hermes-tree <worktree> --plugin-dir run/src/pii/integrations/hermes`, 3 reps.
- **RECHECK/r20261001-02** (T0, $0, round 1): `receipts/RECHECK-r20261001-02.json`.
  - Git: `rev-list --count <ref>..234badf401` per member, `diff --stat 234badf401 main -- <invalidate_on + adjacent files>`, `merge-tree --write-tree main staging/plugin-catalog-entries` (mirror main was `aea969677c` then), `ls-remote` of upstream main and of the fork's `staging`/`staged/*` refs (`raw/r1_git_recheck.txt`).
  - Push triggers: `<venv>/bin/python -I tools/wf_scan.py <bare> main staged/plugin-catalog-entries` (`raw/r1_wf_push_scan_staged_aea969677c.json`).
  - gh, read-only: #102924 comments and the commenter's profile and commits, #102922, the adjacent PRs, the searches in `[ownership].queries`, and kvnloo/hermes-agent#404 (`raw/r1_gh_reads.json`).
  - Wheel: PyPI JSON for programasweights 0.4.10, download, `sha256sum`, then grep `cache.py`, `config.py` and `__init__.py`. Also the plugin source at `d891ebdd` (`raw/r1_disclosure_read.txt`).
- **RECHECK/r20261001-03** (T0, $0, round 2): `receipts/RECHECK-r20261001-03.json`.
  - Git: `log` dates of `98c305b3ec`, `2b05ac2bb8` and `234badf401`; `merge-tree --write-tree` of `98c305b3ec` on `234badf401` and on `aea969677c`, and of `2b05ac2bb8` on `234badf401`; the mirror's newer main `e8c97320ac` (ancestry, count, merge-tree, invalidate_on diff, need); and mtimes of the round-0 outputs (`raw/r2_git_recheck.txt`).
  - gh, read-only: `gh search prs 'PII' --state open --limit 200` (111 hits), `gh pr view` and `gh pr diff` 17472 (`raw/r2_gh_reads.json`).
  - Receipts: `tools/scrub_receipts.py` over `receipts/`. Then, in a scratch copy, `tools/build_receipts.py` followed by `tools/scrub_receipts.py`, compared byte for byte with the published receipts, plus an idempotence rerun (`raw/r2_rebuild_check.txt`).
  - Privacy: `XF_PRIVATE_TERMS=<local list> python3 tools/privacy_scan.py` (`raw/r2_privacy_scan.txt`).
- **RECHECK/r20261001-04** (T0/T1, $0, round 3): `receipts/RECHECK-r20261001-04.json`.
  - Git: `ls-remote` of upstream main (twice), ancestry and `rev-list --count` from the base and from
    `aea969677c`, `merge-tree --write-tree 44a1ce9724 98c305b3ec`, `diff --stat 234badf401 44a1ce9724`
    over the 18 invalidate_on specs and over the adjacent tests, runner, lock, PR template and policy
    docs, the 10 pinned hermes blobs on head and main, `paw-pii.yaml` and `plugin_index.json` on
    main, member behind counts, and `ls-remote` of the fork's `staging`/`staged/*` refs
    (`raw/r3_git_recheck.txt`).
  - Push triggers: `<venv>/bin/python -I tools/wf_scan.py <bare> 44a1ce9724… staged/plugin-catalog-entries`
    (`raw/r3_wf_push_scan_staged_44a1ce9724.json`).
  - Catalog, in a worktree at `44a1ce9724` with `HOME=<testhome>`: `tools/catalog_probe.py` and
    `scripts/validate_plugin_catalog.py` on main; then `git checkout 98c305b3ec -- plugin-catalog/paw-pii.yaml`
    (`git write-tree` gives `60459843c2`, the merge-tree result), the probe, the validator and
    `scripts/run_tests.sh -j 2 tests/hermes_cli/test_plugin_catalog.py -q -k test_shipped_catalog_entries_are_all_valid_and_pinned`
    3 times; then `sha: main` with the validator and the test; then the test once on main
    (`raw/r3_catalog_green.txt`).
  - gh, read-only: state of every PR and issue cited here, #102922, #129692 and #95186 comments,
    `gh search prs 'PII' --state open --limit 200` compared with round 2, the other searches in
    `[ownership].queries`, and kvnloo/hermes-agent#404 (`raw/r3_gh_reads.json`).
  - Privacy: `XF_PRIVATE_TERMS=<local list> python3 tools/privacy_scan_r3.py` (`raw/r3_privacy_scan.txt`).
    It ran without `-B`, so loading `privacy_scan.py` wrote `tools/__pycache__/privacy_scan.cpython-314.pyc`,
    and the scan did not look inside `tools/__pycache__/`. Its 31 files were 31 of the 32 in the declared
    set (RECHECK/r20261001-05).
- **RECHECK/r20261001-05** (T0, $0, round 4): `receipts/RECHECK-r20261001-05.json`.
  - Privacy, before: `XF_PRIVATE_TERMS=<local list> PYTHONDONTWRITEBYTECODE=1 python3 -B tools/privacy_scan_r4.py`
    with the `.pyc` still present (`raw/r4_privacy_scan_before.txt`). The local list has 16 terms. It is
    not the round-3 list, which was not kept. Like that list, it stays local.
  - The `.pyc`: size, sha256, mtime, header and `co_filename` shape read with `python3 -B` (the path
    itself is not printed), then `rm -r tools/__pycache__` (`raw/r4_pycache_removal.txt`).
  - Git: `ls-remote` of upstream main, the branch head, parent, tree and diff, ancestry and
    `rev-list --count` from the base, `merge-tree --write-tree 44a1ce9724 98c305b3ec`, `paw-pii.yaml` on
    main and the entry count, and `ls-remote` of the fork's `staging`/`staged/*` refs
    (`raw/r4_git_recheck.txt`).
  - gh, read-only: the round-3 reads again, comparing the `PII` search with round 2's 111 numbers
    (`raw/r4_gh_reads.json`).
  - Privacy, after, once every other round-4 edit was in place:
    `XF_PRIVATE_TERMS=<local list> PYTHONDONTWRITEBYTECODE=1 python3 -B tools/privacy_scan_r4.py --out raw/r4_privacy_scan.txt`.
    Then `find` checked that no `__pycache__` or `.pyc` exists outside `run/`.
- **F14/r20261001-01** (T1, $0, Wave 0 guard): `receipts/F14-r20261001-01.json`.
  - Git: `worktree add --detach <xf-root>/wt-w0/plugin-catalog-entries 34f8ec3b40`, then
    `cherry-pick 98c305b3ec` with the author kept and Kevin Rajan as committer (clean, giving `dd185c1f84`),
    then `update-ref refs/xf/w0/plugin-catalog-entries dd185c1f84` (scratch mirror only, not pushed).
  - F14: `PYTHONDONTWRITEBYTECODE=1 python3 -B f14_run.py run <worktree> maps/plugin-catalog-entries-r<N>.json --label plugin-catalog-entries-r<N>`
    for N = 1, 2, each followed by `f14_run.py compare baseline-34f8ec3b40.json maps/plugin-catalog-entries-r<N>.json`,
    then `compare` of r1 with r2. Runner `2323a591…`, sandbox `c9586195…`, readtool helper `0df21aee…`, set
    `aba79fe8f09d…`, all equal to the baseline map's.
  - The worktree was removed with `git worktree remove` and pruned. The maps and run dirs stay local
    (`<xf-root>/factory/w0/`); the receipt embeds all three verdict maps.
- **RECHECK/r20261001-06** (T0/T1, $0, round 5): `receipts/RECHECK-r20261001-06.json`.
  - Git (`raw/r5_git_recheck.txt`): the branch head, parent, tree and commit fields; for `34f8ec3b40` and
    `363e9d5f0a`, ancestry and `rev-list --count` from the base and from `44a1ce9724`,
    `merge-tree --write-tree <main> 98c305b3ec`, `diff --stat 234badf401 <main>` over the 18 invalidate_on
    specs and over the 14 adjacent files, `paw-pii.yaml`, the entry count, `plugin_index.json`, the PR
    template, catalog README, CONTRIBUTING and AGENTS blobs, and the contributor email map; what moved
    between the two mains on those paths; member behind counts; then the same freshness checks for
    `105e876586`, appended once gh reported it.
  - Catalog (`raw/r5_catalog_recheck.txt`), in a detached worktree `<worktree>` under the factory worktree
    root, one run dir per main, every Hermes command through the factory sandbox (`xf-sandbox.sh <run> <worktree> -- ...`):
    on each main, `python -B -I tools/catalog_probe.py paw-pii`, `scripts/validate_plugin_catalog.py` and the
    shipped-entries test once; then `git checkout 98c305b3ec -- plugin-catalog/paw-pii.yaml` (`git write-tree`
    equals the merge-tree result), the probe, the validator and
    `scripts/run_tests.sh -j 2 tests/hermes_cli/test_plugin_catalog.py -q -k test_shipped_catalog_entries_are_all_valid_and_pinned`
    3 times; then `sha: main` with the validator and the test; then `reset --hard`. The worktree was left
    clean, removed with `git worktree remove` (no `--force`) and pruned.
  - Push triggers: `PYTHONDONTWRITEBYTECODE=1 python3 -B -I tools/wf_scan.py <bare> <main> staged/plugin-catalog-entries`
    for both mains (`raw/r5_wf_push_scan_staged_34f8ec3b40.json`, `raw/r5_wf_push_scan_staged_363e9d5f0a.json`).
  - gh, read-only (`raw/r5_gh_reads.json`): upstream `commits/main` and the compare from `34f8ec3b40`; the
    state of every cited PR and issue; #129692 comments and reviews; #102922 comment authors; kvnloo/pii
    `main`, the pinned commit's logins and whether its author and committer names are equal (the name is
    not copied), and `integrations/hermes/plugin.yaml` at the pin; the `PII` search compared with round 2's
    111 numbers and the four other searches; kvnloo/hermes-agent#404. Also read, not saved as raw: the fork's
    `staged/*` refs (`gh api .../git/matching-refs/heads/staged`, 18:43:13Z) and kvnloo/hermes-agent#412.
  - Pinned clone (`run/src/pii` at `d891ebdd`, local-only): 0 symlinks, 0 JS/TS files in `integrations/hermes`.
  - Privacy, last, once every other round-5 edit was in place:
    `XF_PRIVATE_TERMS=<local list> PYTHONDONTWRITEBYTECODE=1 python3 -B tools/privacy_scan_r4.py > raw/r5_privacy_scan.txt`
    (its `--out` accepts only `raw/r4_*` names), then the same command again to stdout, which also covers
    `raw/r5_privacy_scan.txt`; then `find` checked that no `__pycache__` or `.pyc` exists outside `run/`.
    `raw/r5_privacy_scan.txt` is written after the receipt, so no receipt pins it.
- **RECHECK/r20261001-07** (T0/T1, $0, round 6): `receipts/RECHECK-r20261001-07.json`.
  - Move: the 41 `raw/` files whose names are not `raw/r<round>_*`, `tools/sandbox.sh` and every file
    under `run/` were hashed (sha256, size), counted for absolute paths, the host name, the local login
    (whole word) and binary bytes with `python3 -B` (counts only), then `mv -n` to `private/<same path>`
    (`run` as one directory rename), re-hashed at the new path (169 of 169 equal, none left behind) and
    listed in `private/MOVED-r6.tsv`. Then every artifact `path`/`sha256` pair in the 10 earlier
    receipts was re-checked at its current location (75 of 75 match; the 3 F14 maps under `<xf-root>`).
  - Scan negative control (`raw/r6_privacy_scan_negative_control.txt`): this directory copied to a
    scratch dir, five leaks planted (see the file header), `XF_PRIVATE_TERMS=<local list>
    PYTHONDONTWRITEBYTECODE=1 python3 -B tools/privacy_scan_r6.py` run there, then the copy deleted.
  - Git (`raw/r6_git_recheck.txt`): the branch head, parent and tree; for `5d077106b8` and `1798b335c4`,
    ancestry, `rev-list --count` from the base, `34f8ec3b40` and the previous main,
    `merge-tree --write-tree <main> 98c305b3ec`, `diff --stat` over the 18 invalidate_on specs and the
    14 adjacent files (from `105e876586`, `363e9d5f0a`, `5d077106b8` and the base), the files changed
    since the previous main, `paw-pii.yaml`, the entry count, `plugin_index.json`, the template, README,
    CONTRIBUTING, AGENTS and validator blobs, member behind counts; then the F14 `patch_sha256` with the
    mirror default and with `-c core.abbrev=10`.
  - Catalog (`raw/r6_catalog_recheck.txt`): a detached worktree `<xf-root>/wt-w0/plugin-catalog-entries-r6`
    at `1798b335c4`, run dir `<xf-root>/factory/w0/runs/plugin-catalog-entries-r6-1798b335c4`, every Hermes
    command through `xf-sandbox.sh <run> <worktree> -- ...`, the same steps as round 5 (probe, validator
    and shipped test on main; `git checkout 98c305b3ec -- plugin-catalog/paw-pii.yaml`, `git write-tree`
    against merge-tree, probe, validator, the shipped test 3 times; `sha: main` with the validator and the
    test; `reset --hard` and `clean -fdx`). The worktree was clean, removed with `git worktree remove`
    (no `--force`) and pruned.
  - Push triggers: `PYTHONDONTWRITEBYTECODE=1 python3 -B -I tools/wf_scan.py <bare> 1798b335c4… staged/plugin-catalog-entries`
    (`raw/r6_wf_push_scan_staged_1798b335c4.json`).
  - gh, read-only (`raw/r6_gh_reads.json`): upstream `commits/main`, `paw-pii.yaml` on main, the compare
    from `105e876586`, the `paw-pii` and `PII` open-PR searches, kvnloo/pii `main`, the fork's
    `staged/plugin-catalog-entries` ref, #129692, #102922, kvnloo/hermes-agent#412 and #404.
  - Privacy, last, once every other round-6 edit was in place:
    `XF_PRIVATE_TERMS=<local list> PYTHONDONTWRITEBYTECODE=1 python3 -B tools/privacy_scan_r6.py --out raw/r6_privacy_scan.txt`,
    then `find` checked that no `__pycache__` or `.pyc` exists outside `private/`.
    `raw/r6_privacy_scan.txt` is written after the receipt, so no receipt pins it.

## Experiments queued (not run)

**E52** (needs OD-2; operator approval to run the hermes CLI). Run it from a disposable 3.14 venv,
never the live install. Expected from T1: FAIL at `d891ebdd`. Rerun it on the re-pinned SHA.

```bash
# placeholders: W=<worktree re-created at 98c305b3ec>, R=<staging>, VENVS=<factory venv dir>,
#               LIVE=<live hermes home>, HOMES=<user home root>
# 1. networked, one-time: build the disposable venv from the staging tree
V=$VENVS/$(sha256sum $W/uv.lock | cut -c1-12)
cd $W && python3.14 -m pm.build_env --source . --out $V --group dev --group test
# 2. sandboxed CLI run (no network, masked home; the plugin declares no deps so --install-deps is a no-op today)
# (round 6) run dirs and as-run outputs hold host paths, so they live under $R/private/; publish only a scrubbed raw/r<round>_* copy
RUN=$R/private/run-e52; mkdir -p $RUN/home/.hermes $RUN/tmp; cp -a $R/private/run/src/pii $RUN/pii
bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs "$HOMES" --tmpfs "$LIVE" \
  --bind $RUN $RUN --bind $RUN/tmp /tmp --unshare-net --unshare-pid --die-with-parent --clearenv \
  --setenv HOME $RUN/home --setenv HERMES_HOME $RUN/home/.hermes --setenv PATH $V/bin:/usr/bin:/bin \
  --chdir $W $V/bin/hermes plugins validate --install-deps --json $RUN/pii/integrations/hermes > $R/private/raw/e52_as_pinned.json
```

**T2-paw-runtime** (local CPU/GPU, serial under the GPU flock, one-time base-model download whose
size is what T2 records). This measures redaction of the canary and per-turn latency with the PAW
runtime present. It is the boundary T1 could not cross.

```bash
# networked prep (owner-approved): runtime + assets into a disposable venv and an isolated HOME
V2=$VENVS/paw-t2; RUN=$R/private/run-t2
python3.14 -m venv $V2 && $V2/bin/pip install 'programasweights==0.4.10' && $V2/bin/pip install -e $W   # hermes deps via the tree
HOME=$RUN/home $V2/bin/python -c "import programasweights as paw; paw.prepare_program('73a0e38b8bbe3427cd1d')"
ls -l $RUN/home/.cache/programasweights/base_models/   # record the base-model file and size (settles the ~600 MB claim)
# offline cell (GPU flock; serial)
flock <gpu.lock> env PAW_OFFLINE=1 RUN=$RUN CHDIR=$W $R/private/tools/sandbox.sh \
  /usr/bin/time -v $V2/bin/python -I $R/tools/t1_probe.py failopen --hermes-tree $W --plugin-dir $R/private/run/src/pii/integrations/hermes \
  > $R/private/raw/t2_runtime_present.json
```

`sandbox.sh` only re-binds the live venv. For T2, add `--ro-bind $V2 $V2`, or extend the script with
a `VENV_DIR` variable. Report as OBSERVED with n ≥ 3:
- canary markers left, and `changed`;
- wall time per request;
- the base-model file and size that `prepare_program` downloaded;
- **protocol fields left intact** (added in round 1). `LocalPiiService._redact_value`
  (`src/paw_pii/service.py:135`) recurses into every string. So with the runtime present, check that
  these come out byte-identical: message `role`, `tool_calls[].id`, `tool_call_id`,
  `function.name`, and Responses-API `input[]` item `id`/`call_id`. Use a request whose content holds
  the canary and whose ids look like PII (e.g. digits, emails). The adjacent privacy-gateway plugin
  reported HTTP 400 malformed-ID errors from this same pattern (NousResearch/hermes-agent#129692).

**F12 for the other members** is blocked until their repos exist. Run the same census per repo at
its pin:

`tools/f12_census.py --clone <repo> --repo <url> --sha <40-hex> --subdir <dir> --catalog-entry <yaml> --hermes-tree <worktree>`

For Spatial, `check_desktop_surface` is the key gate.

**T3:** none. A catalog entry makes no model-behaviour claim.

## Acceptance gates (selection)

| Gate | Status | Evidence |
|---|---|---|
| `hermes plugins validate` passes, including the security scan (no `dangerous`; `caution` read) | **not met** | The production capability probe FAILs 3/3 on `declared middleware`. The security scan is `safe` with 0 findings. The CLI run (E52) is pending OD-2 |
| Declared capabilities match what is registered at the pinned SHA | **split** | Catalog entry: met (0 mismatches). Plugin `plugin.yaml`: not met (2 undeclared middleware), and that is what admission checks |
| No self-updater | met | 0 signals: the CI JS rule, Python exec/write/fetch calls, and no desktop bundle |
| No internal-path imports (ctx only) | met | 0 imports from hermes top-level packages. Note: 1 `sys.path.insert(parents[2]/src)` |
| Owner-or-major-contributor; attribution confirmed with programasweights | pending | kvnloo owns the fork and wrote the integration (1 commit, +1081). The model, library and `paw-pii` package name belong to programasweights (4 commits, da03). Not confirmed |
| One entry per PR, queued behind kvnloo/hermes-agent#404 | pending | The commit holds one entry. #404 has 39 rows. No slot claimed; the owner promotes |
| Dependency floors have upper bounds (rule 9) | **not met** | The plugin declares no dependencies, yet it needs `paw_pii` (not on PyPI) and `programasweights` (PyPI 0.4.10). The repo-root pyproject has 8/8 bare floors |
| (added) Works when installed from the catalog subdir | **not met** | T1 catalog-install: `paw_pii` cannot be imported; the tools raise; the middleware passes PII through |
| (added) Matches the fail-closed claim in NousResearch/hermes-agent#102922 | **not met** | T1: fails open in both layouts. In the full-clone layout the host trace records a redaction that did not happen |
| (added, round 1) Redaction leaves protocol fields alone | **at risk, not tested** | Source read: `_redact_value` scans every string (`service.py:135`). Effect on a real request is a T2 check |
| (added) Structural, loader, docs and adjacent tests green; merge-tree clean; workflow push matches 0 | met | SLICE receipt; merge and push scan re-checked on `aea969677c` (RECHECK/r20261001-02) and on `44a1ce9724` (round 3), with need, green and the negative control rerun there (RECHECK/r20261001-04); need, green 3 of 3, the negative control, merge-tree and push scan re-measured on `34f8ec3b40` and on `363e9d5f0a` in round 5 (RECHECK/r20261001-06), and on the round-6 declared main `1798b335c4` (RECHECK/r20261001-07) |
| (added, round 5) No model download at request time, as a maintainer asked of the adjacent #129692 | **at risk** | The plugin downloads the PAW program bundle (programasweights.com) and a base model (Hugging Face) at first use (RECHECK/r20261001-02). Whether the downloads are hash-pinned was not checked. Owner fix item 3 |

## Gate checklist (P1-P12)

- **P1 Need: PASS.** paw-pii is absent on `234badf401`, `aea969677c`, `44a1ce9724`, the round-5 declared main
  `34f8ec3b40` (loader 348/348) and the newer upstream main `363e9d5f0a` (loader 349/349), and the old
  `plugin_index.json` route is gone on `34f8ec3b40` and `363e9d5f0a` (SLICE, RECHECK/r20261001-02, -04
  and -06). invalidate_on paths are unchanged from the base to `34f8ec3b40`. They changed on
  `363e9d5f0a`, so round 5 reproduced RED there, and they did not change again by `105e876586`.
  Round 6 declared the newest upstream main `1798b335c4` (19:08Z): invalidate_on unchanged since
  `363e9d5f0a`, paw-pii absent (loader 349/349, in the sandbox), old route gone (RECHECK/r20261001-07).
- **P2 Ownership: PENDING.** No external owner or competitor. The six adjacent open PRs and two
  adjacent merged items do not conflict (see the table above; round 2 added #17472 under the
  stated `adjacent_rule`). Attribution and the `paw-pii` key are
  unconfirmed with programasweights.
- **P3 Shape: PASS.** One YAML file, +20 lines.
- **P4 Real path: PASS** for the catalog, admission probe and middleware chain. The runtime-present
  path is NOT_TESTED. FACTORY 11.1 asks for coverage proof, and no receipt holds a coverage
  measurement (round-6 advisory). This PASS rests on the production path having run on the real
  entry: `hermes_cli.plugin_catalog.load_catalog` loaded it and read its capabilities (349/349 in SLICE;
  350/350 on `363e9d5f0a` and `1798b335c4`), `scripts/validate_plugin_catalog.py` and the shipped-entries
  test ran on the real `plugin-catalog/`, the production capability probe ran as a library call (T1),
  and the real middleware chain drove the plugin's callbacks (T1-failopen). For a data-only entry that
  is accepted in place of a coverage report.
- **P5 Proof: PENDING.** Recorded as met: RED with its marker (`348/348 entries, entry_present=false`),
  GREEN 3/3 and ADJ identical, all OBSERVED (SLICE), with green and the negative control reproduced on
  `44a1ce9724` (RECHECK/r20261001-04); and F14 guards equal: EQUAL on the commit cherry-picked onto
  upstream main `34f8ec3b40`, 2 runs, 40 of 40 ids identical to the baseline, no flaky exclusions
  (F14/r20261001-01). Still missing, so P5 is not PASS:
  1. **Per-hunk SABOTAGE re-RED.** Earlier rounds recorded it as N_A for one data file. FACTORY 11.1
     and section 8 step 9 allow no N_A here. The `sha: main` negative control is a mutation, not a hunk
     revert, and the F12 calibration variants test the census, not this diff. The diff has one hunk (the
     whole new file). A receipt must record that hunk reverted alone, the re-RED (validator, loader or
     shipped test) and `unpinned_hunks = []`.
  2. **`flaky = false`.** Neither this manifest nor any cited receipt records it. The GREEN reps agree
     (3/3), but the field itself is absent.
  Round 3 changed this gate from RECORDED to PENDING. The F14 run (2026-10-01T18:28Z) leaves it PENDING
  for the two reasons above. Round 5 re-measured RED, GREEN 3 of 3 and the negative control on
  `34f8ec3b40` and `363e9d5f0a` (RECHECK/r20261001-06), which changes neither missing part. ADJ was
  measured on `234badf401`; the adjacent files are unchanged on `34f8ec3b40`, but
  `tests/scripts/test_validate_plugin_catalog.py` changed on `363e9d5f0a` and was not re-run. Round 6
  re-measured RED, GREEN 3 of 3 and the negative control on `1798b335c4` (RECHECK/r20261001-07), which
  again changes neither missing part.
- **P6 Numbers: N_A.** The "~600 MB" in the entry description is a disclosure, not a value claim. It
  is labelled MODELED until T2 observes it.
- **P7 Package: PENDING** (round 5; was "PASS, resting on merge-tree"). FACTORY 11.1 asks for one
  commit on fresh main. The one commit sits on `234badf401`, 137 commits behind the round-6 declared
  main `1798b335c4` (74 behind the factory main `34f8ec3b40`), so that part is not met, as the round-4
  verifier noted. Every other part holds: correct author and subject; no contaminated paths; merge-tree
  clean on `1798b335c4` (tree `064f9e0c67`, equal to main plus the entry, on which round 6 ran the
  validator, the loader, the shipped test 3 of 3 and the negative control), on `34f8ec3b40` (tree
  `47e2acb8c2`, where round 5 ran the same) and on `105e876586` and `5d077106b8`; 0 of 11 push workflows
  match `staged/plugin-catalog-entries` on `34f8ec3b40`, `363e9d5f0a` and `1798b335c4`
  (RECHECK/r20261001-06 and -07); `--no-follow-tags`. Building v2 directly on fresh main closes it (owner fix
  item 7).
- **P8 Freeze: PENDING.** The receipts no longer carry host paths or the hostname, so they can be
  frozen. `tools/sandbox.sh`, the r01 `raw/` outputs and `run/` stay local-only; since round 6 they sit
  under `private/` (`[evidence].private_moves`, `[evidence].public_scope`), so the rule "publish
  everything outside `private/`" is now safe. Before round 6 it was not: the r01 raw outputs and
  `tools/sandbox.sh` held absolute local paths, and the clone's reflogs under `run/` held the host name
  and the login, none of it inside a `private/` directory (nothing had leaked: the fork's ledger copy
  followed the narrower round-4 scope, per the round-6 verifier).
  Every file in `tools/` is pinned by a cited receipt and must stay byte-identical until the freeze.
  Three r01 receipts keep the pinned commit's public git display name (`[evidence].receipt_privacy`).
  Round 4 removed a host path from the declared publishable set: the round-3 `tools/__pycache__/`
  bytecode. It narrowed the set to `tools/*.py` and rescanned it with a completeness walk, 0 of 38
  files flagged (RECHECK/r20261001-05). Round 5 added `raw/r5_*` and RECHECK/r20261001-06 and reran
  the same scan (see History). Round 6 replaced that scan with `tools/privacy_scan_r6.py`, which walks
  every file outside `private/` and adds a login check; its negative control catches each planted leak
  (RECHECK/r20261001-07), and its final run is in History.
- **P9 Text: PENDING.** `body.md` follows `.github/PULL_REQUEST_TEMPLATE.md` with every section and
  checkbox list kept, including Screenshots / Logs, and only "For New Skills" removed. It holds 8
  distinct placeholders (11 occurrences), listed in `[body].placeholders`. Every one must be filled at
  the re-pin before posting, with test counts written as "N of M pass" (round 4 made line 52 read
  `<N of M pass>`). Round 5 filled the two clone placeholders, removed the line-34 claim that the
  plugin's `plugin.yaml` declares the middleware (false at `d891ebdd`), and split the download
  disclosure so the re-pin states when the downloads happen (`[body].filled_round5`). Round 6 recorded
  that the pre-ticked template boxes are owner attestations to confirm or untick at posting
  (`[body].template_attestations`), and that the AI-assistance line ("ran the checks listed above")
  holds only once E52 has run at the v2 pin (`[body].ai_line_condition`). The tone gate and independent
  lint have not run.
- **P10 Independent read: PENDING.**
- **P11 Demand: RECORDED.** Low pull. The maintainer signal on paw-pii is weak: one AI-assisted triage
  note on #102924 from a Nous-affiliated human account, with no view on the plugin. Round 5 adds an
  adjacent signal: a maintainer reviewed the other local PII catalog entry, #129692, and asked for fail
  closed, no runtime model download, declared middleware and a `requires_hermes` floor
  (`[upstream].maintainer_signal`). An owner submission is allowed.
- **P12 Queue: PENDING.** Behind the 39 kvnloo/hermes-agent#404 rows (re-counted at 18:40Z); staging cap; Wave 0 not passed.

## NOT_TESTED

- **The hermes CLI** (`hermes plugins validate --install-deps`, E52). The production probe function
  ran as a library call instead; the CLI wrapper and dependency install did not.
- **The runtime-present path.** Redaction quality, false positives, per-turn latency, and behaviour
  when `PAW_PII_PROGRAM_ID` points elsewhere all need programasweights and model downloads (T2).
- **Which base model the server assigns to program `73a0e38b`, and its size.** No program metadata
  was fetched and nothing was downloaded, so "~600 MB" is MODELED.
- **Protocol-field safety.** Whether redacting `role`, tool-call ids, function names or Responses
  item ids breaks a provider request (T2).
- **Provider-side effects.** No real provider was called. The request payload was checked at the
  middleware boundary only.
- **Docs-site README rendering.** The entry sets `readme: false`.
- **The `plugin-catalog-ci.yml` pinned-source-validate job.** It needs the CLI. On `363e9d5f0a` the job
  was reworked (pinned-clone and symlink confinement, an entry PR may touch only `plugin-catalog/**`
  and `contributors/emails/**`, 600 s clone and validate timeouts). Read, not run: this branch's diff
  is `plugin-catalog/paw-pii.yaml` only, and the pinned clone has 0 symlinks (RECHECK/r20261001-06).
- **Hash pinning of the first-use downloads.** Whether the programasweights runtime verifies the
  program bundle and base model it downloads was not checked.
- **The catalog entry under F14.** F14 ran and is EQUAL (F14/r20261001-01), but none of its probes
  reads `plugin-catalog/`, so it guards against regressions elsewhere and does not test the entry. RED,
  GREEN and the negative control were re-measured outside F14 on `34f8ec3b40` and `363e9d5f0a` in
  round 5 (RECHECK/r20261001-06), and on `1798b335c4` in round 6 (RECHECK/r20261001-07).
- **Adjacent tests on current main.** ADJ (68 passed / 13 env errors on both arms) was measured on
  `234badf401`. The adjacent files are unchanged on `34f8ec3b40`; on `363e9d5f0a`,
  `tests/scripts/test_validate_plugin_catalog.py` gained 20 lines and was not run. It is unchanged from
  there to `1798b335c4`.
- **Python 3.14.** Main requires 3.14, but the mandated venv is 3.11. The 13 `isolated_python`
  setup errors are environmental and identical on both arms.
- **The other three members.** groq-orpheus, tinyfish and spatial were not censused: they have no repos.

## What is missing before promotion (standalone repo kvnloo/pii, owner action; not done here: no GitHub writes)

1. **Declare the middleware.** In `integrations/hermes/plugin.yaml` add
   `provides_middleware: [llm_request, tool_execution]`. T1 shows that this line alone turns the
   capability probe from FAIL to PASS.
   - Check whether the Hermes APIs the plugin uses (`ctx.register_middleware` and the middleware kinds)
     need a `requires_hermes` floor, and declare it in `plugin.yaml` and the entry if so. The maintainer
     review on NousResearch/hermes-agent#129692 (2026-10-01) asked privacy-gateway for one. Not
     checked here (added in round 5).
2. **Make the subdir self-contained** for `hermes plugins install paw-pii`, which installs a sparse
   subdir only.
   - The plugin's import path needs only stdlib modules from `paw_pii`: `service`, `parsing`,
     `redaction`, `taxonomy`, `types`, `metrics`. It also needs `programasweights`, imported lazily.
   - Vendor those modules into the plugin directory, drop the `sys.path.insert`, and declare
     `python_dependencies: ["programasweights>=0.4.2,<0.5"]` (rule 9: upper bound).
   - The alternative is a repo-root plugin, but it would drag 8 unbounded floors including torch.
3. **Fail closed by default, and move settings to config.yaml.**
   - Add a `config_schema` setting, for example `on_error: block|pass` with default `block`, as
     #102922 promises. When the program cannot load, the middleware should then refuse or
     placeholder the request rather than pass it through.
   - Move the five non-secret env toggles the plugin reads today into `config_schema` too, per
     "config.yaml, not env vars": `PAW_PII_DISABLE`, `PAW_PII_AUTO_LLM`, `PAW_PII_AUTO_TOOLS`,
     `PAW_PII_PROGRAM_ID`, `PAW_PII_PLACEHOLDER` (`integrations/hermes/__init__.py:19-23,48-62`).
   - Return `None` instead of `{"request": ..., "reason": "local PII redaction"}` when nothing
     changed, so the host trace stays truthful.
   - The host-side opt-in in NousResearch/hermes-agent#95186 (open) would complement this but is not
     a substitute: the plugin still needs its own default.
   - **No model download at request time** (added in round 5). Today the first use after install (the
     first redaction) downloads the PAW program bundle from programasweights.com and a base model from Hugging Face.
     The maintainer review on NousResearch/hermes-agent#129692 (2026-10-01T17:14Z) asked privacy-gateway
     to refuse its runtime spaCy model download (~560 MB, unpinned) with a clear error that points to
     the manual install steps, and to block requests when a dependency is missing. The same bar
     applies here: download in an explicit one-time setup step (for example a documented
     `prepare_program` command), pin what is downloaded if the runtime allows it, and when the program
     or model is missing, block with a clear error rather than fetch or pass through. The
     `body.md` placeholder `<when they download at the new pin>` records the choice.
4. **Redact content fields only** (added in round 1). `LocalPiiService._redact_value`
   (`src/paw_pii/service.py:135`) recurses into every string, because the condition
   `key in content_keys or isinstance(item, (str, list, dict))` makes `content_keys` a no-op. So
   `role`, tool-call ids, function names and Responses item ids are scanned, and a false positive could
   corrupt a provider request. privacy-gateway hit exactly this (HTTP 400 on rewritten item ids,
   NousResearch/hermes-agent#129692). Limit redaction to content and argument/output payloads, and add
   a test with PII-looking ids. T2 checks it on the new pin.
5. **Add `integrations/hermes/README.md`.** Then the entry can use `readme: true`.
6. **Attribution, name and platforms.**
   - Confirm with programasweights (da03) that the Hermes integration can be listed.
   - Decide whether the catalog key and manifest name stay `paw-pii`, their package name (the Names
     rule gives the affiliated project the bare key), or become a distinct name such as `paw-pii-hermes`.
   - Declare `platforms: [linux]` unless macOS and Windows are tested (the plugin has only run on
     Linux).
7. **Re-pin.**
   - Set the new 40-hex SHA in `plugin-catalog/paw-pii.yaml`. Update the description: drop the
     fail-open sentence if item 3 lands, and replace "~600 MB" with the size T2 observes (or drop the
     number).
   - Rerun F12, both T1 probes, T2 and E52.
   - Build `staging/plugin-catalog-entries-v2` from fresh main (pushed to the fork as
     `staged/plugin-catalog-entries-v2`). Never force-push v1.
   - Fill all 8 placeholders in `body.md` (`[body].placeholders`), with every test count written as
     "N of M pass", and keep the log block free of host paths. Re-check the adjacent PR list
     (#129692 and #95186 in particular; `body.md` names both) and the state of the #129692 review.
   - Write the v2 commit message for the v2 entry; do not copy v1's (see `commit_message`).
   - Ask the owner to update the fork tracking issue kvnloo/hermes-agent#412 (`[upstream].fork_tracking`).
   - Build the v2 receipts with the GitHub login only, not the git display name.
   - Run every privacy scan with `python3 -B` or `PYTHONDONTWRITEBYTECODE=1` (`tools/privacy_scan_r6.py`
     or a successor that walks every file outside `private/`). Keep run dirs, clones and as-run outputs
     that hold host paths under `private/` from the start, and publish only scrubbed `raw/r<round>_*` copies.

## Origin action (owner only)

The single smallest ask: after the re-pin passes E52, open one catalog PR from the fork branch
`staged/plugin-catalog-entries-v2`, queued behind the 39 kvnloo/hermes-agent#404 rows. The body is in
`body.md` (template-shaped, placeholders filled at re-pin). Command recorded, not run:

`gh pr create -R NousResearch/hermes-agent --head kvnloo:staged/plugin-catalog-entries-v2 --title "feat(plugin-catalog): add paw-pii" --body-file body.md`

## Next steps

1. Owner: make the kvnloo/pii fixes listed above (items 1-5), and decide item 6 with programasweights.
2. Rerun F12 and both T1 probes on the new pin ($0). Ask for OD-2, then run E52. Run T2 with the
   protocol-field check.
3. Rebuild as `staging/plugin-catalog-entries-v2` on fresh main. Get a blind verifier read, then
   freeze the receipts.
4. Groq-Orpheus, TinyFish and Spatial: create the standalone repos (TTS seam at
   `hermes_cli/plugins.py:1126`, browser seam at `:1106`; Spatial stays inside `@hermes/plugin-sdk`
   per rule 8). Census each at its pin, then one catalog entry per PR. Each costs a slot, and demand
   is low.
5. OD-0 is resolved: v1 is on kvnloo/hermes-agent as `staged/plugin-catalog-entries` (HOLD, tracked by
   kvnloo/hermes-agent#412); `staged/plugin-catalog-entries-v2` follows the re-pin. The fork's legacy
   `refs/heads/staging` stays untouched.

## History

| Timestamp (UTC) | Status | Worker | Reason |
|---|---|---|---|
| 2026-10-01T08:50Z | CANDIDATE | builder (Claude Code, Opus 5.5) | Selection entry read; premise re-checked on main `572e4f4fad` |
| 2026-10-01T09:12Z | STAGED | builder | `2b05ac2bb8` committed (09:03:41Z); F12 (09:08Z) and T1 (09:12Z) run; the plugin at the pin fails admission and fails open. Restamped in round 2 from 09:00Z, which predated the commit |
| 2026-10-01T09:15Z | HOLD | builder | Main moved to `234badf401` (11 commits, no invalidate_on paths); rebased to `98c305b3ec` (committed 09:14:45Z); slice checks rerun (09:15:16-09:15:31Z); blocker recorded. Restamped in round 2 from 09:10Z, which predated the commit |
| 2026-10-01T11:15Z | HOLD | fixer, round 1 (Claude Code, Opus 5.5) | Manifest-only fix after the phase-3 verifier (commit unchanged). Behind counts re-measured on `234badf401`. Maintainer signal restated. Ownership search widened (5 adjacent open PRs, 2 merged, none conflicting). Disclosures receipted, with "~600 MB" labelled MODELED. `body.md` split out on the PR template. Receipts scrubbed of host paths. Fork branch named `staged/<id>`, which resolves OD-0. Merge and push scan re-checked on `aea969677c`. Owner fix list gains config_schema toggles, content-only redaction and platforms; T2 gains the protocol-field check |
| 2026-10-01T11:42Z | HOLD | fixer, round 2 (Claude Code, Opus 5.5) | Manifest, receipts and tools only; commit `98c305b3ec` unchanged, promotion form unchanged. Removed a private project name from the T2 block. Hostname in the four r01 receipts replaced by `<host>` (new sha256 in `[evidence]`). Host paths removed from `build_receipts.py` and `scrub_receipts.py`; `sandbox.sh` declared local-only (`public_scope`). `[merge_check].previous` stamp withdrawn and the tree re-measured; recheck command names the SHA. History rows restamped to the commit record. #17472 added as the sixth adjacent PR under a stated rule. RECHECK/r20261001-03 records it all, including a clean privacy scan and a byte-identical receipt rebuild |
| 2026-10-01T16:25Z | HOLD | fixer, round 3 (Claude Code, Opus 5.5) | Manifest, `body.md`, one new receipt, `raw/r3_*` and one new tool; commit `98c305b3ec` unchanged, promotion form unchanged, no existing pinned file edited. Corrected the false "no receipt pins" text: every `tools/` file is pinned, and `build_receipts.py`, `scrub_receipts.py` and `privacy_scan.py` are pinned by RECHECK/r20261001-03. Declared upstream main `44a1ce9724` (ls-remote) and re-measured on it: paths unchanged, merge-tree clean, need, green 3 of 3 runs pass, negative control, push scan, behind counts, cited PR states. P5 RECORDED changed to PENDING (F14 not run). `body.md` names #95186 and its AI-assistance line covers the description. The pinned commit's public display name is kept in v1 so that no pin breaks; v2 drops it. RECHECK/r20261001-04 |
| 2026-10-01T16:47Z | HOLD | fixer, round 4 (Claude Code, Opus 5.5) | Privacy and manifest text only; commit `98c305b3ec` unchanged, promotion form unchanged, no pinned file edited. Blocking finding fixed: deleted `tools/__pycache__/privacy_scan.cpython-314.pyc`. The round-3 scan had written it, it embedded a host path, it sat inside the declared publishable set, and that scan skipped it. Narrowed `public_scope` to `tools/*.py` and corrected the round-3 "clean scan" claim (31 of 32 files). Added `tools/privacy_scan_r4.py`: a completeness walk with bytecode writing off. It FAILs with the `.pyc` present and finds 0 of 38 flagged after the deletion. P7 restated as resting on merge-tree (parent 65 commits behind main; v2 on fresh main). v1 marked never to be promoted as is ("~600 MB" MODELED). `body.md` line 52 now asks for "N of M pass"; its 9 placeholders are listed. Upstream main unchanged, cited states unchanged. The leftover `_out/` and `_repo/` (an empty bare repo) from an earlier worker were removed from this item's worktree slot. RECHECK/r20261001-05 |
| 2026-10-01T18:28Z | HOLD | F14 guard worker, Wave 0 (Claude Code, Opus 5.5) | F14 guard comparison; commit `98c305b3ec` unchanged, no pinned file edited, nothing pushed. Cherry-picked it onto upstream main `34f8ec3b40` (clean, patch byte-identical, arm `dd185c1f84`, local ref `refs/xf/w0/plugin-catalog-entries`). Ran F14 twice: both runs EQUAL to the main baseline on 40 of 40 ids (36 PASS / 4 FAIL, the baseline's own FAILs), no flaky exclusions. `guards.F14` set to EQUAL. P5 stays PENDING: per-hunk sabotage is not N_A under FACTORY and is not recorded, and `flaky = false` is not recorded. Worktree removed and pruned. F14/r20261001-01 |
| 2026-10-01T18:55Z | HOLD | fixer, round 5 polish (Claude Code, Opus 5.5) | Manifest, `body.md`, one new receipt and `raw/r5_*`; commit `98c305b3ec` unchanged, no message-only v2 (v1 is never promoted and `-v2` is reserved for the re-pin; `commit_message` records the v1 message gaps), no pinned file edited, nothing pushed, no GitHub writes. Round-4 advisories: (1) declared main moved to `34f8ec3b40` and re-measured there and on the newer upstream main `363e9d5f0a` in the factory sandbox (merge-tree clean, need, green 3 of 3, negative control, push scan 0 of 11); `105e876586` (newest seen) is merge-tree clean with no invalidate_on change since `363e9d5f0a`; (2) P7 PASS changed to PENDING to follow FACTORY 11.1 (not on fresh main); (3) v1's MODELED "~600 MB" is in the entry YAML, a code change, so not fixed here; the branch is now on the fork and kvnloo/hermes-agent#412 carries HOLD in its title, and a body edit for it is recorded for the owner; (4) `body.md` no longer claims the plugin's `plugin.yaml` declares the middleware (re-read at `d891ebdd`: it does not), and the two clone placeholders are filled (8 distinct placeholders remain); (5) the display-name text now says it is the author and the committer name (gh: equal); the name stays in the pinned v1 receipts by design. New: maintainer review CHANGES_REQUESTED on the adjacent #129692 recorded (fail closed, no runtime model download, declared middleware, `requires_hermes` floor); owner fix items 1 and 3 extended; a download-timing placeholder added to `body.md` line 35. Privacy scan PASS (46 files, 0 flagged). RECHECK/r20261001-06 |
| 2026-10-01T19:20Z | HOLD | fixer, round 6 (Claude Code, Opus 5.5) | Fix after the fresh verifier; commit `98c305b3ec` unchanged, no v2 ref (v1 is never promoted, `-v2` stays reserved for the re-pin, and the v1 entry text that would also need fixing is code), no pinned file edited, `body.md` unchanged, nothing pushed, no GitHub writes. Blocking finding fixed: the publishable set is everything outside `private/`, and local-only material sat outside it. Moved 169 files byte-identical to `private/<same path>`: the 41 r01 raw outputs (27 with absolute local paths), `tools/sandbox.sh` and the whole `run/` tree (the pinned clone's reflogs carry the host name and the login, never scanned before; packs and index are binary). `private/MOVED-r6.tsv` lists old paths, sha256 and sizes; 169 of 169 equal after the move, and 75 of 75 receipt-cited hashes still match. `public_scope` rewritten (current rule first, the 'run/ ... no host paths found' text corrected), `private_moves` added, queued E52/T2 commands point at `private/`. New `tools/privacy_scan_r6.py` walks every file outside `private/` (host name, whole-word login, private terms, binary, bytecode); its negative control flags each of 5 planted leaks; final run PASS: 54 publishable files, 0 flagged, 0 login hits, 0 unclassified, 0 binary, 0 bytecode outside `private/` (`raw/r6_privacy_scan.txt`). Advisories: the newest upstream main `1798b335c4` (after the verifier's `5d077106b8`) declared and re-measured in the factory sandbox (merge-tree clean, invalidate_on unchanged since `363e9d5f0a`, need, green 3 of 3, negative control, push scan 0 of 11); `[body].template_attestations` and `[body].ai_line_condition` added; P4 now states it rests on production-path execution, not a coverage measurement; F14 `patch_sha256` reproduction (`core.abbrev=10`) and the notice_delivery marker recorded under `guards`. Gates unchanged. RECHECK/r20261001-07 |
