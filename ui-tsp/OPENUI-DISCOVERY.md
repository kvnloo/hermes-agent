# Select agent-produced visual candidates without copying a path

This isolated slice is stacked on #464 (`543b66b7`). Kevin's active
`preview/tern-frontend` was rechecked at `ba430cf6`; it is not modified.
It extends the existing `/visual` command, not the gateway or agent toolset.

## Use

Run the existing prepare command **through the agent's terminal tool** with
its four positional arguments and the new trailing `--json` option:

```sh
node ui-tsp/experiments/openui-preview/cli.mjs prepare \
  program.openui host-document.json '["stored-session-id","branch"]' \
  /absolute/output-directory --json
```

Use the exact scope shown by `/visual`, not the placeholder above. The optional
flag emits one JSON object after a successful write or identical-file reuse:
`kind: hermes.visual.candidate`, `version: 1`, `id`, `path`, `scope`.
Without the flag, the CLI still prints just the path for existing scripts.
No model call, repository collection or bundle regeneration is added by discovery.

Then `/visual` lists recent candidates from successful completed terminal tool
results. Choose with Up/Down + Enter or click a row. No filename needs pasting.
Selection invokes #464's existing bounded file read, full bundle validator,
source fingerprints and current scope check; the loaded ID must also equal the
reported ID. A different valid bundle swapped into the path is rejected.
The existing file link opens the separately enabled Luau route; this slice does
not install that plugin or change its renderer. `/visual /absolute/path` remains
available; no candidates or no session falls back to the existing help sheet.

Only paths on the frontend's filesystem can be loaded. Remote/container file
transfer is not added. A prepare command run outside the agent transcript will
not be discovered; use its explicit path. Resumed history may omit tool results,
so this is not a persistent artifact library or a promise of resume discovery.

## Bounded, user-initiated discovery

There is no watcher, directory search, polling, automatic sheet, inference,
new daemon or model prompt-prefix change. The picker snapshots candidates only
when invoked; reopening refreshes it. It inspects at most 128 recent entries,
512 blocks, 64 Ki UTF-16 code units of JSON, and returns at most 12 deduplicated
candidates newest-first. Individual JSON inputs are capped at 8192 code units.
Native frames and local navigation do not repeat discovery or read files.

Assistant prose, tool arguments, summaries, partial/running/failed calls, output
log fragments, bare paths and unsupported notice shapes are not searched. A
notice is untrusted locator data, not provenance, validation, inspection or
publication authority. Listing does not read or execute the reported file.

The current overlay owner handles interaction. Stale/replaced picker actions
cannot cover a newer approval. Observed session/branch or transcript replacement
expires the picker; late reads and transcript clears cannot reveal its old
candidate. No claim is made about unobserved ABA transitions. Publication and
external sharing remain absent. The final file link reads again; same-revision
atomic handoff and actual visual inspection are unchanged separate concerns.

## Checks and credit

The committed tests use the existing frontend test suite. Local behavior checks
transpile the actual modules with TypeScript 5.8.3 on Node 22.16.0 and use a
synthetic JSX tree, not the real SDK or a Tern window. Two acceptance cases fail
on #464's old pathless command route; all 17 new checks pass after this change.
The existing branch-scoped workflow additionally checks real CLI JSON output,
real OpenUI contracts, real Tern SDK types and the focused frontend suites.
CI and local/pixel/latency evidence must be reported separately.

Credit Kevin Rajan for parallel local testing and the advancing frontend;
Can Bölük / Stencil Labs and OMP/Tern contributors for instance-owned overlays
and native controls; Thesys/OpenUI for generation; bmdavis419/T3 Code for the
preview/verify/publish lifecycle; Brit for the explainer direction; and Hermes
contributors for the existing terminal-result and session ownership contracts.
