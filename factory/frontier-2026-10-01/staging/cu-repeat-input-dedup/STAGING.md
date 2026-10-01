+++
xf_staging = 1
id = "cu-repeat-input-dedup"
version = 1
title = "Same-turn duplicate-call elimination keeps order-significant computer_use key presses"
promotion_form = "core-pr"
branch = "staging/cu-repeat-input-dedup"
branch_physical = "staged/cu-repeat-input-dedup on kvnloo/hermes-agent, not pushed yet; local ref refs/heads/staging/cu-repeat-input-dedup in scratchpad h.git. OD-0 resolved by the rename: the fork's legacy refs/heads/staging (28790e597c) blocks staging/*, so the fork branch uses staged/*."
branch_sha = "2f79b549ef40aeb31cb3af36cd92d8d12b9ba799"
status = "HOLD"          # $0 evidence complete (r03); HOLD = OD-6 (CU design hold scope + Hermes-lane ownership, E1/E2)
route = "core-leaf"
feature = "cu-repeat-key-dedup-fix"
invariant = "Two identical computer_use key calls in one assistant message both dispatch, directly or via the tool_search tool_call bridge; all other same-turn duplicates are still dropped."

[base]
repo = "NousResearch/hermes-agent"
sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
fetched_at = "2026-10-01T11:05Z"
proof_bases = ["572e4f4fad (r01, head c9e8b2584c, superseded)", "234badf401 (r02, head 402e9b0bdb, superseded)", "aea969677c (r03, head 2f79b549ef, current)"]

[upstream]
issues = ["NousResearch/hermes-agent#112639 (ours, RFC)", "NousResearch/hermes-agent#124008 (ours, closed 2026-09-30 owner batch self-close)", "kvnloo/hermes-agent#316 (fork parking list)"]
eval_prs = []
carrier = { pr = 0, author = "", head = "" }       # own leaf; no carrier
competitors = []                                    # no open external PR on this defect (STATIC/r20261001-03 upstream_dedupe_search)
close_after = []
demand = { score = 0, source = "none measured; impact lens 3/10; T2/T3 prevalence probe queued" }
maintainer_signal = "none (prior #124008 closed by its author in the 2026-09-30 budget batch, not by a maintainer)"

# Donors are commits whose code or idea the staging commit uses. The staging commit itself
# (branch_sha) is not a donor. The canonical-JSON key from merged #86887 (fangliquanflq) is
# existing main code that moves unchanged, so it needs no trailer.
[[donors]]
sha = "570dc83ba65fc4ce86efb2c00e89dc84d19bd5ca"
ref = "refs/fork/fix/computer-use-repeat-input-dedup-current-main"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "donor of the invariant and the static tests (4 commits, all by this author, +32/-4, merge-base cb3142d325); restructured, not cherry-picked"
trailer = "none needed (same author as the staging commit)"

[ownership]
searched_at = "2026-10-01T11:10Z"
queries = ["deduplicate tool calls computer_use", "repeated key press computer use", "same-turn duplicate tool call", "_deduplicate_tool_calls", "duplicate tool call", "Removed duplicate tool call"]
open_external = []
nearby_open_no_overlap = [119760, 112303, 118837, 6784, 84867, 106257, 74906]   # NousResearch/hermes-agent PRs; none changes the dedup method (STATIC/r20261001-03)
merged_overlap = []              # #86887 (fangliquanflq) added the canonical JSON key this change keeps
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # NousResearch/hermes-agent; checked 2026-10-01: all TUI/HUD perf, no overlap
hard_hold = [69, 70]             # fork issues kvnloo/hermes-agent#69 and kvnloo/hermes-agent#70 (FACTORY E1/E2 hard hold)
design_holds = ["CU/Jev"]        # this is a bug-fix invariant, not CU design work; still needs OD-6 to promote
hermes_lane_overlap = "kvnloo/hermes-agent#316 parks #124008 (Hermes lane board); handoff envelope NOT posted (no GitHub writes in this run)"
verdict = "OWN leaf; lane handoff pending"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]   # untouched

