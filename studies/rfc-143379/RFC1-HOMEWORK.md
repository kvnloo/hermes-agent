RFC1-HOMEWORK

# Homework for the Hermes doc-chain RFC (#143379) and background consent (#116788)

**All reported test numbers below are from synthetic, isolated, PR-style exercises, NOT runs of a full Hermes checkout.** The complete sources, fixtures, raw rows, and a new pinned-head worktree runner are published only under [`studies/rfc-143379/` on our downstream study branch](https://github.com/kvnloo/hermes-agent/tree/study/rfc-143379-homework/studies/rfc-143379). OMP has the full checkout and can fill in actual-head evidence. We have not posted upstream or run a live model. These are investigation targets, not verified Hermes production regressions.

## Architecture: what is established, what is still a proposal

The RFC proposes a connected sequence: restore direct, bounded **memory read**; anchor optional chain documents outside the always-loaded prompt; preserve **source IDs and retention eligibility** through context compression; and promote persistent claims only after source/permission checks. That direction is consistent with our [z0intelligence canonical memory continuity plan #22](https://github.com/kvnloo/z0intelligence/issues/22): authoritative native source archives, scoped retrieval, bounded StatePacket, explicit correction supersession, and memory-as-evidence-not-permission. Do not build a second canonical memory database or a separate approval authority.

- **Code fact on reviewed main:** the built-in memory tool advertises `add`, `patch`, `remove`, not `read` (the original issue traces removal to `56ee8a5cc6`). Restoring read is a small independently testable change.
- **Unmerged PR #141876** adds `MemoryStore.read` plus dispatch/schema in two files; a reviewer reported a prior stray import and then verified the rebased version's neighbor suite at **147 passed / 0 failed**. This is a reported PR review result, not ours; dedicated read-path regression coverage should still land.
- **Unmerged PR #116673** (Finn763) anchors `@doc:name` to a separate on-disk `memories/docs/name.md`, outside prompt injection, with doc reads, orphan reporting, and write reference checks. A reference establishes discoverability, **not statement provenance or truth**. It never compresses or rewrites doc bodies; preserve that scope.
- **Unmerged PR #139606** adds an acceptance/write gate and has a reviewed integration mismatch: the model-visible `read` and `doc` shapes can be advertised before corresponding store primitives exist; the PR itself acknowledges dependency on the chain-doc work. A source probe is supplied for the actual head.
- **Unmerged PR #140008** adds a prototype preservation/dream cycle, claiming fail-closed archive-before-prune behavior; that is separate from, and does not certify, live governed compaction. It references dreaming concept #25309 by Minamaged18.
- **Unmerged PRs #116834 and #116846** address background consent differently: target-based USER.md staging vs phrase-based no-save staging. Neither proposal, as reviewed, applies a trusted source-level hard refusal *before* writing the pending payload; combine only after tests establish the desired contract.

The RFC's **6,275 lines / 118 commits** of subsequent memory-path work may be real repository accounting, but attributing the entire subsequent effort causally to the 14-line read removal needs a controlled commit-lineage analysis. The cited ~799× session extension and 22+ hour anecdotes are field records, not controlled compression-fidelity outcomes. The **35/35 read** and **200/200 write-read, 800/800 concurrency, 100/100 idempotence, 20/20 over-budget** figures are the RFC author's reported local runs and should not be presented as our independently verified tests.

The RFC reports `K=10` improving exact recitation in a 150-cycle probe but **worsening** the 300-cycle result **9.6% → 6.1% (−3.5 percentage points)**. Its “long-session guard: NOT worse” box is nevertheless marked checked. I would keep that acceptance gate OPEN until a preregistered long-horizon experiment closes it. The mocked paraphrase step, pruning disabled, and the probe's own baseline must remain in its claims; those numbers are not a paper replication.

## Exact source pins for OMP

| Slice | Upstream PR | Reviewed head SHA |
|---|---|---|
| Direct read, c0wb0yp0tat0 | [#141876](https://github.com/NousResearch/hermes-agent/pull/141876) | `af16e3ab16eed2492552c325ad1777533a8b7004` |
| Chain-doc read/anchor, Finn763 | [#116673](https://github.com/NousResearch/hermes-agent/pull/116673) | `2c1941aac46efac3b35605d99a8628e75a91c670` |
| Write acceptance, c0wb0yp0tat0 (prior-art issue #135039 by uni5592427) | [#139606](https://github.com/NousResearch/hermes-agent/pull/139606) | `5b31ccb7d56ad614da63588ef876584b9f95dd3f` |
| Session-preservation/dream prototype, c0wb0yp0tat0 | [#140008](https://github.com/NousResearch/hermes-agent/pull/140008) | `e543544aca215bf7ea838444b6df58bdbbd3e38c` |
| Consent USER staging, chelsealong | [#116834](https://github.com/NousResearch/hermes-agent/pull/116834) | `f678f4c7e5d994f03d8759fe0e950d3407ccca7e` |
| Consent phrase gate, liuhao1024 | [#116846](https://github.com/NousResearch/hermes-agent/pull/116846) | `96dc75192a82b6c5645a89c2eb894fba97ad2bbd` |

Consent comparison main snapshot: `fab9b01c915a3118cc8daa6cc1b18c15b3f982d0`. All heads above were open/unmerged when inspected; do not presume later statuses or composability from different base snapshots.

## Isolated experiment receipts: numbers and limits

**Memory/read/concurrency:** **17/17 synthetic mechanism tests passed**, including *negative demonstrations* of (1) `read()` capturing stale bytes before a locked append and then replacing the in-process entries with the stale parse while disk retains the new entry; and (2) an `_anchor_gate` check occurring before a concurrent removal of that reference, followed by a doc write that leaves the doc orphaned. These are deterministic interleavings of the reviewed code shape, **not established on the actual upstream heads yet**. A serialization control prevented the stale-cache outcome; the anchor race needs a multi-file consistency policy, not merely a second unchecked read. An uncapped synthetic doc returned all **131,072 characters** in a read response; a **4,096-byte UTF-8-safe** pager reconstructed the content as a counterfactual design. The 4 KB figure is exploratory, not accepted Hermes product policy.

**150/300-cycle coverage benchmark: exact definition.** This is **synthetic availability math, not observed LLM recall and not a model compressor experiment.** At each `(n, ratio, seed)`, create `n` random 80-bit identifiers with `random.Random(10000*n + 100*ratio + seed)`, where `n ∈ {150,300}`, `ratio ∈ {2,4,8,16,32}`, `seed ∈ {0,...,24}`. Draw **80 uniformly random historical positions with replacement** per seed via `rng.randrange(n)`, giving **2,000 probes** per `(n, ratio)` and **250 raw per-seed rows**. The toy “compressor” drops all exact IDs from the summary. Only the most recent `min(10, floor(n/ratio))` IDs are assumed exactly present. For 4×, `floor(n/4)` is 37 or 75 and does not bind K=10. Thus **analytic availability** is `10/150 = 6.67%` and `10/300 = 3.33%`; **actual seeded Monte Carlo counts** are `146/2000 = 7.30%` and `73/2000 = 3.65%`, respectively. 300-cycle scaled K=10% yields **9.80%** (window 30), costing more exact items. The 100% ideal-archive control is 100% **by construction with an oracle source locator**, not measured retrieval reliability. None of these values reproduces or corroborates the RFC's 9.6%/6.1% compressor sweep. Full generator, seeds, ratios and raw CSV are committed.

**Background consent (`#116788`):** **116/116 isolated test assertions passed** (many specifically assert the unwanted retention behavior). Each version received the **same 12 source-opted-out synthetic inputs**, covering self-reported refusal, refusal omitted from candidate text, alternative wording, and mixed batches, each to `USER.md` and `MEMORY.md`. We inspected *all* on-disk destinations, including pending approval JSON. Every prohibited candidate was retained somewhere:

| Isolated guard | Fully absent from disk | Applied to memory | Staged in pending |
|---|---:|---:|---:|
| Main | 0/12 | 12 | 0 |
| #116834 gate | 0/12 | 6 | 6 |
| #116846 gate | 0/12 | 8 | 4 |
| Hypothetical union of both gates (**not an upstream PR**) | 0/12 | 4 | 8 |

`stage_write()` serializes the full candidate `payload` and a truncated but content-bearing `summary` into `pending/memory/<id>.json`. A staged forbidden fact therefore **still persists on disk**; staging is sensible for eligible facts awaiting approval, not a hard user “do not retain” instruction. The phrase regex can miss a cleaned paraphrase, and USER.md-only policy allows misrouted personal notes into MEMORY.md. A *local-only* trusted, source-linked opt-out **deny-before-write** control prevented persistence in the tested synthetic cases, including batches. We did not test review-model compliance, live source attribution, real user information, or model consent classification. The full synthetic inputs, gate snippets with adapters, test sources, outputs and JSON summaries are in the package.

This is a **product consent / retention eligibility** analysis within the local agent; do not characterize a heuristic bypass itself as a proven OS-isolation security vulnerability. Durable raw transcripts follow their own separate retention rules. In the RFC's archive-before-stub design, we should not silently convert a user-excluded fact into a new durable *memory* artifact just because the original session is archived.

## Paper and interpretation

Guanghui Min and Chen Chen, *[Prune the Summary, Not the History: Source-Judged Compaction for Long-Horizon Agents](https://arxiv.org/abs/2610.20927)*, arXiv:2610.20927 (2026). SJC uses **Jev** to judge whether summary entries have grounding in actual environment outputs or the previous summary. The reported **83%** is a specific failed-run error-attribution statistic, **NOT** a provenance-survival rate or acceptance threshold. The paper reports **2.1–8.9 percentage-point** cross-run reliability improvements in its evaluated settings, not a guarantee for Hermes. Source grounding alone does not certify scope, consent, freshness, or action authorization.

## Questions for the maintainers

1. Which scope is accepted for the minimum `read` change: read-only store entries plus explicit error and disk/read freshness tests, or chain-doc path selection in the same PR? Recommend keeping the independent restore small.
2. Should `MemoryStore.read` mutate the shared in-process entries cache? If yes, what lock/revision contract makes its concurrent writer observation coherent?
3. Is the chain-doc anchor a **discoverability reference** or an authorization/provenance credential? How is a doc write synchronized with an anchor unlink without lock inversion? How are orphans and unreadable docs surfaced?
4. How large may a model-facing chain-doc read response be? Should a large doc require a bounded read with cursor/explicit truncation, without losing exact text or token predictability?
5. What is the signed-off 300+ cycle **exact-recall and correctness** floor, with actual compression and source rehydration? How does adaptive K trade recall against token budget?
6. What is the authoritative place to enforce user "don't save" eligibility **before** memory, pending approvals, audit payloads, chain docs, dreaming, or derived compressed caches? How is a scoped opt-out tied to original source evidence without retaining the prohibited fact as an independent memory record?
7. Should the write gate fail closed when supporting doc/read primitives are absent? What is the dependency/merge sequence and how will mixed-base PR integration be tested before enabling the schema?
8. Who owns retention/scope decisions when session originals are archived before stubbing and the original transcript has a separate retention policy?

## Suggested sequence for downstream reproduction and small upstream contributions

1. **Baseline and exact-head evidence first:** OMP runs `checkout/run_exact_heads.sh` on the six exact SHA commits in disposable worktrees. Include tests failing on old code and succeeding with targeted mitigation; retain logs, stderr, HEAD SHA, OS/Python/test-env metadata. Run each existing PR's own focused suites via `scripts/run_tests.sh`. Do not conflate those with successful green isolated tests.
2. **Read restoration, independently owned:** Focus on #141876, preserving c0wb0yp0tat0's contribution. Add dispatch and unreadable-file behavior tests plus deterministic read/write interleaving. Settle whether a read should refresh shared mutable cache.
3. **Chain-doc substrate separately:** Work with Finn763's #116673 surface rather than fork another memory store. Test anchor cap, orphan recovery, path traversal, doc/anchor race, large-response contract and prompt cost. Preserve strict schema compatibility.
4. **Write gate integration:** Make #139606 compile/test independently where possible, fail gracefully if #116673 primitives are absent, and ensure schema never advertises an action without implementation. Keep audit content-free for explicit no-retain cases.
5. **Consent before staging:** Salvage the strengths of #116834 (USER target gate) and #116846 (phrase detection + both prompts) while specifying a hard source-linked opt-out refusal before any disk serializer. Preserve chelsealong, liuhao1024, and issue reporter credit; test 12 scenarios and clean paraphrases in both targets and pending files.
6. **Preservation and governed compaction as separate changes:** Verify #140008's claimed archive-before-prune and quiet-hours lifecycle with real source IDs, then prototype Jev support scoring as *one* signal, not permission. Gate promotion by source, user consent and scope; enforce K-recency long-session floor with **real** compressor and current evidence.
7. **End-to-end z0evals #56:** Frozen two-client decision → explicit correction → 150/300-cycle compaction → restart → exact source fetch/verified model answer and permitted action. Track p50/p95, tokens, stale/read-cache invalidation, unsupported answer and no-retain leakage, including pending queue. Submit any upstream draft **only after** Kevin approves the exact text.

No upstream write or notification was performed in preparing this homework. The requested next action is for OMP to reproduce, not to accept the isolated numbers as actual Hermes CI receipts.
