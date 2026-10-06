# Real Tern capture lane

This branch does not mark Variant A visually verified by itself. It adds a
traceable receipt format for evidence collected in an actual Tern window.

## Capture matrix

Repeat the same `tern-ux-v1` flow at:

| id | cells |
| --- | --- |
| narrow | 80×28 |
| normal | 120×36 |
| wide | 180×44 |

Record the exact pane dimensions, Tern version and A commit before each run.

## Receipt

After taking a screenshot or screen recording:

```bash
npm run tern:ux:capture-receipt --workspace ui-tui -- \
  --evidence /absolute/path/to/capture.png \
  --viewport normal \
  --mode live-hermes \
  --tern-version "$(tern --version)" \
  --out /tmp/a-normal-live.json
```

Use `--mode fixture-replay` for the authored replay. That mode **never** sets
`liveTernVerified=true`.

For a timed needs-user glance trial, add:

```bash
--time-to-needs-user-ms 410
```

The script hashes the evidence and pins the current git SHA. A receipt cannot be
created from an empty/unhashed file.

## Evidence rule

A real capture is still not an attention result. `attentionMeasured` remains
false until an actual glance observation is supplied. The five answer fields
from `GLANCE_TEST.md` can be added to the receipt by the analysis step after
the run.

No generated mockup or ANSI OMP image counts as live-Tern evidence.