[evidence]
receipts = [   # current: r03, head 2f79b549ef on aea969677c
  { id = "F07/r20261001-03", path = "receipts/F07-r20261001-03.json", sha256 = "68b1ccb257acb07b7b0d1b3f19826f5e0f426c64fefb70f35345e3c34c5382f8" },
  { id = "E25/r20261001-03", path = "receipts/E25-r20261001-03.json", sha256 = "47949080425ca8a2b21f147f8edde537578dccaed8c849a981673b38aad4be01" },
  { id = "STATIC/r20261001-03", path = "receipts/STATIC-r20261001-03.json", sha256 = "e3f906a1f369c88e504b1ff535483c683e29d92e86daae58931c4525049c2fe5" },
  { id = "F07P/r20261001-03", path = "receipts/F07P-probe-dryrun-r20261001-03.json", sha256 = "55d9e38bfa3c4ff68a711e4707e3c3225d19d7fe71ceec0de33e452f6f4af2e3" },
  { id = "cells-r03", path = "receipts/cells-r03.jsonl", sha256 = "b706d8b5a957ea7ce84256c33671cb3f4851eedee2ca23fd1bae707e01db7794" },
]
manifest = { path = "receipts/MANIFEST-r20261001-03.sha256.json", sha256 = "3c54de0fd34316487e51b727b78d424495bcc6488c28da8f8b193a52fb705343" }
superseded_receipts = [   # same verdicts; kept write-once. r01/r02 (and raw/, raw-r02/) contain absolute local paths: local only, never copy them to the ledger
  { id = "F07/r20261001-02", path = "receipts/F07-r20261001-02.json", sha256 = "4352321c53c69c169fa7e66621a6748d18b6552eafaded7e067bc4c3d7c30d73" },
  { id = "E25/r20261001-02", path = "receipts/E25-r20261001-02.json", sha256 = "f440b4584dfd8f843aed6b91545d5e2874b6cd8c34eeb3c7d63fec1c19e5f95d" },
  { id = "STATIC/r20261001-02", path = "receipts/STATIC-r20261001-02.json", sha256 = "005b911add587ae6e38a7623cd383c76471384aa9e15dfe4fb05b7d359a9c276" },
  { id = "F07P/r20261001-02", path = "receipts/F07P-probe-dryrun-r20261001-02.json", sha256 = "7806c1bc077835fe853472765a3ab68f5ca3d8f4455ec58cff13bd304aa41e48" },
  { id = "F07/r20261001-01", path = "receipts/F07-r20261001-01.json", sha256 = "5ecf7cd311efe5c121f53168f0d43acb885d5aaf9d2d685ec360222f667bf6d6" },
  { id = "E25/r20261001-01", path = "receipts/E25-r20261001-01.json", sha256 = "1a23018068a65a02e2579794c07ebebe9f3fcea5033d2cfee7120f40468fc078" },
  { id = "STATIC/r20261001-01", path = "receipts/STATIC-r20261001-01.json", sha256 = "7c4b699283b917a892a83e7cb6da2407030fbbfc1eaacb02bf86dcafab056602" },
  { id = "F07P/r20261001-01", path = "receipts/F07P-probe-dryrun-r20261001-01.json", sha256 = "119a5ea8af838f1d1324d32aef4f15d449d1f2006ce5bdcf09dcef56fe43be51" },
]
red = { test = "tests/agent/test_tool_call_dedup_order_significant.py (both params)", main = "aea969677c", marker = "AssertionError: assert ['key', 'click'] == ['key', 'key', 'click']", receipt = "F07/r20261001-03" }
green = { reps = "3/3", receipt = "F07/r20261001-03" }
negative_control = { mutation = "empty _ORDER_SIGNIFICANT_ACTIONS + per-hunk (bridge peel, facade forwarder)", result = "RED (2/2, 1/2 bridge-only, 2/2)", receipt = "F07/r20261001-03" }
adjacent = { identical = true, base = "559 passed / 0 failed", head = "561 passed / 0 failed (+2 new)", pre_existing = [], attempt = "2 (attempt 1 of both arms lost tests/agent/test_run_agent.py to the 300 s per-file timeout at load1 ~14; re-run with HERMES_TEST_FILE_TIMEOUT=900)" }
guards = { F14 = "NOT_RUN (standing set not built)" }
quantitative = []
cache_read_ratio = { status = "N_A" }   # no prompt/system/tool-schema change; current-turn tool list only
route_scope = "n/a"
not_tested = ["real cua-driver / desktop", "real-model emission rate (T2/T3 queued)", "macOS / Windows", "F14 standing set"]
prereg = { status = "NOT_PREREGISTERED", gap = "FACTORY I5: spec committed to claude/ledger before run 1; no ledger write was allowed, so the r03 receipts carry spec.status = NOT_PREREGISTERED and the decision rule restated after the fact (open P8 item)" }
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-cu-repeat-input-dedup", commit = "" }

[gates]
P1 = "PASS"      # RED on aea969677c (current main at the 11:05Z fetch) 3/3 (F07/r20261001-03); also RED on 234badf401 (r02) and 572e4f4fad (r01)
P2 = "PENDING"   # no external owner (re-searched 11:10Z); Hermes-lane handoff on kvnloo/hermes-agent#316 not recorded (E1); OD-6 ownership open
P3 = "PASS"      # one invariant; no env var/config/hook; facade -17 lines; forwarder uses the facade's lazy_forward idiom (32 on main, this adds the 33rd)
P4 = "PASS"      # real AIAgent turn; seam executed (passive profiler counts); only LLM endpoint + device faked
P5 = "PENDING"   # RED/GREEN 3/3/NEG/per-hunk/ADJ all PASS on r03; F14 guards not run
P6 = "N_A"       # body makes no value claim
P7 = "PASS"      # one commit on aea969677c, author + subject ok, merge-tree clean, 0 of 11 push workflows match staged/cu-repeat-input-dedup, fork ref free
P8 = "PENDING"   # write-once receipts + sha256 manifest exist locally; spec not preregistered (I5); not on claude/ledger; not frozen to z0evals
P9 = "PENDING"   # PR_BODY.md drafted (template, AI disclosure, NOT_TESTED); tone gate needs an independent check
P10 = "PENDING"  # blind exact-head verifier on 2f79b549ef not yet requested (the phase-3 read covered 402e9b0bdb, same diff)
P11 = "RECORDED" # no demand data; real fix, not lone infra
P12 = "PENDING"  # HOLD (OD-6); staging cap / ordering behind the 39 rows on kvnloo/hermes-agent#404 (OD-8)

