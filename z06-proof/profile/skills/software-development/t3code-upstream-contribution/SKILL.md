---
name: t3code-upstream-contribution
description: "Use when contributing to or triaging pingdotgg/t3code."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [t3code, upstream, contribution, oss-factory]
    related_skills: [upstream-contribution, oss-factory-kitchen, third-party-stack-research]
---

# t3code-upstream-contribution

Use when triaging or contributing to pingdotgg/t3code, building fork prototypes, or verifying its client and provider behavior.

## Rules

1. Re-read current upstream contribution policy and attribution requirements each wave. Keep one underlying problem per change; obtain Ideas approval for new behavior and never invent a line-count policy.
2. Check current main, the live installed tag, owner settings, and built-in capabilities before designing machinery. Reuse T3 scheduling, delegation, pairing, and cleanup; see references/builtin-capability-map.md.
3. Search open and closed PRs, issues, and Discussions before drafting. Reconcile maintainer takeover and verification notes; prefer an existing carrier or redesign layer over a competing implementation.
4. Prefer the owner's 2026-11-04 atomic add-on strategy: a smallest fix plus regression test on a downstream commit, offered once on an existing thread. Pin the measured head and respect author/action caps.
5. Keep upstream actions behind scoped owner approval. Save gate drafts, recheck heads/comments, and use owner-post drafts for unsupported Discussion proposal kinds; an explicit wave go authorizes only its specified evidence comments.
6. Keep fork experiments on isolated worktrees and exact upstream-SHA bases. Avoid linkable upstream references in fork bodies and commits; protect peer-owned edits and reconcile existing remote work before creating duplicates.
7. Use normal approved file-edit tools under ACP. Stop a denied write, preserve current changes, and recheck ownership before one renewed approval attempt; never route a refusal through shell rewrites.
8. Qualify exact native model, provider instance, account, and harness before delegation. Use literal brief files, async task handles, stable request IDs, and native steer/cancel; reconcile unknown outcomes before relaunching.
9. Prove bugs reachable in real caller topology, RED on base, GREEN on head, with a negative control and scoped lint/typechecks. Parent-reverify the actual changed union and all numerical claims; use references/fork-prototype-verification.md.
10. Keep heavy work on approved compute and honor explicit queue holds. Keep real owner-data seeds on his hosts; use synthetic public seeds for hosted experiments and real adapter turns for published provider-performance claims.
11. Preserve replay, first-appearance ordering, cross-entity writes, and resume watermarks when changing event storage. Recheck maintainer pruning before proposing folds; use references/event-log-compaction.md.
12. Prove client/provider fixes in an isolated live sandbox and the actual affected surface. Verify APK digest, pairing, native state, and phone locks; keep daily data untouched and report source, runtime, UI, and untested gates separately.

13. Triage host-injected prompt bloat (context rot) by measuring it, not by assuming. Count T3 blocks (`<t3_code_instructions>`, `<runtime_info>`, `<pull_request_linking>`) in the profile's state.db user messages, per model, per thread, and per merged message. Then locate the injector in a blobless clone (`git clone --filter=blob:none`, then `git grep` the tag names) and map each issue to existing PRs/issues before drafting. Recipe: references/injected-instruction-triage.md.
14. Numbers mined from the owner's state.db are private. Draft them as aggregate counts only, and get the owner's OK before posting them upstream; offer a numbers-free variant.

## Details

- [Injected-instruction triage recipe](references/injected-instruction-triage.md): state.db measurement queries, injector locations, the downstream ACP dedupe option.

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
