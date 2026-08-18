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
KANBAN_ATTENTION_EVIDENCE_PACKET=/absolute/path/to/fresh-packet \
  scripts/run-electron-e2e-display.sh npx playwright test e2e/kanban-attention-real-backend.spec.ts --reporter=list
```

The wrapper preserves an explicitly configured graphical session, detects a
live Wayland socket when the environment was scrubbed, and otherwise starts a
private Xvfb server for headless CI. It fails with a diagnostic instead of
silently attempting display-less Electron when neither path is available.

When `KANBAN_ATTENTION_EVIDENCE_PACKET` is an absolute, previously disposable
output path, the test replaces it with a self-contained historical packet. It
includes the exact renderer, Electron-main, and install-stamp bytes; the
synthetic database and schema; before/after logical receipts; backend and
Electron logs; allow-listed launch/process/version records; five lossless PNGs;
the interaction trace; and production sentinels. The generator derives build,
source, runtime, database, and verdict fields from those inspectable records,
hashes every payload in `manifest.json`, and seals that manifest with the
detached `manifest.receipt.json`.

Verify a historical packet without rebuilding by recomputing every listed
payload hash, then recomputing the detached receipt's manifest hash. The copied
database is safe to distribute only when `manifest.json` records
`database.privacyAudit.syntheticOnly: true`; the run fails closed otherwise.
Set `KEEP_KANBAN_ATTENTION_E2E=1` only when locally diagnosing the isolated
sandbox.
