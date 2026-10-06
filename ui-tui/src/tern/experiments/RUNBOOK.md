# Hermes × Tern experiment runbook

Issue: #436

## 1. Create clean worktrees

From the main Hermes checkout:

```bash
git fetch origin
git worktree add ../hermes-tern-a exp/tern-ux-omp-baseline
git worktree add ../hermes-tern-b exp/tern-ux-hermes-baseline
git worktree add ../hermes-tern-c exp/tern-ux-attention-minimal
```

Each worktree is a separate experiment. Do not move commits between A/B/C unless
the change is genuinely shared infrastructure; shared work goes to
`exp/tern-ux-base` first.

## 2. Link the Tern lab plugin once

The plugin is identical across the experiment branches. Link any one copy:

```bash
tern plugin link /absolute/path/to/hermes-tern-a/ui-tui/src/tern/experiments/tern-plugin
tern plugin reload
```

Focus a Tern shell pane inside the worktree you want to test, then run
**Open Hermes UX lab** from the command palette or press
`Ctrl+Alt+Shift+H`.

The command discovers that focused worktree and opens:

```text
┌─────────────────────────────┬────────────────────────┐
│ Hermes --tui --native       │ manifest + TSP tests   │
│                             ├────────────────────────┤
│                             │ scratch shell          │
└─────────────────────────────┴────────────────────────┘
```

The Hermes pane uses worktree-local `HERMES_HOME` and `HERMES_RUNTIME_DIR`
under `.tmp/`, so A/B/C can run simultaneously without sharing experiment state.

## 3. Verify identity before a run

The upper-right pane prints the branch's deterministic experiment manifest.
Manually re-run it with:

```bash
npm run tern:ux:manifest --workspace ui-tui
```

Confirm the `variant.id` matches the branch:

| Branch | Expected id |
| --- | --- |
| `exp/tern-ux-omp-baseline` | `omp-baseline` |
| `exp/tern-ux-hermes-baseline` | `hermes-baseline` |
| `exp/tern-ux-attention-minimal` | `attention-minimal` |

Then run:

```bash
npm test --workspace ui-tui -- src/tern
```

## 4. Run the same fixture

Use `fixture.ts` in exact order and collect all three viewport classes:

- narrow: 80×28
- normal: 120×36
- wide: 180×44

Do not change pane geometry, Tern appearance, or fixture ordering for one variant
without repeating the same change for all three.

## 5. Capture + score

For each meaningful state:

1. capture the real Tern surface;
2. record the `ExperimentFrame`;
3. run the five-second glance test in `GLANCE_TEST.md`;
4. keep the screenshot/video reference with the receipt;
5. note deviations or missing states instead of filling them with generated art.

The experiment is valid only when A/B/C are compared on the same fixture version.

## 6. Promote shared findings

A result is promoted only after evidence:

- shared infrastructure → `exp/tern-ux-base`
- protocol/runtime correction → #432 / #431 family
- presentation result → stays in #437, #438 or #439 until comparison
- winning interaction contract → documented back on #436 before implementation promotion
