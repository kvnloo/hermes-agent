# ui-tsp — Hermes for Tern

A frontend for Hermes that describes its UI to [Tern](https://stencil.so/tern) over the
Tern Surface Protocol (TSP) instead of painting terminal cells: the transcript, tool calls,
thinking, the composer and every sheet are semantic nodes the terminal lays out, draws and
animates natively. It is a sibling of the Ink TUI (`ui-tui/`) and talks to the same backend,
`tui_gateway`, over the same JSON-RPC contract.

## Running

`hermes` picks it on its own inside Tern (`TERM_PROGRAM=tern`, outside tmux/screen/zellij):

| Switch | Effect |
| --- | --- |
| `hermes --cli` | Classic REPL, as always |
| `HERMES_TERN=0` or `display.tern: false` | Never try the Tern frontend |
| `HERMES_TERN=1` | Try it even where `TERM_PROGRAM` doesn't say Tern (Tern over ssh) |

The frontend asks the terminal for TSP first. A terminal that doesn't answer makes it exit with
code 75, and the launcher runs the Ink TUI in its place (`hermes_cli/main_tui_launch.py`).

## Layout

| Path | What |
| --- | --- |
| `src/entry.ts` | Handshake (`@stencil-hq/tern`), gateway start, `App` |
| `src/app.ts` | The controller: one inline surface, gateway events → transcript, keys → overlay → completion → composer, one coalesced render per change |
| `src/model.ts`, `src/transcript.ts` | The structured transcript (prompts, turns of thinking/text/tool blocks, notices, panels) folded from gateway events |
| `src/composer.ts` | The prompt editor's model: text, caret, undo, history, kill ring |
| `src/view/` | Node builders (TSX on the Tern SDK's runtime) for the transcript, tool cards, dock and welcome card |
| `src/overlay.ts`, `src/overlays/` | Floating sheets: approvals, clarify, masked prompts, completions, pickers |
| `src/palette.ts` | The skin as a Tern program palette (`t`) |

The views speak omp's chat vocabulary (`omp.session`, `omp.user`, `omp.assistant`,
`omp.thinking`, `omp.editor`, `tool` names like `bash`/`read`/`edit`): Tern's chat styles
(Reader, Spine, Console), tool folding and Carly's agent integration are written against those
roles, so Hermes gets them as-is. The `hello` names the program `hermes`, which Tern uses for
its icon, deck tile and branding.

`@tui/*` imports reach the renderer-free modules of `ui-tui/src` (the gateway transport, skins,
history, completion requests); nothing here imports React or Ink.

## Developing

```sh
npm run bundle        # fast build to dist/entry.js (TSP_OUT=… overrides)
npm run build         # the receipted product build (scripts/build/tsp.mjs)
npm run typecheck
npm test
```

`TERN_TSP_RECORD=<file>` records every TSP message as JSONL; Tern's `surface-play` replays it.

The Tern SDK is [`@stencil-hq/tern`](https://www.npmjs.com/package/@stencil-hq/tern) from npm
([stencil-hq/tern-sdk](https://github.com/stencil-hq/tern-sdk)), pinned like every other dependency.

## Native settings E2E

`npm run e2e:native -- prepare …` and `npm run e2e:native -- run …` use the
already-installed **e2e 0.16.0** runner. They do not install dependencies, build the
app, launch Tern, create/focus panes, or start a model turn. The parent/operator
must first integrate and build the real settings frontend and gateway, then
allocate a **new private local PTY pane** on the isolated Tern control window.
The active user panes and the existing settings probe are explicitly refused.

Required flags are `--root`, `--entry`, `--control`, `--pane`, `--proof-dir`, and
`--python`. `--root` identifies the integrated application checkout; `--entry`
is its built native entry file. `--control` is a numeric loopback control port,
not the daemon socket. `--python` must identify the existing real Python runtime.
`--framework-root` defaults to `/mnt/zer0models/hermes-wt/e2e`.

For the current isolated display and the parent-allocated fresh pane 11:

```sh
export XDG_RUNTIME_DIR=/tmp/hermes-native-settings-proof/run
export WAYLAND_DISPLAY=wayland-1
PANE=11
ROOT=/mnt/zer0models/hermes-wt/tern-native-settings
SUITE=/mnt/zer0models/hermes-wt/tern-native-e2e/ui-tsp/e2e/run.mjs
PROOF=/tmp/hermes-native-settings-e2e-20261007
PYTHON=/home/kvn/.hermes/hermes-agent/venv/bin/python3
node "$SUITE" prepare --root "$ROOT" --entry "$ROOT/ui-tsp/dist/entry.js" \
  --control 19763 --pane "$PANE" --proof-dir "$PROOF" --python "$PYTHON"
```

`prepare` creates a fresh mode-0700 proof directory, an inert real profile with
a dummy localhost provider, a separate private HOME and foreign-profile sentinel,
and a launcher. It prints the exact quoted `tern ctl … run …` command. Only the
parent runs that command in the allocated pane. The launcher uses the real app
entry and the supplied Python interpreter. Its environment allows only PTY,
locale, and PATH values plus owned fixture paths and dummy credentials.
An owned empty managed directory prevents host managed policy from entering the fixture.
Preparation and real gateway startup refuse a checkout with a project `.env`.
The real env loader may load and sanitize that fallback; no non-fixture dotenv file is permitted.
Existing profiles are never overwritten.

Before launch, the parent reads fresh control state and verifies `focused.id=11`,
`busy=false`, and `running=null`. The exact current launch is:

```sh
tern ctl --control 19763 \
  'run "cd /mnt/zer0models/hermes-wt/tern-native-settings && /tmp/hermes-native-settings-e2e-20261007/launch-native.mjs"'
```

`run` executes in the selected shell; it does **not** allocate a new pane. Run it
only once while that shell is idle. Do not repeat it after the App is running:
that would send command text to the program. After launch the parent confirms
fresh `focused.id=11`; the suite additionally requires its launcher and checkout.

After the real gateway session and native app have started in that pane:

```sh
node "$SUITE" run --root "$ROOT" --entry "$ROOT/ui-tsp/dist/entry.js" \
  --control 19763 --pane "$PANE" --proof-dir "$PROOF" --python "$PYTHON"
```

All tests are deterministic, serial, and uncached; no agent model is acquired.
They compare the actual gateway getter with the canonical runtime schema, reach
every page/leaf through native navigation and global search, exercise switches,
numeric stepping/editing, choices, text, list/object JSON, defaults and nullable
Unset, sparse persistence/readback/reversion, invalid JSON zero-write behavior,
real unreadable-config errors and retry, and consequential confirmations with
**Cancel only**. They also exercise the session-only model-picker action without
selecting a model, live versus profile reasoning, rapid write reversion, delayed
real load/write ownership, session changes, foreign-profile isolation, and
composer draft/caret preservation. Deliberate config corruption is restricted to
the inert profile and restored on failure.

The complete page/leaf coverage case has a 40-minute deadline; other cases have
15-minute deadlines. These limits include serial native AX/tree/dump IPC for each
field. The coverage case does not sample keys or restrict the canonical schema.
Assertions wait up to 30 seconds for real acknowledgements. A broad intermediate
search frame took over 15 seconds to receive its native ACK on Tern 0.6.0; dispatch
or an unacknowledged frame does not count as displayed state.

The transparent gateway wrapper records the original real requests/responses. It
can hold only matching real `settings.get`/`settings.set` responses, unchanged,
for deterministic ownership checks. Tests prove the response is still undelivered
after verified owner closure/replacement and arrives only after explicit release.
Release forwards that response exactly once. A gate expiring after 60 seconds
fails closed instead of forwarding; teardown removes the gate.
No replies are manufactured, no recording is replayed as application input,
and unrelated RPCs are never held. The wrapper fails closed on turns, grants,
confirmations, global reasoning writes, every `model.*` mutation, every
server-originated request, and every client reply to one. Only readonly
`model.options` is allowed.
Its Node line reader has no Python StreamReader 64-KiB line ceiling;
observers incrementally parse complete multi-megabyte JSONL records.

### Tern 0.6.0 adapter limitations

The installed Tern engine's coordinate clicks and separate-argv text quoting do
not work with this control API. The narrow `e2e/engine` SPI adapter instead takes
fresh native AX, tree, and DOM dump evidence, matches bounds within one pixel,
rejects hidden/ambiguous targets, and clicks the unique deepest native `nth`
selector. Selectors stay raw; text is encoded with `JSON.stringify` inside one
scenario string. It verifies the exact focused pane, launcher/entry identity, and
checkout before and after capture. AX, tree and dump targets belong only to the
single visible focused pane's native subtree; ownership ambiguity fails closed.
There is no capture-text or replay fallback.
Field visibility is scoped to the painted native `pf-row` label, not the identical
text in the search query. Multiple visible row labels still fail as ambiguous.

AX checked/unchecked, selection/focus, and actual values are retained, rather
than invented from config defaults. Native program-owned text controls need not
expose `input.value`: their real tree text and acknowledged TSP editing
draft/caret are checked alongside the actual persisted config. This adapter does
not send modifiers: the observed Tern 0.6.0 Linux control driver delivers Ctrl
combinations as Meta. It rejects them instead of substituting another key.
Native Ctrl+F search and Ctrl+C draft/caret preservation were separately exercised
through an isolated Wayland virtual keyboard, with fresh native observations.
That diagnostic does not establish named-seat pointer or KVM support. A controller
must keep virtual input capabilities alive long enough for the native client to
bind them; merely acknowledging key dispatch is not semantic proof.
Offscreen page navigation uses actual native page state and unmodified Tab keys
rather than fixed positions.

Proof stays outside git under `--proof-dir`: raw gateway/TSP JSONL, grounded click
receipts, native AX/tree/dump observations, full isolated `HEADLESS-1` screenshots,
and the framework report/JUnit file under `suite/results`. The private project is
needed because e2e 0.16.0 requires its output directory to be inside its project.
The suite source also ignores accidental receipts/screenshots. Use a fresh proof
directory and launch for each complete acceptance run; do not publish private
proof or reuse the user's existing pane.

The parent runs all checks. After `prepare`, its explicit suite typecheck is:

```sh
node "$ROOT/node_modules/typescript/bin/tsc" --project "$PROOF/suite/tsconfig.json"
```

Runtime prerequisites are the integrated built app/gateway, the existing Python
environment (including its YAML support), the installed e2e framework/dist,
`tern` and `grim`, and the parent-verified isolated display/new selected pane.
Entry startup or a successful `session.create` is not settings acceptance:
`settings.get` must return its real full schema and the suite must pass.
