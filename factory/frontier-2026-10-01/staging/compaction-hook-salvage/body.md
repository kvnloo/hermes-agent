Seven open PRs add plugin hooks around context compaction, each under its own names: #53806, #93391, #118847, #119347, #125881, #4123 and #7150 (#7150 adds the names without a call site). #64231's verdict table salvages #53806 as an observer, and #118382 asks for a plugin signal after compaction. I brought four of them onto current main (`44a1ce97`), merged, re-applied or hand-ported, and ran one behaviour-contract test against each; the table says why the other three were not run. The test fails on main and passes with #53806 plus the fold-in below. It is one commit on main, on the branch [kvnloo/hermes-agent `staged/compaction-hook-salvage`](https://github.com/kvnloo/hermes-agent/tree/staged/compaction-hook-salvage) ([commit](https://github.com/kvnloo/hermes-agent/commit/1ab964166a125b64ea4d5c05e7f5813bffd7bb2d)). The combined production diff is in the collapsed block at the end; it applies with `git apply` on top of that commit.

Proposed disposition:

| issue | carrier (author) | fold in | close after the carrier merges | keep open |
|---|---|---|---|---|
| #118382 (also the #53806 row of #64231; #8643 folds here) | #53806 (ledfoot631). Its post-commit call becomes `on_compression_complete`; its start-side `pre_context_compression` stays, pending point 1 below | the contract test and the fold-in below, with the `Co-authored-by` trailers listed under it | #93391 (same start-side seam as `pre_context_compression`, if that stays), #118847 (post-compaction signal for #118382, now fired after the commit), #4123 (`pre_compact` before the summarizer and `post_compact` at the end of `compress_context`; nothing of it is reused) | #125881 (fail-closed policy gate: a different contract that composes with the observer), #119347 (summarizer-input transform, the #120582 data-loss class), #7150 (its main change is a `pre_tool_call` redirect; its `pre_compress`/`post_compress` names have no fire site in its diff and could be dropped from it) |

**What the test pins** (`tests/agent/test_compaction_observer_hook_contract.py`, 2 tests, 7 cases). Rotated, in-place and manual `/compress` compactions each fire `on_compression_complete` exactly once. When the callback runs, the compacted transcript is already durable under the session id it is handed, the commit fence has no commit in flight, and the session's compression lease is free. The payload carries `session_id`, `old_session_id`, `in_place` and before/after tokens. Three attempts that commit nothing stay silent: a failed summary under `compression.abort_on_summary_failure: true`, the commit site's would-grow refusal, and a SessionDB write failure. Each first checks that the session id and its state.db rows are unchanged, and the first two also check the compressor's abort or refusal flag. A manual compress that its host discards stays silent too, even after a later `finalize(committed=True)`; there the compacted rows are written (the case checks that), and only the host's discard keeps the observer quiet. A raising subscriber and a directive-shaped return leave the compacted messages and system prompt byte-identical. The run goes through real `AIAgent`, `SessionDB`, `ContextCompressor` and `CompressionCommitFence`; only the summary call (and, for the write failure, the SessionDB write) is replaced, and agent init's model-metadata lookups are stubbed, so the test makes no network request.

