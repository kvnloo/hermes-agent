---
name: token-thrifty-agent-routing
description: Use when choosing models or offloading agent work. Burn-pace paid pools to reset, add free lanes, verify.
---

# token-thrifty-agent-routing

Use when choosing models, pacing quota, or delegating work.

## Rules

1. Simplify the stack first: use one burn-pace admission tracker; keep Kerdoios on placement and z0intelligence or the external router on model choice.
2. Read burn-pace before choosing models or counts and every 15 minutes during long runs. Repair probe errors, reconcile every account, honor holds, and cap workers by admitted count and free RAM.
3. Keep Opus as owner-facing orchestrator and core implementation owner, including owner-reported fixes and visual design. Exhaustion requires an explicit Opus hold, not silent family substitution.
4. Run GPT lanes only through fx or pi with explicit model and effort, short contracts, and visible permanent lanes. Keep Hermes delegation on Anthropic Opus or unused; exclude GPT from Hermes, T3 Codex and vllm-sr.
5. Permit coding only after the exact model passes that task tier's coding probe in minimal fx/pi. Treat benchmark rankings as probe priorities, not coding permission.
6. Resolve actual billed accounts and fallback chains before fan-out; state account/count and obtain consent. A named-model request approves billing, not overriding pacing. Stop exhausted-pool consumers and report transport dependencies.
7. Track native subscriptions separately from Nous monthly dollars, app pools and API-equivalent estimates. Verify credential selection per account; use shared root OAuth pool rows, not duplicate profiles. See references/hermes-subscription-pool.md and references/subscription-resets.md.
8. Use ordinary ChatGPT chats for the phone lane; require explicit Work authorization and measured small batches. Keep the main-account Gemini app hand-use only. Preserve phone focus, install locks and the sleep-time ADB/install/mic prohibition.
9. Give each worker a disjoint worktree, file-pointer brief, numbered jobs, exact gates and JSON report. Route heavy commands through fleet-build; preserve draft-only publication and prohibit worker merges/default-branch pushes.
10. Independently check artifacts, changed tests, exact-head receipts and deployment readback; reconcile hosted SHAs/counts. Resume dead workers from edits/transcripts.
11. Measure outcomes, recall, replay/cache tokens and rework in matched trials. Preserve clean-profile handoff; see references/context-rot.md and references/token-reducer-installs.md.
12. Extend existing turbo; qualify routes with real content/tool probes and model metadata under harness/vendor restrictions. See references/read-only-scan-lanes.md.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