[verification]
verifier = ""
provenance = "independent"
exact_head = "2f79b549ef40aeb31cb3af36cd92d8d12b9ba799"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""
prior_read = "phase-3 verifier on 402e9b0bdb (same diff): code and proof sound, accept=false on manifest accuracy and format only; every listed problem is addressed in this revision"

[merge_check]
main_sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
checked_at = "2026-10-01T11:33Z"
clean = true
tree = "cb2b5fe5cf30c50a81a7436e3c34adb7c8fc581c"
recheck = "git -C <h.git> merge-tree --write-tree main staging/cu-repeat-input-dedup"
later_check = "2026-10-01T11:33Z: another worker had moved h.git main to e8c97320ac (6 commits past aea969677c, none touching run_agent.py, agent/tool_dispatch_helpers.py, agent/turn_tool_round.py, tools/computer_use/, tools/tool_search*.py, model_tools.py, hermes_cli/config_defaults.py or the test fakes); merge-tree clean, tree b4baced082. Every count in this file is measured on aea969677c."

[push]
fork_branch = "staged/cu-repeat-input-dedup"
no_follow_tags = true
workflow_push_matches = 0      # 0 of 11 push workflows in the 2f79b549ef tree match staged/cu-repeat-input-dedup (harness/wfscan.py)
collision_check = "2026-10-01T11:06Z ls-remote kvnloo/hermes-agent: no refs/heads/staged and no staged/*; only the legacy refs/heads/staging 28790e597c"
pushed_at = ""

[body]
path = "PR_BODY.md"
kind = "pr-body"
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }   # author self-check only
jargon_lint = "PASS (self-check: no envelope/lane/E##/F## in body)"
privacy_scan = "PASS (synthetic fixtures only; no paths/session ids in body)"

[queue]
board = "kvnloo/hermes-agent#404"   # staged-PR queue: 39 data rows, title "39 reproved branches" (read 2026-10-01T11:06Z)
position = "after the 39 existing rows"
slot_claimed = false
# Not this item's board: kvnloo/hermes-agent#402 (salvage wave) and kvnloo/hermes-agent#403 (close wave) are closed and were posted upstream as NousResearch/hermes-agent#130139 and NousResearch/hermes-agent#130140.

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# staging/cu-repeat-input-dedup

Promotion form: **core-pr**, as a core-leaf with its own PR (`PR_BODY.md`). Status: **HOLD**.

The commit is `2f79b549ef`, one commit on current main `aea969677c`. It has the same diff as `402e9b0bdb`; only a broken line in the commit body was rewrapped. The $0 evidence was re-run on the new head as r03 and gave the same verdicts.

The branch can't be promoted until four things happen: OD-6 is decided, the Hermes-lane handoff on kvnloo/hermes-agent#316 is recorded, P8 (preregistration and freeze) is closed, and a blind exact-head read of `2f79b549ef` (P10) comes back CLEAN. OD-0 no longer blocks: the fork branch will be `staged/cu-repeat-input-dedup`.

References: a bare `#N` in this file is a NousResearch/hermes-agent issue or PR. Fork issues are always written in full as `kvnloo/hermes-agent#N`.

## Invariant

Two identical `computer_use` `key` calls in one assistant message both dispatch, whether the model calls the tool directly or through the tool_search `tool_call` bridge. Every other same-turn duplicate is still dropped, including a repeated `computer_use` click on the same element and identical calls to any other tool.

Real call path tested:

`AIAgent.run_conversation` → `agent/turn_tool_round.py::run_tool_round` (line 88 on `aea969677c`) → `AIAgent._deduplicate_tool_calls` (now a `_forward_static`) → `agent/tool_dispatch_helpers.py::deduplicate_tool_calls` → `_is_order_significant` → `_peel_bridge_call` → `model_tools.handle_function_call` (bridge re-dispatch) → `tools/computer_use/tool.py::handle_computer_use` → backend.

Only the LLM endpoint (`FakeLLMServer` on 127.0.0.1) and the device (the in-tree `_NoopBackend`, injected through `_new_backend`) are fake. A passive `sys.setprofile` observer confirmed that every seam function above ran. No seam was patched.

## Route and carrier choice

The route is `core-leaf`: our own single commit with its own PR.

- There is no external owner. No open upstream PR touches this defect (six searches, re-run 2026-10-01T11:10Z, listed in the front matter).
- None of the seven nearby open PRs changes the dedup method. #6784 adds a loop detector directly after it, against a July-era `run_agent.py` (line ~4471), so it needs a rebase with or without this change.
- Our earlier PR #124008 was closed by its own author in the 2026-09-30 budget batch, not by a maintainer. So this is a new leaf, not a revival over an objection.
- With no external carrier, `salvage-row` and `support-note` don't apply.
- The only alternative carrier is our own donor branch `570dc83ba6` (same author). It loses the A/B because its name-keyed check misses the default `tool_call` bridge path.

A/B line in WAVE.md row form:

