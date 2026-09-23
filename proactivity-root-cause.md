# Proactivity / freeze / focus root-cause audit

Audit time: 2026-08-18 CDT
Task: `t_5a0020a4`
Scope: live gateway, canonical `zer0-company` board, deployed Hermes checkout, proposed conversation-mode branch, company freeze receipt, task/event history. Production state was read-only.

## Executive verdict

The primary cause is an active company-wide operational freeze, not `/chat` or focused-mode scheduling. The canonical receipt `/workspace/zer0/portfolios/chief-of-staff/COMPANY-CODE-FREEZE.json` is still `NARROWED_LEVEL_0`; it explicitly denies worker dispatch and automatic task replenishment for all work except Hermes Keel L0, the preservation-only Paperclip exception, read-only inventory/monitoring, and exact Captain-authorized emergencies. No later release receipt was found.

The system is inconsistent rather than uniformly frozen: the receipt is policy/prose, not connected to the Kanban mutation/dispatcher boundary. The live gateway dispatcher is active and has continued to claim/spawn unrelated product work. Firstmate can therefore obey the freeze and stop proactively creating work while independently created cards still dispatch. This split-brain exactly explains “Firstmate no longer proactively queues/resumes” alongside visible worker activity.

`/orchestration focused` is not a live scheduler control. The implementation exists only on unmerged worktree commit `490157d7d1`; the deployed gateway checkout is `c94454a20` and contains no `gateway/conversation_modes.py`. Even on the proposal branch, `/orchestration` is a hard-coded status string: focused always returns “Keel L0 · no system freeze,” frozen and fully-autonomous always refuse with “nothing changed.” It reads no freeze receipt, persists no orchestration state, and changes no task creation, WIP, allowlist, capacity, or dispatch behavior. Its “no system freeze” claim is currently false.

`/chat` is likewise presentation-only in the proposed branch. `pm`, `brainstorm`, and `copilot` persist by exact `(profile, platform, chat_type, chat_id, thread_id)` in `$HERMES_HOME/gateway/conversation_modes.json`; watchers coalesce/queue routine notifications. The module explicitly does not touch agents, tools, tasks, workers, scheduling, or authorization. No live mode file exists because that branch was never activated. The live effective state is therefore legacy/default notification behavior, not a persisted brainstorm/copilot mode.

## Ranked causes

1. **Active company freeze intentionally suppresses Firstmate replenishment** — intentional governance, currently active. Receipt lines 3–30 deny unrelated mutation, worker dispatch, automatic replenishment, Kanban writes, and scheduled repository mutation. Firstmate stopping proactive follow-ups is compliant.
2. **Freeze is not enforced at canonical mutation/dispatch boundaries** — defect. Dispatcher remained live inside `hermes-gateway.service`; after freeze activation, canonical history records 198 canary runs plus 54 reviewer runs and 61 claims/spawns on Aug 18 alone. PitchTwin, CardTwin, and bounty cards were dispatched despite the receipt. This creates policy/runtime split-brain.
3. **Proposed `/orchestration` reports a hard-coded false state** — defect, not deployed. It claims “no system freeze,” never reads canonical evidence, and cannot actually set focused/frozen/autonomous state.
4. **Long-running monitor work consumes scarce worker capacity** — operational amplifier. `t_aea627f9` occupies one of the live canary-worker slots for an overnight monitor; during audit canary-worker had two running tasks and reviewer one. This delays work but does not explain Firstmate intake suppression.
5. **Synthetic fixtures contaminate the canonical ready queue** — defect/data hygiene. Seventeen ready cards assigned to `alpha`, `beta`, `fixture-alpha`, `fixture-beta`, or `fixture-worker` remain on the production board with `dispatch_reason=nonspawnable_profile`. Fairness now keeps them from blocking valid profiles, but they pollute health/status and previously could cause starvation.
6. **Task-local failures are not focus/freeze causes** — separate causal reasons: CardTwin was claimed immediately, then blocked on missing exact image/gated SAM3D access and later triaged by block-loop recurrence; bounty benchmarks exhausted a 1/1 iteration budget and repeatedly emitted `gave_up`; the overnight bounty run was reclaimed after stale heartbeat; PitchTwin’s `default` profile had only Kanban/browser tools and blocked for missing repo tools; downstream PitchTwin work correctly waited on dependencies/review.

## Exact live evidence

### Freeze and dispatcher

- Freeze receipt state: `NARROWED_LEVEL_0`, effective 2026-08-16 00:07 CDT, narrowed 01:26 CDT.
- Allowed: read-only inspection/inventory/evidence preservation/non-mutating health monitoring/emergency action explicitly authorized by Captain.
- Denied: code/assets, repo mutation, commits/push/PR/merge/deploy, worker dispatch, automatic task replenishment, Kanban/Paperclip sync writes, scheduled repository mutation.
- `hermes-gateway.service` active since 08:37 CDT; dispatcher runs in gateway. No standalone `hermes-kanban-dispatcher.service` exists.
- Gateway systemd environment has `HERMES_HOME=/workspace/hermes-home`; no pause/kill/freeze environment flag was present.
- Live config has `kanban.orchestrator_profile=default`, `default_assignee=canary-worker`, `auto_decompose=false`; no dispatch pause or freeze setting.

### `/orchestration` and `/chat`

