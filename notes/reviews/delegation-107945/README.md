# Per-task route review — Hermes #107945

## Provenance

Original route-pin feature: **KoNit-K**. The partial-batch resource risk and resolve-all-first precedent were already called out in [KoNit-K's comparison](https://github.com/NousResearch/hermes-agent/pull/107945#issuecomment-5630259993) with **apoapostolov's #77953**; this review does not claim that observation as new. Current-head regression verification and the bounded repair below: **kvnloo**.

Reviewed head: `03002b88f404fd6929c365da6f4c3deffd59ecf9`.

This branch contains review notes and an offered patch only. It does not change Hermes production files, replace the original PR, or claim author adoption.

## Findings

### P2 — later route failure abandons earlier constructed children

`_build_children()` resolves a route immediately before constructing each child. A ValueError for a later task returns `([], error)` without closing or detaching earlier children. The real constructor opens a dedicated SessionDB handle, creates the child, attaches it to the parent, and emits `subagent.spawn_requested`; `_run_batch` and its normal cleanup are never entered after this error.

The source-excerpt harness reproduced invalid pins at indices 1, 2 and 3. Respectively 1, 2 and 3 constructor doubles had already been created and retained by the parent; none was closed, and the batch dispatcher was never called. The constructor double explicitly models that observed ownership transfer; this is not a full AIAgent/SQLite resource-leak test.

The adjacent `route-preflight.patch` resolves all task routes before creating any child. It preserves the existing resolver, overlay semantics, order and construction thread. It fixes this *route-resolution* failure window only; it does not add a general constructor-exception rollback mechanism.

### P2 — an unused default route blocks fully pinned tasks

`delegate_task()` resolves the global/call-level routing config before examining per-task pins. A configured default provider with no usable credential fails there even when every task pins a different, successfully resolvable provider/model.

Control: the real resolver excerpt resolves the explicit healthy task overlay successfully. The public-function excerpt still returns the signed-out default's error before looking up the healthy route, with either `background=False` or `True`. No child starts. Unpinned tasks correctly continue to reject that unavailable default.

This needs task-aware route planning: validate the normalized task set, resolve the default only where an effective task route needs it, and finish route preflight before constructing children. Do not simply catch the error and silently inherit.

**The offered patch deliberately does not fix this second finding.** Batch-level metadata and defaults must be reconciled with the chosen per-task route plan rather than supplied arbitrary credentials.

## Exact source anchors

- [Overlay and build loop](https://github.com/NousResearch/hermes-agent/blob/03002b88f404fd6929c365da6f4c3deffd59ecf9/tools/delegate_tool.py#L360-L440).
- [Public preflight ordering](https://github.com/NousResearch/hermes-agent/blob/03002b88f404fd6929c365da6f4c3deffd59ecf9/tools/delegate_tool.py#L486-L536).
- [Dedicated child resources and parent attachment](https://github.com/NousResearch/hermes-agent/blob/03002b88f404fd6929c365da6f4c3deffd59ecf9/tools/delegate_tool.py#L232-L286).
- [Real delegation credential resolver](https://github.com/NousResearch/hermes-agent/blob/03002b88f404fd6929c365da6f4c3deffd59ecf9/tools/delegate_tool_config.py#L331-L384).

The enclosing Git blobs returned by GitHub were `571e4772bef17cef71039d1fe5fbc3381749e465` (delegate_tool.py) and `6fe745e7f96444b4e12895e1315070c2b730cf38` (delegate_tool_config.py). The executable harness uses manually transcribed function excerpts, **not complete blob-verified modules**. These blob IDs identify the fetched source; they are not claims that the excerpt files hash to those blobs.

## Tests actually executed

Linux, Python 3.13.5, pytest 9.0.2; DNS/network calls forbidden in the harness.

| Same 18-case function-level harness | Result |
|---|---|
| Original pinned source excerpts | 13 passed / 5 failed |
| Minimal route-preflight repair | 16 passed / 2 failed |
| Fresh excerpt copy, git apply --check + git apply, rerun | 16 passed / 2 failed |

The two remaining failures are the unused-default cases. The three runs repeat the same 18 cases; do not sum them as distinct coverage. Controls include first-pin refusal, inherited missing credentials, blank/non-string pins, mixed endpoints and credentials, model-only inheritance, explicit fallback config propagation, repeated calls without pin leakage, background dispatch plumbing and detached nested request overrides.

Constructor, runtime-provider account discovery, UI/logging, input normalization and final dispatch are test doubles. Credential resolution and the reviewed function control flow are source excerpts. No full Hermes checkout/suite, real provider auth, retry/resume integration, native platform acceptance, billed request, or CI-green claim is made. Container DNS could not resolve github.com.

## Minimal repo regression to carry with the repair

The expected invariant is: with task 0 valid and task 1's explicit provider failing resolution, `_build_children` must return the route error without calling `_build_child_preserving_parent_tools` at all. Retain inverse controls for valid mixed-route construction and invalid task 0. This should be added to the repository's existing per-task tests and executed with `scripts/run_tests.sh` in a full checkout.

## Composition with #89936 — source check only

The upstream #89936 head `1d36b4148cd274f8d629be185972efc74453c015` still uses the old monolithic delegate layout. **Eva / @100yenadmin** has already provided a modular-layout rebase at `a26963073d8dfb8c6d9df381dbc284e5e4d68a4b`:
https://github.com/100yenadmin/hermes-agent-for-upstream-PR-only/tree/salvage/89936-lifecycle-reasoning-effort

It retains credit for **Dave Hatton / @daveinturkey15-byte**, **Teknium**, and the **Sebastian Müller / Prime Agent** design reference recorded upstream. Reuse that work instead of creating another rebase.

Both changes meet at `_build_children`: resolve each task's route and normalized reasoning override before passing them to `_build_child_preserving_parent_tools`; the child runtime receives provider/model/endpoint credentials together with `override_reasoning_effort`. Keep current image/owner/fallback plumbing when combining signatures. This is a source-level integration observation, not a merged or tested combined implementation.
