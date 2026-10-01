+++
xf_staging = 1
id = "cu-capture-mode-projection"
version = 3
title = "Capability-gated computer-use capture-mode projection, with Linux desktop evidence first"
branch = "staging/cu-capture-mode-projection"       # logical id; also the local branch name in the scratch mirror h.git
branch_fork = "staged/cu-capture-mode-projection"   # name it will be pushed under on kvnloo/hermes-agent (not pushed yet)
branch_physical = "local-only in the scratch mirror h.git; to be pushed to kvnloo/hermes-agent as staged/cu-capture-mode-projection. OD-0 is resolved by that rename: the fork's legacy refs/heads/staging (28790e597c) blocks refs/heads/staging/*, and ls-remote on 2026-10-01 shows no staged/* refs."
branch_sha = "3d64efc27d1247da5dd6b170a87c44ef9e653776"
naming_exception = "FACTORY §10 names a rebuild staging/<id>-vN and forbids force-push. The orchestrator fixes the local name staging/cu-capture-mode-projection and the fork name staged/cu-capture-mode-projection to the newest version, so that local ref was force-moved for v2 and v3. Nothing was ever pushed. Earlier versions are kept, never deleted: as refs/archive/staging/cu-capture-mode-projection-v1 and -v2 in h.git (outside refs/heads, so no branch push picks them up), and as patches next to this manifest."
versions = [
  { v = 1, sha = "ed420d8292349f27affb1a80fbf90e44f48c874a", ref = "refs/archive/staging/cu-capture-mode-projection-v1", base = "572e4f4fad", note = "round 0: 5 cases, +79; patch cu-capture-mode-projection.v1-ed420d8292.patch; phase-3 verdict head" },
  { v = 2, sha = "b71c7ad7e902932e5c249b92b1eea8177fb2d37f", ref = "refs/archive/staging/cu-capture-mode-projection-v2", base = "aea969677c", note = "round 1: 6 cases, +91 (adds vision-cli-refetch); patch cu-capture-mode-projection.v2-b71c7ad7e9.patch; round-1 re-verifier head" },
  { v = 3, sha = "3d64efc27d1247da5dd6b170a87c44ef9e653776", ref = "refs/heads/staging/cu-capture-mode-projection", base = "e8c97320ac", note = "round 2: 6 cases, +90; the guard asserts that no request carries a selector instead of comparing with a hard-coded dict; patch cu-capture-mode-projection.patch" },
]
superseded_shas = ["ed420d8292349f27affb1a80fbf90e44f48c874a (v1)", "b71c7ad7e902932e5c249b92b1eea8177fb2d37f (v2)"]
status = "HOLD"          # staged locally and evidenced at $0; held by OD-6 (CU design hold, FACTORY R8), E23 (Linux timing) and the kvnloo/hermes-agent#316 handoff — see Gates
route = "support-note"   # one delta comment on the external carrier NousResearch/hermes-agent#126447; matches body.kind and specs/E23.toml route_if_keep
promotion_form_selected = "core-pr"
promotion_form_effective = "salvage-support: carrier NousResearch/hermes-agent#126447 + our test-only fold-in, delivered as a support note"
feature = "cu-capture-mode-projection"
invariant = "When the live cua-driver schema advertises the selector, ax captures send include_screenshot:false and vision captures send include_accessibility_tree:false (also on the vision CLI re-fetch); som captures, and drivers whose schema lacks the selector, send neither selector; and the capture keeps the half its mode consumes."

[base]
repo = "NousResearch/hermes-agent"
sha = "e8c97320ac8691d4de92af49f98459f9ef9ddb08"
fetched_at = "2026-10-01T06:41-05:00"   # upstream main fetched into a private ref; it was still e8c97320ac
rebased_from = "aea969677c (6 commits; 0 files changed under tools/computer_use/ or tests/tools/test_computer_use*; cua_backend_capture.py blob d60bce2b4f unchanged)"

[upstream]
issues = ["NousResearch/hermes-agent#112639 (ours, RFC; ~15 self-comments, no maintainer reply: post nothing more there)"]
eval_prs = []
carrier = { pr = 126447, author = "MwC-Trexx", head = "8891ff469a6623d4b6acdb6f04a8c835d1659c2a", base = "105568c155", state = "OPEN (re-read 2026-10-01T06:42-05:00): labels type/perf comp/tools P2 (alt-glitch), 0 reviews, 1 comment (kvnloo static review 2026-09-29), last update 2026-09-29" }
competitors = [
  { pr = 113389, author = "kvnloo", head = "7e809555e6", result = "closed 2026-09-30 (owner budget self-close); breaks test_computer_use_ax_walk_bound on current main (X4 r2)", note = "our donor; Xipong posted the only Windows/Unity sample there" },
]
related = [{ pr = 126449, author = "MwC-Trexx", head = "d9348446de", note = "pm pin 0.21.0 -> 0.28.2; lets default installs use the vision skip" }]
close_after = []
demand = { score = 0, source = "no demand reader score recorded for this item" }
maintainer_signal = "none on #126447 beyond triage labels; precedent: merged AX-walk bound a85b6f9cdd (vgarlu) with follow-ups 76c3b0c735, 8b41224bfc (kshitijk4poor)"

[[donors]]
sha = "8891ff469a6623d4b6acdb6f04a8c835d1659c2a"
author = "MwC-Trexx <MwC-Trexx@users.noreply.github.com>"
role = "carrier (NousResearch/hermes-agent#126447 head, unmodified; not part of our commit)"