**Results on main `44a1ce97`** (each row: contract cases that pass, out of 7, under that candidate's own hook name; 3 runs each, all runs agree):

| candidate | how it was brought onto main | hook | cases that pass | what fails |
|---|---|---|---|---|
| main | n/a | none | 4 of 7 (the 4 silent cases pass trivially) | no compression hook |
| #53806, post-commit call | hand-port (the PR conflicts in 11 files, 33,698 commits behind) | `on_session_start(boundary_reason="compression")` | 3 of 7 | fires before a manual `/compress` host commits and after a discard; no `in_place` or token fields; runs inside the commit fence with the lease held |
| #53806, start-side call | same hand-port | `pre_context_compression` | 0 of 7 | fires before the summarizer on every attempt (start-side by design) |
| #93391 | code and tests apply; 3 docs files conflict | `pre_compression` | 0 of 7 | the same start-side seam |
| #118847 | one-hunk hand-port | `post_compaction` | 1 of 7 | fires inside `ContextCompressor.compress()`, before the commit, so it announces the refused growing summary (after_tokens > before_tokens), failed SessionDB writes and a discarded manual compress; its `session_id` is the pre-rotation id |
| #125881 | merges clean | `pre_compression_commit` | 1 of 7 | a fail-closed admission gate: a subscriber that does not answer `allow` blocks the compaction. That is its intended contract, not an observer's |
| #119347 | 3 semantic conflicts at the pruned-copy seam | `transform_compaction_input` | not run | a transform, not an observer |
| #4123 | not run: conflicts in 3 files, 37,736 commits behind | `pre_compact`, `post_compact` | not run | the payload is `session_id` and `project_dir` only |
| #7150 | not run: 42,445 commits behind | `pre_compress`, `post_compress` | not run | the names are added to `VALID_HOOKS` with no call site |
| **#53806 + fold-in** | built on main | `on_compression_complete` | **7 of 7** | none |

The same call placed next to the context-engine notify, inside the commit fence, passes 5 of 7: the rotated and in-place cases fail on the fence assertion. Moving the call to just before the commit passes 1 of 7, bypassing the manual deferral passes 5 of 7, and dropping either token value passes 4 of 7. `replay_gates` still passes 11 of 11 checks, `ab_checkpoint_preflight` compress-call counts are unchanged, and `test_region_scoping` passes. In 20 adjacent test files (compression commit, rotation and fence, manual compress, plugins, hooks CLI, shell hooks, memory session switch), the only difference from main is the new test.

**The #118120 hazard and #127058.** #118120 (nirvana6) shows a memory-provider hook that blocked inside the compaction commit fence: the interrupt path waits on the fence lock, so the session could only be killed. #127058 (Finn763, open) fixes it by delivering `on_session_switch` after `finish_commit()`. A plugin observer inside that fence would bring the hazard back for any third-party plugin, so the fold-in delivers `on_compression_complete` the same way #127058 delivers the memory hook, and the test asserts it. The two diffs touch the same region of `compress_context`, so I merged #127058's head (`f306319f`) into the fold-in: there is one conflict, where both append a delivery after `commit_fence.finish_commit()`, and keeping both resolves it. With both applied, the contract test passes 7 of 7, #127058's own test passes, and its four named neighbour files pass 92 of 92 tests, as they do with #127058 alone.

**What the fold-in changes.**
- New plugin hook `on_compression_complete`: once per committed local compaction, after the compacted transcript is durable and after the attempt has released its commit fence and the session's compression lease. A manual `/compress` fires it from the host's `finalize(committed=True)` and never after a discard. Payload: `session_id` (current), `old_session_id` (the same id when compacted in place), `in_place`, `tokens_before` (the caller's estimate or `None`), `tokens_after` (rough estimate), `platform`. Return values are ignored, and a raising callback is logged and skipped.
- `on_compression_complete` joins `_HOOK_TIMEOUT_BOUNDED_HOOKS`, so a slow callback is abandoned after `plugins.hook_callback_timeout` (default 30s). #53806's post-commit call went through `on_session_start`, which is already bounded.
- #53806's `pre_context_compression` fires before the summarizer on every attempt, committed or not, and hands plugins the full transcript as `conversation_history` (on current main that includes the session store's row metadata). Three changes from #53806's compression commit: main moved the summarizer call out of `compress_context`, so the call sits in `_run_summary_phase`, still right after the memory providers' pre-compress step; `task_id` is passed into that function so the payload keys are #53806's; and the call goes through `hermes_cli.lifecycle.invoke_hook` (first-party observers, then plugins), as 12 of the 13 files under `agent/` and `gateway/` that dispatch hooks do, instead of `hermes_cli.plugins.invoke_hook`. #53806's `agent/agent_init.py` and `hermes_cli/hooks.py` hunks and its resume-hook commit are left out.
- Both names join `VALID_HOOKS`, which is also the shell-hook allow-list, so `hooks:` entries for them become valid. `hermes hooks test on_compression_complete` gets a payload, and the hooks catalog in `hooks.md` gets an `on_compression_complete` row. `pre_context_compression` has neither yet.
- Both dispatches live in a new sibling, `agent/conversation_compression_observer.py` (82 lines). The facade `agent/conversation_compression.py` gets 16 added lines and 1 changed line: the two calls into the sibling and the `task_id` plumbing.
- No existing hook changes behaviour.

Three points need a maintainer call.

1. The start-side hook. #64231 asks for `pre_context_compression` to become `on_compression_start`. The fold-in does not rename it. Nothing above tests it, #118382 needs only the post-commit signal, and the hook hands plugins the full transcript before every attempt. It runs before the commit fence is entered, so it cannot block an interrupt the way #118120 describes, but it runs with the session's compression lease held and, as in #53806, it is not timeout-bounded. Its name, payload, bound and docs row are the author's and your call. Dropping it also works: the fold-in passes 7 of 7 without it, and the `task_id` plumbing goes with it.
2. Manual `/compress`. The test treats it the way the context engine is treated today: the observer waits for the host to commit its own history and stays silent if the host discards it. If you prefer "fire once state.db holds the compacted rows", delete the `manual_discarded` case and the `fired == []` line before finalize.
3. The timeout bound. It is on by default; the test does not depend on it, so removing the one line in `_HOOK_TIMEOUT_BOUNDED_HOOKS` leaves 7 of 7.

Not tested: native and Codex app-server compaction (they never run a local commit, so the hook cannot fire there); agents without a SessionDB; a real summarizer; the per-host manual `/compress` handlers (the deferral is driven through `compress_context` and `finalize_context_engine_compression_notification`); a shell hook run against a real compaction; a hung subscriber; an actual interrupt issued while the observer runs (the test checks the fence state that the interrupt path waits on). With the default `abort_on_summary_failure: false`, a failed summary commits the deterministic fallback summary, and the observer fires once for it; I checked that on a 61-message window outside the committed test.

Credit: the fold-in reuses #118847's before/after token counts (Baophan00), #93391's `in_place` flag (clomp42) and #127058's delivery after the fence (Finn763), so its trailers credit them. Thanks to carlosrenatoy for #118382 and nirvana6 for the #118120 trace. The contract test, the fold-in (including the sibling module and the port of #53806's start-side call), the A/B harness and this text were written with AI assistance (Claude Code). Every number above comes from a local run of that harness on main `44a1ce97`.

<details>
<summary>Combined diff on current main: #53806's start-side hook ported, plus the fold-in (apply on top of the test commit)</summary>

Trailers for the fold-in commit (author: ledfoot631, as #53806's author):

```
Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>
Co-authored-by: Baophan00 <109447498+Baophan00@users.noreply.github.com>
Co-authored-by: clomp <277387657+clomp42@users.noreply.github.com>
Co-authored-by: finn763 <165816600+finn763@users.noreply.github.com>
```

```diff
diff --git a/agent/conversation_compression.py b/agent/conversation_compression.py
index f832e65dd7..2e9cb5a9d1 100644
--- a/agent/conversation_compression.py
+++ b/agent/conversation_compression.py
@@ -3889,7 +3889,7 @@ def _run_summary_phase(
     agent: Any, messages: list, *, lease: _CompressionLease, in_place: bool, checkpoint_required: bool,
     approx_tokens: Optional[int], focus_topic: Optional[str], force: bool, bypass_cooldown: bool,
     commit_fence: Optional[CompressionCommitFence], hard_cancel_event: Any, system_message: str,
-    attempt: _Attempt,
+    attempt: _Attempt, task_id: str,
 ) -> _SummaryPhase:
     """Adopt a grown durable parent, gather memory context and run the summarizer.
     A hard cancel restores the compressor snapshot + live list, records a stall backoff while the lease is
@@ -3922,6 +3922,11 @@ def _run_summary_phase(
             bypass_cooldown=bypass_cooldown,
         )
         messages_before_compression = copy.deepcopy(messages)
+        from agent.conversation_compression_observer import notify_compression_start
+
+        notify_compression_start(
+            agent, messages, task_id=task_id, approx_tokens=approx_tokens, focus_topic=focus_topic, force=force,
+        )
         _activity_heartbeat = _CompressionActivityHeartbeat(
             agent, commit_fence=commit_fence, emit_client_status=lease.status_emitted,
         ).start()
@@ -4179,12 +4184,14 @@ def compress_context(
         agent, messages, lease=lease, in_place=in_place, checkpoint_required=checkpoint_required,
         approx_tokens=approx_tokens, focus_topic=focus_topic, force=force, bypass_cooldown=bypass_cooldown,
         commit_fence=commit_fence, hard_cancel_event=_hard_cancel_event, system_message=system_message, attempt=attempt,
+        task_id=task_id,
     )
     if phase.abort_prompt is not None:
         return phase.messages, phase.abort_prompt
     messages, compressed = phase.messages, phase.compressed
     messages_before_compression = phase.messages_before_compression
     approx_tokens, _pre_msg_count = phase.approx_tokens, phase.pre_msg_count
+    _compression_complete = None  # on_compression_complete; runs in ``finally`` after fence + lease release
     _commit_fence_entered = False
     try:
         # Capture the verdict before rotation callbacks: lifecycle hooks may reset
@@ -4263,6 +4270,12 @@ def compress_context(
             compression_made_progress=commit.made_progress, compression_used_fallback=_compression_used_fallback,
             compression_feasibility_skip=_compression_feasibility_skip, task_id=task_id,
         )
+        from agent.conversation_compression_observer import stage_compression_complete
+
+        _compression_complete = stage_compression_complete(
+            agent, commit, deferred=defer_context_engine_notification, tokens_before=approx_tokens,
+            tokens_after=_compressed_est,
+        )
         logger.info(
             "context compression done: session=%s messages=%d->%d rough_tokens=~%s awaiting_real_usage=true",
             agent.session_id or "none", _pre_msg_count, len(compressed), f"{_compressed_est:,}",
@@ -4284,6 +4297,8 @@ def compress_context(
         finally:
             if _commit_fence_entered:
                 commit_fence.finish_commit()
+            if _compression_complete is not None:
+                _compression_complete()
 
 
 def _codex_compaction_cooldown_remaining(agent: Any) -> float:
diff --git a/agent/conversation_compression_observer.py b/agent/conversation_compression_observer.py
new file mode 100644
index 0000000000..02dcc0cd5e
--- /dev/null
+++ b/agent/conversation_compression_observer.py
@@ -0,0 +1,82 @@
+"""Plugin hooks at the local compaction boundary.
+
+``pre_context_compression`` runs before the summarizer on every attempt, whether or not it commits.
+
+``on_compression_complete`` runs once per committed local compaction, after the compacted transcript
+is durable. The facade runs it only after the attempt has released its commit fence and the session's
+compression lease, so a slow plugin can neither make an interrupt wait on the fence lock (#118120) nor
+hold up the session's next compaction. A manual ``/compress`` defers it with the context-engine
+notification: it fires from the host's ``finalize_context_engine_compression_notification`` after
+the host commits, and never after a discard.
+
+Both are observers: return values are ignored and a raising callback is logged and skipped.
+"""
+
+from __future__ import annotations
+
+import logging
+from typing import Any, Callable, Optional
+
+logger = logging.getLogger(__name__)
+
+
+def notify_compression_start(
+    agent: Any, messages: list, *, task_id: str, approx_tokens: Optional[int], focus_topic: Optional[str],
+    force: bool,
+) -> None:
+    """Tell ``pre_context_compression`` plugins that older turns are about to be summarized."""
+    try:
+        from hermes_cli.lifecycle import invoke_hook
+
+        invoke_hook(
+            "pre_context_compression", session_id=agent.session_id or "", task_id=task_id,
+            conversation_history=list(messages), approx_tokens=approx_tokens, focus_topic=focus_topic,
+            force=force, model=getattr(agent, "model", ""), platform=getattr(agent, "platform", None) or "cli",
+            conversation_id=getattr(agent, "_gateway_session_key", None),
+        )
+    except Exception:
+        logger.debug("plugin pre_context_compression failed", exc_info=True)
+
+
+def _invoke_compression_complete(payload: dict) -> None:
+    try:
+        from hermes_cli.lifecycle import has_hook, invoke_hook
+
+        if has_hook("on_compression_complete"):
+            invoke_hook("on_compression_complete", **payload)
+    except Exception:
+        logger.debug("plugin on_compression_complete failed", exc_info=True)
+
+
+def stage_compression_complete(
+    agent: Any, commit: Any, *, deferred: bool, tokens_before: Optional[int], tokens_after: Optional[int],
+) -> Optional[Callable[[], None]]:
+    """The ``on_compression_complete`` call this attempt owes, for the caller to run once its commit
+    fence and lease are released. ``None`` when nothing committed, or when the call is deferred.
+
+    The condition is the context-engine notification's in ``_finish_compaction_boundary``. A deferred
+    call is chained onto that notification's pending slot, so the host's finalize fires both or neither.
+    """
+    if not (commit.session_commit_succeeded and (commit.old_session_id or commit.compacted_in_place)):
+        return None
+    session_id = agent.session_id or ""
+    old_session_id = commit.old_session_id or session_id
+    payload = {
+        "session_id": session_id, "old_session_id": old_session_id, "in_place": session_id == old_session_id,
+        "tokens_before": tokens_before, "tokens_after": tokens_after,
+        "platform": getattr(agent, "platform", None) or "cli",
+    }
+    if not deferred:
+        return lambda: _invoke_compression_complete(payload)
+    from agent.conversation_compression import _PENDING_CONTEXT_ENGINE_NOTIFICATION
+
+    pending = getattr(agent, _PENDING_CONTEXT_ENGINE_NOTIFICATION, None)
+    if callable(pending):
+        def _notify_then_observe() -> bool:
+            try:
+                return pending()
+            finally:
+                _invoke_compression_complete(payload)
+
+        setattr(agent, _PENDING_CONTEXT_ENGINE_NOTIFICATION, _notify_then_observe)
+    return None
diff --git a/hermes_cli/hooks.py b/hermes_cli/hooks.py
index 0586aec24e..559bcd4f9f 100644
--- a/hermes_cli/hooks.py
+++ b/hermes_cli/hooks.py
@@ -131,6 +131,10 @@ _DEFAULT_PAYLOADS = {
     },
     "on_session_finalize": {"session_id": "test-session"},
     "on_session_reset": {"session_id": "test-session"},
+    "on_compression_complete": {
+        "session_id": "test-session-2", "old_session_id": "test-session", "in_place": False,
+        "tokens_before": 120000, "tokens_after": 30000, "platform": "cli",
+    },
     "pre_api_request": {
         "session_id": "test-session", "task_id": "test-task", "platform": "cli",
         "model": "claude-sonnet-4-6", "provider": "anthropic",
diff --git a/hermes_cli/plugins.py b/hermes_cli/plugins.py
index 02222185a2..ca50c90cdf 100644
--- a/hermes_cli/plugins.py
+++ b/hermes_cli/plugins.py
@@ -131,6 +131,17 @@ VALID_HOOKS: Set[str] = {
     # error_body may be unredacted.
     "transform_api_error_classification", "on_session_start", "on_session_end",
     "on_session_finalize", "on_session_reset",
+    # Fired immediately before context compression drops/summarizes older
+    # turns. Observer-only: return values are ignored. Plugins can persist
+    # task-state or handoff breadcrumbs without mutating the live message list.
+    "pre_context_compression",
+    # on_compression_complete: once per local compaction, AFTER the compacted transcript is durable and
+    # the attempt has released its commit fence and lease (agent/conversation_compression_observer.py;
+    # a manual /compress waits for its host's commit). Never for an attempt that did not commit, nor
+    # for native/Codex server-side compaction. Kwargs: session_id (current), old_session_id (same id
+    # when in_place), in_place, tokens_before (caller estimate or None), tokens_after (rough
+    # estimate), platform. Observer; returns ignored; fail-open; bounded by hook_callback_timeout.
+    "on_compression_complete",
     # on_skill_lifecycle: successful skill lifecycle facts (local skill name visible to plugins).
     "on_skill_lifecycle", "subagent_start", "subagent_stop",
     # pre_gateway_dispatch: once per incoming MessageEvent, after the internal-event guard, BEFORE
diff --git a/hermes_cli/plugins_dispatch.py b/hermes_cli/plugins_dispatch.py
index 78c3927fc4..66bde275a0 100644
--- a/hermes_cli/plugins_dispatch.py
+++ b/hermes_cli/plugins_dispatch.py
@@ -43,6 +43,7 @@ _HOOK_TIMEOUT_BOUNDED_HOOKS: Set[str] = {
     "post_tool_call", "transform_terminal_output", "transform_tool_result", "transform_llm_output",
     "pre_llm_call", "post_llm_call", "pre_api_request", "post_api_request", "api_request_error",
     "pre_auxiliary_call", "post_auxiliary_call", "pre_verify", "on_session_start", "on_session_end",
+    "on_compression_complete",
 }
 
 # Policy hooks: timeout / still-running must fail closed (block the tool).
diff --git a/website/docs/user-guide/features/hooks.md b/website/docs/user-guide/features/hooks.md
index 59975d14ed..baac0ce1a2 100644
--- a/website/docs/user-guide/features/hooks.md
+++ b/website/docs/user-guide/features/hooks.md
@@ -471,6 +471,7 @@ Payload fields below are the exact event-specific fields supplied by each call s
 | `on_session_end` | Observer | Canonically at each turn finalization; CLI/TUI exits have additional reduced legacy shapes. Return ignored. | Canonical: `session_id`, `task_id`, `turn_id`, `completed`, `failed`, `interrupted`, `turn_exit_reason`, `model`, `platform`; exit paths may add `reason`/`api_request_id` and omit fields. | IDs, model/platform, and outcome; canonical payload has no message body. |
 | `on_session_finalize` | Observer | CLI/TUI/gateway teardown through `finalize_session`; gateway shutdown may finalize without a reset. Return ignored. | Surface-dependent `session_id`, `platform`, optionally `reason`, `old_session_id`, `new_session_id` | Session and routing identifiers. |
 | `on_session_reset` | Observer | CLI/TUI session boundary and gateway after the replacement session exists; return ignored. | CLI: `session_id`, `platform`, `reason`; TUI: `session_id`, `platform`; gateway: those plus `reason`, `old_session_id`, `new_session_id` | Session and routing identifiers. |
+| `on_compression_complete` | Observer | Once per local context compaction, after the compacted transcript is durable in the session store and the compaction has released its commit fence and session lock, so a slow callback cannot hold up an interrupt; a manual `/compress` waits for its host to commit and stays silent if the host discards it. Never for an attempt that did not commit (aborted summary, would-grow refusal, store write failure), and never for native or Codex server-side compaction. Timeout-bounded; return ignored; a raising callback is logged and skipped. | `session_id` (current), `old_session_id` (equal to `session_id` when compacted in place), `in_place`, `tokens_before` (caller's estimate or `None`), `tokens_after` (rough estimate), `platform` | Session identifiers and token counts only; no message body. |
 | `agent_loop_stopped` | Observer | Immediately after a real running agent is interrupted — gateway `_interrupt_and_clear_session` or TUI/desktop `session.interrupt`; return ignored. | `session_key`, `platform`, `reason`, `invalidation_reason` | Session/routing identifiers and interruption reasons; no message body. |
 | `on_skill_lifecycle` | Observer | After an authoritative skill-usage state change; return ignored. | `action`, `skill_name`, `provenance`, `task_id`, `session_id`, `use_count`, `reused`, `reuse_after_patch` | Exposes the local skill name and provenance. |
 | `subagent_start` | Observer | Child constructed and about to run; return ignored. | `parent_session_id`, `parent_turn_id`, `parent_subagent_id`, `child_session_id`, `child_subagent_id`, `child_role`, `child_goal` | Child goal may contain user/project content. |
```

</details>
