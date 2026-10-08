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
app, launch Tern on the host desktop, or start a model turn. The parent/operator
must first integrate and build the real settings frontend and gateway on the
isolated Tern control window. `prepare` itself opens a **fresh tab and pane**, binds
that pane's cwd to the canonical proof directory, and writes an owner receipt plus a
launcher whose filename contains the startup nonce. `--pane` on prepare must **not**
already exist on the window. Run accepts only that created pane after `running`
includes the nonce launcher. There is no denylist of pane ids and no `/tmp` cwd heuristic.

Required flags are `--root`, `--entry`, `--control`, `--pane`, `--proof-dir`, and
`--python`. `--root` identifies the integrated application checkout; `--entry`
is its built native entry file. `--control` is a numeric loopback control port,
not the daemon socket. `--python` must identify the existing real Python runtime.
`--framework-root` defaults to `/mnt/zer0models/hermes-wt/e2e`.

For the isolated display, pass an unused numeric `--pane` placeholder; prepare prints the created id:

```sh
export XDG_RUNTIME_DIR=/tmp/hermes-native-settings-proof/run
export WAYLAND_DISPLAY=wayland-1
ROOT=/mnt/zer0models/hermes-wt/tern-native-settings
SUITE=/mnt/zer0models/hermes-wt/tern-native-e2e/ui-tsp/e2e/run.mjs
PROOF=/tmp/hermes-native-settings-e2e-20261007
PYTHON=/home/kvn/.hermes/hermes-agent/venv/bin/python3
node "$SUITE" prepare --root "$ROOT" --entry "$ROOT/ui-tsp/dist/entry.js" \
  --control 19763 --pane 0 --proof-dir "$PROOF" --python "$PYTHON"
```

`prepare` creates a fresh mode-0700 proof directory, opens a new tab on the isolated
control window, and requires `realpath(cwd)` to equal that proof directory,
then writes an inert real profile with a dummy localhost provider, a separate
private HOME and foreign-profile sentinel, `owner.json`, and a nonce-named launcher.
It prints the created pane id and the exact quoted `tern ctl … run …` command. Only the
parent runs that command in the created pane. The launcher uses the real app
entry and the supplied Python interpreter. Its environment allows only PTY,
locale, and PATH values plus owned fixture paths, dummy credentials, and the owner nonce.
An owned empty managed directory prevents host managed policy from entering the fixture.
Preparation and real gateway startup refuse a checkout with a project `.env`.
The real env loader may load and sanitize that fallback; no non-fixture dotenv file is permitted.
Existing profiles are never overwritten.
Preparation checks an explicit open native gate on both sides of native input.
Open means `phase === "off"` and `error === null`, with either `applies === false`
or `applies === true && signed_in === true`. The latter is the actual authenticated
0.6.1 beta-window state; `applies` alone does not mean the overlay is blocking.
Pixel evidence stays `*.pending.png` until a post-capture state check confirms the
same owned pane and nonce launcher with no account gate; only then is the accepted
PNG/JSON pair published. Rejected pending images are diagnostics, not native proof.
Zero-budget and cancelled operations stop before target resolution or dispatch.

Before launch, the parent reads fresh control state and verifies the printed
`focused.id`, `busy=false`, and `running=null`. Use the launch line prepare printed;
the launcher path contains the proof token.

The printed `tern ctl run` executes in the created shell; it does **not** allocate
another pane. Run it only once while that shell is idle. Do not repeat it after the App is running:
that would send command text to the program. After launch the parent confirms
the created `focused.id`; the suite additionally requires the nonce launcher and checkout.

After the real gateway session and native app have started in that pane:

```sh
node "$SUITE" run --root "$ROOT" --entry "$ROOT/ui-tsp/dist/entry.js" \
  --control 19763 --pane "$CREATED_PANE" --proof-dir "$PROOF" --python "$PYTHON"
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

The installed Tern engine's coordinate clicks and separate-argv text quoting do not work with this control API. The narrow `e2e/engine` SPI adapter instead takes
fresh native AX, tree, and DOM dump evidence, matches bounds within one pixel,
and rejects hidden/ambiguous targets. Official `a11y <action> <selector>` targets a
DOM element, not an AX id. Advertised AX `click` and `scroll-into-view` therefore
dispatch `a11y …` only at the unique dump `nth` whose leaf tag and class set are
exactly the unique tree host for that AX node, with host/dump/AX bounds agreement.
There is no outermost or class-subset fallback; missing or ambiguous identity fails closed.
Pointer `click ${nth}` remains only when the AX node does not list `click`.
Selectors stay raw; text is encoded with `JSON.stringify` inside one
scenario string. Click, key, type, reveal, capture, and resource operations share
one deadline and abort signal for the whole operation; a pre-delivery timeout is
`OPERATION_TIMEOUT`, and a failure after `execFile` starts or after successful dispatch
is `ACTION_MAY_HAVE_COMMITTED`.
It verifies the exact focused pane, launcher/entry identity, and
checkout before and after capture. AX, tree and dump targets belong only to the
single visible focused pane's native subtree; ownership ambiguity fails closed.
There is no capture-text or replay fallback.
The native AX owner is correlated with that pane's **Agent block** region, so
offscreen descendants remain observable without accepting sibling-pane targets.
Footer actions use documented [accessibility scrolling](https://docs.stencil.so/tern/scripts/harness.md):
keep the owned AX identity, dispatch `a11y scroll-into-view` on that owner, then
require fresh visible geometry before clicking.
This scroll is not a focus or click substitute. A broad search placed a footer
13,035 pixels below the viewport; its visible position and unchanged YAML were verified.
Locator taps use a native AX `click` action when the target advertises it;
otherwise they retain native pointer dispatch. Settings is addressed by its
actionable AX name, `Open Hermes settings`, not its decorative `Settings` label.
Action ownership matches an explicit/intrinsic DOM role or an exact AX-name/title
identity, then requires one tagged tree host and one visible dump host with the
exact tag/class set and matching geometry. AX roles may be implicit in the DOM:
the real 0.6.1 Settings owner is a titled `div`; Session is a titled `button` with
two identical-sized wrappers. Unnamed wrappers do not qualify; ambiguous owners
still fail, without deepest-node or class-subset fallback.
The label click returned success without issuing `settings.get` in a fresh pane.
The advertised action produced that request and SDK reconciliation, but a fresh
screenshot exposed the closed-beta sign-in gate over the app: **not visible proof**.
Captures require that explicit open gate state before and after reading native
trees. Signed-out, waiting, waitlisted, errored and unknown states block input and
acceptance. Restore access interactively; never automate account approval or act
through a visible gate.
Serial and MCP attempts share an atomic per-proof owner claim. The inert sentinel
and canonical home/config path are required before the engine starts. A second
engine cannot acquire the same fixture; use separate manifests and proof roots.
Cleanup atomically quarantines and verifies its claim before removal. A changed
claim is retained as diagnostic evidence; crashed attempts require a fresh fixture.
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
