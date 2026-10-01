# cu-capture-mode-projection: upstream text (owner use only, nothing here has been posted)

This item is **not a new upstream PR**. NousResearch/hermes-agent#126447 (MwC-Trexx, open since 2026-09-28) already
makes this exact change, and our own NousResearch/hermes-agent#113389 is closed. Our part is a fold-in contract test
plus Linux evidence. The sections below are in priority order:

- **A**: the delta comment for #126447. **Not to be posted while the item is HOLD.** It can go only after OD-6 is
  resolved (this invariant is outside the CU design hold) and the kvnloo/hermes-agent#316 handoff is posted. Then it
  can go with the test and schema facts alone, or later with the Linux timing table added.
- **B**: a fallback PR body. Use it only if #126447 closes without merging and the owner decides to carry the change.

There is no wave-row form any more. The salvage-wave board it targeted, kvnloo/hermes-agent#402, closed on
2026-10-01 and was posted upstream as NousResearch/hermes-agent#130139 without this item. The fork queue is
kvnloo/hermes-agent#404, and this item gets no row there while it is HOLD. The fold-in branch will be on the fork as
`staged/cu-capture-mode-projection`.

---

## A. Delta comment for NousResearch/hermes-agent#126447 (one comment, no @mentions)

> Follow-up to my earlier static review, with two things that might be useful here.
>
> **1. A contract test that goes through the real capability seam.** The tests in this PR and in my older #113389 both
> stub `supports_input_property`. I made `_CuaDriverSession.supports_input_property` return `False` on this branch,
> and all 13 tests here still passed. This one fails in that case:
> `tests/tools/test_computer_use_capture_lane_schema.py` (2 tests, 6 cases, 90 lines, test-only). It fills the
> capability map through `_CuaDriverSession._populate_capabilities` using the `get_window_state` property names that
> the Linux release binaries list. Only the driver calls are faked (the MCP call and the CLI re-fetch), and they
> answer the way the Linux driver does. It checks two things:
> - ax sends `include_screenshot: false` and vision sends `include_accessibility_tree: false`, and the capture keeps
>   what the mode uses: elements for ax; pixels plus `window_title` for vision.
> - som, and a schema that lacks the selector, send neither selector. It doesn't pin the rest of the request, so a
>   new default argument in `_gws_args` won't break it.
>
> It also covers a second call path. When MCP returns no image, vision re-fetches over the CLI with
> `self._gws_args("vision")`. If that call site goes back to `self._gws_args()`, the 13 tests here still pass, and the
> `vision-cli-refetch` case fails. I reverted each production hunk of this PR one at a time, and that call site was
> the only one none of the 13 tests noticed.
>
> It fails on main and passes on this head (`8891ff469a`) 3/3. It also passes on current main with this PR merged in
> (`merge-tree` clean). All 23 `tests/tools/test_computer_use*.py` files give the same result with this PR merged as
> on main: 240 passed, 8 skipped. Patch: <attach `cu-capture-mode-projection.patch`, or offer to push it as a commit
> on this branch>.
>
> **2. What five Linux release binaries advertise.** Read via `tools/list` through Hermes' own session, x86_64 builds
> only:
>
> | cua-driver | `include_screenshot` | `include_accessibility_tree` | standalone `screenshot` tool |
> |---|---|---|---|
> | 0.21.0 (current `pm/lock.json` pin) | yes | no | no |
> | 0.22.2, 0.23.2 | yes | no | no |
> | 0.24.0, 0.28.2 | yes | yes | no |
>
> So on a default Linux install the ax skip takes effect as soon as this lands. The vision skip waits for the pin bump
> in #126449, or for the `hermes-sandbox:desktop` image, which already ships 0.28.2. None of these five has a
> standalone `screenshot` tool, so with them vision on main always goes through `get_window_state` and walks AT-SPI.
> All five declare `additionalProperties: false`, but none rejected an unknown property before its target check. I had
> no display, so I couldn't see what happens after that check. Either way, the gate here means older drivers get
> exactly today's request.
>
> One side effect, for the description: on Linux the AT-SPI tree markdown has no `AXWindow "…"` line. So the
> `structuredContent.window_title` fallback in `_tree_and_title` also fills `window_title` for som and ax captures,
> where it is empty on main today. That looks like an improvement (it feeds the screenshot-dedup key), but it is a
> visible change for som and ax too, not only for the two skips.
>
> Not measured yet: capture latency on a Linux desktop with a real AT-SPI tree. The bare-Xvfb numbers I had earlier
> are null by construction. I have a timing harness ready for the sandbox-desktop image and can post median/p95 per
> mode if that would help.
>
> AI assistance (Claude Code) was used to write the test and the probe; I reviewed and ran them.