| issue | carrier (author) | A/B | fold in | close after | evidence |
|---|---|---|---|---|---|
| #124008 (ours, closed) / #112639 RFC | `staging/cu-repeat-input-dedup` (fork branch `staged/cu-repeat-input-dedup`) `2f79b549ef` (Kevin Rajan) | main `aea969677c`: FAIL, both F07 cases (`['key','click']`), E25 27/1. Donor `570dc83ba6` fix: FAIL on the `tool_call-bridge` case, PASS direct, E25 28/28. Staging head: PASS 2/2 in 3/3 reps, E25 28/28. | none (the donor's 4 commits are all by the same author) | none | F07/r20261001-03, E25/r20261001-03 |

E1/E2: the CU/Jev design hold covers computer-use design work. This change is a dispatch bug fix and touches no `tools/computer_use/` file, but whether it may promote under the hold is OD-6's call (see "OD-6 scope" below). The Hermes lane parks #124008 on kvnloo/hermes-agent#316, and the handoff draft is under "Acceptance gates".

## Links

| Kind | Link | State |
|---|---|---|
| RFC | NousResearch/hermes-agent#112639 | open, ours (script-speed CU RFC) |
| Prior PR | NousResearch/hermes-agent#124008 | closed 2026-09-30T03:15:51Z in the owner's own budget batch, not a maintainer rejection |
| Older PR | NousResearch/hermes-agent#113453 | closed 2026-09-26 (wider executor design, retired) |
| Fork board | kvnloo/hermes-agent#316 | open; parks #124008. Its gate requires revalidating on current main and having one active candidate at a time. |
| Related merged | NousResearch/hermes-agent#86887 (fangliquanflq) | added the canonical-JSON key that this change keeps |
| Queue | kvnloo/hermes-agent#404 | open staged-PR queue, 39 rows; this item goes after them |

## Member branches

| Ref | SHA | Role | Rebase status |
|---|---|---|---|
| `refs/fork/fix/computer-use-repeat-input-dedup-current-main` | `570dc83ba6` | Donor of the invariant and the static tests (4 commits, +32/-4, merge-base `cb3142d325`). It was restructured, not cherry-picked. Its fix keys on `tc.function.name == "computer_use"` inside the facade, which **misses the default `tool_call` bridge path** (F07 donor arm: the bridge case stays RED). | E25 applies its full diff to `aea969677c` with `git apply -3` (28/28) |
| `refs/heads/staging/cu-repeat-input-dedup` (local, scratchpad `h.git`); fork name `staged/cu-repeat-input-dedup` | `2f79b549ef` | Staging commit: fix plus the real-path test, one commit on current main `aea969677c`. Author and committer Kevin Rajan; trailer Co-Authored-By Claude Opus 5.5. | On current main. `merge-tree` clean (tree `cb2b5fe5cf`). |
| (superseded, local only, no ref) | `402e9b0bdb` | r02 build on `234badf401`. Same diff as `2f79b549ef`; its commit body had one 96-character line. Kept as `cu-repeat-input-dedup.r02-402e9b0bdb.patch`. | Superseded by `2f79b549ef` |
| (superseded, local only, no ref) | `c9e8b2584c` | r01 build on `572e4f4fad`. Same production diff; the test used the tolerated legacy `tool_call` shape. Its r01 receipts are kept write-once. | Superseded by `402e9b0bdb` |

FACTORY §10 says a rebuild goes to `staging/<id>-v2` and that nothing is ever force-pushed. This branch was never pushed. The fix round was told to move the local ref to the rebuilt commit, so no published ref changed. The earlier commit survives as a patch file.

## First slice (committed, `2f79b549ef`)

`fix(agent): keep repeated computer_use key presses in same-turn dedup`. 3 files, +105/-19 (`git diff --numstat aea969677c 2f79b549ef`).

- `agent/tool_dispatch_helpers.py` (+33/-1):
  - `deduplicate_tool_calls()`, moved out of the facade;
  - the table `_ORDER_SIGNIFICANT_ACTIONS = frozenset({("computer_use", "key")})`;
  - `_is_order_significant()`, which reuses `_peel_bridge_call` and runs only after a duplicate is found;
  - an `__all__` entry.
- `run_agent.py` (+1/-18): the method becomes `_deduplicate_tool_calls = _forward_static("agent.tool_dispatch_helpers", "deduplicate_tool_calls")`. No tool-name branch remains: `computer_use` appears 0 times in the file (base 0, donor 2).
- `tests/agent/test_tool_call_dedup_order_significant.py` (new, +71): one test, parametrized over `tool_call-bridge` and `direct`. The bridge case uses the advertised `tool_call` shape `{"calls": [{"name": "computer_use", "arguments": ...}]}`. One assistant message carries Tab, Tab (keys reordered) plus a click on element 3, sent twice. The test asserts:
  - the backend records `key, key, click`;
  - the three tool results come back in that order;
  - both key results carry `verdict.decision == "verify_fresh_state"`;
  - the request advertised the expected form (bridge or direct).
- Unchanged: `tests/agent/test_agent_guardrails.py` (byte-identical, 26/26 pass) and `agent/turn_tool_round.py`.
- Size: `run_agent.py` goes from 1582 to 1565 lines and `agent/tool_dispatch_helpers.py` from 588 to 620.
- Prompt-cache stability: no change to the system prompt, the tool schema or past messages. The only effect is which current-turn calls are kept, and that is deterministic.

