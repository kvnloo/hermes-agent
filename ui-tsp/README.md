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

## Composer submission

Enter, the Send control and Tern's atomic `send` event use the same composer consumption path.
Each submission clears the draft and caret, resets draft undo, and records the submitted text in prompt history.
Native `send` records its own text, including multiline text, rather than an older draft.
Hermes retains command dispatch, prompt queues and gateway submission authority.

## Reasoning effort

`/reasoning` reads the live session through `config.get`.
`/reasoning <level>` uses `config.set`, not the separate slash worker.
The composer adopts the confirmed effort, including before the first model turn.
`none` appears as `off` in the native effort control.
Click that control or press Shift+Tab to cycle the effort.

Effort changes apply to this session by default. `--session` makes that scope explicit.
Only `--global` persists the effort in the profile config.
Display commands such as `/reasoning show` do not change the effort.
A late command response cannot overwrite the status or transcript of another session.

## Native Settings

Open `/settings`, `/prefs`, or the composer's **Settings** control.
The help sheet and slash completion list include both commands.
Hermes sends one SDK `prefs` sheet directly in `layer`, not inside the inline transcript.

Each portable schema category has a **Profile defaults** page.
The caption names the canonical profile.
The **Session** page is separate. It uses the native model picker with session-only scope and the same live reasoning owner as `/reasoning`.
Profile writes do not replace live session pins.

Type to search all pages, or press Ctrl+F.
Use Up/Down to select a row, Enter to edit it, and Tab or Left/Right to change pages.
Boolean, number, choice and text rows use native controls.
List and object rows use JSON text. Hermes rejects invalid JSON and the wrong root shape before it sends a write.
Untouched nullable values stay unset, including nullable choices.
Boolean and numeric environment templates stay visible as raw text, not false switches or blank numbers.
Nullable booleans and numbers show **Unset**, not false or zero.
During numeric editing, the native text control shows the raw draft, including incomplete numbers.
Enter validates and commits the number. Typing alone does not change the saved value.
Stored credential values remain undisclosed. Null credential leaves in JSON preserve the stored credential. An explicit empty string clears a scalar credential.

Each row has the saved value and its default.
**Use default for selected field** restores a public field's default. For a structured private field, credential nulls still preserve stored credentials.
Nullable public fields also have **Unset selected field**. Private scalar fields do not offer false reset or unset controls.
**Reload saved values** discards unsaved drafts and reads the profile again.
Escape cancels an open editor or search before it closes the sheet.
The composer retains its draft and caret. Ctrl+C closes Settings without clearing that draft.

Hermes sends one changed key per write and serializes profile operations.
Duplicate native commits do not repeat a mutation.
The displayed saved value comes from canonical `settings.get` readback.
Errors retain the draft and offer **Retry**.
If a write was acknowledged but readback failed, Retry repeats the read, not the mutation.
An explicit revert after failed readback is retained and saved, including when the acknowledged value was null.
Policy and consent changes show the exact profile, setting and proposed value.
**Cancel** is the default. Enter or Escape cancels. Only the explicit confirmation control accepts the change.
Every open belongs to its original live session and overlay instance.
Late replies, old native IDs and queued callbacks cannot write into a replacement session or sheet.

The SDK routes `change` to `onChange`, `select` to `onSelect`, `activate` to `onActivate`, and named `action` to `onAction`.
Prefs changes use the sheet ID plus `item` (the schema key) and typed `value`.
Page actions use `act: "page"` and `value` (the page ID).
Choice previews use `item: "<row>=<option>"`. Close with a row value cancels its editor. Close without a value closes the sheet.
Hermes owns the search text, edit draft, caret and raw keys. Tern owns native layout, chrome and control rendering.

## Native overlay actions

An overlay action belongs to the instance that produced its native node.
Each open has a distinct native root ID, even when its logical request key is reused.
An event from an older painted view cannot target the replacement.
The SDK can bind a callback before an overlay closes, is replaced, or becomes covered.
Hermes checks that owner again when the queued callback runs.
Only the current top overlay can act, and no overlay can act after the surface closes.
The SDK still owns handler lookup, native events, frame credits and surface transport.

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
