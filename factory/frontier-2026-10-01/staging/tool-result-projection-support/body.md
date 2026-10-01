Some evidence on the open questions here. It comes from a $0 harness: a real `AIAgent`, the real `read_file` tool and the real request assembly, against the repo's recording loopback providers. No paid calls were made. Everything below was measured on main at `44a1ce9724`. The 9 commits since then, up to current main `34f8ec3b40`, change Codex catalog, Responses replay and media-policy code plus some unrelated tests. None of them touches this PR's files, the fixtures the new test uses, or the converter code it relies on.

**Rebase.** Merged onto main at `44a1ce9724`, only `tests/tui_gateway/test_compression_config_hot_reload.py` conflicts, and it is still the only conflict on `34f8ec3b40`. It is an add/add at the end of the file, and keeping both sides works. On the rebased tree, 130 of 130 tests pass across this PR's new test file and the four touched-module test files. 55 of the 130 come from this PR: 53 in `tests/agent/test_tool_result_projection.py` and 2 added to the hot-reload file. On main without this PR, 75 of 75 pass in the four existing files. `replay_gates` (11 of 11 pass) and the compaction region-scoping tripwire give the same results with projection forced on as on main. Their transcripts hold no tool rows that projection could archive, though, so they never exercise it.

**1. Boundary stability (OpenAI-compatible route, no cache markers).** This checks teknium1's point that a pass should break the prefix once per batch at a stable boundary, not once per turn. The run was 14 turns, each reading a distinct ~20K-char file, with `min_tokens: 8000` and `tail_ratio: 0`.
- There were 6 projection passes in 28 requests. Every other request was a byte-identical extension of the one before it.
- Each pass archived 2 rows, about 11.7K estimator tokens, so every pass cleared the trigger. (The exact count shifts by about 1% between environments, because the stub carries the file path and the archive path.)
- Archived rows replayed identical stubs afterwards. That also held after a fresh agent resumed the session from `SessionDB`.
- On kshitijk4poor's question 2 (stickiness lives only in memory): on this route, losing it on resume did not show. The first request after the resume re-projected every stale row with the same content-addressed stub. It does show when a gate declines that first re-projection; see "The gate does not survive a restart" below.
- Controls: with the trigger forced to 1, the same session broke the prefix on 12 of 28 requests, each time with a one-row pass of about 5.8K tokens. With `ProjectionState.remember` made a no-op, it broke the prefix on 11 of 28 requests: the first pass archived 2 rows (about 11.7K tokens), and each of the next 10 archived one row.

