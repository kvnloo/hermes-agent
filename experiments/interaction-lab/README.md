# Hermes Interaction Lab

Downstream experiment ledger for small, evidence-driven UX changes across Desktop, TUI, and Web.

The purpose is to improve human-agent coordination **through Hermes' existing architecture and design system**, not to introduce a parallel framework. Every experiment should be independently useful upstream even if the larger direction is abandoned.

## North star

Increase useful work completed per unit of user attention while preserving agency.

In practice:

- conversation carries high-entropy intent;
- direct controls resolve bounded choices;
- ongoing work stays legible without flooding the interface;
- background work never steals foreground context;
- recovery/reload preserves meaning;
- each action has one semantic owner across surfaces.

## Upstream design constraints

Treat these as hard constraints unless upstream explicitly changes them:

1. **One source per concern.** Reuse the existing state owner, resolver, primitive, or transport seam.
2. **Chat stays home.** Panes and tools complement the conversation rather than replacing it.
3. **One action, one home.** Multiple affordances may invoke the action; they must not fork behavior.
4. **Intent before automation.** Tool output may update badges/caches, but must not move focus or navigate on the user's behalf.
5. **Immediate feedback.** Direct manipulation updates locally first; persistence reconciles visibly afterward.
6. **Preserve context.** Background completion, refreshes, and tool results must not replace the foreground transcript.
7. **Fail closed on ambiguous targeting.** If we cannot prove which visible object/input/session owns an action, do not guess.
8. **Presentation may differ; semantics may not.** Desktop, Web, and TUI can render differently while sharing the same behavioral contract.
9. **No framework-first work.** Start from a concrete failure, one invariant, one falsifying control, and one small repair.
10. **No scope laundering.** Follow-up design questions stay follow-ups unless required for the current invariant.

## What we learned from OpenMuse / CopilotKit

The useful work clustered around the same recurring contracts:

- **identity:** observation/session/runtime identity must not be conflated;
- **activity lifecycle:** pending/settled state should come from the execution owner, not reconstructed from mounted UI;
- **interrupt ownership:** a visible human decision must resolve the exact pending operation that produced it;
- **history/recovery:** remounts and reloads must not reorder or duplicate activity;
- **attention preservation:** an item the user is reading should not disappear merely because new work arrives;
- **runtime-to-consumer acceptance:** test the real producer → consumer path, not only helpers shaped like the expected input.

A good research unit is:

> existing user problem → behavioral invariant → counterexample → minimal owner-aligned repair → regression → receipt

## Experiment protocol

Every experiment gets:

- **User friction:** one sentence.
- **Existing owner:** file/module/issue/PR already responsible.
- **Invariant:** one behavioral rule.
- **Positive control:** behavior that must keep working.
- **Falsifying control:** case that defeats a fake or overly broad fix.
- **Intervention:** smallest change that can test the hypothesis.
- **Measures:** observable outcomes, not aesthetic preference.
- **Stop condition:** when to abandon or split.
- **Upstream seam:** existing issue/PR to join instead of creating a competing architecture thread.

### Shared measures

Track where applicable:

- wrong-target actions: target **0**;
- foreground focus steals caused by background work: target **0**;
- ambiguous timeout before actionable feedback;
- state disagreement between sidebar/composer/thread/pane;
- correction turns caused by UI misunderstanding;
- duplicate/replayed actions after restore;
- time from symptom → deterministic reproduction;
- reviewer clarification rounds;
- number of new semantic owners introduced: target **0**.

## WIP policy

Maximum **3 active experiments**.

An experiment is active from first implementation/test change until one of:

- upstreamed;
- disproved;
- blocked on a maintainer decision;
- archived with a receipt explaining why.

Do not open a fourth lane to avoid finishing a hard one.

---

# Wave 1

## E1 — Attention state: make “what needs me?” unambiguous

**Upstream seams**

- NousResearch/hermes-agent#50718 — session visibility / unread / needs-input
- NousResearch/hermes-agent#83239 — authoritative turn-state indicator
- NousResearch/hermes-agent#46357 — TUI attention hook

**User friction**

A quiet agent can mean completed, blocked, waiting, stalled, or merely working in a child task.

**Invariant**

The same runtime state has one semantic meaning across Desktop/Web/TUI, and background state changes never steal foreground focus.

**First proof**

Create a scenario fixture covering:

1. working;
2. waiting for user input;
3. background child still working while parent is quiet;
4. completed-unread;
5. interrupted;
6. reconnect/stall.

Assert that the state owner produces one semantic state and each surface projects it without independently re-deriving meaning from rendered text or timers.

**Falsifying control**

A renderer-only implementation that looks correct during a live foreground turn but disagrees after reload/background completion must fail.

**Measures**

- surface disagreement count = 0;
- focus steals = 0;
- completed/needs-input state survives backgrounding and reload;
- no second parallel status store.

**Stop / split**

