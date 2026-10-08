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
| `src/orb.ts` | Owning-agent activity reducer and bounded native thinking-orb animation |
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

## Thinking orb

The composer includes a 34px native image whose geometry is adapted from OMP Handsfree's
`omp_hud/voice_orb.py`: the quiet seed, orbit particles, listening rings and response ribbons.
It follows events belonging to the shown Hermes session, not a guessed progress percentage.

| State | Source |
| --- | --- |
| Idle | Finished turn or idle voice status |
| Working | Submitted turn, tool preparation or active tools |
| Thinking | Reasoning events or voice transcription |
| Composing | Streamed answer or interim text |
| Listening | Voice listening, recording or captured status |
| Speaking | Voice speaking, playback or TTS status |
| Waiting | An open approval, clarification or masked-input prompt |
| Error | Failed turn, rejected submission or failed gateway |

Active tools remain working until their matching completions arrive. Session adoption clears
the previous activity. Voice states are displayed only when Hermes reports them; this feature
does not add a microphone, live-talk transport or TTS.

Animation changes only the orb image at 12fps. SVG blobs are cached for a finite 96-frame
cycle per state and appearance. Blocked protocol credits skip frames instead of building a
queue. Idle, waiting and error are static; hidden surfaces, modal sheets, reduced motion and
closed sessions stop the timer. The image has the accessible name `Hermes agent: <state>`.

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
