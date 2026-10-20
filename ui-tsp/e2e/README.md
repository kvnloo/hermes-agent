# Tern per-feature E2E lane

```sh
# From the harness checkout. The target can be a different worktree at any SHA.
scripts/dev/tern-e2e.sh /absolute/path/to/worktree \
  smoke settings file-links answer-copy todo-hud shortcuts ink-fallback openui media agent-inspector \
  --node /absolute/path/to/node

# All available journeys are the default; inspect runtime overrides with --help.
scripts/dev/tern-e2e.sh /absolute/path/to/worktree --node /absolute/path/to/node
```

No installation, authentication, model turn or merge is performed. Build output
is generated in the **target** checkout's ignored `ui-tsp/dist` (and `ui-tui/dist`
for Ink). Prepare its dependencies first. On the current development host:

```sh
/mnt/zer0models/hermes-wt/preview-homes/link-node-modules.sh "$TARGET"
scripts/dev/tern-e2e.sh "$TARGET" \
  --node /mnt/zer0models/hermes-wt/preview-homes/tern-frontend/tools/node-26.7.0-linux-x64/bin/node
```

Prerequisites: Node with native TypeScript stripping (tested on 26.7.0), Python
with the target Hermes dependencies, Tern developer tooling, `grim`, headless
Sway, and the already-built `e2e` 0.16.0 framework. `--python`, `--framework`,
`--sway`, `--sway-lib`, `--node` and `--receipts` override host-specific defaults.
The Python executable spelling is preserved so venv discovery still works.
`TMPDIR` must be the operator's private scratch directory; Unix socket paths
must fit the platform limit. Receipt directories are never auto-pruned.

## Journeys and evidence

| Journey | Assertions | Input/data class |
|---|---|---|
| `smoke` | launch, welcome, actual gateway session, unsent composer edit, `/exit`, idle-shell readback, 500 ms late-byte audit | Real frontend + real gateway; no prompt submission |
| `settings` | `/settings`, canonical-schema equality, Session navigation, profile search, edit/Escape, byte-identical cancellation, reopened readback | Real gateway; no fixture replies |
| `lsp-diagnostics` | grouped diagnostic disclosure plus typed cross-file references, stable nested symbol tree, full long-label locations and hover at measured widths | Explicit notification/result fixtures; no real semantic-server success claim |
| `file-links` | read tool's exact session-relative href, modifier click, exact file-block path | Explicit notification fixture, actual README bytes, actual Tern click/file block |
| `answer-copy` | native Copy action, exact answer-only OSC52 bytes, attempted host Paste roundtrip | Explicit notification fixture; read-only stdout observation; never seed expected clipboard text |
| `todo-hud` | exact done/total/current summary, native expand/collapse, full checklist | Explicit `todo.updated` notification fixture |
| `shortcuts` | Alt+M model picker, Alt+, Settings, F1 action-table help, Alt+C exact `/context` request and real reply; no config writes | Real gateway; allowlisted Alt/F1 control chords, no Ctrl-to-Meta ambiguity |
| `openui` | exact `/visual` scope, real locked prepare CLI, picker discovery/selection, full-ID validation, dismissal and composer focus | Real CLI output; completed-terminal notification explicitly fixture-replayed; no agent/model turn or renderer installation |
| `media` | negotiated native media node, exact real PNG path, successful read status, unclipped viewer | Explicit completed-read notification fixture with the real checked-in logo; no model turn or blob fabrication |
| `written-artifacts` | confirmed SVG/Mermaid figures before retained source; failed SVG stays source-only with visible error | Actual source files plus explicitly labelled completion fixtures; attached-gateway paths are not claimed host-local |
| `agent-hub` | `/agents`, canonical owned roster and full transcript page, real Next page RPC, unsupported controls absent, restored composer | Explicit SQLite child fixture in the isolated home; real gateway responses, no model turns or control intents |
| `agent-inspector` | real agent-row click, scoped live tools/notes, long-log scrolling, final status, exact draft/cursor restoration | Explicit `subagent.*` notification fixtures; no model turn or control RPCs |
| `ink-fallback` | actual frontend exits 75 without handshake, real `_launch_tui` runs actual Ink, painted PTY and clean exit | Real non-Tern PTY; only prebuilt-entry resolution overridden, no subprocess/UI/exit mocked |

The preserved **ten-case native Settings suite** runs after the short Settings
journey when an actual ordinary isolated Tern window is available. It is serial,
uncached, retries=0 and keeps all canonical fields/pages/types. Its framework
reports remain under `proof/suite/results`. The six inherited bug-bash charters
are plans, not executed evidence. No sampled headless Settings journey qualifies
the full native acceptance suite.

The real gateway recorder refuses turns, grants, confirmations and consequential
RPCs. Its optional fixture channel accepts **notifications only** from a test-owned
file. Fixture records are separately tagged `fixture-replay`, never `delivered`
real gateway replies. Fixtures never call an LLM. `observe-stdout.mjs` records
OSC52 bytes and forwards writes and callbacks unchanged; a verified OSC52 sequence
is not proof of the host clipboard's contents. If Paste produces no text, that
readback step and the journey are **blocked**, not green or a proven Hermes bug.

## Isolation and gate handling

The runner launches an ordinary Tern window under its own headless Sway. It
sets a private `HOME`, all XDG paths, `TERN_CONFIG_DIR` and `TERN_DAEMON_SOCKET`.
Ambient display, Tern pane identities, D-Bus and credentials are not inherited.
It checks `tern plugin dir` before launching. Every control endpoint belongs to
this run; no host window or live daemon is used. Numeric loopback ports are
allocated per process; all actions verify the private pane, nonce launcher and
account gate. The lower-level `run.mjs` now requires this runner's explicit
`isolation.json`; being under `/tmp` or having a particular display *name* alone
is not ownership proof. This is cooperative same-UID test isolation, not a
security boundary against a malicious peer.

