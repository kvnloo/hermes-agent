# Actual Electron attention E2E

This harness launches the repository's built Electron application and its real
isolated `hermes serve` backend. It never uses `page.setContent`, never force
clicks, and creates all Kanban state in disposable `HERMES_HOME` and
`HERMES_KANBAN_DB` paths.

Replay from the repository root:

```sh
npm ci
cd apps/desktop
npm run build
scripts/run-electron-e2e-display.sh npx playwright test e2e/kanban-attention-real-backend.spec.ts --reporter=list
```

The wrapper preserves an explicitly configured graphical session, detects a
live Wayland socket when the environment was scrubbed, and otherwise starts a
private Xvfb server for headless CI. It fails with a diagnostic instead of
silently attempting display-less Electron when neither path is available.

Evidence is written below the test's Playwright output directory as lossless
PNG captures plus `evidence/manifest.json`. The manifest contains hashes,
process identity, Electron version, isolated DB transition names, viewport
results, and production task/event sentinel checks; disposable task IDs are
redacted. Set `KEEP_KANBAN_ATTENTION_E2E=1` only when locally diagnosing the
isolated sandbox.
