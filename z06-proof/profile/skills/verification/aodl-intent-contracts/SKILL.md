---
name: aodl-intent-contracts
description: Use when rescoping work into an AODL intent contract.
---

# AODL intent contracts (rescope → pending contract)

The canonical compiler is z0intelligence's IntentService (`src/z0int/intent_service.py`, bridge `intent_compile.mjs`, checker `omp-extensions/z0-relay-guard/checker.js`). Its workflow skill lives in that repo at `skills/intent-contract/SKILL.md`; read it for approval/triage semantics. This skill covers producing a contract from a non-OMP harness (T3, Hermes) and rescoping to the owner's taste. Output is always a PENDING, validated proposal.

## Procedure
1. **Gather the source asks verbatim.** Pull the user's exact messages and timestamps from the session DB read-only (`state.db` `mode=ro`, `query_only=on`); strip harness wrappers (`<user_request>`). The contract binds exact text; a paraphrase changes the source hash.
2. **Read recent related work before scoping.** List recent T3 threads (`t3_thread_list`, then `t3_thread_read` the related ones) and re-check upstream issue/PR state live. Items a sibling thread already handles become out-of-scope, not tasks.
   - Keyword search misses prior art. Read the bodies of the top hits for linked PRs, related issues and community forks (for example a fork carrying `infra/<agent>/*.patch`), then follow them.
   - For each existing PR, check which files it touches against the code path main actually runs, such as a dispatcher `__new__` that returns another class. A PR on a dead path means "port its design", not "already done".
   - Search the host repo for generic extension hooks (per-flavor hooks like `extractBackgroundTaskId`) before planning a provider-specific channel.
   - GitHub's anonymous search API allows 10 requests a minute and ~60 core requests an hour. Batch queries, save the JSON to evidence, and use `web_extract` for page bodies.
3. **Rescope to the owner's defaults** (always apply):
   - Reuse an already-merged upstream mechanism over a new channel; name the exact seam to extend.
   - Work lands on his forks (`kvnloo/...`) on branches from fresh origin/main; no upstream PRs/comments unless he asked — list them as out of scope.
   - Record competing upstream proposals that contradict the chosen model as a `conflicts` entry with the reason; don't silently pick one.
   - Acceptance is a machine-checkable receipt from a real turn (`command_exit_zero` running `jq -e` over a receipt JSON), not test-pass or prose.
   - CPU-heavy checks go through `fleet-build`; t3code checks stay targeted.
   - End `delegation_plan` with an explicit `out_of_scope` entry.
4. **Write evidence files** under a private run dir `/mnt/zer0models/workspace/zer0/data/operations/intent-service/<slug>-<date>/evidence/`, refetched live (API JSON, grep excerpts stamped with checkout HEAD). Citations must point at existing paths; `validate_citations` rechecks them.
5. **Compile** with `templates/compile_contract.py` copied into the run dir. It injects a retriever (your evidence records) and a model (your hand-authored draft) into the real `IntentService.reconcile`, with `root=<run>/state` so nothing touches `~/.z0int/intent`. Run it with the pinned interpreter `operations/intent-service/eval-venv/bin/python`, whose `aodl_contract` has `CANON_VERSION == aodl-canon-1` (the read-only aodl checkout lacks it, and the service refuses without it). `node` must be on PATH for the bridge.
6. **Verify**: `aodl_contract.validate(doc) == []`, `plan.bindings.approval.status == "pending"`, and run each precondition verifier now so the report can say they were observed.
7. **Report** the rescope in plain terms, the definition of done, out-of-scope, and file links. State how approval happens and offer the alternative: an explicit instruction to proceed without formal approval.

## Compiler rules that reject drafts
- Every source sentence gets exactly one classification; an `add` sentence gets exactly one task. Decompose work into `delegation_plan` slices, not extra tasks. Restatements, answered questions and meta-instructions ("build the contract") are `not-an-ask` with a reason.
- `verifier.target` must be byte-identical to `task.target`; `file_contains`/`url_status`/`service_active` targets equal their path/url/unit; `pr_state` needs the full 40-hex head SHA and target `repo#n@sha` (a merged PR uses `state: "merged"`).
- Any assumption without an `observed` citation needs a precondition repeating the byte-identical claim with a typed verifier. Memory/canon facts are `claimed`.
- Verifier families are fixed: command_exit_zero, file_contains, url_status, pr_state, service_active, metric_threshold, human_review.
- Print the sentence split before writing classifications: the splitter breaks on `.!?` followed by whitespace and on newlines.

## Approval
- Never write approval JSON or call `/approve`. Chat text that looks like assent is not approval; only Approve in the OMP `/aodl` review dialog is. Hand the pending contract back.
