# Spatial (minimal desk)

Infinite **project-scope** desk for Hermes Desktop. Complements Kanban
(execution state) with PRD / FRD / roadmap / specs / decisions as paper piles.

## Design process (keep this thin)

1. **Reference first** — Spatial Mac app stills/motion under alpha
   `design/references/spatial-app/` (get-spatial.com). Paper, not glass.
2. **One metaphor** — freeform desk + folders + cards. No grid cockpit.
3. **Reuse, don’t invent** — `useGrabScroll` (SDK), CSS springs/shadows,
   Dialog/Badge/icons from the design language. No custom animation engine.
4. **Launch curator** — on open, walk project roots + `cwd`, classify docs by
   priority (PRD → decisions → roadmap → specs → context → misc), layout
   highest-priority stacks left/expanded, collapse the long tail. Seed desk
   only when the scan finds nothing.
5. **Opt-in plugin** — `defaultEnabled: false` in-tree; enable in Settings.

## Files

| File | Role |
|------|------|
| `plugin.tsx` | Route `/spatial`, sidebar, palette, ⌘⌥S |
| `desk.tsx` | Stage + launch curator wiring |
| `discover.ts` | Project-root walk via desktop FS bridge |
| `model.ts` | Classify / priority / layout / seed |
| `spatial.css` | Paper tokens (light/dark) |
| `model.test.ts` | Ranking + layout invariants |

## Try it

Settings → Plugins → enable **Spatial**, or ⌘K → “Spatial: Open desk”.
