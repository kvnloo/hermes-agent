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
npx playwright test e2e/kanban-attention-real-backend.spec.ts --reporter=list
```

On a display-less Linux host, run the same Playwright command under a headless
Wayland compositor (the CI image uses Cage):

```sh
WLR_BACKENDS=headless WLR_NO_HARDWARE_CURSORS=1 cage -- \
  npx playwright test e2e/kanban-attention-real-backend.spec.ts --reporter=list
```

Evidence is written below the test's Playwright output directory as lossless
PNG captures plus `evidence/manifest.json`. The manifest contains hashes,
process identity, Electron version, isolated DB transition names, viewport
results, and production task/event sentinel checks; disposable task IDs are
redacted. Set `KEEP_KANBAN_ATTENTION_E2E=1` only when locally diagnosing the
isolated sandbox.