- Deployed checkout: `/workspace/hermes-home/hermes-agent` at `c94454a20`; conversation-mode files absent.
- Proposed/verified worktree: `490157d7d1`.
- Proposed `/orchestration` has no persistence and always describes focused as active; it does not enforce source/task allowlists, active-product limits, WIP/concurrency, auto-create suppression, or dispatch.
- Proposed `/chat` mode is destination-scoped notification presentation only. Brainstorm queues routine updates but does not stop execution; copilot focus filters notification presentation; PM digests routine updates.
- Targeted proposal tests passed: 75/75 (`test_conversation_modes.py`, `test_kanban_attention.py`, `test_commands.py`). These prove isolation/coalescing contracts, not live activation or intake creation.

### Intake and dispatcher path

The canonical implemented path is: agent/tool creates task → parent-gated promotion → profile validation/capacity/fairness → atomic claim/run → spawn. There is no deterministic Telegram “actionable classifier → task create” subsystem in the deployed code. Firstmate creates tasks through model tool use, governed by its system instructions/current policy. Therefore an informational-vs-actionable isolated canary cannot truthfully prove automatic intake behavior: no such classifier exists to invoke. The safe actual-code canary result is “no production feature path available”; fabricating a task via `create_task()` would test Kanban, not Firstmate intake.

### Named incidents

- **CardTwin `t_27027ed9`:** created ready 00:36:55, claimed 8 seconds later. It did not remain Ready due focus/capacity. It blocked on exact source/SAM3D credentials, was later unblocked, reclaimed/claimed, and moved to triage after the same `needs_input` recurred (block-loop circuit breaker).
- **Bounty cards:** tasks did not disappear due focus. Benchmark cards timed out on `Iteration budget exhausted (1/1)` and hit failure limit; a monitor dependency was repeatedly promoted because dependency blocking lacked a real parent at first; the overnight worker then stopped heartbeating and was reclaimed on gateway restart.
- **Preview/chiefstaff:** current history shows chiefstaff runs (2 done, 2 blocked) rather than a global dispatch halt. Stalls are task-specific/profile/tool/capacity outcomes, not `/chat`.
- **PitchTwin:** `t_3d60382c` was deliberately assigned `default`, spawned, and blocked because that profile exposed only Kanban/browser tools. The canary-worker replacement completed; downstream `t_ca660b00` is dependency-gated on capture and review. Wrong-profile/toolset routing is causal.
- **Synthetic E2E:** 17 canonical ready fixtures are assigned to nonexistent test profiles. Current fairness labels them `nonspawnable_profile`, so they no longer block claimable profiles, but E2E violated board isolation and left production contamination.

## Timeline

- 2026-08-16 00:07: company freeze activated.
- 2026-08-16 01:26: narrowed only for Keel L0 plus preservation-only Paperclip receipt; all unrelated product work remains frozen.
- 2026-08-17: attention-mode feature/rework developed on isolated worktrees; never activated.
- 2026-08-17: 52 tasks created and 20 claimed despite freeze; synthetic fixtures entered canonical board.
- 2026-08-18 00:36–01:09: CardTwin/bounty tasks dispatched; prerequisite, iteration-budget, dependency, and heartbeat failures recorded.
- 2026-08-18 08:37: gateway restarted on `c94454a20` with dispatcher health/fairness stack.
- 2026-08-18: 46 tasks created and 61 claims/spawns recorded by audit time; PitchTwin and other unrelated product work continued despite active freeze.

## Intentional versus defective

Intentional:
- Captain-only release of company freeze.
- Keel L0 does not permit broad autonomous authority.
- Human gates for root, secrets/credentials, publication/accounts/payments.
- Chat brainstorm/PM/copilot affect attention delivery only.
- Dependency and recurring-block fail-closed behavior.

Defective:
- Freeze receipt is not machine-bound to create/promote/claim/spawn.
- `/orchestration` proposal hard-codes “no system freeze” and presents a status it does not measure.
- Synthetic E2E wrote fixtures into the canonical board.
- Wrong profile/toolset was accepted for a repo-building task.
- Repeated terminal `gave_up` events were emitted after circuit breaker state.

## Minimal correction

Do not lift the freeze implicitly. Implement one canonical, read-only policy resolver plus a mutation-boundary gate:

1. Resolve a signed/hashed canonical freeze receipt from configured policy state (not an ambient repo path in UI code).
2. Enforce it in core Kanban create/promote/claim/spawn boundaries with explicit scoped exceptions and durable denial receipts.
3. Make `/orchestration` a read-only projection of that resolver until a Captain-authenticated, sealed state transition exists. Remove the hard-coded “no system freeze.”
4. Keep `/chat` presentation-only.
5. Isolate all E2E boards by construction and reject fixture assignees on non-test boards.

## Recommended operating model

After explicit Captain replacement of the current freeze receipt: **focused local autonomy**. Permit proactive intake, queueing, resumption, local reversible edits, tests, evidence creation, and bounded worker dispatch for allowlisted Keel/Hermes/CardTwin/PitchTwin scopes. Retain mandatory human gates only for root/system mutation, secrets/credential acceptance, public publication/deployment, external accounts, and payments. Encode scope and exceptions in the canonical resolver; do not infer authority from `/chat`, notification focus, profile prompts, or ambient repository state.

Until that replacement receipt exists, the correct operating state is frozen for unrelated product mutation. The current ongoing product dispatch is a governance enforcement defect, not evidence that the freeze was lifted.
