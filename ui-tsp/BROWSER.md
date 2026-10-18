# Tern browser adapter

`Alt+Shift+B` uses the existing action registry to open the browser-block sheet.
Discovery never grants permission. Only **Hand over to agent** adopts a user's
undriven block. **Focus** rechecks the task's ownership. **Release / close owned
block** releases adopted pages (never closes them), and closes agent-created
pages. Retarget/release/frame changes are refused while a turn is running and
all intents retain the gateway transport, profile, task and window fences.

## Native API boundary

- The adapter uses the documented `tern browser JSON --window KEY` CLI. Explicit
  CDP configuration still wins at initial selection. A lost native context with
  a known owned/pending task produces an ownership error, not a different backend.
- **Evaluation frame…** accepts `main` or an exact native index path (`0`, `1.0`).
  `eval` with `frame` verifies the path before committing the selection. Existing
  `browser_console(expression=...)` evaluates there; its result identifies the
  selected frame. Selection is owned by the Python adapter, not a frontend store.
- Child-frame snapshot, trusted input, navigation and capture are deliberately
  refused. The documented `snapshot`/`act` signatures do not take `frame`, and
  silently acting on the main document would be unsafe. Select `main` first.
- Console buffering, recording and annotated capture remain explicitly
  unsupported. OMP implements those using additional page instrumentation and a
  recording controller; there are no corresponding documented native ops. The
  adapter does not invent `console`, `record` or `capture.annotate` requests.
  Ordinary PNG/full-page capture remains supported on the main page.
- Native error kinds (`js`, `not_found`, `unsupported`, etc.) remain distinct.
  A page crash is not evidence that the native capability is unavailable. Only
  an initial explicit capability failure, after blank-page cleanup, can fall back.

## Abandoned opens and disconnects

The CLI client for an `open` is retained when the outer wait expires. A later
explicit command, sheet discovery, or cleanup can consume its **exact late
answer** and close that block. There is no idle polling or timer. The CLI's own
wait is bounded to 300 seconds. No discovery-list difference, pane-owner guess,
or URL/title matching is used to infer ownership.

If the CLI exits without a definitive id (timeout, protocol loss, disconnect),
the adapter quarantines that open and refuses further opens/adoption in the
same window scope. Cleanup retains this state; it does not claim the page is
closed. Inspect the window manually before restarting the owning runtime. There
is no automated way to identify an unknown orphan after its answer is lost, and
no claim of durable reconciliation across a process restart.

Failed handover probes retain cleanup-only release claims without granting
model drive permission or displacing the prior target. A failed release/close
retains its claim for explicit cleanup retry. Cleanup never releases another
profile's pages.

## Evidence and remaining native acceptance

Unit tests exercise the connected App surface, gateway dispatcher and injected
CLI/page contracts. These are **not native-browser certification**. Neither fake
interfaces nor `tern-serve` load real native pages. Real signed-in isolated
open/adopt/focus/release, page-vs-capability failure, frame switching and
late-open/disconnect cleanup still need a signed-in isolated native window.
Never copy a user's Tern authentication or drive their live window to bypass it.

Sources: Tern `browser --help`, the [native page-call signatures](https://docs.stencil.so/tern/print.html#browser-blocks),
and [OMP's TernTab](https://github.com/can1357/oh-my-pi/blob/eb74cf84d8e16ac9b8c4fa5d7c43037023d016ac/packages/coding-agent/src/tools/browser/tern/tern-tab.ts)
(frame paths, late-open cleanup, adopted-block release; Can Bölük / Stencil, MIT).
No uncertain SDK node props or native operation names are introduced.