A signed-out/unknown/active gate stops input. The runner captures the **gate
only** as a diagnostic, marks ordinary-window journeys and all ten native
Settings cases blocked, stops that owned client, then starts a separate
`tern serve` process. Its naturally nonapplicable account gate is not a sign-in
bypass. All fallback results are labelled `tern-serve`, never native-window or
real model turn evidence. No account commands, copied auth or user's keyring
session are used.

Cleanup terminates supervised process groups and exact-owned-scope detached
processes only. It records exits/escalations. It never uses executable-name
`pkill`, and it never deletes another client's state.

## Receipts and sizes

Default output:

```
/mnt/zer0models/project-artifacts/hermes-tern-e2e/<UTC-date-time>-<target-sha>/
  source.json                 target + harness SHA, target dirty state, argv
  commands.jsonl              executed argv, cwd, log/PID references
  summary.json                per-journey status and evidence classes
  full-settings-suite.json    each original native case blocked by the gate
  <evidence-class>-<journey>/
    isolation.json, startup-state.json, plugin-dir.log, cleanup.json
    *.log, control.jsonl
    proof/manifest.json, owner.json, gateway.jsonl, tsp.jsonl, steps.json
    proof/sizes.jsonl, observations/*.png, *.json, *.layout.json
```

The same owned session is resized and the **actual PTY columns/rows** read back
until 80×28, 120×36 and 180×44 match (font 15). If a host minimum prevents a size,
its screenshot is named `actual-mismatch` and the measured geometry is recorded;
requested pixel dimensions never stand in for cells. `tern serve` PNGs are copied
from the exact shot response path into persistent receipts. Ordinary-window PNGs
use `grim` on the private compositor. Opening a file changes pane focus, so its
whole-window capture is separately named, not passed through the old pane's
ownership assertion. Inspect images before calling them pixel-qualified.

Step milliseconds are **command-to-observed-state upper bounds**, not
input-to-paint latency or provider timings. No provider latency is measured.

Exit codes: **0** all requested gates pass; **1** a failure; **2** no failures but
one or more blocked gates. `--help` is side-effect free. A blocked native run is
not release acceptance, even if its independent headless journeys pass.

## Mobile geometry and real-turn release gate

`live_ux_geometry.py` now includes exact 390×844 and 412×915 pixel-sized phone
simulations plus measured 80/100/180-column panes. It checks the working-row
spinner, elapsed/intent order, visible Stop geometry and footer containment.
Use `--baseline --baseline-ref <exact-base-sha>` for a negative control without
checking out or editing baseline product sources. Expected-red is evidence,
not a successful release gate.

The separate opt-in `real_turn_journey.py` runs the real frontend and gateway,
submits two real free-model turns, observes busy pixels across phone/desktop
sizes, and checks actual terminal output and canonical SQLite messages before
clean exit. It refuses non-`:free` models; credentials are symlinked from the
explicitly authorized dotenv target, never copied. It creates settings from
scratch with terminal-only tools, no delegation, no paid fallback and telemetry
off. No account credentials or ambient Tern socket are inherited.

```sh
# On the development host; check free -g has >=4 GiB available first.
# Queue ONE bounded heavy batch, not parallel builders or independent nested locks.
flock --close --wait 1800 "$TMPDIR/heavy.lock" nice -n 10 \
  timeout 480 python3 ui-tsp/e2e/live_ux_geometry.py "$TARGET" --receipts "$RECEIPTS/geometry"
flock --close --wait 1800 "$TMPDIR/heavy.lock" nice -n 10 \
  timeout 600 python3 ui-tsp/e2e/real_turn_journey.py "$TARGET" \
  --receipts "$RECEIPTS/real" --python "$HERMES_TEST_PYTHON" \
  --env-file "$HERMES_HOME/.env" --allow-free-model-turns
```

The lock wait is bounded separately from execution; do not treat an empty log
while queued as a product timeout. Inspect all captured PNGs and paired native
trees. These are **tern-serve** receipts: a phone-sized viewport is not touch,
software-keyboard, safe-area, physical phone, or signed-in native-client proof.
Retain blocked cases separately and qualify the owner device before saying the
mobile client is fixed. Hosted `Tern frontend checks` runs unit/type/lint/bundle
gates only; it deliberately makes no native paint/model-turn claim.

## Harness checks

```sh
node node_modules/typescript/bin/tsc -p ui-tsp/e2e/tsconfig.json
python -m unittest discover -s ui-tsp/e2e -p test_lane.py
(cd ui-tsp && npm run typecheck && npm test && npm run lint)
```

The test-only E2E directory needs the existing framework's `node_modules` when
running the compile check directly; the entry command creates that link only
inside its private proof project. Seven behavioral checks cover fail-closed gate
states, owned-vs-peer cleanup, transparent stdout/callback forwarding, zero/late
post-exit byte audits and rejection of unknown journey names before startup. An eighth
check verifies exact read-only `/context` forwarding and refuses other slash payloads.

Authorship: the thirteen original harness commits and four-file WIP snapshot
are cherry-picked intact from `feat/tern-native-e2e`/its preserved WIP branch.
Can Bölük/Stencil own the ui-tsp/SDK/Tern foundations; NousResearch own Hermes.
This lane changes the test harness, not their product ownership boundaries.
