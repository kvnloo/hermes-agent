# Hermes #116788 — no-save consent boundary experiment

**Date:** 2026-10-23 (local test). **GitHub:** no writes, comments, PRs, or commits. **Data:** invented marker only, no personal user data. **Result:** 116/116 tests pass, where many tests deliberately assert and detect a *privacy failure* in the existing implementations. Passing tests are **not** evidence that the upstream code satisfies the no-save safety invariant.

## The question

When the original conversation contains an explicit user request not to save a fact, what happens if a background reviewer nevertheless proposes that fact for `memory(action="add")`? Test both `USER.md` and `MEMORY.md`, single and batch operations, and the pending-approval store. The reviewer is deliberately forced to propose the fact; this is a **write-boundary adversarial test**, not a model-behavior or prompt-compliance benchmark.

## Reproduction and outcomes

All 12 prohibited-write cases for each version resulted in durable persistence of the fabricated marker — either the memory file or the JSON pending record.

| Tested design | Current privacy-satisfying cases | Applied to memory | Staged to pending | Exact provenance |
|---|---:|---:|---:|---|
| Main | 0/12 | 12 | 0 | `NousResearch/hermes-agent` main `fab9b01c915a3118cc8daa6cc1b18c15b3f982d0` |
| PR #116834 | 0/12 | 6 | 6 | `chelsealong/hermes-agent` `f678f4c7e5d994f03d8759fe0e950d3407ccca7e` |
| PR #116846 | 0/12 | 8 | 4 | `liuhao1024/hermes-agent` `96dc75192a82b6c5645a89c2eb894fba97ad2bbd` |
| Local combination of both guards | 0/12 | 4 | 8 | Hypothetical only, NOT in GitHub |

Note: mutually exclusive outcomes per case; 'staged' counts as persistence because `tools/write_approval.py::stage_write` writes the complete replay `payload` and a content-bearing `summary` to `<HERMES_HOME>/pending/memory/<id>.json`. No user-profile or memory write is needed for the forbidden fact to remain in the pending queue. The experiment verified the invented marker exists in both JSON fields for the self-reporting case.

### Four adversarial classes

1. **Self-reporting:** candidate includes the explicit user refusal ('asked NOT to save'). PR #116846 stages it with the original plaintext; PR #116834 stages USER but directly applies MEMORY.
2. **Clean paraphrase / omission:** candidate contains only the fabricated fact, omitting 'don't save' even though the *original source conversation* says not to save it. PR #116846 cannot detect it and directly writes either store; PR #116834 still writes the MEMORY target and stages the USER target.
3. **Alternative no-save wording:** `don't retain`, `opted out`, etc. The PR #116846 regex misses the tested variants; controls also check known matched phrases. A regex keyed to the candidate's own text is an incomplete consent authority.
4. **Mixed batches:** a normally permissible operational add and a prohibited add are submitted together; a triggered gate stages the *entire batch*, including the prohibited plaintext. Untargeted variants still apply it.

**Positive controls:** Routine operational MEMORY adds were allowed on every evaluated guard. A consensual, ordinary USER add is staged by PR #116834, and allowed by the others. This shows the branch differences are from policy, not a blanket inability to write.

## Mitigation control

We added a *local-only* control that consumes a trusted, source-bound opt-out verdict already known to the session/reviewer and **denies before either the memory writer or pending serializer runs**. It left no marker in `USER.md`, `MEMORY.md`, or pending JSON in the associated cases, including mixed batches. This is **not an implemented Hermes fix**; it demonstrates the necessary ordering and an acceptance invariant. It cannot verify how a production agent would classify free-form opt-out language or maintain identity/provenance across compaction.

## Suggested engineering boundaries

- **Hard no-save**: reject rather than stage. Do so before serialization, summaries, pending approval, journaling, dream consolidation, index builds, and any derived memory archive.
- **Normal user-profile add**: approval-staging is appropriate only if content is eligible to be saved and merely needs approval.
- **Source-aware consent**: carry `retention_allowed` / `no_save` as a trusted, scoped verdict linked to an original source span or user action. Do not let a model claim its own authority. Never infer consent from absent no-save wording in a proposed summary.
- **No-save under compression**: original conversation retention and durable memory are different policy domains. An `archive-before-stub` compactor must not convert a fact excluded from memory into an *independently durable memory artifact*. Raw transcripts remain subject to their own retention permissions.
- **Fail closed on missing consent evidence** for operations whose eligibility depends on that evidence. Keep the failure telemetry content-free; do not accidentally log the forbidden payload.
- **Regressions to add to Hermes**: source opt-out + clean paraphrase to each store; self-reporting candidate; mixed batch; pending JSON content; both review prompts; foreground/attended boundaries; replay after approval; cross-compaction retention; write-approval disabled/enabled.

## Connection to our other work

Hermes RFC [#143379](https://github.com/NousResearch/hermes-agent/issues/143379) argues for provenance-aware read/compaction. This experiment shows **retention eligibility has to accompany provenance**, not just a pointer back to the source. [z0intelligence #22](https://github.com/kvnloo/z0intelligence/issues/22) separately requires memory to be evidence, never permission. For this privacy boundary, opt-out is a user instruction/consent restriction, not just a low-confidence memory claim; a StatePacket or OptMem summary cannot override it.

## Scope, fidelity, and limitations

- Local Python test modules carry the fetched production **gate predicates, regex, and `stage_write` call shape**, with test-only adapters for imports, memory add persistence, the pending record's atomic JSON write helper, and provenance context. Real GitHub PR source was read directly on 2026-10-23; see pinned links below.
- These tests **did not import or execute the full Hermes repository, open a real agent/model, or exercise CI on the actual PR checkout**. Container networking could not resolve GitHub, so this environment could not clone the repo. Treat findings as deterministic source-level reproductions of the tested add/stage seam, not complete integration verification.
- The isolated gate models a reviewer proposing a forbidden fact even though prompt rules advise otherwise. It does not estimate how frequently LLM reviewers will disregard those prompts.
- A synthetic memory write in this lab stands in for the normal `MemoryStore.add` after the gate returns `None`; no store cap, concurrent writer, or live profile was involved.
- The local combination and trusted-source denial are **independent experimental controls**, not deployed upstream code.
- No actual user no-save fact, file, transcript, or stored memory was used or modified.

## Source references

- [Issue #116788](https://github.com/NousResearch/hermes-agent/issues/116788)
- [PR #116834](https://github.com/NousResearch/hermes-agent/pull/116834) — [code at pinned head](https://github.com/chelsealong/hermes-agent/blob/f678f4c7e5d994f03d8759fe0e950d3407ccca7e/tools/memory_tool.py)
- [PR #116846](https://github.com/NousResearch/hermes-agent/pull/116846) — [code at pinned head](https://github.com/liuhao1024/hermes-agent/blob/96dc75192a82b6c5645a89c2eb894fba97ad2bbd/tools/memory_tool.py)
- [Main write gate](https://github.com/NousResearch/hermes-agent/blob/fab9b01c915a3118cc8daa6cc1b18c15b3f982d0/tools/memory_tool.py)
- [Main pending record writer](https://github.com/NousResearch/hermes-agent/blob/fab9b01c915a3118cc8daa6cc1b18c15b3f982d0/tools/write_approval.py)

## Re-run

```sh
python -m pytest -q test_consent.py
python runtime.py
```

The first command validates the logic and reproductions; the second writes `results.csv` with outcomes and on-disk leak location booleans. All case files are created inside auto-deleted temporary directories.
