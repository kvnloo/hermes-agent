# Hermes × Tern reference board

Issue: #436

This board distinguishes **visual evidence** from source-level behavioral evidence.
Do not substitute generated mockups, ANSI OMP screenshots, or descriptions for a
native Tern capture.

## A. OMP inside Tern — canonical visual reference

Primary:

- https://stencil.so/tern
- section **03 Graphics**
- controlled comparison: `omp ANSI any terminal` → `omp native drawn by Tern`

This is the baseline visual evidence for Variant A.

Source/behavior references, not screenshots:

- `can1357/oh-my-pi/packages/tui/src/prompt/composer.ts`
- `packages/tui/src/chrome/transcript-container.ts`
- `packages/tui/src/chat/tool-execution.ts`
- `packages/tui/src/native/`
- `packages/tui/src/overlays/agents-hub.ts`

Credit: Can Bölük / Stencil Labs for OMP's mature native Tern/TSP implementation.

### Capture checklist

- [ ] idle/welcome
- [ ] ordinary conversation
- [ ] working/thinking
- [ ] tool running
- [ ] tool success
- [ ] tool failure/retry
- [ ] composer + model/context/git facts
- [ ] queued follow-up
- [ ] subagent/todo HUD
- [ ] model picker
- [ ] context view
- [ ] git view
- [ ] usage
- [ ] background jobs
- [ ] rewind / branch navigation
- [ ] BTW history
- [ ] browser PiP
- [ ] narrow pane
- [ ] wide pane

## B. Hermes Desktop — canonical Hermes visual language

Actual current-repo screenshots:

- full shell/sidebar/composer:
  https://github.com/NousResearch/hermes-agent/blob/main/apps/desktop/pr-assets/session-source-folders.png
- profile contextual menu:
  https://github.com/NousResearch/hermes-agent/blob/main/apps/desktop/pr-assets/profile-launch-menu.png

Design contract:

- `apps/desktop/DESIGN.md`

Current-source route/pane structure is authoritative when a screenshot is absent.
Use the existing Desktop E2E / visual-snapshot harness to capture current main
rather than inventing a representation.

### Capture checklist

- [ ] fresh/new chat
- [ ] active chat
- [ ] streaming/tool activity
- [ ] approval stack
- [ ] queue/status stack
- [ ] live subagents
- [x] sessions/sidebar shell
- [x] profile contextual menu
- [ ] projects/worktrees
- [ ] Files
- [ ] Preview/browser
- [ ] Review
- [ ] Terminal
- [ ] Capabilities
- [ ] Messaging
- [ ] Artifacts
- [ ] Settings
- [ ] Command Center
- [ ] Profiles
- [ ] Agents
- [ ] Starmap/Memory Graph
- [ ] Simple mode
- [ ] Advanced mode
- [ ] HUD mode
- [ ] split/multi-pane

## C. Hermes TUI — canonical terminal behavior

Actual current-repo capture:

- Session Orchestrator:
  https://github.com/NousResearch/hermes-agent/blob/main/website/static/img/docs/tui-session-orchestrator/session-orchestrator.png

Actual current-repo interaction demo:

- https://github.com/NousResearch/hermes-agent/blob/main/website/static/img/docs/tui-session-orchestrator/session-orchestrator-demo.mp4

Behavior/source:

- `ui-tui/README.md`
- current `ui-tui/src/`

### Capture checklist

- [ ] intro/fresh session
- [ ] normal chat
- [ ] streaming assistant
- [ ] live activity lane
- [ ] approval
- [ ] clarify
- [ ] sudo/secret
- [ ] queue editing
- [ ] model picker
- [x] Session Orchestrator
- [ ] live-agent dock
- [ ] expanded agent roster
- [ ] agent details
- [ ] replay/history/logs
- [ ] narrow terminal

## Evidence rules

1. A visual claim requires a real capture, canonical live demo, or reproducible
   current-build capture.
2. Source code can establish interaction/state behavior but does not prove visual
   appearance.
3. Ordinary ANSI OMP is useful for behavior history but is not visual evidence
   for native OMP in Tern.
4. Generated images are design proposals only and never enter this reference board.
5. Date/pin moving implementations when a comparison depends on exact behavior.
