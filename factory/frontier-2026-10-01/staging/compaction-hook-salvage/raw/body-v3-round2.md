TITLE: Compaction observer hook for #118382: #53806 A/B-checked against one observer contract, plus a fold-in

Five open PRs add a plugin hook around context compaction, each with its own name and fire point. #64231's verdict table salvages #53806 as an observer, and #118382 asks for a plugin signal after compaction. I merged or hand-ported each candidate onto current main and ran one behaviour-contract test against it. The test fails on main and passes with #53806 plus the fold-in below. Proposed disposition: #53806 carries the post-commit hook as `on_compression_complete` with its author kept, takes the fold-in with the `Co-authored-by` trailers listed in the row if wanted, and the listed duplicates close after it merges. The test is one commit on main, on the branch [kvnloo/hermes-agent `staged/compaction-hook-salvage`](https://github.com/kvnloo/hermes-agent/tree/staged/compaction-hook-salvage) ([commit](https://github.com/kvnloo/hermes-agent/commit/111f361fb0003405e4724b4c6523f6ce5d118c22)). The combined production diff (#53806's compression commit hand-ported, plus the fold-in) is in the collapsed block at the end; it applies with `git apply` on top of that commit.

| issue | carrier (author) | A/B | fold in (author: what) | close after carrier merges | evidence |
|---|---|---|---|---|---|
| #118382 (also the #53806 row of #64231; #8643 folds here) | #53806 (ledfoot631), post-commit hook renamed `on_compression_complete` | main `a3b56cac`: FAIL, 3 of 7 (no compression hook; the 4 "stays silent" cases pass trivially). #53806 is CONFLICTING in 11 files, so its compression commit is hand-ported without that commit's `agent/agent_init.py` and `hermes_cli/hooks.py` hunks, and its resume-hook commit is left out. Main has since moved the summarizer call from `compress_context` into `_run_summary_phase`, so the hand-port puts #53806's `pre_context_compression` call there: still after the memory providers' pre-compress step and right before the summarizer, as #53806 placed it, with `task_id` passed in so the payload keys are #53806's. Its post-commit plugin call `on_session_start(boundary_reason="compression")` passes 3 of 7 under its own name. It fires once after the durable commit and stays silent when the summary aborts, when the commit site refuses a growing summary, and when the SessionDB write fails. It also fires before a manual `/compress` host commits and after the host discards, and it carries no `in_place` or token fields. Its `pre_context_compression` fires before the summarizer on every attempt (start-side, 0 of 7 by design). #53806's own three tests, ported to main's moved test file: the agent-init test needs the hunk left out above, and the other two fail on current main for reasons outside the hook (main now attaches store-row metadata to the transcript the hook receives, and a one-message compaction no longer commits); with those two drift edits both pass on the hand-port. #93391 (docs-only conflicts): `pre_compression`, the same start-side seam, 0 of 7. #118847 (one-hunk hand-port): `post_compaction` fires inside `ContextCompressor.compress()` before the commit, so it announces attempts that never commit, including the refused growing summary (after_tokens > before_tokens) and a failed SessionDB write; its `session_id` is the pre-rotation id: 1 of 7. #125881 (merges clean): `pre_compression_commit` is a fail-closed admission gate, so a subscriber that does not answer `allow` blocks the compaction. That is its intended contract, not an observer's: 1 of 7. #119347: a transform of the summarizer input (CONFLICTING, 3 semantic hunks); not run. #53806 + fold-in: PASS 7/7 (3 of 3 reps) | kvnloo: `tests/agent/test_compaction_observer_hook_contract.py`. Rotated, in-place and manual `/compress` compactions each fire exactly once, after the compacted transcript is durable, with `session_id`, `old_session_id`, `in_place` and before/after tokens. Three attempts that commit nothing stay silent: a failed summary under `compression.abort_on_summary_failure: true`, the commit site's would-grow refusal, and a SessionDB write failure. Each of these first checks that the session id and its state.db rows are unchanged, and the first two also check the compressor's abort or refusal flag. A manual compress that its host discards stays silent too, even after a later `finalize(committed=True)`; there the compacted rows are written (the case checks that), and only the host's discard keeps the observer quiet. A raising subscriber and a directive-shaped return leave the compacted messages and system prompt byte-identical. The test stubs agent init's model-metadata lookups, so it makes no network request. The fold-in moves the post-commit call into `_notify_context_engine_compression_complete`, so it inherits the manual-host deferral the context engine already has. It names the hook `on_compression_complete`, adds the payload, and adds a row to the hooks catalog in `hooks.md` plus a `hermes hooks test` payload. It leaves the hand-ported start-side `pre_context_compression` alone (see point 1 below). The payload reuses #118847's post-compaction before/after token counts and #93391's `in_place` flag, so the fold-in credits both: `Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>`, `Co-authored-by: Baophan00 <109447498+Baophan00@users.noreply.github.com>`, `Co-authored-by: clomp <277387657+clomp42@users.noreply.github.com>` (the test commit carries the last two and ledfoot631's) | #93391 (the same start-side seam as #53806's `pre_context_compression`, if that stays), #118847 (post-compaction signal for #118382, now fired after the commit) | Main never fires. The run goes through real `AIAgent` + `SessionDB` + `ContextCompressor`, with only the summary call replaced. With #53806 + fold-in, the observer runs after `archive_and_compact`/`publish_compression_child` return and, for a manual compress, only after the host's `finalize(committed=True)`. Moving the same call to just before the commit re-fails 6 of 7. Bypassing the manual deferral re-fails 2 of 7. Dropping the token plumbing re-fails 1 to 3 of 7. `replay_gates` stays 11/11 PASS, `ab_checkpoint_preflight` compress-call counts are unchanged, and `test_region_scoping` passes. In 17 adjacent files (compression, plugins, hooks CLI, shell hooks, manual compress), the only difference from main is the new test. #125881 (fail-closed policy gate) and #119347 (task-aware transform, #120582 data-loss class) stay open: they are different contracts and compose with the observer. |

