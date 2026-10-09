# ui-tsp — Hermes for Tern

A frontend for Hermes that describes its UI to [Tern](https://stencil.so/tern) over the
Tern Surface Protocol (TSP) instead of painting terminal cells: the transcript, tool calls,
thinking, the composer and every sheet are semantic nodes the terminal lays out, draws and
animates natively. It is a sibling of the Ink TUI (`ui-tui/`) and talks to the same backend,
`tui_gateway`, over the same JSON-RPC contract.

## Running (downstream experiment)

The experimental TSP frontend is disabled by default. Opt in with
`HERMES_TERN=1 hermes --tui`, or set `display.tern: true` in
`config.yaml` to allow Tern detection. Merely running inside Tern
does **not** change the classic CLI default.

| Switch | Effect |
| --- | --- |
| `hermes --cli` | Classic REPL, highest precedence |
| `hermes --tui` | Ink TUI, unless TSP is opted into |
| `display.tern: true` | Attempt TSP when `TERM_PROGRAM=tern` |
| `HERMES_TERN=1` | Explicit TSP probe, including over SSH |
| `HERMES_TERN=0` | Disable TSP even when enabled by config |
| `display.tern: false` | Default: no TSP unless explicitly forced via environment |

The launcher never probes inside tmux/screen/zellij, even with the forced flag.
A terminal that does not answer TSP exits the native frontend with code 75;
the launcher then runs Ink. Other TSP failures retain their real exit status
and are not silently converted to an Ink success.

The standalone `ui-tsp` product is a downstream dogfood carrier, **not**
the proposed first upstream PR. See [PROMOTION.md](PROMOTION.md) for the
bounded upstream seam and evidence gates.

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
