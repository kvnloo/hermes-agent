# Proactivity / freeze / focus root-cause audit — corrected copy

Audit correction: `t_3755aaac` supersedes the causal wording from `t_5a0020a4` without overwriting its historical artifact.

## Corrected verdict

The active `NARROWED_LEVEL_0` receipt is a governing constraint and a proven **conditional** suppressor, not a proven historical primary cause of the live Firstmate intake gap.

A matched six-cell replay used the deployed Hermes agent loop, exact `gpt-5.6-sol` / `openai-codex`, actual chief-of-staff `AGENTS.md`, real Kanban schemas/handler, and an isolated board:

- informational input: 0 creates under no policy, narrowed receipt, and focused allowlist;
- actionable input: 1 create with no policy, 0 with narrowed receipt explicitly presented, 1 with focused Hermes OSS allowlist;
- isolated outputs: `t_aa772fd7` and `t_2e4aa69d`, both ready; dispatcher absent, zero claims/spawns.

This proves that presenting the narrowed receipt changes the matched actionable decision. It does not prove that production presented it. The deployed Firstmate context does not automatically load `COMPANY-CODE-FREEZE.json`, and the receipt is not enforced at Kanban boundaries. Production evidence also records 29 Firstmate-associated `compliance-kick` follow-up receipts after narrowing, from 06:31Z to 20:57Z on August 16.

## Ranked factors

1. **No durable proactive wake/replenishment trigger** — leading live explanation, medium-high confidence. “On every wake/heartbeat” is a contract, not a scheduler. Dispatcher ticks process existing cards and do not wake Firstmate to discover work. Current chiefstaff cron inventory contains no such loop.
2. **Receipt presentation** — high-confidence suppressor when presented; low-confidence historical cause. Task-local sessions that read it stopped, while other post-freeze writes continued.
3. **Per-turn model behavior** — material. There is no deterministic Telegram actionable classifier; classification and tool selection happen per model turn.
4. **Routing/tool split** — amplifier. Firstmate historically routes through `company_registry.py intake` via terminal, while canonical `kanban_create` visibility depends on orchestrator/task context.
5. **Task-local stalls** — high impact after creation, low impact on intake: capacity, profile/tool mismatch, dependencies, recurring blocks, stale heartbeats, iteration budgets, and fixture contamination.

## Governance and engineering are separate

- **Governance:** only the Captain can replace/narrow the receipt. The selected focused model may allow proactive local/reversible Keel, Hermes OSS, CardTwin, PitchTwin, and monetize-ai shadow work while retaining gates for root/system mutation, secrets/credentials, accounts, payments, publication/deployment/submission, destructive operations, strategic pivots, and merges.
- **Enforcement:** only after that replacement exists, bind one canonical resolver to create/promote/claim/spawn with durable denial receipts. Enforcing the stale narrowed receipt first would suppress more work.
- **Proactivity:** separately implement a bounded idempotent event/heartbeat that wakes Firstmate to reconcile and replenish inside resolved scope. Policy enforcement alone does not create proactive behavior.

Full evidence, limitations, session IDs, and historical reasoning are preserved in `proactivity-root-cause-addendum.md` and `evidence/firstmate-causality/replay-results.json`. Production policy and boards were not mutated.