**2. Preserved thinking (Claude with thinking on).** The fake server signs each thinking block over its prefix (system, tools and earlier messages, as in Anthropic's preserved-thinking docs) and checks every replay against it.
- Native Messages (`claude-opus-5-5`, no `base_url`): every projection pass replayed the latest signed thinking block over a rewritten prefix, 3 of 23 replayed blocks over 12 turns. On accounts that enforce the check, the API rejects such a request with a 400. With that emulated, the run got 16 rejections in 12 turns. The signature recovery strips `reasoning_details`, but the block is replayed from `anthropic_content_blocks`; #70107 and #129620 cover that gap. With #106426's `drop_block` the blocks would be dropped instead, so the reasoning is still lost at every pass.
- Bedrock Converse (`anthropic.claude-opus-5-5`, the repo's `FakeBedrock` through real boto3): Converse replays the signed reasoning of every earlier assistant turn. Once the first pass rewrites an early row, every later request carries invalidated blocks: 17 of 24 requests. The Anthropic docs I worked from state the check for the Messages API on every platform, Bedrock included, and don't cover Converse. I'm assuming the same rule there because the signature is the same.

**A gate, and what it costs.** The diff below declines a *fresh* pass when the request carries a signed thinking block on a route that checks it: native Messages (anthropic.com, or Nous Portal, which the converter treats the same way) and Bedrock Converse. Rows the same agent already archived keep replaying. Within one agent, the checks above then find 0 invalidated blocks and 0 rejections on Messages, and 0 invalidated blocks on Converse.

Other Anthropic-compatible endpoints (MiniMax, Kimi, DeepSeek and the like) are left alone. `_manage_thinking_signatures` strips their signed thinking before the request goes out; Kimi keeps the blocks, but it doesn't check Claude signatures. In the same scenario against `https://api.minimax.io/anthropic` (TLS-intercepted to the fake), this PR made 3 passes with 0 thinking blocks on the wire, with or without the gate. Without the endpoint check the gate would decline every pass there, because the stored rows still carry signatures.

The gate reads every assistant row and every stored copy (`reasoning_details`, `anthropic_content_blocks`, `bedrock_content_blocks`). That is more than main sends today: Messages keeps only the latest turn's signed block, and Converse replays only the Bedrock copy. So it also declines in two cases where nothing bound is on the wire: a native session whose latest turn has no signed thinking but an earlier turn does, and a Converse session whose earlier turns ran on native Messages. I kept the wider read so the gate stays right if every-turn replay (#129620) lands. Narrowing it is a few lines if you prefer.

**The gate does not survive a restart.** `ProjectionState` lives in memory. After a process restart, a resume or a gateway agent rebuild, every row archived earlier counts as fresh again. If the history then holds a signed thinking block on one of these routes, the gate declines that re-projection and the archived rows go back to full bytes, under a block that was signed over their stubs. So the gate undoes archived rows, which is exactly what the stickiness is there to prevent, and the request can carry an invalidated block. Getting there takes rows archived while nothing signed was in the history, then signed thinking, then a restart. Examples are a `/model` or provider switch to native Claude or Converse, a fallback-provider round trip, or thinking turned on after projection ran, each followed by a restart or rebuild (editing any of the four keys rebuilds the gateway agent). Two runs show it:
- Thinking turned on mid-session, end to end on native Messages with a `SessionDB` resume: with the gate, all 4 archived rows went out in full on the first request after the resume, and that request replayed 1 block over a rewritten prefix (the same in 3 of 3 runs). With no resume, 0 blocks were invalidated. This PR without the gate re-stubbed its 7 archived rows byte-identically on that request, but it also archived 1 more row there, which invalidated the same block.
- A route switch, by direct call on this PR's module: 9 rows were archived on chat completions. The same agent, switched to native Messages, still sent the 9 stubs after a signed turn. A new agent with the gate sent all 9 in full, and the latest signed block's prefix changed. Without the gate, the new agent re-stubbed the same 9 byte-identically.

I don't see a narrower predicate that avoids this: after a restart, nothing tells which rows the block saw as stubs. So on Claude routes the gate needs stickiness that survives a restart, which is kshitijk4poor's question 2. The restart case is not in the test file.

The cost, plainly: **with this gate, projection does not run on native Claude (anthropic.com, Nous Portal) or Bedrock Converse sessions whose history holds a signed thinking block, and without persisted stickiness a restart sends rows archived earlier back in full on those routes.** In the native run no pass fired, and the request bytes were identical to main's. The predicate goes by route and history, not by model, so it also turns projection off for older Claude models that don't bind thinking to the prefix. If projection matters for Claude with thinking, the other options are server-side tool-result clearing (#526; context editing doesn't count as an edit under the binding rule) or accepting dropped reasoning through #106426. That trade-off is yours and the maintainers' call.

**3. Cache economics (modeled, not measured).** teknium1's note asks for the cache-read ratio before and after. These figures are a model, not that measurement: they assume a perfect message-level prefix cache, 1.25x write and 0.10x read, and tokens = chars/4. The session was 20 turns at a 128K window.

| arm | prefix breaks | cache-read ratio | modeled billed input vs prune-off |
|---|---|---|---|
| prune off (default) | 1 (compaction) | 0.917 | baseline |
| `proactive_prune_tokens: 48000` | 2 | 0.896 | +19% |
| projection, uncached trigger | 6 | 0.802 | -11.7% |
| projection, cached-route trigger | 3 | 0.872 | -8.1% |

Measured on the loopback wire, the total characters sent over the session fell 47% (uncached trigger) and 27% (cached-route trigger). The before/after cache-read ratio on a real caching route is still the measurement this needs, and it is not here.

<details><summary>Gate diff (on this PR's <code>agent/tool_result_projection.py</code>)</summary>

```diff
@@ -450,6 +450,57 @@ def _backend_is_remote() -> Optional[bool]:
         return None
 
 
+_SIGNED_THINKING_MODES = frozenset({"anthropic_messages", "bedrock_converse"})
+
+
+def _is_signed_thinking(block: Any) -> bool:
+    """A replayable signed thinking block, in any copy Hermes keeps on an assistant row: Anthropic
+    ``{type: thinking | redacted_thinking}`` with ``signature`` / ``data`` (``reasoning_details`` and
+    ``anthropic_content_blocks``), or Bedrock Converse ``reasoningContent`` with ``signature`` /
+    ``redactedContentBase64`` (``bedrock_content_blocks``)."""
+    if not isinstance(block, dict):
+        return False
+    if str(block.get("type") or "").strip().lower() in ("thinking", "redacted_thinking"):
+        return bool(block.get("signature") or block.get("data"))
+    reasoning = block.get("reasoningContent")
+    return isinstance(reasoning, dict) and bool(reasoning.get("signature") or reasoning.get("redactedContentBase64"))
+
+
+def replays_bound_thinking(agent: Any, api_messages: Sequence[Dict[str, Any]]) -> bool:
+    """Whether this request replays signed Claude thinking that a fresh pass would invalidate.
+
+    A signed thinking block is bound to the conversation prefix it was produced over (system,
+    tools and every earlier message). Rewriting an earlier tool row is a history edit: on
+    preserved-thinking models the API drops every later thinking block, or rejects the request
+    on accounts it enforces, and the turn loses that reasoning. Both wires that replay signatures
+    (Messages and Bedrock Converse) are covered. Every assistant row and every stored copy is
+    read, a superset of what the converters replay today, so the check still holds if more turns
+    are replayed. Messages endpoints other than anthropic.com and Nous Portal are skipped: the
+    converter strips their signed thinking (Kimi keeps it, but checks no Claude signature).
+    Only a FRESH pass is declined: rows this agent already archived keep replaying their stubs.
+    That holds only while the in-memory ProjectionState lives. After a restart, a resume or an
+    agent rebuild, every row archived earlier counts as fresh again, this check declines the
+    re-projection, and those rows go back to full bytes under a block that may have been signed
+    over their stubs. On these routes the gate needs stickiness that survives a restart.
+    """
+    api_mode = str(getattr(agent, "api_mode", "") or "")
+    if api_mode not in _SIGNED_THINKING_MODES:
+        return False
+    if api_mode == "anthropic_messages":
+        from agent.anthropic_endpoints import _is_nous_portal_endpoint, _is_third_party_anthropic_endpoint
+
+        base_url = getattr(agent, "_anthropic_base_url", None)  # the URL the Messages converter gets
+        if _is_third_party_anthropic_endpoint(base_url) and not _is_nous_portal_endpoint(base_url):
+            return False
+    return any(
+        _is_signed_thinking(block)
+        for msg in api_messages
+        if isinstance(msg, dict) and msg.get("role") == "assistant"
+        for key in ("anthropic_content_blocks", "bedrock_content_blocks", "reasoning_details")
+        for block in (msg.get(key) or ())
+    )
+
+
 def _resolve_active_env(agent: Any):
     """Best-effort live terminal env for this agent, or None.
 
@@ -565,6 +616,9 @@ def _project(agent: Any, api_messages: List[Dict[str, Any]], env: Any) -> int:
 
     trigger = trigger_tokens(policy, window, cache_capable)
     approved = fresh_reclaim >= trigger
+    if approved and planned and replays_bound_thinking(agent, api_messages):
+        approved = False
+        logger.debug("Tool-result projection declined: the request replays signed thinking bound to this prefix")
     if approved and cache_capable:
         # The rewrite invalidates the cached prefix from the first stub onward, and that region
         # is re-prefilled once. Require the reclaim to cover it.
```
</details>

The two scenarios are one new test file (`tests/e2e/core/history/test_tool_result_projection_wire.py`, ~300 lines) that needs the rebase. I can share it as a patch if you want it in this PR, or leave it out. What the file pins and what it doesn't: its native-Messages case would also pass with a narrower gate that reads only `reasoning_details` on Messages, and it runs inside one agent, so it never restarts. The wider reads, the Converse case, the endpoint check and the restart case are shown only by separate harnesses (direct calls against the real converters and this module, plus the Bedrock, MiniMax and restart runs), not by the file.

Not tested: real provider caches, Vertex Claude, remote terminal backends, and the real `/model` and fallback-provider code paths into the restart case (the direct call switches the route in place). The gate also doesn't look at chat completions. Hermes does replay signed `reasoning_details` there when the route is OpenRouter or the Portal's chat endpoint; whether Anthropic checks the binding through them is something I haven't tested.

This comment, the harness, the two tests and the gate diff were written with Claude Code. The numbers come from the runs described above.
