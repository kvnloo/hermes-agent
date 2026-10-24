# Review follow-up: RFC #143379 (2026-10-24)

Downstream evidence addendum to REPORT.md. This is not an upstream comment, upstream PR, production change, or an independently rerun Hermes CI result.

## New upstream peer feedback

The substantive new review is [jfugalde's issue comment](https://github.com/NousResearch/hermes-agent/issues/143379#issuecomment-6386263138). The RFC author subsequently updated the issue discussion and body.

1. **Stale-base collection error:** On #139606, and on #116673's old base, tui_gateway/methods_onboarding.py uses Path without importing it. Main fixed the import in 95610a5db4. That explains the broad collection failure, not a broken memory-read implementation. The existing exact-head read-only harness imported tools/memory_tool directly and therefore could test the *separate* read dispatch issue: #139606 tries to invoke an absent MemoryStore.read and raises AttributeError. These findings are compatible; do not claim one disproves the other.
2. **Read restoration:** On current main read is unknown; on #141876 it returns entries and usage for the single-operation path, corroborated by the reviewer and the earlier downstream exact-head run. This does not certify concurrent cache correctness: the downstream scheduled interleaving is RED (7/12 native checks vs 12/12 with an instrumented control).
3. **PR compatibility:** The reviewer reports exact-head pairwise merge-tree conflicts for #141876 + #116673 and #141876 + #139606. No actual combined runtime is tested. First land the independently scoped read restoration, then re-cut dependent changes atop it. Pairwise merge conflicts are *not* proof the design cannot compose after conflict resolution.
4. **Scope of 6,275 changed lines:** The reviewer counted 106 memory-path commits, with most changes addressing other classes; the read-compensation subset is much smaller. Do not attribute every later line to removal of read.
5. **K-recency:** The reported 150-cycle result used a mocked paraphrase and the original 300-cycle reversal was confounded by a scope bug in the author's probe. Neither the -3.5pp finding nor the +1.1pp mock sanity check is certifying evidence. The >=300-cycle floor is still unpassed.

## New reproducible diagnostics

### Exact-head source and merge matrix

Run with an existing full Git checkout containing the pinned head objects and sufficient history for merge-base. Fetch is the operator's explicit step; the tool itself never checks out or moves a branch:

~~~sh
git -C /absolute/hermes-repo fetch --no-tags https://github.com/NousResearch/hermes-agent.git \
  refs/heads/main refs/pull/141876/head refs/pull/116673/head refs/pull/139606/head
python3 harness/review_followup.py --repo /absolute/hermes-repo \
  --output results/review-followup-2026-10-24.json
~~~

This checks Path imports using parsed exact-head source, then uses pairwise **git merge-tree --write-tree**. Exact SHAs are pinned in the source. Missing objects or merge bases produce **BLOCKED**, not a misleading clean merge. Expected conflict paths are reported, not pre-filled. This is an AST **source preflight**, not an executed onboarding import or rebase; pairwise merge-tree does not test the composed application. The reviewer already reported the real merge conflicts; **this new script has not yet run against the complete upstream checkout** in this ChatGPT session.

### Long-session hard gate

**harness/long_gate.py** consumes scored, paired, per-cycle model-recall receipts. It does not call an LLM or compressor. A receipt must identify a fixed baseline, actual benchmark and fixture hashes, seeds, K=10, fixed probe scope, real paraphrase and compressor, production pruning conditions and model-graded answers. Required measured ratios are 4x and 8x at **every cycle from 300 through a claimed maximum greater than 300**, including identical probe-set identity for each baseline/K paired score. A missing point or any mocked prerequisite is **BLOCKED**, not PASS. One negative delta is **FAIL**; PASS requires the minimum per-point delta to be >=0 percentage points.

~~~sh
python3 harness/long_gate.py /absolute/actual-real-recall-scores.json \
  --output results/long-gate-2026-10-24.json
~~~

Receipt format: metadata with the booleans/identifiers enumerated in REQUIRED, plus k=10; max_cycle: integer >300; rows of objects with ratio, cycle, probes, baseline_correct, k_correct, probe_set_id. Counts must be from the same paired probe population. This evaluator trusts submitted metadata and cannot authenticate experiment provenance by itself.

Our existing 150/300/600 boundary traces are valuable but use a deterministic summary substitute. They cannot certify this real-compressor gate; the original RFC author's probe, scope fix, fixture and exact K-recency patch are still needed. **Result today: BLOCKED / NOT CERTIFIED.**

### Test receipts

On the sandbox's isolated Python environment, the new diagnostics completed **6/6 offline unit tests** (source-import and synthetic Git merge conflict fixtures; score-gate PASS, FAIL and BLOCKED behavior). These tests validate our tooling, **not** Hermes's actual mergeability or a new recitation result. No MBP/fleet job, original 300-cycle suite, or upstream integration run was executed in this update.

~~~sh
(cd harness && python3 -m unittest -v test_review_followup test_long_gate)
~~~

Existing native findings and receipts remain unchanged in REPORT.md; the original study pins and authors' credit remain intact. Nothing posted upstream.
