# Variant A integrated dogfood lane

Base: `exp/tern-ux-omp-baseline` @ `37796d64`
Umbrella: #432 / #436
Control: #437

This branch is the **integration target** for independently proven A slices.

## Promotion order

1. #443 — native tool lifecycle
2. #444 — native subagents
3. #445 — real-Tern evidence tooling

Do not pull a lane here merely because it compiles. Promotion requires its
focused TSP checks green and its own invariant tests intact.

## Merge rules

- preserve lane authorship/provenance;
- resolve `composerSurface.ts` by composition, not by choosing one lane's file;
- require all semantic kinds actually emitted by the combined surface;
- tools and agents share the baseline's one bounded TSP frame-credit window;
- no second runtime/tool/subagent state stores;
- keep Ink fallback;
- evidence tooling may merge independently because it does not alter rendering.

## Combined dogfood gate

After tools + agents land:

- one native surface spans prompt → prose stream → tool → subagent → idle;
- tool and agent ids mutate in place;
- tool failure remains failed after a later recovery;
- no fake tool/agent progress;
- native input still uses current busy/modal/completion authority;
- credits=1 coalescing remains bounded;
- focused TSP test suite green.

Real-Tern 80/120/180 capture remains a separate evidence gate; do not mark it
complete from fixture/fake-peer tests.