[[donors]]
sha = "3d64efc27d1247da5dd6b170a87c44ef9e653776"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "fold-in test (staging commit v3, on fresh main e8c97320ac)"
trailer = "Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"

[[donors]]
sha = "7e809555e6951a444626465a6d97c7e5a17ee541"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "superseded donor (refs/fork/feat/cu-capture-mode-projection-112639 = closed #113389); not used in the commit"

[ownership]
searched_at = "2026-10-01T06:17-05:00; first four queries re-run 2026-10-01T06:46-05:00 (open PRs): still only #126447 and #126449 send or name either selector"
queries = ["include_accessibility_tree", "include_screenshot", "get_window_state", "cua_backend_capture", "capture mode projection", "vision mode accessibility walk", "get_window_state slow"]
open_external = [126447, 126449]
merged_overlap = []
claimant_lanes = [127373, 127374, 127375, 127332, 127228]
hard_hold = [69, 70]
design_holds = ["CU/Jev (applies: OD-6)"]
hermes_lane_overlap = "kvnloo/hermes-agent#316 parks #113389; lane handoff pending"
verdict = "EXTERNAL -> salvage/support (no competing PR); the 2026-10-01 re-search found no other open PR sending either selector"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
receipts = [
  { id = "X1-driver-schema/r20261001-04", path = "receipts/X1-driver-schema.r20261001-04.json", sha256 = "e0a56bf7820214454183c97880c1cec050afa307bd3e4db5b016206207f0f0a9" },
  { id = "X2-ab-regression/r20261001-02", path = "receipts/X2-ab-regression.r20261001-02.json", sha256 = "48dd236051ceaf00ffca68832b7d5a5d83ef2c9df1d265c5f3198b0a07837b13", note = "fold-in v1 ed420d8292 on 572e4f4fad" },
  { id = "X2-ab-regression/r20261001-01", path = "receipts/X2-ab-regression.r20261001-01.json", sha256 = "e707c3d1549955e5e885ad975bc551c0298fbf90b656b236cbe88613466f5b8e", note = "SUPERSEDED by r20261001-02" },
  { id = "X2b-seam-sabotage/r20261001-01", path = "receipts/X2b-seam-sabotage.r20261001-01.json", sha256 = "95daf6c8daad867952f8e87d8ab1dd8de3ae866243823c738bfb4b025f06b6e7", note = "fold-in v1 ed420d8292 on 572e4f4fad" },
  { id = "X2c-carrier-foldin/r20261001-01", path = "receipts/X2c-carrier-foldin.r20261001-01.json", sha256 = "49a32e33da2aef56bf9f6bc22179f5755bb184c83184b81232f550b8b27f17f9", note = "fold-in v1 ed420d8292" },
  { id = "X3-e23-harness-selftest/r20261001-01", path = "receipts/X3-e23-harness-selftest.r20261001-01.json", sha256 = "811fdc7fb72fbf96174508799148e21c3dffcd5b54b0789a4f77c22def75f5f6", label = "MODELED (harness check only)" },
  { id = "X4-stfix-reproof/r20261001-01", path = "receipts/X4-stfix-reproof.r20261001-01.json", sha256 = "d3bcac1163c9d2a46fd0a47127009271a1a4e25a1ceb68e360ada95d9f46e0cf", note = "SUPERSEDED for the current head by r20261001-02 (it proved v2 b71c7ad7e9 on aea969677c)" },
  { id = "X4-stfix-reproof/r20261001-02", path = "receipts/X4-stfix-reproof.r20261001-02.json", sha256 = "7ac04dac77c0d3a489ba946b227709ecdfeb471ceb9a2b269f05f4e9a5009f9d", note = "current head 3d64efc27d on e8c97320ac: RED, GREEN, negative, seam, per-hunk sabotage, guard arms, adjacent" },
]
red = { test = "tests/tools/test_computer_use_capture_lane_schema.py::test_capture_skips_the_half_its_mode_discards[ax|vision|vision-cli-refetch]", main = "e8c97320ac", marker = "AssertionError: assert ([{'pid': 123, 'window_id': 456, 'session': 'hermes-...', 'max_elements': 200}] and False)", result = "3 of 6 cases fail, 3/3 reps; the 3 guard cases pass", receipt = "X4-stfix-reproof/r20261001-02" }
green = { reps = "3/3 on main+#126447 (24/24: fold-in 6, carrier 13, ax_walk_bound 5) and 3/3 on the unmodified carrier head 8891ff469a with the fold-in added (24/24)", receipt = "X4-stfix-reproof/r20261001-02" }
negative_control = { mutation = "both selector assignments in the carrier replaced by pass", result = "fold-in 3/6 fail and carrier 6/13 fail, 3/3 reps", receipt = "X4-stfix-reproof/r20261001-02" }
sabotage = { per_hunk = "8 production hunks of #126447 reverted one at a time; every hunk is caught by the fold-in or the carrier suite", unpinned_by_fold_in = ["capabilities_discovered guard in _gws_args (caught by the carrier's test_flags_fail_closed_before_capability_discovery)"], unpinned_by_carrier_suite = ["vision CLI re-fetch call site _cli_refetch(..., self._gws_args(\"vision\"), ...) (caught only by the fold-in's vision-cli-refetch case)"], unpinned_by_both = [], receipt = "X4-stfix-reproof/r20261001-02" }
guard = { asserts = "no get_window_state request in the som/0.28.2, vision/0.21.0 and ax/no-selector cases carries include_screenshot or include_accessibility_tree; the rest of the request is not pinned", unrelated_arg = "args['max_depth'] = 64 added to _gws_args: guard 0/3 fail on main+#126447 (3/3 reps, 24/24) and on main; the v2 test (hard-coded dict) fails 3/3 guard cases on the same tree", schema_blind_gate = "both supports_input_property calls -> True: guard 2/3 fail (vision/0.21.0, ax/no selector)", som_selector = "ax branch also fires for som: guard 1/3 fails (som/0.28.2)", receipt = "X4-stfix-reproof/r20261001-02" }
seam_check = { mutation = "_CuaDriverSession.supports_input_property -> False", result = "fold-in 3/6 fail; carrier 13/13 stays GREEN (it stubs the seam)", receipt = "X4-stfix-reproof/r20261001-02" }
adjacent = { identical = true, files = 23, set = "every tests/tools/test_computer_use*.py on main except the fold-in", main = "240 passed / 0 failed / 8 skipped", carrier = "240 / 0 / 8, identical per file", donor = "test_computer_use_ax_walk_bound.py 4/1 on e8c97320ac (stub lambda TypeError)", pre_existing = [], receipt = "X4-stfix-reproof/r20261001-02" }
guards = { F14 = "NOT RUN (factory Wave 0 not built)" }
flaky = false                      # every repeated cell gave the same result 3/3
quantitative = []                  # no OBSERVED latency yet; E23 queued
cache_read_ratio = { status = "N_A" }
route_scope = "n/a"
not_tested = ["capture latency/timeouts on a real Linux WM + AT-SPI desktop (E23)", "driver replies past the target check (no display in any $0 cell)", "macOS", "Windows UIA beyond the single #113389 prior", "Wayland", "cua-driver 0.25-0.27, 0.29, 0.30, and any non-x86_64 Linux build", "F14 standing regression set and the full suite", "tests/computer_use/ package"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-cu-capture-mode-projection", commit = "" }

[gates]
P1 = "PASS"       # RED on e8c97320ac (X4 r2), < 24 h
P2 = "PENDING"    # EXTERNAL owner -> support-note route; OD-6 (CU design hold) and kvnloo/hermes-agent#316 handoff open
P3 = "PASS"       # one test file, +90, no env/config, no production change of ours
P4 = "PASS"       # production _populate_capabilities -> supports_input_property -> _gws_args -> capture(); only the driver calls (MCP, CLI) faked; display/driver boundary NOT_TESTED
P5 = "PENDING"    # RED marker, GREEN 3/3, combined negative control, per-hunk sabotage (all 8 hunks caught; fold-in alone leaves the discovery guard to the carrier suite), guard arms, adjacent identical, flaky=false; F14 NOT RUN
P6 = "PENDING"    # Linux latency claim needs E23 (OBSERVED, A/A, n>=40); the fold-in itself claims no number
P7 = "PASS"       # one commit on fresh main e8c97320ac, author/trailer correct, workflow push matches 0 for staged/cu-capture-mode-projection; no push made
P8 = "PENDING"    # receipts sha256 recorded; harness/__pycache__ removed; no z0evals freeze
P9 = "PENDING"    # PR_BODY.md section A revised; needs an independent read
P10 = "PENDING"   # phase-3 verifier rejected v1; round-1 re-verifier on v2 listed 3 problems (fixed in round 2); no verifier on 3d64efc27d yet
P11 = "RECORDED"  # test-only: rides on #126447 as a fold-in, never alone (D5)
P12 = "PENDING"   # HOLD; not a queue row; staging cap / freeze sweep not run

[verification]
verifier = ""
provenance = "independent"
exact_head = "3d64efc27d1247da5dd6b170a87c44ef9e653776"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""
previous = ["phase-3 verifier on v1 ed420d8292: accept=false (8 problems; all addressed in round 1, see History)", "round-1 re-verifier on v2 b71c7ad7e9: 3 problems (guard test froze the base request; version/archive ref; harness/__pycache__); all addressed in round 2, see History"]

[merge_check]
main_sha = "e8c97320ac8691d4de92af49f98459f9ef9ddb08"
checked_at = "2026-10-01T06:52-05:00"
clean = true                       # the commit's parent is this main; merge-tree tree 7011753832
recheck = "git merge-tree --write-tree main staging/cu-capture-mode-projection"

[push]
fork_branch = "staged/cu-capture-mode-projection"
no_follow_tags = true
workflow_push_matches = 0          # push triggers of all workflows on e8c97320ac checked against staged/cu-capture-mode-projection
pushed_at = ""

[body]
path = "PR_BODY.md"
kind = "support-note"              # section A = delta comment for #126447; section B = fallback PR body
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
jargon_lint = "PASS (self-check after round 1: section A prose has no E##/X##/F##/lane/envelope; 'lane' remains only inside the file names test_computer_use_capture_lane_schema.py and the carrier's test_computer_use_cheap_lanes.py)"
privacy_scan = "PASS after round 2 (receipts, harness, raw and body scanned for home, scratch, mount and live-install paths, the local user and host names, real session ids and credentials: none left; raw path-sanitized by harness/sanitize_raw.py. The raw pytest logs keep the random hermes-<12 hex> ids that the backend under test mints in the scratch HOME; they name no real session. harness/__pycache__ deleted.)"

[queue]
board = "kvnloo/hermes-agent#404"  # staged-PR queue (39 rows); this item is not a row and is not added while HOLD
position = "after existing rows"
slot_claimed = false
closed_boards = ["kvnloo/hermes-agent#402 (salvage wave) closed 2026-10-01T07:32Z, posted upstream as NousResearch/hermes-agent#130139; this item is not in it", "kvnloo/hermes-agent#403 became NousResearch/hermes-agent#130140"]

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# Capability-gated computer-use capture-mode projection, with Linux desktop evidence first

**Promotion form.** Selected: `core-pr`. Effective: **salvage-support**, delivered on the `support-note` route.
NousResearch/hermes-agent#126447 (MwC-Trexx, opened 2026-09-28, still open) makes the same change, and its tests are
stricter than our donor's. So there is no new upstream PR. Our deliverable is a test-only fold-in for that carrier,
plus the Linux evidence the item was selected to produce, offered in one comment on the carrier thread. The staging
branch holds that fold-in as one commit on fresh main (version 3). It is local in h.git as
`staging/cu-capture-mode-projection` and will be pushed to the fork as `staged/cu-capture-mode-projection`. That
rename resolves OD-0 for this item. Versions 1 and 2 stay reachable under `refs/archive/staging/` in h.git (see
`versions` and `naming_exception` in the front matter).

**Status: HOLD.** Per FACTORY R8, cu-\* items stay HOLD until OD-6. Nothing in this item goes upstream before OD-6
is resolved and the kvnloo/hermes-agent#316 handoff is posted.

## Links

| Kind | Ref | Note |
|---|---|---|
| Carrier (external, open) | NousResearch/hermes-agent#126447 | head `8891ff469a`, base `105568c155`, 3 files +207/−10 |
| Related (external, open) | NousResearch/hermes-agent#126449 | pm pin 0.21.0 → 0.28.2 (head `d9348446de`) |
| Our closed draft | NousResearch/hermes-agent#113389 | head `7e809555e6`, closed 2026-09-30 (budget self-close) |
| RFC | NousResearch/hermes-agent#112639 | ours. About 15 self-comments, no maintainer reply. Post nothing more there. |
| Fork parking list | kvnloo/hermes-agent#316 | lists #113389; lane handoff pending |
| Fork queue | kvnloo/hermes-agent#404 | staged-PR queue, 39 rows. This item is not a row; no row while HOLD (no writes made). |
| Closed fork boards | kvnloo/hermes-agent#402, kvnloo/hermes-agent#403 | #402 (salvage wave) closed 2026-10-01T07:32Z and was posted upstream as NousResearch/hermes-agent#130139, without this item. #403 became NousResearch/hermes-agent#130140. |
| Precedent | `a85b6f9cdd` (vgarlu), `76c3b0c735`, `8b41224bfc` (kshitijk4poor) | merged AX-walk bound, same shape |

## Member branches

All values measured against main `e8c97320ac` (upstream main re-fetched 2026-10-01T06:41-05:00; no newer commit).

| Ref | SHA | Role | Merge check on `e8c97320ac` |
|---|---|---|---|
| `staging/cu-capture-mode-projection` (local, h.git; fork name `staged/cu-capture-mode-projection`) | `3d64efc27d` | staging commit v3: fold-in contract test, 1 file +90 | parent is `e8c97320ac` (tree `7011753832`) |
| `refs/archive/staging/cu-capture-mode-projection-v2` | `b71c7ad7e9` | v2 (round 1), superseded | kept, not re-measured |
| `refs/archive/staging/cu-capture-mode-projection-v1` | `ed420d8292` | v1 (round 0, phase-3 verdict head), superseded | kept, not re-measured |
| `refs/pr/126447` (fetched read-only into h.git) | `8891ff469a` | carrier | merge-tree clean (tree `3e77388e3d`); 1 ahead, 1,229 behind |
| `refs/pr/126449` | `d9348446de` | related pin bump | merge-tree clean (tree `a929dcb4ca`); 1 ahead, 1,229 behind |
| `refs/fork/feat/cu-capture-mode-projection-112639` | `7e809555e6` (on `d0288be5b3`) | superseded donor (closed #113389) | merge-tree clean (tree `61194f1ac8`); 2 ahead, 2,884 behind; fails `test_computer_use_ax_walk_bound.py` (X4 r2) |

The fold-in onto the unmodified carrier: the cherry-pick merge-tree is clean (tree `bbded16c23`), and the test passes
there 3/3 (X4 r2). The carrier plus the fold-in on main: merge-tree clean (tree `e2c1e22462`).

## Invariant

Stated in the front matter. Real call path exercised: `CuaDriverBackend.capture()` → `_capture_vision` /
`_capture_window_state` → `_gws_args(mode)` → `_CuaDriverSession.supports_input_property`, whose map is filled by
the production `_populate_capabilities` from a `tools/list` result. Only the driver calls are faked:
`session.call_tool` (the MCP boundary) and `session._call_tool_via_cli` (the CLI re-fetch subprocess). Both reply in
the Linux 0.28.2 shape.

## Re-check of the premise on current main

- **Still needed.** `_gws_args()` on `e8c97320ac` has no mode parameter and never sends either selector. Blob
  `d60bce2b4f` of `cua_backend_capture.py` is unchanged since `d0288be5b3`. From `572e4f4fad` to `e8c97320ac`, no
  file under `tools/computer_use/` or `tests/tools/test_computer_use*` changed.
- **Already being done by someone else.** #126447 implements it with 13 stub-based tests. kvnloo left a supportive
  static review there on 2026-09-29. Adjusted per E3 to salvage/support. A 2026-10-01 re-search found no other open
  PR that sends either selector.
- **Mechanism exists on Linux.** In the `cua-driver-rs-v0.28.2` source (`platform-linux/src/tools/impl_.rs`
  ~741–860), `include_accessibility_tree:false` skips `walk_tree_bounded`, and `include_screenshot:false` skips
  `screenshot_dispatch_with_pid`. `structuredContent.window_title` comes from window metadata either way.

## Route and carrier choice

Route: `support-note` (one delta comment on the carrier thread). FACTORY §10 pairs `salvage-row` with a wave-row
body, and the salvage-wave board this would have joined (kvnloo/hermes-agent#402) is closed. Our body is a comment
for #126447, so `support-note` is the matching route, as in `specs/E23.toml`.

Carrier: **#126447 wins** (X4 r2 on `e8c97320ac` unless noted).
- main: RED, 3 of 6 fold-in cases.
- Carrier: GREEN 3/3 on its own 13 tests, `ax_walk_bound`'s 5 and the fold-in's 6. Adjacent: 23 files, 240 = 240.
- Donor (closed #113389): GREEN on the v1 fold-in, but 3 carrier tests fail (X2, on `572e4f4fad`). It breaks
  `test_computer_use_ax_walk_bound.py::TestAxWalkBound::test_configured_value_reaches_the_driver_args` on
  `e8c97320ac` (TypeError: the stub's `_capture_window_state` lambda takes no mode).
- Fold-in: the only suite that notices a broken capability seam, and the only one that pins the vision CLI re-fetch
  call site.

## Evidence

| Experiment | Receipt | Verdict | Label | n | Numbers |
|---|---|---|---|---|---|
| X1 driver schema probe: production session against 5 real Linux x86_64 release binaries, bwrap, no network | `receipts/X1-driver-schema.r20261001-04.json` | KEEP | OBSERVED | 5 versions | See the schema table below. 60 tools each. All 5 declare `additionalProperties:false`, yet a bogus property gets the same stale-target error as a clean request. 0 egress attempts. |
| X2 A/B regression (v1 fold-in `ed420d8292`, main `572e4f4fad`): main / +#126447 / +donor / two negative controls; rival suites cross-applied | `receipts/X2-ab-regression.r20261001-02.json` | KEEP (superseded for the current head by X4) | OBSERVED | 3 reps × 5 arms + 3 adjacent runs | main: fold-in 2 failed / 5 (18 failed across the 3 suites). Carrier: 24/24 ×3. Donor: 21/24 ×3. neg-carrier: fold-in 2/5 failed ×3. neg-donor: fold-in 2/5 failed ×3. Adjacent (11 files): 158/0, 158/0, 157/1. |
| X2 r1 (superseded) | `receipts/X2-ab-regression.r20261001-01.json` | SUPERSEDED | OBSERVED | same | The first fake used macOS-shaped markdown; fixed to the Linux shape |
| X2b seam sabotage (v1 fold-in) | `receipts/X2b-seam-sabotage.r20261001-01.json` | KEEP (repeated in X4) | OBSERVED | 3 reps | Fold-in RED 2/5; carrier 13/13 GREEN; donor 6/6 GREEN |
| X2c v1 fold-in on the unmodified carrier head `8891ff469a` | `receipts/X2c-carrier-foldin.r20261001-01.json` | KEEP (repeated in X4) | OBSERVED | 3 reps + adjacent | 23/23 ×3 (fold-in 5, carrier 13, ax_walk_bound 5); adjacent 153/0 (10 files) |
| X3 E23 harness self-test, fake driver (tree 30 ms, grab 10 ms) + wrapper self-test against the local 0.28.2 binary | `receipts/X3-e23-harness-selftest.r20261001-01.json` | KEEP (harness ready) | **MODELED**; wrapper part OBSERVED | 20 per cell | ax −10.12 ms, vision −29.99 ms (both beyond the A/A bound); som −0.08 ms (inside it). Wrapper: contract ready 0.28.2, invocation rewritten to the wrapper `mcp --no-overlay`, gate sees both selectors |
| X4 r1: re-proof of v2 `b71c7ad7e9` on main `aea969677c` | `receipts/X4-stfix-reproof.r20261001-01.json` | SUPERSEDED for the current head by X4 r2 | OBSERVED | 3 reps per proof arm, 1 per mutant | Same numbers as X4 r2 on every shared arm. Its guard compared the request with a hard-coded dict (round-1 re-verifier finding). |
| X4 r2: re-proof of the current head `3d64efc27d` on main `e8c97320ac`: RED, GREEN on main+#126447 and on the carrier head, negative control, seam sabotage, per-hunk sabotage, guard arms, donor, adjacent | `receipts/X4-stfix-reproof.r20261001-02.json` | KEEP | OBSERVED | 3 reps per proof arm, 1 per mutant | main: fold-in 3/6 failed ×3. main+#126447: 24/24 ×3. Carrier head + fold-in: 24/24 ×3. Negative: fold-in 3/6 and carrier 6/13 failed ×3. Seam: fold-in 3/6 failed, carrier 13/13 ×3. Unrelated `max_depth` argument: 24/24 ×3 (the v2 test fails its 3 guard cases there). Guard mutants: schema-blind gate 2/3 guard cases fail, som-selector 1/3. Donor: ax_walk_bound 4/1. Adjacent (23 files): 240/0/8 skipped on both arms, identical per file. |

### Per-hunk sabotage of #126447 (X4 r2; identical to X4 r1)

Each row reverts one production hunk of the carrier on main + #126447 and runs the fold-in (6 cases), the carrier's
`test_computer_use_cheap_lanes.py` (13) and `test_computer_use_ax_walk_bound.py` (5).

| Hunk reverted | Fold-in | Carrier suite |
|---|---|---|
| `_tree_and_title`: `structuredContent.window_title` fallback | 2 fail (vision, vision-cli-refetch) | 2 fail |
| `_gws_args`: `capabilities_discovered` guard | 0 fail (not pinned) | 1 fail (`test_flags_fail_closed_before_capability_discovery`) |
| `_gws_args`: vision branch sets `include_accessibility_tree=False` | 2 fail | 3 fail |
| `_gws_args`: ax branch sets `include_screenshot=False` | 1 fail | 3 fail |
| `_capture_vision`: MCP call uses `_gws_args("vision")` | 2 fail | 1 fail |
| `_capture_vision`: CLI re-fetch uses `_gws_args("vision")` | 1 fail (vision-cli-refetch) | **0 fail (not pinned)** |
| `_capture_window_state`: `_fetch_or_refetch` uses `_gws_args(mode)` | 1 fail | 1 fail |
| `capture()`: passes `mode` to `_capture_window_state` | 1 fail | 1 fail |

Every hunk is pinned by at least one suite. Unpinned by the fold-in alone: the discovery guard. With the real session
that guard does not change the request, because `supports_input_property` reads an empty schema map before
discovery. Unpinned by the carrier's suite alone: the vision CLI re-fetch call site. The round-0 fold-in also missed
that call site; round 1 added the `vision-cli-refetch` case for it.

### Guard test shape (round 2, X4 r2)

`test_som_and_drivers_without_the_selector_keep_the_full_request` covers som on the 0.28.2 schema, vision on 0.21.0
and ax with no selector. It now asserts that no `get_window_state` request carries `include_screenshot` or
`include_accessibility_tree`. Up to v2 it compared each request with a hard-coded `{pid, window_id, session}` dict,
and it had to patch `_cua_configured_ax_max_elements` to 0 to keep that dict stable. Upstream AGENTS.md calls that a
change-detector. The rest of the request is no longer pinned, and the patch is gone: the requests now carry the
default `max_elements: 200`.

| Arm (main + #126447 unless noted) | Guard cases that fail |
|---|---|
| Unrelated `args["max_depth"] = 64` added to `_gws_args` | 0 of 3, 3/3 reps (24/24). Also 0 of 3 on main. |
| Same tree, run with the v2 test file | 3 of 3. This reproduces the round-1 finding. |
| Gate ignores the schema (both `supports_input_property` calls → `True`) | 2 of 3: vision/0.21.0 and ax/no selector |
| The ax branch also fires for som | 1 of 3: som/0.28.2 |

The carrier's own tests also catch both guard mutants (2 tests each), so the guard is not the only coverage there.

What the Linux x86_64 release binaries advertise, read via `tools/list` through Hermes' own session (OBSERVED, X1):

| cua-driver | binary sha256 (prefix) | `include_screenshot` | `include_accessibility_tree` | `screenshot` tool |
|---|---|---|---|---|
| 0.21.0 (`pm/lock.json` pin) | `43d926a1` | yes | no | no |
| 0.22.2 | `574c6c4b` | yes | no | no |
| 0.23.2 | `2aaad67b` | yes | no | no |
| 0.24.0 | `a033485d` | yes | yes | no |
| 0.28.2 (`sandbox-desktop.Dockerfile` pin) | `3739101d` | yes | yes | no |

Consequences, for these five Linux x86_64 releases only:
- Default Linux host installs (0.21.0 pin) get the ax skip only, until #126449 lands.
- The vision skip needs 0.24.0 or later; the sandbox image has it.
- None of the five has a `screenshot` tool, so on them vision on main always goes through `get_window_state` and
  always walks AT-SPI.
- Observation for the carrier's description: Linux AT-SPI markdown has no `AXWindow "…"` line. #126447's
  `_tree_and_title` fallback therefore also fills `window_title` for som and ax on Linux, where it is `""` on main.
  The som request still carries no selector; this is a CaptureResult change.

## Experiments queued (not run)

The harness scripts take their local paths from environment variables (see each script's usage line). The commands
below are relative to this staging directory.

| Id | Tier / lane | Why not now | Exact command |
|---|---|---|---|
| E23 (spec `specs/E23.toml`, rev 2) | local docker (no GPU, no paid), cpu-quiet | OD-6 (CU design hold) not granted. The image is not present locally, and building it needs network (base image, apt, the cua tarball). | `SCRATCH=<dir holding h.git> E23_WORKTREES=<scratch dir> HERMES_PYTHON=<venv python> bash harness/e23_run.sh <main sha at claim> raw/e23-r1` (run only when load1 < 4) |
| E23-pin021 | same | same; measures what default host installs get (ax skip only) | `CUA_DRIVER_VERSION=0.21.0 SCRATCH=… E23_WORKTREES=… HERMES_PYTHON=… bash harness/e23_run.sh <main sha> raw/e23-pin021-r1` |
| F14 | factory Wave 0 | the standing regression set is not built | none yet; P5 stays PENDING until it runs |
| T2 (local GPU) | none | no model in the loop | none |
| T3 (paid) | none | no provider in the loop | none |

After E23: `python3 harness/e23_summarize.py raw/e23-r1/rows.jsonl --base main --aa main-aa --candidates c126447`
(already called by `e23_run.sh`). Then write a new X-numbered receipt.

## Acceptance gates (from selection.json)

| Gate | Status | Basis |
|---|---|---|
| E23 shows a capture-ms or timeout reduction in ax/vision beyond run-to-run noise on a real WM + AT-SPI desktop (n ≥ 40 per arm, median and p95) | **pending** | Harness built and self-tested (X3, MODELED); run held by OD-6 and the image build |
| som mode and the older-driver path are byte-identical (capability-gate test) | **met** | Fold-in `test_som_and_drivers_without_the_selector_keep_the_full_request` (som/0.28.2 schema, vision/0.21.0 schema, ax/no selector) is GREEN on main and on main + #126447 (X4 r2). It asserts that those requests carry neither selector. The selectors are the only keys #126447 adds, so the request matches main's, but the test does not freeze the rest of it (AGENTS.md: no change-detectors). The schemas are the real ones (X1). |
| A real-seam test against the installed driver, or the boundary explicitly marked NOT_TESTED | **met** | X1 drives the production `_CuaDriverSession` against the installed 0.21.0–0.28.2 binaries. The fold-in exercises the production seam (X4 r2 seam sabotage proves it). Capturing a real window is marked NOT_TESTED (no display). |
| Lane handoff on kvnloo/hermes-agent#316 | **pending** | No GitHub writes allowed from this builder |
| Owner confirms under PLAN §10F that this invariant is outside the CU design hold | **pending** | OD-6 |

## Gate checklist (P1–P12)

- **P1 PASS.** RED on `e8c97320ac`, 3 of 6 cases, 3/3 reps (X4 r2).
- **P2 PENDING.** External owner, so the support-note route was taken. OD-6 and the kvnloo/hermes-agent#316 handoff
  are open. Claimant lanes and hard holds don't apply.
- **P3 PASS.** One test file, 90 lines. No env vars or config. No production code of ours.
- **P4 PASS.** Production seam, with only the driver calls faked (X4 r2 seam sabotage). Device and display boundary:
  NOT_TESTED.
- **P5 PENDING.** Met: RED marker, GREEN 3/3 (X4 r2), combined negative control re-RED, per-hunk sabotage with the
  unpinned hunks listed above, the guard arms (unrelated argument ignored, both guard mutants caught), adjacent
  identical (23 files), `flaky = false`. Not met: F14 guards, which have not run.
- **P6 PENDING.** E23.
- **P7 PASS.** One commit on fresh main `e8c97320ac`. Author Kevin Rajan plus the Claude trailer. Workflow push
  matches for `staged/cu-capture-mode-projection` = 0. Nothing pushed.
- **P8 PENDING.** Receipts are hashed but not frozen to z0evals. `harness/__pycache__/` was deleted before any
  freeze.
- **P9 PENDING.** `PR_BODY.md` revised in rounds 1 and 2 (claims scoped, jargon removed, guard wording matches the
  test). Needs an independent read.
- **P10 PENDING.** The phase-3 verifier did not accept v1 (`ed420d8292`). The round-1 re-verifier listed 3 problems on
  v2 (`b71c7ad7e9`), fixed in round 2. No verifier on `3d64efc27d` yet.
- **P11 RECORDED.** Test-only, so it rides on #126447 and never goes alone.
- **P12 PENDING.** HOLD, so it is not a row on kvnloo/hermes-agent#404. Staging cap and freeze sweep not run.

## NOT_TESTED

- Capture latency, timeouts and AT-SPI walk cost on a real Linux desktop. This is the item's purpose (E23).
- Any driver reply past the target check: no display existed in any $0 cell. Bogus and unadvertised properties
  produced the same stale-target error, so whether a driver rejects an unknown property after that check is unknown.
- macOS (only the #126447 author's M5 Max numbers, PRIOR) and Windows UIA (one Xipong sample on #113389, PRIOR).
- Wayland compositors, where `screenshot_error` / surface identity is unproven.
- cua-driver 0.25.x–0.27.x, 0.29.x and 0.30.x (not present as release directories on this host), and any Linux
  build other than x86_64.
- The factory standing regression set (F14), the full test suite, and the `tests/computer_use/` package. Run: all 23
  `tests/tools/test_computer_use*.py` files plus the fold-in and the carrier's two contract files.
- Model-visible effects: ax width/height become 0×0 when the screenshot is skipped. That is the same shape main
  already produces on Wayland's tree-only path, and was not evaluated with a model.

## Origin action (owner only)

The smallest ask: one comment on NousResearch/hermes-agent#126447 using `PR_BODY.md` section A, with
`cu-capture-mode-projection.patch` (sha256 `697a4f6c…`) offered as a fold-in.

Timing: not while the item is HOLD. Section A can go only after both of these:
1. OD-6 is resolved and says this invariant is outside the CU design hold.
2. The kvnloo/hermes-agent#316 handoff is posted.

Once both hold, section A can go without the timing table, since it makes no latency claim, or after E23 with the
table. Before posting, re-run the merge-tree and the X4 arms on the newest main and carrier head. Do not open a new
PR. Do not comment on #112639. Fallback: section B, only if #126447 closes unmerged.

## Next steps

1. **Owner:** OD-6 (may E23 run; is this invariant outside the CU design hold, per PLAN §10F). OD-0 needs no
   decision for this item: the fork push name is `staged/cu-capture-mode-projection`.
2. **Lane:** post the handoff on kvnloo/hermes-agent#316, noting that #113389 is superseded by carrier #126447.
3. **Builder:**
   - When OD-6 is granted and the host is quiet, run E23, then E23-pin021.
   - Add the receipt.
   - If E23 shows a reduction beyond the A/A bound, put the table into section A.
   - If not, record the null and set the status to KILLED for the latency claim. The fold-in test can still be offered.
   - Run F14 when Wave 0 exists (P5).
4. **Verifier:** blind exact-head read of `3d64efc27d` (patch plus oracle: RED on main, GREEN on `8891ff469a`,
   seam sabotage RED, the CLI re-fetch mutant RED, the guard GREEN with an unrelated `_gws_args` argument and RED
   with a schema-blind gate).
5. **Before any origin action:** re-run the merge-tree and X4 on the newest main and carrier head (head drift
   invalidates).

## History

- 2026-10-01T04:18-05:00 | HOLD | builder (Claude Code, Opus 5.5) |
  - Staged the fold-in `ed420d8292`; ran X1, X2 (r1→r2), X2b, X2c and X3 at $0; queued E23.
  - Route adjusted from core-pr to salvage-support because of open external #126447.
  - Worktree removed.
- 2026-10-01T06:26-05:00 | HOLD | staging fix round 1 (Claude Code, Opus 5.5) | addressed the 8 phase-3 problems:
  - Board: #402 is closed (posted upstream as NousResearch/hermes-agent#130139, without this item). The queue is now
    kvnloo/hermes-agent#404 (not a row while HOLD). The wave-row form was removed from `PR_BODY.md`.
  - P5: ran per-hunk sabotage (X4). The vision CLI re-fetch call site was unpinned by the fold-in and by the
    carrier's 13 tests. The fold-in gained a `vision-cli-refetch` case (it fakes the CLI transport as well), so the
    commit was amended, rebased onto `aea969677c` as `b71c7ad7e9` (+91), and the local branch was forced to it.
    P5 is now PENDING: F14 has not run. Unpinned hunks are listed above.
  - Jargon: section A no longer says "lane"; the `jargon_lint` line now states what was checked.
  - HOLD: section A is conditioned on OD-6 and the #316 handoff in `PR_BODY.md` and in Origin action.
  - Member branches: every value re-measured on `aea969677c`, and the column says so.
  - Section A claims scoped to the five Linux x86_64 releases tested. "Not dodging a hard error" dropped. Adjacent
    re-measured over all 23 `tests/tools/test_computer_use*.py` files (240 passed, 8 skipped on both arms).
  - Route: `support-note`, matching `body.kind` and `specs/E23.toml`.
  - Privacy: harness scripts now take local paths from environment variables; receipts re-pin those hashes, keep the
    as-run hashes, and drop the host name and live-install path; `raw/` sanitized by `harness/sanitize_raw.py`.
  - Branch name on the fork: `staged/cu-capture-mode-projection` (OD-0 resolved by the rename).
  - Worktree and test home removed.
- 2026-10-01T06:55-05:00 | HOLD | staging fix round 2 (Claude Code, Opus 5.5) | addressed the 3 round-1 re-verifier
  problems:
  - Test shape: the guard test compared the request with a hard-coded dict and patched
    `_cua_configured_ax_max_elements` to keep it stable, which AGENTS.md rejects as a change-detector. It now asserts
    that no request carries either selector. The patch is dropped and the unused import removed. The v2 commit was
    cherry-picked onto `e8c97320ac`, amended as `3d64efc27d` (+90; same 2 tests and 6 cases; commit message
    reworded to match), and the local branch was forced to it. X4 r2 re-ran every X4 arm and added the guard arms.
    The unrelated `max_depth` argument leaves the new guard GREEN and fails the v2 guard 3 of 3. Patch re-hashed.
  - Version: `version = 3`, plus the `versions` list and a `naming_exception` (FACTORY §10 wants `-vN` branches and no
    force; the orchestrator fixes the unsuffixed name). v1 `ed420d8292` and v2 `b71c7ad7e9` are kept under
    `refs/archive/staging/` in h.git, and the v2 patch is kept as `cu-capture-mode-projection.v2-b71c7ad7e9.patch`.
  - Hygiene: deleted `harness/__pycache__/`. The round-2 scripts run with `python3 -B` /
    `PYTHONDONTWRITEBYTECODE=1`, and no `__pycache__` is left.
  - Re-measured on `e8c97320ac`: member branches, merge trees, workflow push matches, carrier state, ownership search.
  - Worktree and test home removed.

## Files

| File | sha256 |
|---|---|
| `cu-capture-mode-projection.patch` (v3 `3d64efc27d`) | `697a4f6c35cc8e2131312f35e578c7ab3c2ac0e80d1eec0f292917b7ef2fee93` |
| `cu-capture-mode-projection.v2-b71c7ad7e9.patch` (round 1, superseded) | `82ab7ebc8a3b0ac70a89334e99780e63d6a3d5a57927d16360f8709572af737b` |
| `cu-capture-mode-projection.v1-ed420d8292.patch` (round 0, superseded) | `784bfaaf589730ff19b2ad4299cbadabee00328f9416e118ac51adc8a4cb0c64` |
| `specs/E23.toml` | `2fcc388296342fe22f2e9ea94fd15c8c2e68f162d5f245dbcc545f6ae28d3898` |
| `harness/` | per-file hashes are inside each receipt's `inputs.harness` (as-run hashes in `inputs.harness_as_run` where round 1 sanitized a script; the round-2 scripts `run_stfix_r2.sh` and `make_x4_receipt_r2.py` are pinned in X4 r2). Sources only: no `__pycache__` or `.pyc`. |
| `raw/` | run outputs, path-sanitized by `harness/sanitize_raw.py` (local paths and the local user name replaced with placeholders such as `<worktree>`, `<HERMES_PYTHON>`, `~`, `pytest-of-<user>`) |