If the three upstream issues intentionally define different semantics, document the divergence and stop trying to unify presentation.

---

## E2 — Voice intent: trusted per-turn modality, not engine identity

**Upstream seams**

- NousResearch/hermes-agent#109455 — trusted per-turn voice context
- NousResearch/hermes-agent#122296 — chained voice path lacks modality

**User friction**

A spoken turn currently can be indistinguishable from typed text, so the agent cannot reliably adapt delivery to the interaction mode.

**Invariant**

Input modality is ephemeral, trusted client state. It is independent of provider/voice engine and clears on the next typed turn.

**First proof**

One Desktop chained-voice turn + one TUI dictation turn carry the same semantic `input_modality=voice` contract into the existing hook/context boundary.

Then submit typed text in the same session and prove the voice signal is gone.

**Falsifying control**

Changing TTS provider or live-voice engine must not change the semantic modality contract.

**Measures**

- voice attribution accuracy = 100% in the fixture;
- typed-turn leakage = 0;
- persisted-history additions = 0;
- engine-specific branches added to semantic consumers = 0.

**Stop / split**

If maintainers choose an existing request-metadata contract with a different field shape, follow that owner rather than introducing a second one.

---

## E3 — Pending intent: one place for “what will happen next?”

**Upstream seams**

- NousResearch/hermes-agent#68083 — TUI steer + queue pending area
- existing Desktop approval/clarify card stack and session attention state

**User friction**

Pending steer, queued prompts, approvals, and clarifications can be represented in different places even though the user's core question is the same: **what happens next, and can I change it?**

**Invariant**

Each pending action has one durable visible representation, exact identity, ordering, and cancel/edit path appropriate to that action.

Do **not** force unlike action types into one universal widget.

**First proof**

Start narrowly with the TUI steer/queue case already requested upstream:

- pending steer is visible beside queued work;
- steer sorts first because it fires first;
- it can be edited/cancelled before injection;
- successful submission does not leave only a transient transcript/sys-line acknowledgement.

**Falsifying control**

A UI-only row that edits local text but leaves the backend pending steer unchanged must fail.

**Measures**

- wrong item edited/cancelled = 0;
- pending UI/backend disagreement = 0;
- orphan acknowledgement-only states = 0.

**Stop / split**

Do not generalize into a universal pending-action framework unless two independently shipped surfaces demonstrate the same missing semantic owner.

---

# Wave 2 candidates

Keep these parked until a Wave 1 slot closes.

## C1 — Pane intent and visible-object ownership

References:

- #121476 — read the preview zone the user is looking at
- #121473 — refuse unfocused typing / abort leftover keystrokes
- #119333 — pane request when no window hosts the asking session

Direction:

- read the visible/focused object;
- act only on the proven owner;
- fast-fail when no UI owner exists instead of burning a long ambiguous timeout.

This is a strong reusable pattern for any future agent-controlled pane.

## C2 — Activity that does not disappear while being read

Carry forward the CopilotKit activity lessons:

- recency belongs to conversation/history, not mount order;
- explicit user expansion can pin an item temporarily;
- restored history must not become “new activity”;
- settling a run should not be inferred from the disappearance of content.

Find the smallest Hermes surface with the same concrete failure before implementing anything.

## C3 — Live artifact co-work

Reference:

- #88647 — live pen.dev canvas beside chat

Do **not** build another canvas.

Useful experiments are around the existing ownership model:

- artifact belongs to the conversation;
- hide is not destroy;
- switching chats rebinds without duplicate panes;
- agent and human can manipulate the same artifact without fighting focus;
- Web should reuse the same renderer/contract where possible.

## C4 — Desktop/Web parity without duplicated product logic

Reference:

- #93508 — browser-hosted Desktop renderer

Use this as the preferred direction: adapt capability boundaries, not duplicate the Desktop product.

A candidate UX change should be tested once at the shared renderer contract and then have explicit Electron/Web capability controls where necessary.

---

# Review checklist

Before proposing anything upstream:

- [ ] Read current DESIGN.md and AGENTS.md.
- [ ] Search existing issue/PR ownership.
- [ ] Confirm the behavior on current main.
- [ ] Identify the authoritative state owner.
- [ ] Write the counterexample before the fix.
- [ ] Keep the positive control.
- [ ] Test restore/background/concurrency when identity is involved.
- [ ] Avoid new primitives when an existing primitive can own it.
- [ ] Avoid new network round-trips when already-fetched authoritative data exists.
- [ ] Separate blocking correctness from non-blocking follow-up design.
- [ ] State exactly what was executed vs source-reviewed.
- [ ] Auto-merge off for behavior/identity changes.

# Success condition

This lab is working when we can land small Hermes-native UX improvements whose local value is obvious, whose behavioral evidence is easy for maintainers to verify, and whose combined direction gradually improves human-agent coordination without requiring upstream to adopt a new named framework.
