# Hermes readiness snapshot — 2026-10-05

Observed main was `824a942e972ea0ccca05e83282e3fea1387afcdc`, committed October 5 at 15:13:08 UTC. This is a dated source snapshot, not a permanent latest-head claim.

## CI supplies no actionable test trace

The bounded snapshot of failed main runs created since 14:00 UTC returned:

| Run | Source | Evidence |
| --- | --- | --- |
| [37331034051](https://github.com/NousResearch/hermes-agent/actions/runs/37331034051) | `824a942e` | Zero jobs; log not found |
| [37325346242](https://github.com/NousResearch/hermes-agent/actions/runs/37325346242) | `f4329126` | Zero jobs |
| [37323526450](https://github.com/NousResearch/hermes-agent/actions/runs/37323526450) | `2efd6961` | Zero jobs |

These workflow failures provide no ordinary test name or traceback. No source regression, infrastructure root cause, or actionable unowned fix was inferred. No workflow was rerun.

## Auxiliary retry artifact has a specific integration boundary

Published `f6792ca7eadf6aac33df2215ecd90818c9189963` remains qualified on historical base `715742`: two final real AsyncOpenAI/synthetic HTTP consumers, 78 previously tested unchanged neighbors, and 11 checks. This audit did not merge, rebase, or rerun it.

Between `ac28abc9` and `824a942e`, these inputs are byte-identical: `agent/auxiliary_client.py`, `agent/auxiliary_codex_response.py`, `agent/codex_responses_adapter.py`, `agent/auxiliary_hooks.py`, `agent/auxiliary_wire.py`, `agent/relay_llm.py`, `pyproject.toml`, and `uv.lock`. This preserves the previously inspected ac28 changes; it does **not** make the delivered artifact equivalent to current main. Other current changes include Codex runtime/native compaction, gateway/platforms, approvals, and Desktop code; those were not qualified here.

The artifact routes same-provider retries through existing progress wrappers with `force_stream` and extracts preparation into a sibling. Earlier ac28 changes instead added issuer-sensitive Codex normalization and completion/phase handling. The nine retry/progress/relay functions previously compared remain unchanged. Progress wrappers recognize internally streaming clients and return their completed adapter response without external reaggregation. The new parser maps incomplete non-tool-call responses to `length`, preserves completed `tool_calls`, and retains usage.

**Remaining uncertainty:** the combined same-provider recovery callback and internally streaming Codex adapter must preserve issuer/phase/completion semantics and internal progress signaling through validation. The artifact's two final consumers cover external Chat Completions streaming with and without hooks; upstream normalization tests cover a separate boundary. Neither recorded qualification proves the composed recovery path. This is an integration question, not an observed defect or permission to duplicate another lane's provider work. Any future integration needs owner/scope coordination and preserved author history.

Provenance: nonbundled local receipts `/workspace/receipts/h5-current-ci-1513/`, `/workspace/receipts/source-delta-ac28/`, and `/workspace/receipts/aux-retry-progress-owner-port.md`. Exact source comparisons were read-only. No blanket runtime equivalence or new test pass is claimed.
