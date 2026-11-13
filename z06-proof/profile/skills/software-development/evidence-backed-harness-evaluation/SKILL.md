---
name: evidence-backed-harness-evaluation
description: "Use when evaluating evidence injection in AI harnesses."
---

# Evidence-backed harness evaluation

## When to Use

Use for source-backed memory/context evaluations, shared executable cohorts, and real retrieval-to-model-injection proofs across agent harnesses.

## Procedure

1. Establish the requested lane and exact baseline. Fetch the named branch and create an isolated checkout. Inspect the study contract, receipt schema, discussion, existing evaluator artifacts, and previously tested adapter/cache before coding.
2. Validate the frozen cohort before model resolution: require exact question IDs, executable prompt templates, source/evidence slots, expected behavioral outcomes, executable oracles, mutations, and verification rules. Separate the versioned repo-safe case contract from one shared local source binding; keep private source text and oracle values out of Git. Freeze instantiated prompt identities and binding/contract digests so every consumer receives the identical cohort. Follow references/executable-cohorts.md for preflight. Family labels or committed synthetic facts do not establish historical source-backed recall. A controller-authored fixture delivered through real native input can qualify synthetic continuity only when its capture and consumer behavior are witnessed; retain that attribution and never promote it to human history. Search current canonical artifacts and discussion; if required evidence or the executable cohort is absent, emit a machine-readable blocker with `model_called=false`. Never substitute smoke artifacts.
3. Reuse existing integration seams and caches with minimal transport adaptations. Compare reused files against pinned Git-object bytes. Keep authoritative sources separate from derived packets; retrieved memory is evidence, not truth. Preserve configured model/provider policy and fail open when optional integration is unavailable.
4. Capture retrieval, injection, answer, and verification separately. Locate the current assembly/injection seam and observe the actual model request and provider completion from a real session; retrieval, direct response serialization, or a hook callback alone proves neither injection nor use. Pin the executing package/import graph rather than assuming the installed runtime matches a nearby checkout. Keep expected-answer projections in the independent oracle, not in model-visible evidence. Record provider/model identity without credentials.
5. Exercise cold, warm, exact replay, source-version change, missing-required-evidence, and integration outage. See references/live-cache-proof.md for the sequence. Distinguish controlled source replacement from historical supersession.
6. Validate receipts against the pinned schema and read them back programmatically. Preserve session/trace identity, evidence references, source versions, evidence count, context bytes, source reads, retrieval and whole-turn latency, duplicate flag, support, abstention, and verification. Use schema-defined fields instead of unsupported top-level additions.
7. Run relevant deterministic tests on the exact delivered commit and independently verify delegated artifacts. Keep raw proof private and outside Git. Return branch/SHA, tests, live-proof summary, absolute receipt path, and blocker in plain CLI text.

## Read-only latency attribution

For a read-only latency brief, inspect existing traces and native entries without launching a profiler or loading raw trace volumes into model prompts. Deduplicate forked histories by originating native request/event identity, not filenames or repeated reports. Keep requested effort separate from observable effective effort, preserve unknowns, and compare cache behavior only within matched workload, prompt/tool-prefix identity and warmness. Classify the actual next action and planning need rather than calling every read/edit request wasted reasoning. Keep optional performance work independent of continuity acceptance. Under a free-only brief, use existing offline decision/shadow interfaces and propose only policy-eligible local or verified-free comparisons; do not activate routing, spend paid tokens or replace capability/risk gates with a global cheap-first ladder. Follow `references/latency-attribution.md` for the extraction and recommendation procedure.

## Claim boundaries

- Give diagnostic smoke distinct IDs so it cannot masquerade as the frozen cohort.
- Name the answer oracle and its scope; exact structured checks are not unconstrained semantic verification.
- Record hook-only replay suppression separately; never manufacture a second model answer.
- Report sample counts and separate retrieval latency from whole-turn latency; one observation per arm is not a benchmark conclusion.
- Preserve provenance on cache hits and misses; cached text without source identity cannot support an auditable answer.
- Do not weaken isolation guards for tests. If linked Git metadata lies under a protected home, use an independent checkout of the same commit outside that home.
- Leave untested cross-harness recall, contradictions, historical supersession, and minimum-context superiority explicitly unproven.
