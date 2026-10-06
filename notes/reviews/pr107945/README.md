# Review companion: Hermes #107945

Exact reviewed head: `03002b88f404fd6929c365da6f4c3deffd59ecf9`.

This branch holds **patch files and review evidence**, not an already-applied runtime fix. It starts at the author's exact head. No competing upstream PR was opened, and author adoption is not claimed.

## Credit

- Per-task routing implementation and duplicate comparison: **KoNit-K**.
- Earlier resolve-all-first/cleanup approach in #77953: **apoapostolov**, identified in [KoNit-K's comparison](https://github.com/NousResearch/hermes-agent/pull/107945#issuecomment-5630259993). The cleanup gap is therefore a previously acknowledged issue, not a new discovery claimed here.
- This exact-head regression pass and the two offered patches: **kvnloo**.

## Findings and bounded repairs

### P2: partial batch construction abandons earlier children

At `tools/delegate_tool.py:412`, a later task's provider lookup can fail after a previous child has already been constructed. `except ValueError: return [], str(exc)` discards the accumulated list. In the production builder, returned children have dedicated SessionDB ownership and are attached to the parent's interrupt list; the normal runner, which owns cleanup, is never reached.

The controlled regression builds a valid child followed by an unknown provider, a missing-key provider or a missing ACP command. Original behavior allocates the first child; it remains attached and unclosed when the later pin rejects. Separate constructor-failure cases demonstrate the same ownership problem even after routes are resolvable.

[delegate-batch-preflight.patch](delegate-batch-preflight.patch) first resolves every task route, then wraps construction in `ExitStack` using the existing `_close_child` and `_detach_child` helpers. Success transfers ownership to the normal runner; error cleanup does not touch unrelated parent children. This changes no public schema or tool policy.

### P2: an unused default route blocks a valid explicit task route

`delegate_task()` resolves the global routing config before it normalizes tasks or reaches the per-task overlay. A configured but unavailable default provider prevents a task explicitly pinned to a healthy provider from being considered. The model-only equivalent occurs when the default model is unavailable but the task pins a supported model on that provider.

[delegate-unused-default.patch](delegate-unused-default.patch) validates task shape first, resolves the shared route only when a child inherits it without a route pin, and otherwise obtains the existing neutral inheritance bundle without touching the unused provider. Pinned overlays still go through the normal resolver, including its missing-key/command checks. Unpinned siblings still require a valid default. This is separate from the cleanup patch.

For all-pinned batches the shared model/provider metadata is unset; individual children retain their actual resolved routes. The background dispatcher runs the prebuilt child objects; its shared model field is metadata, not a request-time reroute. Full background/UI acceptance still needs checking in a complete checkout.

## Tests actually executed

Environment: Linux, CPython **3.13.5**, pytest **9.0.2**, plugin autoload disabled.

The 26-case harness executes selected source functions from the pinned revision: task overlays, delegation credential resolution, fallback selection, batch construction and cleanup. External provider resolution, child construction, validation/UI helpers, configuration and final execution are controlled doubles. Resource-bearing fake children own real temporary SQLite connections; they are NOT actual AIAgent/SessionDB instances.

| Variant | Passing | Failing |
|---|---:|---:|
| Original selected source | 17 | 9 |
| Cleanup/preflight patch only | 24 | 2 |
| Unused-default patch only | 19 | 7 |
| Both patches | 26 | 0 |

Controls include successful ownership transfer, invalid first/later pins, constructor and progress-wrapper exceptions, best-effort close failures, unrelated parent children, mixed routes, model-only direct endpoints, blank/nonstring inheritance, request-override copies, and unchanged fallback ownership.

The adjacent [test_regressions.py](test_regressions.py) is a smaller handoff set using the production facade imports and controlled resolver/constructor boundaries. Against the same local source adapter: **1 passed / 5 failed** before, **6 passed** after. These overlap the 26 cases; do not add them as independent coverage. They still need execution under the actual repository's conftest and runner.

Both production patches were `git apply --check`-checked and applied to a fresh **source-bearing excerpt**; the result exactly matched the tested repaired excerpt. This is NOT a full-checkout apply or test claim. GitHub DNS prevented cloning. The source excerpts were transcribed from connector reads; they are not represented as complete hash-verified modules.

Not run: the author's full tests, complete Hermes imports/installation, real credential pools/refresh, native platform or live model calls, actual background/resume/restart behavior, full CI, or a merged #89936 composition. Exact-head upstream CI/Docker/Nix runs were `action_required`, not passing, when checked.

## Apply in the author's complete checkout

Copy the two patch files outside the checkout, then:

```bash
git apply --check /path/to/delegate-batch-preflight.patch /path/to/delegate-unused-default.patch
git apply /path/to/delegate-batch-preflight.patch /path/to/delegate-unused-default.patch
# Copy test_regressions.py to tests/tools/test_delegate_route_preflight.py first.
bash scripts/run_tests.sh tests/tools/test_delegate_route_preflight.py tests/tools/test_delegate_task_provider_pin.py
```

These are suggested acceptance commands, not commands claimed to have run against a full checkout here. Preserve the original author's commits; apply/cherry-pick a repair onto their existing branch rather than replace the feature.

## Composition with neighboring work

#89936 (`1d36b4148cd274f8d629be185972efc74453c015`) adds per-task and top-level reasoning effort, but its patch targets the older pre-split builder. On the #107945 head, reasoning is assembled by `tools/delegate_tool_config.py::_resolve_child_runtime`. A rebase must carry the effort through that actual constructor path; a textual addition to the obsolete location is insufficient.

The composition witness to add after rebasing is a mixed `{provider, model, reasoning_effort}` batch, checking each child's final constructor kwargs, unchanged parent configuration, explicit child fallback ownership, and no resources leaked if a later route is invalid. This is a proposed acceptance test, not an executed merged-branch result.

Reasoning-work credit: **teknium1**, **daveinturkey15-byte** for the preserved #81921 lifecycle plumbing, and **Sebastian Müller** for Prime Agent #1510's design reference.

#112741 (DresvyanskiyDenis) proposes a broader provider/model/reasoning/toolsets surface plus cross-provider grants. That is a maintainer API/policy choice, not something these two narrow repairs silently absorb.

## Source anchors

- [Per-task overlay and build failure](https://github.com/NousResearch/hermes-agent/blob/03002b88f404fd6929c365da6f4c3deffd59ecf9/tools/delegate_tool.py#L379-L441)
- [Eager default preflight](https://github.com/NousResearch/hermes-agent/blob/03002b88f404fd6929c365da6f4c3deffd59ecf9/tools/delegate_tool.py#L489-L526)
- [Child resource/attachment ownership](https://github.com/NousResearch/hermes-agent/blob/03002b88f404fd6929c365da6f4c3deffd59ecf9/tools/delegate_tool.py#L230-L301)
- [Existing cleanup helpers](https://github.com/NousResearch/hermes-agent/blob/03002b88f404fd6929c365da6f4c3deffd59ecf9/tools/delegate_tool_child_run.py#L45-L79)

Recorded upstream file blob IDs (provenance metadata, not a claim of complete local-file verification): delegate_tool.py `571e4772bef17cef71039d1fe5fbc3381749e465`; delegate_tool_config.py `6fe745e7f96444b4e12895e1315070c2b730cf38`; delegate_tool_child_run.py `7d49038a8df4bc5729e2ed68938feecda8d1260e`.