If E23 has run, append its table in place of the "Not measured yet" paragraph, labelled with the image id, the driver
version, n per arm and the A/A bound. If E23 shows nothing beyond noise, say so in one sentence and drop the offer.
Before posting, re-check that the head is still `8891ff469a` and re-run the counts above on the newest main.

---

## B. Fallback PR body (only if #126447 closes unmerged; NOT to be opened while it is open)

Before using it, the branch must gain #126447's production change as its own commit, authored by MwC-Trexx or
carrying `Co-authored-by: MwC-Trexx <MwC-Trexx@users.noreply.github.com>`. Re-run the full proof on the new head.

## What does this PR do?

`computer_use` asks cua-driver for the full `get_window_state` result on every capture, then throws half of it away.
vision discards the accessibility tree (the AT-SPI/AX/UIA walk), and ax discards the screenshot. When the live
`tools/list` schema advertises the matching selector, this sends `include_accessibility_tree: false` for vision and
`include_screenshot: false` for ax, on the MCP call and on the CLI re-fetch alike. som, and drivers that don't
advertise a selector, send neither selector, so their request is unchanged. When the tree is skipped, the window
title falls back to `structuredContent.window_title`.

The production change is MwC-Trexx's from #126447 (credited as co-author). This PR adds a contract test that fills
the capability map through the real `_CuaDriverSession._populate_capabilities` instead of a stubbed session.

## Related Issue

Refs #126447, #113389, #112639

## Type of Change

- [x] ✨ New feature (non-breaking change that adds functionality)
- [x] ✅ Tests (adding or improving test coverage)

## Changes Made

- `tools/computer_use/cua_backend_capture.py`: `_gws_args(mode)` adds the advertised selector per mode; the title
  falls back to `structuredContent.window_title` when there is no tree (from #126447)
- `tests/tools/test_computer_use_cheap_lanes.py`, `tests/tools/test_computer_use_ax_walk_bound.py` (from #126447)
- `tests/tools/test_computer_use_capture_lane_schema.py`: 2 contract tests (6 cases) on the real capability seam,
  including the vision CLI re-fetch

## How to Test

1. `scripts/run_tests.sh tests/tools/test_computer_use_capture_lane_schema.py -q`: fails on main (the request is sent
   without either selector) and passes on this branch.
2. `scripts/run_tests.sh tests/tools/test_computer_use_cheap_lanes.py tests/tools/test_computer_use_ax_walk_bound.py -q`
3. Sibling suites: every `tests/tools/test_computer_use*.py` file; the pass set is the same as on main.

## Checklist

### Code

- [x] I've read the Contributing Guide
- [x] My commit messages follow Conventional Commits
- [x] I searched for existing PRs (this exists only because #126447 closed)
- [x] My PR contains only changes related to this feature
- [ ] I've run `pytest tests/ -q` and all tests pass (targeted computer_use files only; full suite not run)
- [x] I've added tests for my changes
- [x] I've tested on my platform: Linux x86_64 (unit level; real-desktop timing: see below)

### Documentation & Housekeeping

- [x] Documentation: N/A (no user-facing knob)
- [x] `cli-config.yaml.example`: N/A (no config keys)
- [x] `CONTRIBUTING.md` / `AGENTS.md`: N/A
- [x] Cross-platform: the selector is gated on the live schema, so macOS, Windows and Linux each take it only when
      their driver advertises it
- [x] Tool descriptions/schemas: N/A (the model-facing schema is unchanged)

## Screenshots / Logs

- Five Linux x86_64 release binaries, `tools/list` through Hermes' session: 0.21.0, 0.22.2 and 0.23.2 advertise
  `include_screenshot` only; 0.24.0 and 0.28.2 advertise both selectors; none of the five has a standalone
  `screenshot` tool.
- Not tested: capture latency on a real Linux desktop (pending), macOS, Windows. A single Windows/Unity sample on
  #113389 showed vision recovering from a 4 s UIA timeout (3.942 s timeout vs 2.029 s valid PNG). That is one
  sample, reported by Xipong, not a benchmark.

AI assistance (Claude Code) was used for the test and the probe harness; disclosed per repository policy.
