# Hermes × Tern: OMP interaction parity

**Scope:** Match OMP's Tern-visible *interaction and presentation* contracts
while Hermes retains its own gateway, providers, tools, session authority and
Ink fallback. Matching OMP's internal agent architecture is **not** the goal.

**Integration branch:** `feat/tern-omp-parity` → downstream draft
[`kvnloo/hermes-agent#508`](https://github.com/kvnloo/hermes-agent/pull/508);
target `preview/tern-frontend`.
Coordination: [#477](https://github.com/kvnloo/hermes-agent/issues/477);
promotion queue: [#447](https://github.com/kvnloo/hermes-agent/issues/447).

## Parity ledger

| UX contract | State | Evidence / next gate |
| --- | --- | --- |
| Native Tern protocol, semantic `omp.*` views and Ink fallback | Existing preview | Handshake/terminal E2E required |
| Composer editing/undo/send, slash completion, prompt queue | Existing preview | Native-send and session queue tests; verify Tern IME and selection |
| Markdown, thinking, tool cards, native approvals, model/session picker | Existing preview | UI tests; real Tern comparison |
| Splash, theme palette, reduce-motion entry | Existing preview | Splash tests and host visuals |
| Native Settings across profile defaults and session pins | **Integrated** | Existing Settings Vitest + Python contract tests, not rerun here |
| Keyed notices, sticky/TTL expiry and dismiss | **Integrated** | `attention.test.ts`, not rerun |
| Pane visibility, bounded deferred notices and turn/task catch-up | **Integrated** | Reducer tests; real `visible` event / host timing required |
| Retry only gateway-confirmed retryable text failures | **Integrated** | `retry.test.ts`; test stale action, queue and image gating on host |
| Parent/child agent cards and delegation-id isolation | **Integrated** | Transcript/tools tests; nested real-gateway trace required |
| Focus mode and configurable off/new/all/verbose tool-progress projections | **Missing** | Define renderer-only preference semantics with thefullctx before coding |
| ACK-level frame pacing vs SDK coalescing | **Unproven** | Compare `exp/tsp-frame-pump`; only merge with real host E2E measurements |
| Full OMP/Tern visual equivalence (keyboard/pointer/accessibility) | **Unproven** | Captured TSP traces + screenshots on matched Tern/SDK versions |
| Browser/host interaction and reconnect across screen lifecycle | **Unproven** | Native E2E, including stale overlay and out-of-order RPCs |

**State definitions:** “Integrated” means source code and tests have been
committed on this branch, **not** that the tests passed. No host-measured
FPS, render-latency or complete parity claim exists yet.

## Mandatory local gates

From the checkout root, with the repo's pinned toolchain:

```sh
npm ci
npm --prefix ui-tsp run check
npm --prefix ui-tsp run build
python -m pm.build_env --source . --out .venv --group dev --group test
HERMES_PYTHON=.venv/bin/python scripts/run_tests.sh tests/tui_gateway/test_settings_contract.py
```

Follow root `AGENTS.md`, `tui_gateway/AGENTS.md`, `tests/AGENTS.md`.
Never run bare `pytest` for Hermes suite. If the test environment already
exists, use the prepared interpreter; don't overwrite it accidentally.

## Native Tern acceptance checklist

1. In Tern, open `/settings`, change a nonsecret profile default, confirm
   canonical readback; separately change live model/effort. Confirm no
   cross-profile write and no leaked saved credential.
2. Verify Settings close/replace retains draft and caret, modal keyboard
   focus, native send of multiline/emoji, and session switches during
   pending RPC responses.
3. Open a busy turn, hide the pane, trigger a keyed ephemeral notification
   and complete the turn. Return: bounded notices appear once, TTL starts
   on return, and a cancelled key stays absent.
4. Trigger one retryable provider error and one nonretryable error.
   Only the former offers Retry. Replaying it sends a single text turn
   to its owning idle session. Switch sessions / queue work / attach an
   image: reject stale or unsafe retry.
5. Use a task with parent/child workers and two overlapping delegation
   IDs: native agent nesting matches `parent_id`; late foreign progress
   never attaches to an unrelated task. Cyclic parent IDs remain flat.
6. Record matching OMP/Tern and Hermes/Tern scenarios, compare semantic
   roles, frame/op counts, time-to-first-visible-content, backlog
   after hidden/show, and reduced-motion behavior on the **same host**.

No live Tern host or Actions run was available during this consolidation.
**Do not merge** until contract tests, TypeScript checks and native host
acceptance pass and maintainers authorize an origin-scoped change.

## Frame pacing decision

Tern's SDK already diffs semantic views and obeys ACK credits (normally
two in flight). `exp/tsp-frame-pump` implements an additional dirty/credit
gate, but source presence alone is not evidence of better latency. Capture
blocked-frame counts, number of ops, p50/p95 visible frame age and CPU
load with/without it; avoid layering a second throttle blindly.

## Provenance

- Existing Hermes gateway and TSP frontend: original NousResearch/Hermes
  contributors and historical fork contributors.
- Settings contract and native sheet donor:
  Kevin Rajan, `feat/tern-native-settings`
  (`5742c3e`, `1a71d33`, `17c19c2`).
- Hidden dispatch, retry behavior, nested-agent UX reference:
  [thefullctx/hermes-for-tern](https://github.com/thefullctx/hermes-for-tern)
  and original thefullctx contributors.
- Tern protocol and SDK: Stencil Labs contributors.
- OMP interaction/semantic node conventions: the original OMP contributors.

Consolidate all future parity slices on **this same feature branch**;
review-only upstream promotion must respect fork/origin HITL and the
repository's PR cap. No parallel reimplementation branches.
