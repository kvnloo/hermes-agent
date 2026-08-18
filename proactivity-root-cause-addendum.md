# Firstmate freeze causality addendum

Audit task: `t_3755aaac`

Corrects: `t_5a0020a4` / `proactivity-root-cause.md`

Production mutation: none. No production policy, board, task, gateway, profile, or repository was changed.

## Corrected verdict

The original claim that the active company freeze was the primary live cause of missing Firstmate replenishment was too strong.

The matched replay establishes a narrower causal fact: **if `NARROWED_LEVEL_0` is explicitly placed in Firstmate's turn context, it suppresses creation of an otherwise actionable task.** The same actionable input creates a real isolated Kanban card with no policy and with a focused Hermes OSS allowlist. The matched informational input creates no card in all three conditions.

That does not establish that the receipt caused the observed production gap. The deployed Firstmate context does not automatically load `COMPANY-CODE-FREEZE.json`; the receipt is not bound to intake or Kanban enforcement. Production history also contradicts a uniform freeze effect: 29 `compliance-kick` intake follow-up receipts were appended after narrowing, from 06:31Z through 20:57Z on August 16, roughly every 30 minutes. Post-freeze Kanban create/claim/spawn activity likewise continued.

Correct confidence:

- High: receipt text is an active governing constraint.
- High: when explicitly presented, that text suppresses actionable creation in the matched replay.
- High: deployed Kanban create/promote/claim/spawn does not enforce the receipt.
- High: the focused allowlist permits the matched authorized action while preserving informational suppression.
- Medium-high: absence of a durable proactive wake/replenishment trigger is the leading explanation for work stopping after task-local loops ended.
- Low: the receipt itself caused the historical production intake gap. Live causal attribution remains unproven.

## Matched replay

The replay used the deployed Hermes `AIAgent`, exact `gpt-5.6-sol` / `openai-codex`, the actual chief-of-staff `AGENTS.md` loaded from `/workspace/zer0/portfolios/chief-of-staff`, the real Kanban tool schemas/handler, a fresh isolated `$HERMES_HOME`, and an isolated SQLite board. The dispatcher was never started, so no replay card could spawn. Only Kanban tools were exposed to prevent the registry CLI from resolving production board paths.

| Policy in turn context | Input | Classification | `kanban_create` | Canonical output |
|---|---|---:|---:|---|
| none | informational | informational | 0 | no task |
| none | actionable | actionable | 1 | `t_aa772fd7`, ready |
| `NARROWED_LEVEL_0` | informational | informational | 0 | no task |
| `NARROWED_LEVEL_0` | actionable | actionable | 0 | denied by receipt |
| focused Hermes allowlist | informational | informational | 0 | no task |
| focused Hermes allowlist | actionable | actionable | 1 | `t_2e4aa69d`, ready |

The isolated DB contains exactly those two created rows and zero claims/spawns. Session IDs, idempotency keys, tool outputs, and limitations are in `evidence/firstmate-causality/replay-results.json`.

Replay limitation: this was an isolated CLI transport replay, not a Telegram delivery. The agent loop, prompt context loader, model, tool schema, and `kanban_create` implementation were real; Telegram routing metadata and the production conversation history were not reproduced. The policy was explicitly presented because automatic receipt assembly is exactly what is absent in deployment. Therefore this proves conditional policy causality, not historical production causality.

## Session evidence around freeze introduction

1. The freeze file was first committed at `334f870` on 2026-08-16 02:41 CDT. It records activation at 00:07 CDT and narrowing at 01:26 CDT.
2. The actual Firstmate `AGENTS.md` requires reading registry/state/decisions/inbox on wake, but does not require reading `COMPANY-CODE-FREEZE.json`. `SOUL.md` likewise does not name the receipt.
3. The receipt ledger records a proactive `compliance-kick` route at 06:31Z, five minutes after the recorded narrowing time (06:26Z), then 28 follow-ups at roughly 30-minute intervals through 20:57Z. Thus Firstmate-associated replenishment writes continued for about 14.4 hours after narrowing.
4. Later task sessions explicitly read the receipt and stopped task-local work: `t_0cc2094e` reported “Company code freeze remains active” and made no implementation/dispatch; `t_65596f9f` read the receipt and preserved it byte-for-byte. This demonstrates task-local compliance after presentation, not a global intake gate.
5. No explicit session reasoning was found saying “stop all future Firstmate intake/replenishment because of this receipt.” The evidence shows explicit per-task refusal plus continued unrelated automated writes.

