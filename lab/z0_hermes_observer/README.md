# z0 Hermes observer lab plugin

Tracking: Hermes #319, #322, #323.

This is the first executable slice of the full z0 ↔ Hermes program.

It records **metadata-only** lifecycle events into a profile-scoped JSONL spool.
It does not route models, inject context, alter tools, grant authority, or label
execution completion as success.

## Privacy

Raw prompt, conversation, tool arguments, tool results, and assistant text are
not persisted by default.

`Z0INT_HERMES_CAPTURE_SANITIZED_CONTENT=1` opts into Hermes' sanitized
`request` / `response` API envelopes. These can still contain user text.

For tests or one-off experiments, set `Z0INT_HERMES_EVENT_PATH=$TMPDIR/z0-hermes-events.jsonl`.

## First experiment

1. Load the plugin in a downstream Hermes profile.
2. Run a fixed set of turns with tools and one auxiliary task.
3. Verify one trace id joins pre/post provider attempts, tool calls, auxiliary
   calls, and `on_session_end`.
4. Confirm plugin enabled/disabled runs have identical model/tool behavior.
5. Feed the JSONL into z0intelligence offline observer/eval work; do not promote
   any learned decision into the hot path yet.

The next slice will join independent outcomes and run DecisionBackend shadow
questions over these receipts.

## Identity

Every row carries `identity.trace_id`: an explicit `trace_id` when the host supplies one,
otherwise a hash of `session_id` and `turn_id`, falling back to the session (or task) id when
there is no turn. The host announces `subagent_stop` from the parent's side, so that row is
keyed by the parent's session and turn and joins the trace of the turn that delegated;
`subagent.child_session_id` links to the child's own rows.

## Delivery

Hook callbacks never wait on storage. Each row is encoded on the calling thread, tagged
with the active profile's spool path, and appended by one background writer. Hermes fails a
`pre_tool_call` callback closed when it outlives `plugins.hook_callback_timeout` and runs
`subagent_stop` callbacks on the caller thread, so a synchronous disk write there would turn a
stalled filesystem into blocked tools or a hung parent.

- Up to 4096 rows are buffered while the writer is busy or storage is stalled. Beyond that,
  rows are dropped and counted. The next successful write starts with an
  `observer_rows_dropped` row whose `fields.dropped_rows` is the number of rows missing
  before it. Rows that could not be written count as dropped too.
- A normal interpreter exit waits up to 2 seconds for buffered rows. Rows still buffered at a
  hard exit (`os._exit`, SIGKILL) are lost.
- A profile whose spool directory cannot be created loses its rows; they are never redirected
  to another profile.
