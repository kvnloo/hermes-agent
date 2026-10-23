# Hermes doc-chain, read, and compaction experiment lab

**Scope:** local, isolated mechanism experiments for [RFC #143379](https://github.com/NousResearch/hermes-agent/issues/143379). No repo writes, GitHub posts, branches, or PRs. Results are from a synthetic, stdlib-only Python model that intentionally mirrors the relevant PR control flow; **none of the local tests import the upstream Hermes implementation or run a live LLM**.

## Reviewed upstream heads (2026-10-22 US Central)

| Slice | Author | Open PR | Reviewed head |
|---|---|---|---|
| Read restoration | c0wb0yp0tat0 | [#141876](https://github.com/NousResearch/hermes-agent/pull/141876) | `af16e3ab16eed2492552c325ad1777533a8b7004` |
| Memory anchor/chain docs | Finn763 | [#116673](https://github.com/NousResearch/hermes-agent/pull/116673) | `2c1941aac46efac3b35605d99a8628e75a91c670` |
| Write acceptance pipeline | c0wb0yp0tat0, building on uni5592427's issue and related design discussions | [#139606](https://github.com/NousResearch/hermes-agent/pull/139606) | `5b31ccb7d56ad614da63588ef876584b9f95dd3f` |
| Session preservation/dreaming | c0wb0yp0tat0, building on Minamaged18's dreaming issue | [#140008](https://github.com/NousResearch/hermes-agent/pull/140008) | `e543544aca215bf7ea838444b6df58bdbbd3e38c` |

## Execute locally

```sh
cd hermes_memory_lab
python -m pytest -q test_lab.py
python bench.py
```

There are no network dependencies beyond pytest for the tests. `results.json` and `raw_coverage.csv` are deterministic output, recomputed by `bench.py`.

**Optional, requires a real checked-out Hermes repository elsewhere:**

```sh
./run_against_checkout.sh /absolute/path/to/hermes-agent
```

This runs **existing** Hermes suites on whichever revision is currently checked out. It does not switch branches and makes no code changes. The command has not been executed in this isolated environment: GitHub DNS is unavailable in the container.

## Local tests

- Restore-style `MemoryStore.read()` sees exact disk entries and does not change bytes.
- Chain-doc references are visible in the anchor read; bodies are excluded from the anchor view.
- Orphans remain readable but are refused for new writes.
- Filename/path traversal is rejected.
- An uncapped chain document accepts 131,072 characters; the proposed read shape returns all 131,072 in one response. A 4,096-byte paged reader succeeds instead.
- Negative test: under scheduled concurrency, a `read()` that captured older disk bytes can overwrite a newer shared in-memory entry cache after `add()` commits. The on-disk file remains correct.
- Positive control: serializing the read on the writer's lock ends with disk and in-memory entries agreeing.
- Negative test: a doc write may pass the anchor reference gate before a concurrent anchor unlink; it commits after the unlink and leaves an orphan. This is a cross-file check/use race.
- Budget-refused writes leave files unchanged.
- Correction, scope, user-origin trust, and source-digest checks work in an idealized source-backed resolver (not Hermes).
- UTF-8 paging control reconstructs a multilingual document byte-exactly.

## Synthetic 150/300-cycle benchmark

`bench.py` creates 25 seeded streams per setting, with 80 randomly sampled historical-identifier probes per stream: **2,000 probes each** for 2×/4×/8×/16×/32× at each length. Its summary explicitly loses exact IDs; a K-recency buffer retains exact recent entries. A source-backed policy presumes an ideal always-available exact archive and an oracle source locator. **This is availability math, not model correctness, hallucination rate, or the RFC's published experiment.**

The benchmark answers: how much of arbitrary long-session history could a K-window answer exactly if it had no secondary lookup? At 4×, K=10: 150-cycle coverage 7.30%; 300-cycle coverage 3.65%. At 300 cycles/4×, K scaled to 10% yields 9.80% but requires 30 exact entries (vs. 10). At high ratios, the modeled exact-entry budget limits that window. The always-resolvable archive policy reads 100.00% **by construction**, so it is an upper bound, not measured end-to-end retrieval success.

## What should be reproduced in the actual repo

1. Attach a deterministic barrier to `_read_raw_checked` in `MemoryStore.read`, interleave a locked `add`, and assert the store's in-memory entries and file agree after both return. Verify whether this race exists on the actual PR head.
2. Interleave `_anchor_gate` with unlinking the `@doc:` reference. Assert accepted writes are never committed against an unreferenced anchor version. Consider lock ordering or an explicit anchor-revision compare-and-swap.
3. Assert `memory(action="read", doc="large")` cannot silently return unbounded content; choose and document pagination or a bounded response with explicit truncation.
4. Run the project suites separately on main, restore branch, chain-doc branch, then a reviewed integration branch, with the same baseline interpreter/environment. CI results on one branch are not compositional proof.
5. Move the synthetic 150/300-cycle test into `kvnloo/z0evals#56`'s frozen source-backed questions: real source refs, actual model-input inspection, exact-ID checks, correction supersession, unauthorized scope rejection, stale cache handling, p50/p95 costs. Preserve the canonical z0int #22/#66 architecture; do not create a second store.

## Interpretation guard

These synthetic reproductions show that the **ordering in the reviewed PR diffs allows** specific adverse outcomes. They do not establish how frequently the real Hermes code encounters them, nor that a proposed lock fix is safe across all its file/approval/drift paths. The benchmark's archive control should not be reported as 100% real recall. No GitHub writes or upstream comments were made.