Four points need a maintainer call.

1. The start-side hook. #64231 asks for #53806's `pre_context_compression` to become `on_compression_start`. The fold-in does not rename it. Nothing above tests it, #118382 needs only the post-commit signal, and the hook hands plugins the full transcript before every attempt. Its name, payload and docs row (it has none yet) are the author's and your call. Dropping it from this PR also works, and then the `task_id` pass-through goes with it.
2. Manual `/compress`. The test treats it the way the context engine is treated today: the observer waits for the host to commit its own history and stays silent if the host discards it. If you prefer "fire once state.db holds the compacted rows", delete the `manual_discarded` case and the `fired == []` line before finalize.
3. A slow plugin. The observer runs while the compaction lease is still held, like the context-engine callback today. Adding `on_compression_complete` to `_HOOK_TIMEOUT_BOUNDED_HOOKS` bounds a slow plugin under `plugins.hook_callback_timeout`, and the contract still passes 7/7 that way.
4. File size. The call sits next to the context-engine notify in `agent/conversation_compression.py`, which is already about 4.6k lines; the combined diff adds 38 net lines there. If you would rather have the dispatch in a `conversation_compression_*` sibling per AGENTS.md, it can move. I have not built that variant.

With the default `abort_on_summary_failure: false`, a failed summary commits the deterministic fallback summary instead of aborting. That compaction is real, so the observer fires once for it; I checked this on a 61-message window, outside the committed test. Scope is local compaction only: native and Codex app-server compaction never run a local commit, so the hook cannot fire there. This text was drafted with AI assistance (Claude Code). Every number in it comes from a local run.

<details>
<summary>Combined diff on current main: #53806's compression commit hand-ported, plus the fold-in (apply on top of the test commit)</summary>

