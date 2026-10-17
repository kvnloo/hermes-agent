# Long-session transcript retention

## Contract and SDK boundary (design before implementation)

Hermes remains the owner of session history. This feature releases presentation
nodes, not gateway transcript entries. Keep the newest 20 completed assistant
turns and all running turns, running tools/agents, approval-time entries, errors
and interrupted turns. There is no failure-acknowledgement intent in this frontend;
failures therefore remain protected indefinitely rather than guessing acknowledgement.
Prompts preceding a protected turn remain protected too. Non-error notices and
panels preceding the cold boundary may settle; warning/error notices do not.

The installed `@stencil-hq/tern` 0.1.0 exposes `Surface.settle`, `Surface.send`,
`Tree`, `View.ops` and `gone`; it does **not** expose entry adoption, forgetting,
a scroll event, a reload event, or viewport ranges. `OpenOptions.adopt` reopens
an entire surface, not an evicted child. The published retention protocol only
promises `gone`. Do not invent a terminal event or a gateway RPC.

For terminals advertising `settle`, a feature-owned incremental main writer
uses public Tree/View diffing and raw Surface ops. A local SDK reconciler owns
an empty `main` root plus `dock`/`layer`; only the writer owns main children.
Chrome and history ops are combined into one real Surface.send frame, avoiding
a credit-blocked half-frame that could target history evicted in between.
Terminals without settle retain the existing render path.
The writer retains trees only for hot/protected entries. On settling it drops
both its Tree and the entry-node cache, retaining only entry identity/order and
revision metadata. Streaming examines the hot/protected set, not all historical
entries. Structural changes and late changes to old turns update that set; a
late change rebuilds only that entry and settles it again after the targeted diff.
Changes to presentation context invalidate retained descriptions explicitly.

## Eviction and explicit lazy reload

A matching-surface `gone.ids` marks known top-level entry IDs as evicted.
Settled roots stay cold; active/protected roots and partially evicted subtrees
are rebuilt under normal credits. Never send edits, deletes, or settle against
an evicted ID. Other surfaces and unknown IDs are ignored. Evicted settled
entries are not re-added by tokens. Chrome and whole-document lifetime compose
with [the protocol boundary](SURFACE_PROTOCOL.md).
A persistent `Load older history` action at the start of main, and the registered
Ctrl+Home history-scroll intent, reload the newest page of evicted entries (up to
40) in original order, with original `main.<entry-id>` identities. Restore before
the next resident sibling, never by deleting/recreating main. The keyboard intent
reveals the first restored entry only after its adds. Reload is event-driven,
with no idle timers or polling. Keep the currently requested page (at most 40
entries) un-settled, otherwise the same budget pass would immediately evict it
again before it can be read. Requesting another page releases and re-settles the
previous one; clear/resume also release it. This adds one bounded reading page
to the hot window. A future SDK viewport/reload event can call the same page
request; automatic wheel-triggered reload is **not currently supported by Tern**.

## Scroll, actions and lifetime

Normal token frames preserve every resident entry ID and send no move/reveal
operations for history. Tern keeps native scroll/fold state. Explicit history
navigation restores IDs in place then reveals the requested page; the writer
never clears main to paginate. Main action routing rebuilds only the addressed
settled entry on an actual gesture, preserving Copy/Rewind/tool folds without
retaining historical handler closures. Queued handlers recheck entry lifetime.
Clear/resume/rewind reconcile the current gateway projection, deleting resident
removed entries and forgetting evicted removed entries without invalid ops.

## Work projection identities

A tool-bearing turn owns several main siblings: `main.<turn>` anchors its first
non-work run, `main.<turn>~<block>` identifies each tool, and
`main.<turn>~<tool-block>~after` anchors the following text/thinking/footer run.
These keys do not depend on tool status, visibility, expansion or host style.
Only successful settled work is a top-level tool; protected work stays inside
an `omp.activity` column so host group folding cannot conceal its state.

Retention settles all parts as one logical turn and tracks each part's `gone`
identity independently. Partial eviction never targets a missing part; an
explicit reload replaces remaining resident parts and restores the full turn
in order. Global presentation intents invalidate resident turns without
resurrecting evicted history. Lazy reload applies the current presentation.

## Evidence plan

Vitest mounts real App/Surface with a fake gateway and records actual emitted
ops. Cover the 20-turn boundary/protected states, zero old-node builds on tokens,
exact ordered eviction/reload, stale session events, late updates and actions.
Extend the existing `bench/replay.ts` App + SDK + encoder harness with 200/2,000
history-entry cases, 5,000 streaming deltas, identical ACK cadence and five
interleaved fresh-process runs per side. Report steady streaming p95 build time
and bytes separately from cold history upload: initial history is necessarily
linear and is not a constant-space/wire claim. Gate 2,000-entry p95 <= 1.5 times
the 200-entry case. Verify all final text/tool/history identities on the wire.

Sources: [Tern operations/retention](https://docs.stencil.so/tern/protocol/operations.md#retention)
and OMP's [pinned gone handling](https://github.com/can1357/oh-my-pi/blob/eb74cf84d8e16ac9b8c4fa5d7c43037023d016ac/packages/tui/src/native/backend.ts#L828-L837)
(Can Bölük / Stencil, MIT). Implementation uses the SDK public primitives rather
than copying OMP's reconciler or modifying the installed SDK.
