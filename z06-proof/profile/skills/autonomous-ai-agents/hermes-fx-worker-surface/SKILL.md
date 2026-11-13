---
name: hermes-fx-worker-surface
description: Use when running libfx/fx0 workers under Hermes.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [libfx, fx0, z0bridge, dash, ripple, hermes]
    related_skills: [dash-host-only-qualification, dash-living-night-proof]
---

# Hermes-owned fx worker surface (libfx + fx0)

This covers running, proving and benchmarking the fast lane, where libfx/fx0 workers run under Hermes via z0bridge.

Code: kvnloo/z0bridge `feat/fx-worker` (`src/fx/*`, `docs/fx-worker.md`), kvnloo/fx0 `feat/design-kit` (`fx0/design-kit`), Dash `feat/libfx-live-surface` (`shared/live.ts`, `bridge/src/live-surface.ts`, `LiveSurface.tsx`), Ripple `feat/fast-controls-native` (`src/native`).

## Run

- `bun src/cli.ts serve --port <spare> --token-file <scratch> --fx --fx-dir <scratch>/fx --fx-model gpt-5.6-sol` with `HOME=/home/kvn`, `Z0BRIDGE_FX_EFFORT=low`, `Z0BRIDGE_DEFAULT_CWD=<repo Hermes should work in>`. libfx's N-API addon loads under Bun; no Node sidecar needed.
- Codex provider reads `~/.codex/auth.json` per request and never passes the refresh token to libfx.
- Dash bridge for web proofs: `DASH_ALLOW_LOOPBACK=1 DASH_HOST=127.0.0.1 DASH_PORT=<spare> DASH_CREDENTIAL_DIR=<scratch> DASH_ALLOWED_ORIGINS=http://127.0.0.1:<static> DASH_Z0BRIDGE_URL=... DASH_Z0BRIDGE_TOKEN_FILE=... DASH_LIVE_HERMES_PROFILE=clean bun index.ts`. Seed only `dash.settings.v1` (address, execution token, harness hermes) in localStorage, then click "New chat"; seeded conversations don't show in Chats.
- Playwright from Dash's node_modules needs `PLAYWRIGHT_BROWSERS_PATH=/home/kvn/.cache/ms-playwright`.

## Pitfalls

- Same-model A/B: do not switch a Hermes session's model over ACP. `session/set_model` and `/model X --provider Y` end in `Internal error` and wedge the session. Use a Hermes profile whose default already is the model (default profile = openai-codex gpt-5.6-sol) and point `--fx-model` at it.
- Hermes session titles must be unique: a duplicate `/title` crashes the gateway's `session.mutate`. Suffix titles with a nonce.
- Bun applies tsconfig.json `paths` at runtime. A typed boundary for a stricter-checked git dependency belongs in a separate `tsconfig.typecheck.json`.
- The fx0 git dependency pulls fx0's Next.js deps (~574 MB). Install under the heavy lock.
- Tool shells may drift `HOME` (a sibling task's sandbox). If git push or gh fails with auth errors, set `HOME=/home/kvn GH_CONFIG_DIR=/home/kvn/.config/gh`. Before you trust a provider result, check `echo $HOME`.
- Ports 8790/8791 are taken on this host. Check `ss -ltn` before binding a static server.
- Measure first visible char from the app's own store timing (`live-timing`), not a DOM MutationObserver: the owner's own line trips the observer.
- Prove that receipts reached Hermes with a read-only query on `state.db`: child `fxw_<worker>`, source `fx-worker`, `display_kind='fx_receipt'`, and zero worker rows in the parent transcript.

## Same-model harness study

For a controlled Hermes vs fx vs pi vs omp comparison, reuse z0evals `studies/harness-speed-v1` (bench.py, warm.py, fx_run.ts, verify.py, analyze.py) and the `harness-speed-ab` skill. On the MBP with gpt-6.1-sol, the cold first token was fx 2.1 s, pi 2.1 s, omp 3.7 s and Hermes 7–11 s. Warm, fx, pi and omp were all about 1.7–1.8 s.

## Measured (2026-10-20, host load ~25)

On gpt-5.6-sol, fx was faster than warm Hermes: TTFT p50 1.7 s vs 2.5 s, full turn p50 1.9 s vs 3.1 s. p95 was about 5.5–6.2 s for both. fx0's first HTML takes 16–19 s, with outliers of 64–90 s. Raw data: `zer0/data/operations/libfx-surface/`.
