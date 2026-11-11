# Experiment findings — Hermes RFC #143379

**No upstream comment drafted or posted.** Local isolated test suite: **17 passed** (`pytest -q`). This cannot be called a pass of Hermes's own tests.

## Key findings

| Severity | Observation | Evidence from the local experiment | Candidate upstream test / mitigation |
|---|---|---|---|
| High | Read/write ordering can roll back *in-memory* entries | Paused read after capturing old disk bytes, ran add, then released read. Disk has `original + newer`, in-memory has only `original`. | A barrier-based concurrency test on `MemoryStore.read`; serialize on the existing lock or return immutable read data without altering shared state. |
| High | Chain-document reference gate has a potential TOCTOU race | Checked `@doc:notes`, unlinked anchor before doc write, then doc write succeeded and left an orphan. | Revalidate reference within a reviewed multi-file consistency policy, including lock order; do not just add a redundant unlocked check. |
| Medium | Uncapped doc can produce arbitrarily large tool response | A 131,072-character doc was returned in full. Bounded 4,096-byte reader worked, with Unicode-safe cursors. | Bound doc read by bytes/tokens and give a cursor + explicit truncation. |
| Design | A fixed recent window covers a falling share of growing history | At simulated 4× compression, 2,000 probes: K=10 150 turns 7.3%, 300 turns 3.65%. | Make K a measured prompt-budget-dependent policy; exact archival lookup should resolve old content. |
| Guard | Old user correction, unknown scopes, and tampered sources must not be treated as current evidence | Source-backed synthetic controls pass after requiring hash validation of corrected evidence, not just the original. | Add z0evals #56 frozen cohort and enforce z0int #22/#66 scope/provenance in the integration. |

## What does *not* follow

- A 17/17 pass here does **not** imply #116673 or #141876 pass the true upstream suite.
- The toy policy's 100% archive lookup is an idealized upper bound, **not** observed model recall.
- The author's own 300-cycle -3.5pp claim was **not** independently reproduced; this lab uses its own toy conditions.
- A document reference (`@doc:`) is a pointer, **not proof** of claim provenance or trust.

## Recommended next gate

Bring two *failing* deterministic regression tests into a clean downstream integration worktree first: (1) read/cache interleaving, (2) anchor-link/write interleaving. Then add an unbounded-read guard, run baseline vs candidate, and only after the actual runtime and z0evals evidence are green draft a concise reply. Nothing should post or merge while this investigation is underway.