The fix is also at `cu-repeat-input-dedup.patch` (`git format-patch -1 2f79b549ef`).

## Evidence

Every experiment below is T1 or T0 and **OBSERVED**. Shared setup:

- `run_tests.sh` with `env -i`;
- `HOME=$TH` and `HERMES_HOME=$TH/.hermes`, where `$TH` is `scratchpad/testhome-sf-cu-repeat-input-dedup`;
- `HERMES_PYTHON` set to the venv interpreter, which was only executed;
- `HERMES_TEST_FILE_RETRIES=0` and `-j 2`;
- the loopback-only connect guard (`harness/_xf_t1_guard.py`, lifted from `evals/provider_fallback/probe_104260.py:11-39`) loaded with `-p`.

The current run is r03: head `2f79b549ef` on `aea969677c`. Its files:

- driver `harness/proof-r03.py`;
- probe driver `harness/probe_dryrun_r03.sh`;
- workflow scanner `harness/wfscan.py`;
- aggregator `harness/receipts_r03.py`;
- raw logs in `receipts/raw-r03/`, sanitized so they hold no absolute local paths;
- cells in `receipts/cells-r03.jsonl`. r02 (`402e9b0bdb` on `234badf401`) and r01 (`c9e8b2584c` on `572e4f4fad`) gave the same verdict in every cell and are superseded. The table reports r03.

| Experiment | Receipt | Arm | Verdict | Label | n | Counts |
|---|---|---|---|---|---|---|
| E25 (static method) | E25/r20261001-03 | main + donor test hunk | **RED** | OBSERVED | 1 | 27 passed / 1 failed (`test_repeated_computer_key_inputs_are_preserved`) |
| | | main + full donor diff | GREEN | OBSERVED | 1 | 28 passed / 0 failed |
| | | staging head + donor test hunk | GREEN | OBSERVED | 1 | 28 passed / 0 failed; head also meets the donor's static contract |
| F07 (real-path turn) | F07/r20261001-03 | base = main + new test | **RED** | OBSERVED | 3 reps | 2/2 failed in each rep; marker `assert ['key', 'click'] == ['key', 'key', 'click']` matched 2/2 |
| | | head | **GREEN** | OBSERVED | 3 reps | 2/2 passed in each rep |
| | | NEG: empty table | RED | OBSERVED | 1 | 2/2 failed |
| | | sabotage: drop bridge peel | RED (bridge only) | OBSERVED | 1 | 1/2 failed (`tool_call-bridge` only); pins that hunk |
| | | sabotage: restore old facade method | RED | OBSERVED | 1 | 2/2 failed; pins the forwarder |
| | | test sensitivity: verdict fallback returns `done` | RED | OBSERVED | 1 | 2/2 failed, `assert ['done', 'done'] == ['verify_fres..._fresh_state']`; pins the verify_fresh_state assertion |
| | | donor fix + new test | RED (bridge only) | OBSERVED | 1 | 1/2 failed (`tool_call-bridge`); the donor misses the default path |
| ADJ (9 neighbour files) | F07/r20261001-03 | main vs head | identical | OBSERVED | 1 each | 559 passed / 0 failed vs 561 passed / 0 failed (+2 new) |
| STATIC | STATIC/r20261001-03 | static checks | PASS | OBSERVED | n/a | no tool-name branch in `run_agent.py`; forwarders 32 on main (5 `_forward_static` + 27 `_forward`), 33 on head; ruff clean; seam not patched by the test; diff identical to `402e9b0bdb`; merge-tree clean; 0 of 11 push workflows match `staged/cu-repeat-input-dedup`; fork ref free; kvnloo/hermes-agent#404 has 39 rows; no external owner |
| F07P (probe dry run) | F07P/r20261001-03 | `probes/repeat_key_prevalence.py --fake` on main and head, tool_search default and off | harness works | OBSERVED | 3 turns per cell | main: 6 presses emitted, 3 kept, 3 delivered. Head: 6/6/6. Same in both tool_search modes. Scripted model, so this validates the harness only. |

ADJ attempts: in the first attempt of both ADJ cells, `run_tests.sh` killed `tests/agent/test_run_agent.py` at its 300 s per-file limit (load1 about 9 and 14, because other workers were running tests). No test failed: main logged 278 passes and head 280, each with that one file missing. Both cells were re-run once as attempt 2 with `HERMES_TEST_FILE_TIMEOUT=900`, and only attempt 2 is scored. The F07 receipt keeps both INFRA attempts under `retried_infra_attempts`, and its denominators list 15 attempts for 13 scored cells.

Safety observations, all OBSERVED:

- The new test made 0 non-loopback connect attempts.
- The neighbour files made 92 blocked attempts on port 443 on **both** arms: `test_run_agent.py` 84, `test_tool_batch_segmentation.py` 4 and `test_tool_call_guardrail_runtime.py` 4. They pass anyway. These attempts come from existing tests, not from this change.
  - Destinations were kept for the head cell only, in `receipts/raw-r03/egress-destinations-ADJ-head-a2.json` (prefixes only, sha256 `27b301e549`).
  - 84 attempts went to Cloudflare (`104.18.x.x` / `2606:4700::/32`).
  - The other 8, all from `test_run_agent.py`, went to `160.79.x.x` / `2607:6bc0::/32`.
  - r02 recorded all 92 as Cloudflare. That was not re-checked here.
