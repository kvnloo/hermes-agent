---
name: trace-query
description: "Use when asked about Hermes session traces, slowness, tool failures, subagent cost or usage. Query with trace_query, show its board, expand @trace refs."
---

# Answering trace questions with /stats boards

## When
The user asks how a session went: why it was slow, what failed, what a subagent or model cost, what
happened in a turn, how two sessions compare, or where the money went this week. Also when a message
carries an `@trace:v0;...` reference.

## How
1. Call `trace_query` with the user's words as `question`. Set `session` when they name one:
   `current` (default, this conversation), `latest` / `previous` (newest other sessions), `last 2`,
   or a session id. Set `intent` only when the question is ambiguous. Pick `layers` for the question:
   slowness → spans, tokens, errors, subagents; failures → spans, errors (+ transcript); cost → cost,
   tokens; walkthrough → spans, subagents, transcript.
2. Read `analysis` (and `rangeAnalysis`, `delta`, `focus`). Every row has an id. Answer from those
   numbers in two to five sentences: the cause first, then the evidence with ids or tool names.
   Say what `truncation` notes cut.
3. Show the board: call `html_render` with `html` set to `render.handle` exactly (`trace-render:…`),
   `title` = `render.title`, `height` = `render.height`. The plugin swaps the handle for the
   document. Never paste the HTML, never rebuild the tables the board already shows.
4. Tell the user they can click spans, tool rows or error groups, zoom the timeline, Pin, then press
   **Copy for chat** and paste the reference into their next message.

## Selections coming back
- A pasted `@trace:v0;s=…;k=…;ids=…;r=…` is usually expanded for you as a 📌 block before you read
  the message. Answer about exactly those ids and that window.
- If the raw reference is still in the text, call `trace_resolve` with `ref` set to it verbatim.
- To redraw the board around the selection, call `trace_query` with `ref` (or `focus` ids /
  `focus_range`) and the follow-up question, then `html_render` the new handle.

## Limits
- Hermes records usage per session and model, not per request: model spans have no latency or TTFT,
  and request-level cost is an estimate. Say "not recorded" instead of inventing per-call numbers.
- Idle time includes waiting on the user. Do not call it slowness without checking the idle gaps.
