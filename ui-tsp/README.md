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
| `src/splash/`, `src/view/splash.tsx` | The launch splash: seven pure designs, their Tern view, and the shell that times and hands off |

The views speak omp's chat vocabulary (`omp.session`, `omp.user`, `omp.assistant`,
`omp.thinking`, `omp.editor`, `tool` names like `bash`/`read`/`edit`): Tern's chat styles
(Reader, Spine, Console), tool folding and Carly's agent integration are written against those
roles, so Hermes gets them as-is. The `hello` names the program `hermes`, which Tern uses for
its icon, deck tile and branding.

`@tui/*` imports reach the renderer-free modules of `ui-tui/src` (the gateway transport, skins,
history, completion requests); nothing here imports React or Ink.

## Launch splash

Before the session chrome appears, a splash covers gateway boot on its own `screen` surface and
hands off when the gateway is ready. Any key skips it; it never holds past 15 seconds.

| Switch | Effect |
| --- | --- |
| `HERMES_TUI_SPLASH=0` | No splash |
| `HERMES_TUI_SPLASH=<design>` | `kerykeion` (default), `sigil`, `velocity`, `atlas`, `windows`, `unleash` or `soul` |
| `HERMES_TUI_SPLASH=random` | A different design each launch |

It is also skipped under Reduce Motion and when the launch carries a prompt (`hermes -q …`).

Each design is a pure function of size, elapsed time and a palette (`renderSplashFrame`), so a
frame is reproducible without a gateway or a model. A frame is cells, not ANSI: `text` nodes whose
inks are span tokens naming palette tokens (`text`, `accent`, `dim`, `border`) and whose grounds are
roles a small stylesheet paints from Tern's fill tokens (`userMessageBg`, `selectedBg`). No colour
value lives in the view, so `gateway.ready` and `skin.changed` recolour it through
`surface.palette()` alone. The dark default (`DARK_SEEDS` in `ui-tui/src/theme.ts`) is the Hermes
website's palette, shared with the chrome.

```sh
npx tsx scripts/splash-demo.ts            # gallery in a Tern pane: h/l switch, r replay, t swap skin, q quit
npx tsx scripts/splash-demo.ts --once     # one launch, as the app plays it
SPLASH_DEMO_AT=3000 npx tsx scripts/splash-demo.ts --design atlas   # hold one instant, for a still
```

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
