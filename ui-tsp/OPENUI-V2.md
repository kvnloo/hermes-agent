# OpenUI visual replies on the parity lane

This branch rebuilds the draft OpenUI stack on `feat/tern-omp-parity` at
`f762f60f4ba7771b83309e1c5e20101ea42209b7`. It does not replace the parity frontend
with the old carrier or advance the live dogfood branch.

## Source and authority

Cherry-picked, in dependency order, preserving original authorship:

| Source PR | Source commits |
|---|---|
| #456 generation/compiler | `ad418c46aa`, `2d6240fc44` |
| #457 native preview/capture | `1fb36535a2` |
| #461 capture guards | `ef6acdc972` |
| #460 pinned Git collector (sibling of #461) | `61d64eee69` |
| #464 frontend preview | `4a4471dbb5`, `543b66b78b` |
| #466 terminal-result discovery | `f9d8fff353` |

No merge-only carrier commits were imported. Both `/settings` and `/visual`
remain in the local command table. No new global shortcut was added: the parity
`src/actions.ts` registry remains the owner of app keys. Picker-local navigation
and the fixed Luau block keep their existing local keys. Retired OMP experiments
are not revived.

OpenUI only generates bounded catalog selections. Tern/Luau renders fixed host
code; no generated Lua or JavaScript is executed. Hermes retains session,
approval and publication authority. There is no automatic browser fallback,
model call, renderer installation or publication. Every prepare execution must
set `OPENUI_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1`, including execution through an
agent terminal tool.

## Three blockers: observed RED, then GREEN

1. **Focused install / `edgesOut`:** npm 10.9.8's Arborist crashes on the real
   frontend workspace/file-dependency graph, before checks run. The identical
   no-scripts install succeeds with npm 11.19.0. The frontend workflow now pins
   Node 26.7.0 (bundled npm 11.19.0); its explicit-file TypeScript 6 invocation
   also supplies `--ignoreConfig --types node`. No dependency pin is weakened.
   `scripts/dev/test-openui-install.mjs [npm-executable]` extracts tracked HEAD
   into private scratch and exercises the actual install without touching donor
   dependencies. It failed with npm 10.9.8 and passed with npm 11.19.0.
2. **Dock-aware attestation:** `plugins expect` searches main content, while the
   full identity and Location/Mode live in the dock. Capture now reads the
   focused `.tn-pane.on` native main+dock tree, requires one of each region and
   the complete exact 64-hex ID, and observes exact Location/Mode boundaries.
   All pre-input, pre/post-shot and final identity checks remain. Truncated,
   extended, wrong and duplicate/missing identities fail closed. Eight new
   transport tests include the formerly failing dock-only success case; they
   are not themselves rendering evidence. The unchanged full capture recipe
   also passed against actual Luau in Tern serve after this repair.
3. **Dense treemap:** fixed 4px cell padding imposed an 8px minimum leaf box;
   recursive 2px gaps spent space unavailable to tiny weighted allocations.
   The real Luau regression reproduced 97/113 synthetic cells outside the map
   at 720x800. Geometry now pays zero recursive gutter/padding tax: inset paint
   supplies separators and absolutely positioned labels carry their own inset.
   No map-level clipping or tile suppression was added. The same synthetic
   test and the original saved real 113-root-cell document each pass all three
   viewports in Code and Churn, with every cell measured and zero outside.
   Tiny labels still truncate; tiny pointer targets/readability are not solved
   by geometric containment.

Each blocker has an explicit RED test commit followed by a GREEN fix commit.
The canonical-file-URL assertion was also corrected to expect the loader's
resolved path, and imported frontend files were adopted to parity lint rules.

## Repeatable local gates

Use a qualified Node/npm on PATH. Prepare normal frontend dependencies first;
the isolated OpenUI parser is not supplied by the donor link helper:

```sh
(cd ui-tsp/experiments/openui-generation && \
  OPENUI_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 npm ci --ignore-scripts --no-audit --no-fund --workspaces=false)
(cd ui-tsp && npm run check)
(cd ui-tsp/experiments/openui-generation && OPENUI_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 npm test)
(cd ui-tsp/experiments/openui-preview && npm test && \
  OPENUI_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 node --test test/integration.mjs && \
  lua5.4 test/renderer.lua tern/host.luau)
node --test ui-tsp/experiments/openui-repository/test/collect.test.mjs
python3 -m unittest discover -s ui-tsp/e2e -p test_lane.py -v
scripts/dev/tern-e2e.sh "$PWD" smoke openui
python3 ui-tsp/e2e/openui_geometry.py "$PWD" --receipts /absolute/private/receipts --capture
# Optional: --document /absolute/path/to/an/approved/repository.json
```

For a standalone E2E TypeScript check, link its ignored `e2e/node_modules` to the
installed framework's dependencies before `tsc -p ui-tsp/e2e/tsconfig.json`.
The orchestrator already provides that link in each disposable execution suite.
The geometry script uses Tern serve's explicit fixture-plugin root to load the
exact checked-in Luau/CSS, not a JS/Lua API stub. It retains control replies,
source dirty-state receipts, screenshots and cleanup. This loader is **not**
proof of ordinary daemon/plugin routing. Keep all artifacts outside the repo.

## Observed gates and evidence classes

| Gate | Observed result |
|---|---|
| Frontend project typecheck | 0 errors |
| Full frontend Vitest | 342 passed, 0 failed, 0 skipped |
| ESLint | 0 errors; warnings outside the imported OpenUI files are reported, not suppressed |
| Real locked OpenUI package/parser | 68 passed |
| Preview/bundle/control/lifecycle contracts | 85 passed (includes 8 new dock checks) |
| Real parser-to-bundle integration | 2 passed |
| Real Git collector contracts | 14 passed |
| Lua 5.4 + stub Tern renderer logic | 12 passed; not live Luau evidence |
| Harness Python contracts | 8 passed |
| Harness TypeScript | 0 errors with installed framework dependencies |
| Actual no-scripts frontend install | npm 10.9.8 RED; npm 11.19.0 GREEN |
| `smoke` | 3 steps passed in `tern-serve+real-gateway`; idle-shell readback and 0 post-exit bytes |
| `openui` | 4 steps passed in Tern serve: scope/help, actual prepare, discovery/selection, composer focus |
| Luau geometry | synthetic and saved-real documents; 3 viewports x 2 modes each, 113 cells in every sample, 0 outside |
| Full capture recipe | synthetic and saved-real documents each produced 4 PNGs; `captured-not-inspected` |

The discovery journey explicitly **fixture-replays the real CLI output** as a
completed terminal notification. It does not claim a new model/agent tool turn.
Other frontend journey steps use the real gateway. The saved real Git document
retains its original pinned range/omission policy; it is not current-HEAD metrics.
Representative real-document 720px/root and drilled PNGs were visually reviewed
by the agent: the map stays contained; dense labels truncate. No human inspection
or publication receipt was minted.

Receipts for this rebuild are retained locally under
`/mnt/zer0models/project-artifacts/hermes-openui-v2/`. Test classes overlap across
some workflows; do not sum them into a unique-test or latency claim.

## Still unverified

Ordinary isolated-window Tern is **blocked by its sign-in gate**. The runner
returns exit 2 and records this as blocked, even when the separately labelled
Tern-serve journey passes. All ten native Settings acceptance cases remain
intact and blocked, not reduced to the smoke journey. No live dogfood window,
host daemon, auth grant or other profile was touched.

Current ordinary-window pixels/routing/focus, controlled native callback races,
model-generation quality, physical input-to-paint, first verified artifact
latency, remote/Windows behavior, human pixel inspection and verified transcript
publication remain unverified. Pre/post checks do not attest an unobserved ABA
change or a dishonest host. Final file links reopen current bytes rather than
providing atomic same-revision handoff. Keep the PR draft; do not merge on these
headless results alone.

Existing source licenses and provenance in the experiment READMEs are retained.
Credit Kevin Rajan; Thesys/OpenUI; Can Bölük / Stencil Labs and OMP/Tern;
bmdavis419/T3 Code; Brit; and Hermes contributors as recorded there. No upstream
endorsement is implied.