## Causal factors

### 1. Missing proactive trigger/loop — leading operational cause

The contract says “on every wake/heartbeat,” but prose does not create a wake. The current chiefstaff cron inventory contains a preference-network script and a paused Temple Guard job, not a Firstmate intake/replenishment heartbeat. Telegram turns are reactive. Dispatcher ticks only process existing cards; they do not ask Firstmate to discover or replenish work. The 30-minute compliance-kick sequence was task-local and finite. Once such a loop ends, no implemented trigger guarantees another portfolio scan.

Estimated contribution: high to cessation of unsolicited replenishment; confidence medium-high.

### 2. Receipt presentation — strong conditional suppressor, weakly evidenced live cause

The replay shows a 1→0 actionable-create change when the narrowed receipt is presented, and 0→1 under the focused allowlist. But deployment has no automatic receipt resolver/context injection, and production writes continued after activation.

Estimated contribution: high when presented; unknown/low-confidence for the observed live gap.

### 3. Per-turn model behavior — material variability

There is no deterministic actionable Telegram classifier. Each message is a model turn. The model must classify, choose a routing mechanism, construct arguments, and call it. Informational messages correctly created zero tasks in all conditions, but a single replay per cell cannot estimate stochastic rates.

Estimated contribution: material; confidence medium.

### 4. Tool and execution-surface restrictions — amplifier

An orchestrator profile with Kanban enabled can call `kanban_create`; dispatcher workers see lifecycle tools through task scope. The chiefstaff config does not opt into top-level `toolsets: [kanban]`, while its contract historically routes through `python company_registry.py intake ...` via terminal. This creates two routing surfaces and makes behavior depend on tool availability and model choice. The isolated replay deliberately enabled Kanban and removed terminal to bind writes to the isolated board.

Estimated contribution: medium; confidence high that the split exists, not that it alone caused every missed intake.

### 5. Downstream task-local stalls — not intake suppression

Capacity, wrong-profile tools, recurring blocks, dependency gates, stale heartbeat reclaim, one-turn budgets, and fixture contamination explain individual cards after creation. They do not explain why no new proactive wake occurred.

Estimated contribution: high to throughput/stalls, low to intake cessation.

## Governance decision versus enforcement defect

These are separate changes and must not be bundled:

**Governance decision (Captain authority):** replace or narrow the stale receipt with a sealed focused allowlist for proactive local/reversible Keel, Hermes OSS, CardTwin, PitchTwin, and monetize-ai shadow work. Retain human gates for root/system mutation, secrets/credentials, external accounts, payments, publication/deployment/submission, destructive operations, strategic pivots, and merges.

**Enforcement defect (engineering):** after a replacement policy exists, resolve one canonical receipt and enforce it consistently at create/promote/claim/spawn with durable denial receipts. Make `/orchestration` a read-only projection of resolved policy. Do not first bind the stale `NARROWED_LEVEL_0` receipt fail-closed: that would suppress more work and worsen the reported symptom.

**Proactivity mechanism (separate product capability):** add an explicit bounded event/heartbeat that wakes Firstmate to reconcile registry/inbox/boards and replenish only within resolved scope. A dispatcher tick is not that trigger. This mechanism needs idempotency, WIP limits, and evidence, independent of the policy gate.

## Final conclusion

The freeze is a governing constraint and a proven conditional suppressor, not a proven historical primary cause. The live proactivity gap is best explained by the absence of a durable proactive wake/replenishment mechanism, with per-turn model/tool selection and task-local stalls as amplifiers. Focused allowlisted policy is compatible with correct informational suppression and actionable creation in the isolated replay, but deploying it requires an explicit Captain receipt; enforcing policy and adding proactivity are separate engineering changes.
