# First live-window UX regression receipts

The regression lane renders the real `App`, dock, transcript, run box and model
picker in an isolated **`tern serve`**, with deterministic presentation fixtures.
It makes no model/audio calls and never connects to an ambient Tern daemon.
This is not ordinary signed-in native-window certification.

```sh
export TMPDIR=/home/kvn/.hermes/profiles/clean/cache/scratch
python ui-tsp/e2e/live_ux_geometry.py "$PWD" \
  --receipts /mnt/zer0models/project-artifacts/hermes-tern-live-ux/after
# Same fixture and assertions, but the affected renderers loaded verbatim from
# 84fb40cf59117fd4b5a48fc91b69ca431cad1224. Expected failures are retained.
python ui-tsp/e2e/live_ux_geometry.py "$PWD" --baseline \
  --receipts /mnt/zer0models/project-artifacts/hermes-tern-live-ux/before
```

The runner measures the focused pane's actual columns, adjusting viewport pixels
until it reaches **80, 100 and 180 columns**. It saves PNGs, layout JSON, native
text trees and computed-geometry dumps for idle and busy docks, plus the model
picker. At 80/100 columns the host uses a compact provider menu (no headings);
that menu is opened and captured too. At 180 columns the sidebar headings are
asserted exactly once each. All provider scope orders must be stable,
authenticated-first in both layouts.

The 44 rendered assertions cover:

- No idle live-voice UI and no always-on unsupported hold-to-talk hint.
- A single painted command, while preserving wrapped input, output and status.
- No whitespace-only Thought disclosure.
- Context below the placeholder; Settings intact; no intersecting, wrapped or
  out-of-dock footer text, idle or busy.
- Higher-priority model/Settings controls survive while help is dropped; session
  cost disappears at 80 columns and returns when measured space permits.
- Provider group heading counts and visible scope order, including compact menus.

The footer uses native measured `status`/`seg` priority layout, not column guesses
or text-length breakpoints. Send/Stop stays outside the degradable hint area.
The existing `omp.composer.extras` role avoids generic status caption/location
injection; zero flex basis/minimum allows actual shrinkage. Vim, model, Settings,
jobs, Context, Mic, effort, cost, profile, cwd, branch and help all participate in
priority degradation. Hidden actions remain available through their existing
shortcuts/help/settings. Opt-in live voice is still reachable via Alt+Shift+V;
its consent and active/error UI remain rendered.

The ordinary feature gates remain:

```sh
npm run typecheck --prefix ui-tsp
npm test --prefix ui-tsp
npm run lint --prefix ui-tsp
node_modules/.bin/tsc --noEmit -p ui-tsp/e2e/tsconfig.json
scripts/dev/tern-e2e.sh "$PWD" smoke shortcuts run-box settings
```

A signed-out isolated native window is reported **blocked**, not green; the
runner separately executes the requested journeys under `tern serve`.
Exact before/after capture directories, source SHAs and final gate receipts are
listed in the pull request.
