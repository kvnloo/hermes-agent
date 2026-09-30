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