```diff
diff --git a/agent/conversation_compression.py b/agent/conversation_compression.py
index f832e65dd7..e1077b9c93 100644
--- a/agent/conversation_compression.py
+++ b/agent/conversation_compression.py
@@ -2561,8 +2561,11 @@ def _hand_off_metrics_segment(old_session_id: str, new_session_id: str) -> None:
         rotate_segment(old_session_id, new_session_id)
 
 
-def _notify_context_engine_compression_complete(agent: Any, *, new_session_id: str, old_session_id: str) -> bool:
-    """Notify the active context engine after a durable compression commit."""
+def _notify_context_engine_compression_complete(
+    agent: Any, *, new_session_id: str, old_session_id: str, tokens_before: Optional[int] = None,
+    tokens_after: Optional[int] = None,
+) -> bool:
+    """Notify the active context engine and ``on_compression_complete`` plugins after a durable compression commit."""
     # Opt-in relay session-span segmentation. Observer semantics — failure must
     # never undo or delay the committed compression.
     with _swallow('relay segment rotation notification failed', exc_info=True):
@@ -2571,6 +2574,14 @@ def _notify_context_engine_compression_complete(agent: Any, *, new_session_id: s
             profile_key=relay_runtime.current_profile_key(), session_id=new_session_id, old_session_id=old_session_id
         )
     _hand_off_metrics_segment(old_session_id, new_session_id)
+    with _swallow('on_compression_complete plugin hook failed', exc_info=True):
+        from hermes_cli.lifecycle import has_hook, invoke_hook
+        if has_hook("on_compression_complete"):
+            invoke_hook(
+                "on_compression_complete", session_id=new_session_id, old_session_id=old_session_id,
+                in_place=new_session_id == old_session_id, tokens_before=tokens_before, tokens_after=tokens_after,
+                platform=getattr(agent, "platform", None) or "cli",
+            )
     callback = getattr(agent.context_compressor, "on_session_start", None)
     if not callable(callback):
         return False
@@ -2588,14 +2599,16 @@ def _notify_context_engine_compression_complete(agent: Any, *, new_session_id: s
         return False
 
 
-def _queue_context_engine_compression_notification(agent: Any, *, new_session_id: str, old_session_id: str) -> None:
+def _queue_context_engine_compression_notification(
+    agent: Any, *, new_session_id: str, old_session_id: str, **payload: Any,
+) -> None:
     """Stage exactly one existing hook call for an outer host transaction."""
     if callable(getattr(agent, _PENDING_CONTEXT_ENGINE_NOTIFICATION, None)):
         raise RuntimeError("a compression notification is already pending")
 
     def _notify() -> bool:
         return _notify_context_engine_compression_complete(
-            agent, new_session_id=new_session_id, old_session_id=old_session_id
+            agent, new_session_id=new_session_id, old_session_id=old_session_id, **payload
         )
 
     setattr(agent, _PENDING_CONTEXT_ENGINE_NOTIFICATION, _notify)
@@ -3455,7 +3468,7 @@ def _finish_compaction_boundary(
     agent: Any, compressed: list, *, new_system_prompt: str, old_session_id: Optional[str], in_place: bool,
     compacted_in_place: bool, session_commit_succeeded: bool, defer_context_engine_notification: bool,
     compression_made_progress: bool, compression_used_fallback: bool, compression_feasibility_skip: bool,
-    task_id: str,
+    task_id: str, tokens_before: Optional[int] = None,
 ) -> int:
     """Post-commit bookkeeping: notify engines/providers/hooks, re-arm usage tracking.
     Returns the rough post-compression token estimate (diagnostics only)."""
@@ -3472,6 +3485,11 @@ def _finish_compaction_boundary(
             if callable(_clear_labels := getattr(type(_labels_db), "clear_session_activity_labels", None)):
                 _clear_labels(_labels_db, _old_sid)
 
+    # Diagnostics only, not provider usage: schema-heavy rough estimates can stay
+    # above threshold even after the next real request fits.
+    _compressed_est = estimate_request_tokens_rough(
+        compressed, system_prompt=new_system_prompt or "", tools=agent.tools or None
+    )
     # Plugin engines use boundary_reason="compression" to keep lineage/checkpoint
     # state. Fires in BOTH modes: in-place passes the same id, the boundary is real.
     if session_commit_succeeded and (bool(_old_sid) or compacted_in_place):
@@ -3480,7 +3498,10 @@ def _finish_compaction_boundary(
             if defer_context_engine_notification
             else _notify_context_engine_compression_complete
         )
-        notify(agent, new_session_id=agent.session_id or "", old_session_id=_boundary_parent)
+        notify(
+            agent, new_session_id=agent.session_id or "", old_session_id=_boundary_parent,
+            tokens_before=tokens_before, tokens_after=_compressed_est,
+        )
 
     # Providers refresh cached per-session state; reset=False, conversation goes on.
     # Fires in BOTH modes so buffers don't double-count dropped turns in-place.
@@ -3519,11 +3540,6 @@ def _finish_compaction_boundary(
     agent._last_compression_attempt_in_place = compacted_in_place
     agent._last_compaction_in_place = compacted_in_place
 
-    # Diagnostics only, not provider usage: schema-heavy rough estimates can stay
-    # above threshold even after the next real request fits.
-    _compressed_est = estimate_request_tokens_rough(
-        compressed, system_prompt=new_system_prompt or "", tools=agent.tools or None
-    )
     compressor.last_compression_rough_tokens = _compressed_est
     compressor.last_prompt_tokens = -1
     compressor.last_completion_tokens = 0
@@ -3889,7 +3905,7 @@ def _run_summary_phase(
     agent: Any, messages: list, *, lease: _CompressionLease, in_place: bool, checkpoint_required: bool,
     approx_tokens: Optional[int], focus_topic: Optional[str], force: bool, bypass_cooldown: bool,
     commit_fence: Optional[CompressionCommitFence], hard_cancel_event: Any, system_message: str,
-    attempt: _Attempt,
+    attempt: _Attempt, task_id: str,
 ) -> _SummaryPhase:
     """Adopt a grown durable parent, gather memory context and run the summarizer.
     A hard cancel restores the compressor snapshot + live list, records a stall backoff while the lease is
@@ -3922,6 +3938,26 @@ def _run_summary_phase(
             bypass_cooldown=bypass_cooldown,
         )
         messages_before_compression = copy.deepcopy(messages)
+        # Notify generic plugins before compression discards/summarizes older turns.
+        # Observer-only: return values are ignored. Plugins can persist task-state,
+        # handoff breadcrumbs, or external-memory snapshots without mutating the
+        # live conversation or breaking prompt caching.
+        try:
+            from hermes_cli.plugins import invoke_hook as _invoke_hook
+            _invoke_hook(
+                "pre_context_compression",
+                session_id=agent.session_id or "",
+                task_id=task_id,
+                conversation_history=list(messages),
+                approx_tokens=approx_tokens,
+                focus_topic=focus_topic,
+                force=force,
+                model=getattr(agent, "model", ""),
+                platform=getattr(agent, "platform", None) or "cli",
+                conversation_id=getattr(agent, "_gateway_session_key", None),
+            )
+        except Exception as _plugin_err:
+            logger.debug("plugin pre_context_compression failed: %s", _plugin_err)
         _activity_heartbeat = _CompressionActivityHeartbeat(
             agent, commit_fence=commit_fence, emit_client_status=lease.status_emitted,
         ).start()
@@ -4179,6 +4215,7 @@ def compress_context(
         agent, messages, lease=lease, in_place=in_place, checkpoint_required=checkpoint_required,
         approx_tokens=approx_tokens, focus_topic=focus_topic, force=force, bypass_cooldown=bypass_cooldown,
         commit_fence=commit_fence, hard_cancel_event=_hard_cancel_event, system_message=system_message, attempt=attempt,
+        task_id=task_id,
     )
     if phase.abort_prompt is not None:
         return phase.messages, phase.abort_prompt
@@ -4262,6 +4299,7 @@ def compress_context(
             defer_context_engine_notification=defer_context_engine_notification,
             compression_made_progress=commit.made_progress, compression_used_fallback=_compression_used_fallback,
             compression_feasibility_skip=_compression_feasibility_skip, task_id=task_id,
+            tokens_before=approx_tokens,
         )
         logger.info(
             "context compression done: session=%s messages=%d->%d rough_tokens=~%s awaiting_real_usage=true",
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
index 02222185a2..4e41c06231 100644
--- a/hermes_cli/plugins.py
+++ b/hermes_cli/plugins.py
@@ -131,6 +131,16 @@ VALID_HOOKS: Set[str] = {
     # error_body may be unredacted.
     "transform_api_error_classification", "on_session_start", "on_session_end",
     "on_session_finalize", "on_session_reset",
+    # Fired immediately before context compression drops/summarizes older
+    # turns. Observer-only: return values are ignored. Plugins can persist
+    # task-state or handoff breadcrumbs without mutating the live message list.
+    "pre_context_compression",
+    # on_compression_complete: once per local compaction, AFTER the compacted transcript is durable
+    # (agent/conversation_compression.py; a manual /compress waits for its host's commit). Never for
+    # an attempt that did not commit, nor for native/Codex server-side compaction. Kwargs: session_id
+    # (current), old_session_id (same id when in_place), in_place, tokens_before (caller estimate or
+    # None), tokens_after (rough estimate), platform. Observer; returns ignored; fail-open.
+    "on_compression_complete",
     # on_skill_lifecycle: successful skill lifecycle facts (local skill name visible to plugins).
     "on_skill_lifecycle", "subagent_start", "subagent_stop",
     # pre_gateway_dispatch: once per incoming MessageEvent, after the internal-event guard, BEFORE
diff --git a/website/docs/user-guide/features/hooks.md b/website/docs/user-guide/features/hooks.md
index 59975d14ed..317917dff8 100644
--- a/website/docs/user-guide/features/hooks.md
+++ b/website/docs/user-guide/features/hooks.md
@@ -471,6 +471,7 @@ Payload fields below are the exact event-specific fields supplied by each call s
 | `on_session_end` | Observer | Canonically at each turn finalization; CLI/TUI exits have additional reduced legacy shapes. Return ignored. | Canonical: `session_id`, `task_id`, `turn_id`, `completed`, `failed`, `interrupted`, `turn_exit_reason`, `model`, `platform`; exit paths may add `reason`/`api_request_id` and omit fields. | IDs, model/platform, and outcome; canonical payload has no message body. |
 | `on_session_finalize` | Observer | CLI/TUI/gateway teardown through `finalize_session`; gateway shutdown may finalize without a reset. Return ignored. | Surface-dependent `session_id`, `platform`, optionally `reason`, `old_session_id`, `new_session_id` | Session and routing identifiers. |
 | `on_session_reset` | Observer | CLI/TUI session boundary and gateway after the replacement session exists; return ignored. | CLI: `session_id`, `platform`, `reason`; TUI: `session_id`, `platform`; gateway: those plus `reason`, `old_session_id`, `new_session_id` | Session and routing identifiers. |
+| `on_compression_complete` | Observer | Once per local context compaction, after the compacted transcript is durable in the session store; a manual `/compress` waits for its host to commit and stays silent if the host discards it. Never for an attempt that did not commit (aborted summary, would-grow refusal, store write failure), and never for native or Codex server-side compaction. Return ignored; a raising callback is logged and skipped. | `session_id` (current), `old_session_id` (equal to `session_id` when compacted in place), `in_place`, `tokens_before` (caller's estimate or `None`), `tokens_after` (rough estimate), `platform` | Session identifiers and token counts only; no message body. |
 | `agent_loop_stopped` | Observer | Immediately after a real running agent is interrupted — gateway `_interrupt_and_clear_session` or TUI/desktop `session.interrupt`; return ignored. | `session_key`, `platform`, `reason`, `invalidation_reason` | Session/routing identifiers and interruption reasons; no message body. |
 | `on_skill_lifecycle` | Observer | After an authoritative skill-usage state change; return ignored. | `action`, `skill_name`, `provenance`, `task_id`, `session_id`, `use_count`, `reused`, `reuse_after_patch` | Exposes the local skill name and provenance. |
 | `subagent_start` | Observer | Child constructed and about to run; return ignored. | `parent_session_id`, `parent_turn_id`, `parent_subagent_id`, `child_session_id`, `child_subagent_id`, `child_role`, `child_goal` | Child goal may contain user/project content. |
```

</details>
