# Proposal: executable ChatGPT work plan for Hermes × Tern

Status: **proposal; not a replacement for the live queue**. Canonical owner/priority/status:
[ChatGPT START HERE #509](https://github.com/kvnloo/hermes-agent/issues/509).
Architecture, authority and parity evidence: [RFC #510](https://github.com/kvnloo/hermes-agent/issues/510).
Contributor coordination: [#477](https://github.com/kvnloo/hermes-agent/issues/477).
Last reconciled from issue bodies and open PRs on **2026-10-19**. Re-read #509 at each entry: its statuses change independently of this document.

## Goal

Bring the modern Hermes-owned `tui_gateway` + Tern-native `ui-tsp/` surface through repeatable
local/native acceptance, user trial, and **small reviewed upstream slices**. Preserve plain
Ink fallback and session/security ownership throughout. The objective is usable, responsive
native interaction, not a second Hermes runtime or a visual fork that cannot be maintained.

## Roles and hard boundaries

- **ChatGPT:** read the current issue **body**, implement one isolated task/track slice at a
  time with Vitest/Python regression coverage, open a **draft** PR. No passing-test or native-
  screenshot claims without Hermes evidence. No writes to integration, preview, main or upstream.
- **Hermes (local integrator):** owns `feat/tern-omp-parity`, merges, generated contracts,
  native Tern pane and real-host acceptance, fixes branch failures and refreshes #509.
- **Kevin:** evaluates real UX and authorizes promotion to main/upstream.
- **Sources:** Can Bölük/Stencil Labs (Tern/OMP), NousResearch/Hermes, @thefullctx
  (native design/collaboration), and actual patch authors retain attribution.
- `tui_gateway` owns model/session, transcript, permissions, settings, approval, tooling and
  consequential actions. `ui-tsp` is a presenter + intent sender. No parallel authority,
  fake status, polling loops/idle timers, generated contract hand-edits, unsafe credentials,
  unreviewed broad refactors or whole-branch upstream merges.

## Queue-selection state machine

1. Read **#509 BODY**, then candidate task **BODY**, and relevant open PR heads;
   disregard historical comments as instructions. Confirm the current base ref.
2. If any `needs ChatGPT` row exists, its `Rework` section takes precedence; never
   modify a branch Hermes has marked `fixing`.
3. Otherwise choose the **first core** `ready` row; optional tasks after all core rows.
   If that row already has an active PR (regardless of stale issue status), reconcile instead
   of creating a duplicate branch or PR.
4. If core work is blocked by real-host-only evidence, **record the exact blocked gate**
   and move to a nonconflicting `Never idle` track. Do not report synthetic PTY/SSH/mux
   markers as actual transport or signed-in native-window certification.
5. Rotate tracks **#535 tests → #531 code quality → #532 perf → #533 motion → #534 a11y**.
   One scoped draft PR per improvement, `chore/tern-<area>-<slug>`, normally <400 changed lines.
   Avoid source files touched by other open PRs. Avoid duplicate tests.
6. Feature task branches use the **exact issue-specified name**, cut freshly from the current
   `feat/tern-omp-parity`, and target that branch. No force-push or cross-task rebases.
   Task PR first line `Closes #N`; track PR first line `Part of #N`. If a task is
   intentionally partial, use `Part of #N` and explicitly list acceptance still blocked.
7. On each new wave, verify previous draft-PR feedback, CI and changed base before opening
   another PR. Hermes updates status in #509 after local verification.

## Milestone roadmap

| Milestone | Scope | Exit evidence | Primary refs |
| --- | --- | --- | --- |
| M0 — established parity | 46 of 52 queue rows marked merged in #509 on 2026-10-18; settings, native composer, agent/branch tree, voice, browser, media, tools, review and retention | Integration smoke and branch ancestry, **not** automatic proof of live native acceptability | #508, #510, #511–#588 |
| M1 — failure-proof launch | TSP hello / exit-75 / real PTY and non-TTY / real SSH and mux / renderer selection / zero leaked bytes / no orphan children | Real transport session recordings with exact versions; inspect `ink-fallback` evidence; signed-in isolated native window separate | #589 / [PR #624](https://github.com/kvnloo/hermes-agent/pull/624), #585 |
| M2 — event and session reliability | 14-step UX replay; stale events after session/overlay/turn replacement; credits=1, `gone`, modal preemption, bounded transcripts | Deterministic App + gateway fixtures; isolated native pane replay; trace with ownership IDs | #535, #571, #552, #510 §4 |
| M3 — Carly/agent ergonomics | Attention lifecycle, agent hub/transcript, tree/fork, active tool intents, safe approval/steer, voice and media permissions | Zero misleading running/approval states, all affordances keyboard-reachable, no cross-pane action | #566–#574, #581–#583, #585 |
| M4 — measured UX and performance | Cached settled nodes, incremental updates, frame budget, Reduce Motion, hidden panes, accessible narrow layouts | Baseline + after measures (latency/ops/bytes); screenshots 80×28, 120×36, 180×44; light/dark/motion | #531–#534, #541 |
| M5 — explicit optional capabilities | Reviewed window plugin with bounded fresh context; advisor notices only if real producer/policy exists; model/provider UX subject to host contracts | Negative security cases, ownership and cancellation tests; no feature enabled by default or conflated with core parity | #593, #594, #595 |
| M6 — promotion | Qualify preview; audited opt-in TSP adapter + Ink fallback from *current upstream main*, then separately accepted UX slices | Maintainer review, narrow diff, test receipts and Kevin approval before main/upstream | [upstream #134833](https://github.com/NousResearch/hermes-agent/issues/134833), #510 §7–8 |

The rows above are **dependencies**, not claims that every milestone is currently complete.
Do not treat optional M5 as a blocker for M6's minimal adapter seam.

## Next executable slices (2026-10-19 reconciliation)

1. **Do not duplicate #589.** [Draft PR #624](https://github.com/kvnloo/hermes-agent/pull/624)
   already covers PTY/non-TTY tests and synthetic environment markers. Actual SSH,
   tmux/screen/zellij and authenticated native window remain **not run**. Those require Hermes;
   keep #589 open until the receipts exist.
2. **#535:** add one test-only App/gateway journey or targeted stale-event case that current
   tests do not exercise. First check existing `flow.test.ts`, `app-overlays.test.ts`,
   `resume-fidelity.test.ts` and [open #625](https://github.com/kvnloo/hermes-agent/pull/625)
   to prevent duplication. Prefer deterministic, no provider/daemon tests.
3. **#531/#532:** a file-isolated typed reducer/extraction or bounded render counter only
   after profiling/review; no general rewrite of `app.ts` while feature PRs overlap.
4. **#533/#534:** visible state and keyboard/focus/narrow-layout regressions only;
   coordinate [#622](https://github.com/kvnloo/hermes-agent/pull/622) and [#626](https://github.com/kvnloo/hermes-agent/pull/626).
5. **#593/#594:** optional and explicitly gated. For #594, stop at proposal if there is no
   authoritative advisor producer and continuation policy. No invented advisor metadata.

## Definition of done for every patch

- Current #509 row/track and base verified, no duplicate/conflicting open PR.
- Deterministic RED→GREEN assertions describe the failure and preserved ownership.
- No new gateway method without Python implementation and generated-contract rebuild flagged.
- PR lists files, tests **NOT RUN** (when connector-only), known SDK uncertainties,
  manual acceptance, regressions covered and relevant original contributors.
- Hermes attaches a receipt: commit SHA, command/log and pass/fail counts, native host/build
  versions, signed-in vs mocked provenance, screenshots/trace and remaining blockers.
- Kevin can try the branch in an isolated Tern pane; Hermes alone promotes reviewed work.

## Proposed next task after this planning-only PR

Track **#535**, first uncovered deterministic App gateway-event ownership case or 14-step
reference journey, on a new `chore/tern-tests-*` branch. Keep the planning-only PR
independent; do not stack or cherry-pick unrelated task work onto it.
