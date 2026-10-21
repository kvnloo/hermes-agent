# F4 tester findings

G04-001 is fixed in the action registry. Alt+Up is consumed even with an empty
queue. Plain Up still recalls sent history. No chord changed; the shortcut
generator produces no documentation diff.

G02-002 is fixed in native Settings. After profile readback, Settings applies the
canonical boolean through `App.setReasoning`, the same live RPC owner used by
`/reasoning hide` and `/reasoning show`. A failed live update remains pending so
Retry can apply it. Historical reasoning stays visible. No Python RPC or contract
changed.

G02-001 is **deferred**, not fixed. The frontend resolves the relative Markdown
destination into a session-owned `file:///...#L1-L2` URL. The native Markdown
renderer removes both that URL and an explicit file URL, while retaining HTTPS.
The SDK's `md` props expose no URI allowlist option. The renderer is shipped in
the external Tern executable, not this repository. Fix the native Markdown URI
policy before treating this finding as closed. Replacing Markdown with a partial
frontend parser or adding duplicate file-link rows would change unrelated prose
layout and is not part of this patch.

## Evidence runner

Use the host's shared thermal lock. Pass an isolated `TMPDIR` per command. The
runner creates its own config and daemon socket there and stops its owned
processes. It uses the real App, Settings surface events, action registry and
native Tern renderer. The gateway is a deterministic fixture, not a real model
turn or a Python gateway acceptance test.

```sh
flock ~/workspace/z0-resume/test.lock nice -n 10 env \
  TMPDIR=~/workspace/z0-resume/tmp/f4 \
  python ui-tsp/e2e/f4_geometry.py "$PWD" --baseline --receipts /path/to/before
flock ~/workspace/z0-resume/test.lock nice -n 10 env \
  TMPDIR=~/workspace/z0-resume/tmp/f4 \
  python ui-tsp/e2e/f4_geometry.py "$PWD" --receipts /path/to/after
```

The baseline loads `actions.ts` and `settings.tsx` verbatim from `724b2aaec5`.
It captures exact pane sizes 80x28, 100x30 and 160x44. Each size records Markdown,
empty-queue Alt+Up, Settings on/off, and reasoning immediately after hiding and
2.2 seconds later. The baseline asserts recalled sent history and continued
reasoning. The patched run asserts neither occurs. Both runs explicitly retain
the unresolved native file-link evidence. PNGs, layout JSON, native trees, dumps,
source identity and cleanup receipts are retained under the chosen receipts and
TMPDIR paths.

Vitest regressions exercise real input dispatch for Alt+Up and real native
Settings change dispatch for hide/show and failed-live-update Retry. No
implementation-source inspection is used by those tests.
