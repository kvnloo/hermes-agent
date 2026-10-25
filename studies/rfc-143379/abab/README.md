# RFC #143379 — smallest A/B/A/B experiment

**Goal lock.** Verify one root cause before building a memory architecture:
does `MemoryStore.read` publishing a stale disk snapshot into shared in-process
state erase a concurrent writer's newer cache value? Is a **stateless** explicit
read sufficient, without introducing another shared lock, to avoid that failure?
The authoritative source remains the on-disk store.

## Four phases: A1 → B1 → A2 → B2

- **A**: the unmodified native `MemoryStore.read` from upstream
  [#141876](https://github.com/NousResearch/hermes-agent/pull/141876),
  c0wb0yp0tat0's exact head `af16e3ab16eed2492552c325ad1777533a8b7004`.
- **B**: a local, disposable intervention on the **same imported native
  store**: call its real disk reader and parser, calculate usage from the
  returned snapshot, but do *not* call `_set_entries`. No upstream patch.
- Run four periods against fresh, disjoint `HERMES_HOME` directories.
  Identical initial entry, correction, real file I/O and thread interleave.
  Reader captures bytes, writer commits a correction, reader resumes.
  Record disk, cache, returned entries, usage and frozen prompt separately.
- `score.py` accepts only one pinned head/fixture, actual native imports,
  distinct profiles and proven writer-before-reader-release order.
  `PASS_MECHANISM`: A fails freshness twice and B preserves it twice.
  `NO_GAP`: both A repetitions are already safe; do not claim a benefit.
  `INCONCLUSIVE` / `BLOCKED`: different responses/ordering/identities.
  `FAIL_CANDIDATE`: either B loses freshness.

The A/B phases are **mechanism tests, not LLM recall evidence**. An instrumented
candidate is not an upstream commit. The runner saves exact checkout SHA,
original `MemoryStore.read` source digest, synthetic fixture digest,
per-period serialized outcomes and the strict score. A head mismatch fails
before importing modules. `--output` must be outside the checkout.

```bash
python studies/rfc-143379/abab/read_abab.py \
  --checkout /absolute/pinned-hermes-pr141876-checkout \
  --expected-head af16e3ab16eed2492552c325ad1777533a8b7004 \
  --output /tmp/rfc-143379-read-abab.json
python -m unittest discover -s studies/rfc-143379/abab -p test_score.py -v
```

**Why this before a massive 300-turn sweep?** It distinguishes two remedies to
a demonstrated native stale-cache interleaving. Stateless read is the smaller
hypothesis than a cross-platform shared lock. It must still pass the adjacent
external-file-edit, schema, BOM, invalid-UTF-8, chain-doc discoverability and
failure-metrics tests before being proposed to the owning PR; a clean ABAB
result alone cannot approve a change. The earlier full actual-head experiment
on [the companion branch](https://github.com/kvnloo/hermes-agent/tree/study/rfc-143379-exact-heads/studies/rfc-143379/exact-heads)
already measured a shared-lock *instrumented* control. This is a distinct
side-effect-free-read comparison, not an attempt to overwrite that work.

## Next real-world falsifier: do source references actually help the model?

After the reader's contract is settled, reuse a frozen **eight-question**
public-safe cohort under [z0evals #56](https://github.com/kvnloo/z0evals/issues/56).
The paired variants should be the same real Hermes compressor, model,
prompt, seeds and context budget: **A** uses existing lossy summary and its
ordinary in-context memory; **B** preserves a resolvable source reference and
allows *real model-initiated, bounded reread* of the original. Run A/B/A/B
in fresh sessions; then counterbalance B/A/B/A in a second frozen cohort to
check time/order effects. Do not replace B with an oracle that always
hydrates the correct answer; that only measures availability.

The eight facts/questions span exact SHA/path; a corrected decision and its
superseded predecessor; a contradiction with differing provenance; paraphrase
without lexical overlap; missing required source with abstention; cross-profile
denial; explicit source-linked do-not-retain (including pending approval);
and an action whose authority may not be inferred from a memory entry.

For each turn record source ID/revision, explicit correction, triggered
`memory.read` invocation (including **silent non-invocation**), actual
model-visible injected context, model answer, independent source verification,
consent traces including pending files, and whether the model took or
declined an action. Record raw source reads, bytes/tokens, p50/p95 latency,
prompt-cache effect and unanswered/re-explanation rate separately.
Re-run with 150 / 300 / 600 cycles, production pruning and a **real**
compressor; at ratios 4× and 8× the >=300 floor is the worst paired
per-cycle delta, not an average. If the original K-recency fixture/patch
remains unavailable, label this a *different experiment*, not an RFC replication.

## Architectural reuse, not a new system

- [Hermes RFC #143379](https://github.com/NousResearch/hermes-agent/issues/143379):
  bounded read → chain-doc anchor → provenance → governed compaction.
  Preserve Finn763's ownership of the chain-doc work and c0wb0yp0tat0's
  read restoration.
- [Hermes #116788](https://github.com/NousResearch/hermes-agent/issues/116788)
  and chelsealong / liuhao1024's PRs: no-retain must be tested **before**
  both active memory and pending approval serialization. Model text alone
  cannot authenticate consent.
- [Hermes #140005](https://github.com/NousResearch/hermes-agent/issues/140005):
  archive-before-stub can protect original source bytes, but a retained
  archive is neither correct model recall nor permission to retain excluded
  facts. Credit Minamaged18's original dreaming concept.
- [z0intelligence #22](https://github.com/kvnloo/z0intelligence/issues/22):
  reuse native authoritative archives, EventLog, OptMemTree, EvidenceRefs
  and the bounded State Packet; memory is evidence, never authorization.
- [z0evals #56](https://github.com/kvnloo/z0evals/issues/56):
  separate capture, retrieval, model-input injection, supported answer,
  abstention, and replay. No new canonical memory DB or approval authority.

**Evidence status at creation:** ABAB source and its offline evaluator tests
are provided; an actual upstream-head ABAB trace is not yet certified by
these files. GitHub Actions or an isolated fleet runner must attach an
executed SHA + receipt before changing that status. No origin-facing action.