- The guard covers `connect()` but not DNS lookups.
- No credential-like environment variable names were present.
- Wall time (r03): about 9–23 s per F07 cell (the first cell 22.9 s, the rest 8.7–11.1 s), about 7 s per E25 cell, and 318 s (main) and 363 s (head) per scored ADJ cell, at load1 between 6.3 and 16.1.

## Experiments queued (not run)

| Id | Tier | Gate | Exact command |
|---|---|---|---|
| F07P-T2 (repeat-key prevalence, local model) | T2 (GPU, serial, flock) | OD-1: needs a ≥64K preset. The 8K router presets and the 32K ollama models fall below `MINIMUM_CONTEXT_LENGTH`. | `for TREE in <wt@main aea969677c> <wt@staging 2f79b549ef>; do T=$(mktemp -d -p <cells-dir>); flock <gpu-lock> env -i PATH=/usr/bin:/bin HOME=$T HERMES_HOME=$T/.hermes TZ=UTC LANG=C.UTF-8 <venv-python> <staging-dir>/probes/repeat_key_prevalence.py --tree $TREE --base-url <router-url> --model <OD-1 64K preset id> --trials 10 --tool-search default --out <staging-dir>/receipts/raw-t2/F07P-T2-$(basename $TREE).json; done` |
| F07P-T3 (prevalence, frontier model) | T3 (paid, owner launches) | OD-3: owner-authored decision, $ cap, and credentials injected by the owner | Same loop with `--base-url https://openrouter.ai/api/v1 --model <owner-chosen tool-capable model> --api-key-env OPENROUTER_API_KEY --trials 10`. That is 30 turns per tree, at most 4 iterations each. Cost estimate UNVERIFIED (small). |
| E24 (verdict distribution per action type, plus a real Tab,Tab focus check) | local docker (sandbox-desktop) | OD-6 and the sandbox-desktop image (#121169) | Inside the image, on a tree = staging + `refs/fork/feat/cu-real-workload-runner-112639` (`25030eb574`) + `refs/fork/feat/cu-shadow-state-112734` (`f8ff341d1e`): `DISPLAY=:99 HERMES_YOLO_MODE=1 python -m tools.computer_use.real_workload_runner --tasks perceive,act,dialog --session-id e24 --json-out /out/e24-<arm>.json`, run on main and on staging. UNVERIFIED: the runner refuses to start without a display, cua-driver and the yolo bypass, and a Tab,Tab task still has to be added. |
| F14 guards | T1 | needs `staging/factory-replay-gate` | `xf run F14 --arm staging/cu-repeat-input-dedup` (factory executor, not built yet) |

The commands use placeholders, not local paths. `<staging-dir>` is this item's staging directory (the one holding this file). `<cells-dir>` is the factory's scratch-cell directory (`factory/xf/cells`). `<gpu-lock>` is the operator's GPU flock file, `<venv-python>` is the venv interpreter, and `<router-url>` is the local model router's OpenAI-compatible `/v1` base URL. The operator fills these in at run time.

## Gate checklist (P1-P12)

- P1 Need: PASS. RED with the marker matched on `aea969677c`, current main at the 11:05Z fetch, 3/3 reps (F07/r20261001-03). It was also RED on `234badf401` (r02) and `572e4f4fad` (r01). Re-check within 24 h of queueing.
- P2 Ownership: PENDING. No external owner, and no nearby open PR changes the dedup method (STATIC/r20261001-03). Still open: the Hermes-lane handoff on kvnloo/hermes-agent#316 (E1), and OD-6's ownership question.
- P3 Shape: PASS.
  - One invariant; 3 files, +105/-19.
  - No env var, config key or hook.
  - The facade shrinks by 17 lines.
  - The forwarder uses the facade's `agent.lazy_forward` idiom. Main `aea969677c` has 32 forwarders (5 `_forward_static` + 27 `_forward`) and this commit adds the 33rd. See Risks for the "no re-export shims" reading.
- P4 Real path: PASS. A real `AIAgent` turn runs through `run_tool_round`, and the profiler shows every seam function ran. Only the LLM endpoint and the device are fake (F07/r20261001-03). The device boundary is marked NOT_TESTED.
- P5 Proof: PENDING. RED 3/3, GREEN 3/3, per-hunk sabotage RED again (the `__all__` entry is listed as unpinned), ADJACENT identical and `flaky = false` all pass (F07/r20261001-03). The F14 standing-set guards have not run.
- P6 Numbers: N_A. The body makes no value claim.
- P7 Package: PASS.
  - One commit on `aea969677c`, author and committer Kevin Rajan, subject `fix(agent):`.
  - No contaminated paths.
  - merge-tree clean.
  - 0 of 11 push workflows in the head tree match `staged/cu-repeat-input-dedup`.
  - The fork has no `staged` or `staged/*` ref yet. Push with `--no-follow-tags` (STATIC/r20261001-03).
- P8 Freeze: PENDING. Write-once receipts and a sha256 manifest exist locally (MANIFEST-r20261001-03). The F07 and E25 r03 receipts carry every `xf.receipt.v1` field in FACTORY §9.2, including spec, changed_files, carrier_choice, learning and frozen. STATIC and F07P carry spec, changed_files, learning and frozen. They leave out the A/B-only fields (gates, ab, measurements, denominators, carrier_choice, plus arms for STATIC), which don't apply to a static check or a harness dry run. Three gaps remain:
  - the spec was **not preregistered**: FACTORY I5 wants it committed to the ledger before run 1, and this run could not write the ledger, so `spec.status = NOT_PREREGISTERED`;
  - the receipts are not on `claude/ledger`;
  - nothing is frozen to z0evals.

  r01 and r02 (and `receipts/raw/`, `receipts/raw-r02/`) contain absolute local paths. They stay local and must not be copied.
- P9 Text: PENDING. PR_BODY.md follows the template, lists what was not tested, discloses AI assistance, and has no paths, @mentions or factory jargon (self-check). The tone gate needs an independent check.
- P10 Independent read: PENDING. The phase-3 verifier read `402e9b0bdb` (same diff) and found the code and proof sound. A blind read of the exact head `2f79b549ef` is still needed.
- P11 Demand: RECORDED. No demand data; the T2/T3 prevalence probe is queued. This is a real fix, not lone infra.
- P12 Queue: PENDING. HOLD on OD-6. The row goes behind the 39 rows on kvnloo/hermes-agent#404, with a staging cap of 5 (OD-8). No slot claimed.

## Acceptance gates (selection)

| Gate | Status | Evidence |
|---|---|---|
| RED on main through turn_tool_round (2 calls become 1 press), not only through the static method | **met** | F07 base 3/3 on `aea969677c`; the profiler shows `turn_tool_round.py::run_tool_round` → `run_agent.py::_deduplicate_tool_calls` |
| GREEN with the table | **met** | F07 head 3/3 |
| Negative control: an empty table makes the test fail again | **met** | F07 neg-empty-table, RED 2/2 |
| Identical non-CU duplicates still removed; adjacent `tests/agent/test_agent_guardrails.py` unchanged | **met** | File byte-identical, 26/26 on both arms. The click duplicate is collapsed in the turn test. The ADJ set is identical. |
| The verify_fresh_state interaction is pinned by a test | **met** | Verdict assertion in the turn test; the sensitivity arm goes RED when the verdict is forced to `done` |
| No tool-name branch remains in run_agent.py | **met** | `computer_use` count in `run_agent.py` = 0 |
| The lane handoff is recorded on kvnloo/hermes-agent#316 | **not met** | Needs a GitHub write, which this run must not make. Draft text below. |
| OD-0 physical branch name | **resolved** | The fork branch is `staged/cu-repeat-input-dedup`; the legacy `refs/heads/staging` stays untouched |

Draft handoff comment for kvnloo/hermes-agent#316, for the owner or the Hermes lane to post:

> NousResearch/hermes-agent#124008 revalidated on current main (aea969677c). It is still RED through the real turn path. The original fix missed the default tool_search `tool_call` path (computer_use is deferred by default). Rebuilt as one commit on `staged/cu-repeat-input-dedup` (2f79b549ef): the helper moves out of the run_agent.py facade into agent/tool_dispatch_helpers.py, with an `_ORDER_SIGNIFICANT_ACTIONS` table and the bridge unwrap. RED, GREEN, negative control and neighbouring files all recorded. Holding for the CU design-hold decision before any origin action.

## OD-6 scope (open ambiguity)

FACTORY contradicts itself on whether E25 and F07 needed OD-6 before they could run:

- §15 OD-6 asks "may E23, E25 and F07 run, and may cu-\* branches reach PROMOTION_READY?" and lists rows 17, 18 and 27 as what it unblocks.
- §13 rows 17 and 18 (E25, F07) say "Runs. Promotion is HOLD (OD-6)".

The builder followed §13 and ran E25 and F07 with OD-6 still pending (r01, r02). This fix round re-ran them as r03. Every run was $0, T1, local and synthetic, with no origin action. E23 (row 27) and E24 have not run.

If the owner reads OD-6 as covering the runs too, these receipts are out-of-scope evidence. They should stay local and be re-run after OD-6 before any promotion. Either way, OD-6 still gates promotion.

## NOT_TESTED

- A real cua-driver or desktop delivering two presses (device boundary; the no-op backend only records calls). Queued as E24.
- How often real models emit identical key presses in one message (no demand data). Queued as F07P-T2 and F07P-T3.
- macOS and Windows. The change is pure Python with no platform branch.
- Gateway, TUI and ACP surfaces. They share `run_tool_round`, but no surface-specific test was run.
- The F14 standing guard set and the full test suite. Only targeted files were run.
- The tolerated legacy `tool_call` shape `{"name", "arguments"}` has no r03 receipt. r01 tested it (GREEN), and r02/r03 test the advertised `calls` shape. The phase-3 verifier's throwaway edge test (deleted, no receipt) also kept the legacy shape on `402e9b0bdb`.

## Origin action (owner only)

After OD-6, the kvnloo/hermes-agent#316 handoff, P8, and a CLEAN blind read of `2f79b549ef`:

1. Push: `git push --no-follow-tags <kvnloo/hermes-agent remote> 2f79b549ef40aeb31cb3af36cd92d8d12b9ba799:refs/heads/staged/cu-repeat-input-dedup`, after a fresh `ls-remote` collision check.
2. Open the PR: `gh pr create -R NousResearch/hermes-agent --head kvnloo:staged/cu-repeat-input-dedup --base main --title "fix(agent): keep repeated computer_use key presses in same-turn dedup" --body-file PR_BODY.md`.

The factory has NOT run either command.

## Next steps

1. Owner decides OD-6: whether cu-* may reach PROMOTION_READY, whether the E25/F07 runs were in scope (see "OD-6 scope"), and Hermes-lane ownership of this leaf (E1).
2. Post the handoff comment above on kvnloo/hermes-agent#316 (owner or Hermes lane).
3. Ask a different worker for a blind exact-head read of `2f79b549ef` (P10). Inputs: the diff, the repo, and the oracle "F07 RED on main / GREEN on head".
4. Close P8: commit a preregistered F07/E25 spec to `claude/ledger:factory/xf/specs/` before the next run. Copy STAGING.md, PR_BODY.md, the patch and the r03 receipts (not r01/r02) to `claude/ledger:factory/xf/staging/cu-repeat-input-dedup/`. Do not copy `harness/` or `probes/`: the drivers hard-code local paths and stay local. Freeze the cited receipts to z0evals.
5. Within 24 h of queueing: refresh main, re-run `merge-tree` plus the F07 RED/GREEN pair (about 25 s each), then push as in "Origin action".
6. Optional, gated: F07P-T2 (OD-1) or F07P-T3 (OD-3) for demand evidence; E24 under OD-6.

## Risks

- Reviewers may want repeatability declared in the tool registry (tool-effect-algebra) rather than in a dispatch table. The table is one line, so it can move into the registry later.
- The `_forward_static` line keeps `AIAgent._deduplicate_tool_calls`. It uses the facade's existing `agent.lazy_forward` idiom: main `aea969677c` has 32 such forwarders (5 `_forward_static` + 27 `_forward`), and this commit adds the 33rd. It keeps the call site and the old tests unchanged. A strict reading of "no re-export shims" could still ask for the tests to import the helper directly instead.
- Slot pressure: the 39 rows already on kvnloo/hermes-agent#404 come first. FACTORY OD-8 and T6 still say 40 rows; the board's own count is 39.

## History

| Timestamp | Status | Worker | Reason |
|---|---|---|---|
| 2026-10-01T09:21Z | HOLD | builder (Claude Code, Opus 5.5) | r01: first slice `c9e8b2584c` on `572e4f4fad`, proven at $0 |
| 2026-10-01T09:50Z | HOLD | builder (Claude Code, Opus 5.5) | r02: test switched to the advertised `tool_call` shape and the commit rebuilt on current main as `402e9b0bdb`; full matrix re-run with identical verdicts. Blocked on OD-6, E1 handoff, OD-0, P10. |
| 2026-10-01T11:36Z | HOLD | stfix round 1 (Claude Code, Opus 5.5) | Fixed the phase-3 verifier's list. Corrected numstat (+33/-1), forwarder count (32 on main, 33 with this commit) and kvnloo/hermes-agent#404 rows (39). Added FACTORY §10's Route, Evidence and Gate checklist sections, dropped the staging commit from `[[donors]]`, recorded the OD-6 ambiguity and the P8 prereg gap, and added the missing `xf.receipt.v1` fields to the receipts (spec marked NOT_PREREGISTERED). Rewrapped the 96-character commit-body line and rebuilt on `aea969677c` as `2f79b549ef` (same diff). r03 matrix re-run with identical verdicts. OD-0 resolved by the fork name `staged/cu-repeat-input-dedup`. Still blocked on OD-6, the E1 handoff, P8 and P10. |
| 2026-10-01T11:51Z | HOLD | stfix round 2 (Claude Code, Opus 5.5) | Text only; commit `2f79b549ef`, receipts and PR_BODY.md unchanged (r03 hashes re-checked, all match). Replaced the local paths and the private router address in the queued F07P-T2 command with `<cells-dir>`, `<gpu-lock>`, `<venv-python>`, `<staging-dir>` and `<router-url>`. Wrote every fork issue in full as `kvnloo/hermes-agent#N` (the queue, the two closed wave boards and the Hermes-lane board were bare in places), added the bare-`#N`-means-upstream note, and gave the handoff draft a full `NousResearch/hermes-agent#124008` link, since it will be posted on the fork. The A/B row now names the fork branch `staged/cu-repeat-input-dedup` next to the local ref. Said in Next steps that `harness/` and `probes/` stay local. Corrected the round-1 timestamp from 11:45Z to 11:36Z (the time the file was written). Re-read with `gh` just before this edit: kvnloo/hermes-agent#402 and kvnloo/hermes-agent#403 closed (posted upstream as NousResearch/hermes-agent#130139 and NousResearch/hermes-agent#130140); kvnloo/hermes-agent#404 open with 39 rows. Still blocked on OD-6, the E1 handoff, P8 and P10. |
