# Tern ↔ Hermes ownership matrix

Issue: #436

"Owner" means who should own **state/intent** versus **presentation/chrome** in the
Tern-native product. This is evidence-backed where confidence is high; low and
medium rows stay experiment questions.

| Concern | OMP/Tern evidence | Hermes TUI/Desktop evidence | Owner hypothesis | Confidence | Open question |
| --- | --- | --- | --- | --- | --- |
| host/window chrome | TSP docs: Tern always owns the window around the pane | Desktop owns its own native window only outside Tern | **Tern** | high | none |
| tabs / splits / panes | Tern layout API owns tabs, splits, focus and pane lifecycle | Desktop has its own pane tree; TUI has no outer window manager | **Tern** | high | how much session identity belongs in tab title |
| session identity | OMP projects session title/path/branch into Tern chrome | Hermes has Session Orchestrator + Desktop session sidebar | **Hermes state → Tern chrome** | medium | which session actions need an in-pane surface |
| transcript | TSP: program owns what is shown/history; Tern lays it out and retains node view state | Hermes TUI/Desktop own authoritative turns | **Hermes state/content → Tern layout** | high | exact grouping/settle treatment |
| composer | TSP native editor sends edits/actions back; program owns editor state | Hermes owns draft, queue, history, submit guards | **Hermes state/actions → Tern editor** | high | which status facts ride in dock |
| model selection | OMP uses native picker while app owns catalog/model semantics | Hermes model hop/catalog are already app state | **Hermes semantics → Tern picker** | medium | overlay vs sheet vs command palette |
| context usage | OMP exposes context as native status/view | Hermes already computes context usage | **Hermes value → Tern presentation** | high | persistent fact vs on-demand only |
| git / review | Tern has native Git block; OMP exposes git state | Desktop has task-attached Review pane | **shared / experiment** | low | use Tern Git directly, Hermes projection, or both |
| tool lifecycle | OMP maps app tool state to TSP tool nodes | Hermes gateway/TUI already own tool lifecycle | **Hermes authority → Tern tool** | high | compact/full density rules |
| subagents | OMP renders agent nodes but app owns lineage/control | Hermes `subagent.list/tail/steer/interrupt` are authoritative | **Hermes authority → Tern agent** | high | dock HUD vs sheet/overlay balance |
| queue / steering | OMP composer owns queued follow-ups/steering | Hermes TUI owns queue editing + steering semantics | **Hermes** | high | native pill/editor treatment |
| approvals | TSP can render interactive layers; no terminal may grant authority itself | Hermes server-request approval path owns allow/deny | **Hermes authority → Tern layer** | high | exact native parity before Ink fallback can go away |
| clarification | native interactive surface possible | Hermes server-request clarify owns questions/answers | **Hermes authority → Tern layer** | high | batch question navigation |
| failures / retry | OMP uses a focused native error frame | Hermes owns failure classification and retry actions | **Hermes semantics → Tern presentation** | high | failure density vs transcript history |
| files | Tern has native file/code/markdown/image/PDF blocks | Desktop has a task-attached Files pane | **shared / experiment** | low | route open intent into Tern block or retain Hermes view |
| preview / browser | OMP opens Tern-native browser PiP; Tern owns browser view | Desktop has preview/browser + annotation semantics | **Hermes intent → Tern browser where capability fits** | medium | Hermes annotation/comment-mode parity |
| artifacts | no direct OMP product analogue required | Desktop Artifacts is a durable Hermes destination | **Hermes product semantics** | medium | in-pane gallery, Tern block, or external page |
| capabilities / skills | no Tern ownership of agent skill model | Hermes owns capability/plugin/skill configuration | **Hermes** | high | native sheet vs separate management destination |
| messaging | not a Tern terminal concern | Hermes owns messaging platforms/routes | **Hermes** | high | whether management belongs inside coding pane at all |
| scheduled jobs | Tern can show generic jobs; OMP has background jobs | Hermes Cron is durable product state, distinct from one turn | **Hermes semantics; Tern may present** | medium | session-local vs global job surfaces |
| profiles / gateways | Tern host identity is not Hermes profile identity | Hermes profiles/gateways own credentials/config/session scope | **Hermes** | high | expose profile in pane chrome or only picker |
| settings | Tern Preferences configure terminal; OMP settings configure app | Hermes settings configure agent/product | **separate namespaces** | high | which Hermes settings deserve a Tern-native sheet |
| memory graph | no Tern authority over Hermes memory model | Desktop Starmap/Memory Graph is Hermes state | **Hermes** | high | whether it belongs in the coding pane |

## Evidence anchors

### Tern / TSP

- Surface ownership: https://docs.stencil.so/tern/protocol/index.html
- Layout/workspaces: https://docs.stencil.so/tern/guides/layout.html
- Native node/view model: https://docs.stencil.so/tern/guides/views.html
- Canonical OMP native visual: https://stencil.so/tern — **03 Graphics**

### Hermes

- TUI behavior and hotkeys: `ui-tui/README.md`
- TUI/backend authority boundary: `tui_gateway/AGENTS.md`
- Desktop design/IA: `apps/desktop/DESIGN.md`
- Desktop routes: `apps/desktop/src/app/routes.ts`
- Desktop visual evidence: `apps/desktop/pr-assets/`
- Session Orchestrator visual/demo: `website/static/img/docs/tui-session-orchestrator/`

## Confidence

- **high** — current protocol/product ownership is explicit
- **medium** — state ownership is clear; presentation ownership still needs A/B/C
- **low** — genuine product decision; do not settle without experiment evidence
