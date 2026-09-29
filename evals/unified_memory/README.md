# Hermes source-backed memory study lane

Local evaluation artifact for [z0evals#56](https://github.com/kvnloo/z0evals/issues/56).
This is **not** a completed cross-harness study and does not install a plugin into
an active profile. DSH/OMO/OMP are read-only dependencies, not implementation targets.

## Pins and prior art

- Hermes base: `5000e29936df69d5209f7cf2eea8e5776cb4cbb1` (re-fetched fork main).
- z0int: `c4a4554d8a3874b456c46feef6ea937993af744a`.
- Receipt and question contracts: PR #57,
  `e41696618c12e6556b49b98ca57a5902833a5a72`; copied unchanged.
- `agent/memory_packet_cache.py` is copied **unchanged** from DSH agent's existing
  `memory-packet-cache` commit `3e762e9d8f2f71fd89e0909911b23be44e22c9e3`.
  The 21 cache-only tests are reused. Its MemoryManager integration is deliberately
  not ported. No new memory backend, canonical DB, provider, or model policy.
- `smoke-manifest.schema.json` is the real `schemas/study-manifest.schema.json`
  from the same z0evals revision, used only for controlled source replacement.

## Executable path

```
explicit source pointers -> real z0int.resolve_context / EvidenceRef
                        -> reused MemoryPacketCache (scoped, revision checked)
                        -> existing z0int Hermes adapter register/before_turn
                        -> real Hermes lifecycle pre_llm_call + user sidecar
                        -> pre_api_request inspection -> actual AIAgent model call
                        -> separate structured answer/provenance verifier
                        -> PR57 receipt JSONL + private raw proof
```

The existing adapter is loaded from the clean pinned z0int checkout. Its
`register` and `before_turn` implementations are unchanged. This opt-in evaluator
binds the adapter's `invoke` transport to `PacketBridge.invoke`, which calls the
real `context_resolve` primitive. It **does not call z0int's automatic function
router**, so no second model selection or provider policy is introduced. This is
an explicit transport composition, not proof that the stock automatic service
already routes memory queries.

The resolver's second-resolution `mtime:size` versions are strengthened at this
boundary with content SHA-256, checked before/after retrieval and on every hit.
Warm cache hits still read source bytes for freshness. Those reads are counted;
claims of zero warm source reads would be false. Missing results and gap packets
are not cached. Stale retained entries are never injected as current. The
verification oracle is not included in retrieval, cache keys, or the model prompt.

The delivery ledger uses session + actual Hermes turn identity + exact question
ID. It prevents duplicate hook delivery within the process. Replays run through
the real Hermes context collector with the original identity; they do not invent
a second model answer. This is not restart-durable exactly-once delivery. It is
bounded to 1024 events and fails open when unavailable or exhausted. Existing
MemoryPacketCache eviction remains bounded. No prompt prefix or past message is
rewritten; only the normal per-turn user sidecar carries the packet.

## Frozen-cohort blocker (do not substitute the smoke)

The full issue #56 comments and PR #57 were read. At the pinned revision,
`question-contract.json` contains only six family labels:
`exact-identifier`, `supersession`, `cross-harness`, `contradiction`,
`missing-evidence`, `minimal-context`. It has **no actual prompts, source
pointers, expected evidence sets, or answer oracle**. The local earlier DSH E2E
probe is a fictional-museum automatic-function test, not this frozen cohort.
No matching executable frozen cohort was found in the located DSH/z0evals trees
or the local proof directories consulted. Passing the scaffold to the CLI exits
2, creates `blocker.json`, and makes no model call. None of the six IDs is marked
run by the smoke, and no frozen-cohort receipt is fabricated.

A frozen input must preserve the DSH prompts verbatim. The evaluator expects:

- `origin`: `harness: dsh`, exact 40-character `revision`, source `locator`;
- all six unique `questions`, with their exact IDs and `prompt`;
- each question's `sources`: public-safe `source_id`, absolute local `path`,
  frozen content `sha256` (64 hex characters);
- `expected_evidence`: required source IDs;
- `verification`: exact structured output `{answer, citations, abstained}`.

The oracle must be independently frozen from the authoritative sources, not
copied from a model answer. This verifier checks exact structured answers and
citation sets; it is not a general semantic-entailment judge. A different DSH
answer contract needs a reviewed verifier adaptation, not silently rewritten
questions. Source material remains evidence, not instructions or truth.

## Run

From the Hermes worktree, with its supported test/runtime interpreter:

```sh
HERMES_PYTHON=/path/to/hermes/venv/bin/python scripts/run_tests.sh \
  tests/evals/test_unified_memory.py --file-retries 0 -- \
  --z0int-root=/absolute/pinned/z0intelligence

HERMES_PYTHON=/path/to/hermes/venv/bin/python scripts/run_tests.sh \
  tests/agent/test_memory_packet_cache.py \
  tests/agent/test_api_content_sidecar.py \
  tests/agent/test_detached_fork_lifecycle_hooks.py \
  tests/plugins/test_memory_hook_registration.py --file-retries 0

python -m evals.unified_memory.run --questions /private/frozen-dsh.json \
  --z0int-root /absolute/pinned/z0intelligence --live --out /private/new-proof-dir

# Independent diagnostic only. This does NOT satisfy the frozen-cohort gate.
python -m evals.unified_memory.run --smoke --live \
  --z0int-root /absolute/pinned/z0intelligence --out /private/new-smoke-dir
```

Use separate canonical runner invocations: the opt-in `--z0int-root` pytest
option belongs to `tests/evals/conftest.py`, and per-file isolation means other
suites cannot see that option. Without it the real-z0int integration test skips.
Live calls never run in deterministic CI.

The live runner resolves the current profile's configured model/provider through
Hermes's resolver, keeps credentials in memory, then uses an isolated temporary
Hermes home. It does not edit live config, credential policy, plugins, memories,
or transcripts. Tools, built-in memory, context files, and background review are
excluded for evidence isolation; model/provider identity is recorded in
`policy.json`. No fallback or substitute provider is selected by this evaluator.

## Evidence and limits

`raw-proof.jsonl` contains source packets, actual model-visible requests, API
completion observations, actual final answers, and separate verification results.
Keep it local/private even when a particular smoke uses public sources.
`receipts.jsonl` is validated against the exact PR57 schema; it includes session,
trace, harness/z0int revisions, SHA-based source versions, provenance hit/miss,
evidence count, bytes, reads, latency, support, abstention and duplicate flags.
Source versions belong in `evidence_refs[].source_version`: the strict schema
does not allow an extra top-level `source_revision` field.

`replays.jsonl` records hook-only replay suppression, not fake model responses.
`summary.json` derives counts and nearest-rank p95/median p50 by reading receipts
back. A smoke has one observation per cold/warm arm, so those percentile fields
are descriptive only, not a performance conclusion. Cache latency and whole
model-turn latency are separate; a warm model call can be slower.

The smoke reads a real public schema, repeats it warm, replaces the same local
source with another real public schema, then removes it. All model answers are
live. Its replacement case demonstrates content-revision invalidation and
preserves old/new evidence in the raw log; it does **not** prove historical DSH
supersession, cross-harness recall, contradiction handling, or minimal-context
superiority. Those remain blocked on the actual frozen source-backed cohort.

Output directories must be new and outside the repository. They are private
(mode 0700; JSON files 0600). Do not commit raw proofs or real private source
corpora. No publishing or PR creation is part of this lane.
