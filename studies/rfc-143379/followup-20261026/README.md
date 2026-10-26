# RFC #143379 follow-up, 2026-10-26 (downstream only)

Scope: the three upstream RFC comments posted after `runs-20261026` (3oltan-seo 6411683234,
xngg1021 6412944809, c0wb0yp0tat0 6416423226), plus executed K-gate statistics.
No upstream writes. No model, no compressor LLM, no network in any probe.

Upstream main pinned: `edfa1c2a135532a8b64f7825c0ac0af6cfe73d4d` (moved from `0107da5d2a` since RUNS-20261026).
PR heads read: #140008 `e543544aca215bf7ea838444b6df58bdbbd3e38c`, #139606 `5b31ccb7d56ad614da63588ef876584b9f95dd3f`.
Probe hashes: `receipts/SHA256SUMS`.

## K1: K-gate statistics (executed, stdlib, seed 143379)

`probes/kgate_stats.py` -> `receipts/kgate_stats.json`. Inputs are only the RFC's published numbers
(300 cycles: K=10 6.1% vs K=0 9.6%; rerun spread -9.2 to +10.2pp).

| Question | Result |
| --- | --- |
| Smallest per-arm n consistent with 6.1% and 9.6% | 114 (next: 115, 197, 198, 228) |
| Null SD of an unpaired delta at n=114, p~7.9% | 3.56pp |
| P(\|delta\| >= 3.5pp) when the true delta is 0, n=114 | 0.38 |
| P(range of 5 reruns >= 19.4pp) under pure binomial noise, n=80 / 114 / 200 | 0.013 / <0.001 / 0 |
| Gate as written ("any point < 0 fails"), truly neutral window, 5 points, n=80 | FAIL 93% |
| Same, window truly +1.1pp better, 18 points, n=1000 per point | FAIL 86% |
| Paired NI (one-sided 95% LCB > -eps, 90% power/bin), eps=3pp, discordance 10% | 952 pairs/bin, 17,136 for 18 bins |

Reading:
1. The headline -3.5pp is about one null SD. It is not evidence of harm on its own.
2. The -9.2..+10.2pp spread is too wide for binomial noise at any n consistent with the published rates.
   This supports the author's "broken ruler" (a systematic probe defect), not a sampling explanation.
3. The worst-point >= 0 rule fails a neutral or mildly helpful window almost surely as points grow.
   A paired non-inferiority gate with a pre-registered eps keeps the intent ("never worse") and is certifiable.
   Changing the gate is the RFC author's and maintainers' decision.

## X: xngg1021 claims (6412944809)

| ID | Claim | Where | Verdict | Evidence |
| --- | --- | --- | --- | --- |
| F1 | Anchor Index survives only one compaction generation | `agent/context_compressor.py` `_augment_summary_lean` | **Confirmed, and sharper**: two failure shapes. If the LLM drops the heading, gen-1 anchors are lost. If it keeps the heading, `if heading not in summary` skips the harvest, so gen-2 anchors are never added | executed on main, `test_f1_*` PASS |
| F1c | Carry-forward (union under the 7,000-char budget, outside the LLM body) fixes it | study-only reference in the probe | Keeps gen 1, 2 and 3 anchors in both LLM behaviours, one heading | executed, `test_f1c_*` PASS |
| F2 | DeepSeek reasoning fallback is cut to 8,000 chars with no length signal | `agent/auxiliary_client.py` `extract_content_or_reasoning`, compressor call site | **Confirmed**: 17K-char reasoning summary -> 8,000 chars, finish_reason stays `stop`, the partial-summary guard keys on finish_reason only | executed on main, `test_f2_*` PASS |
| F3 | session_search scroll is uncapped | `tools/session_search_tool.py` `_scroll` | **Confirmed**: read caps a 74K message at 2,000 chars; scroll returns all 74,000 | executed on main, `test_f3_*` PASS |
| P1 | #140008 `preserve_session` writes `kind="message"`, `DreamCycle.light_sleep` drops it | `tools/spa_integration.py`, `tools/dream_cycle.py` | **Confirmed by source** (the constant is `LOAD_BEARING_KINDS`, not `PROMOTABLE_KINDS`). Also: items carry no `provenance`, so every item scores as "agent" | probe written, NOT RUN (see limits) |
| P2 | #139606 `verify_post_write` checks memory, not disk | `tools/write_gate.py` `_store_entries` -> `store._entries_for` | **Confirmed by source**: read-back uses the in-memory list; a lost or concurrently reverted file write is attested as success | probe written, NOT RUN (see limits) |

Main run: `receipts/main-edfa.xml` (5 testcases, 5 PASS), `receipts/main-edfa.log`, via the canonical
`scripts/run_tests.sh` in the checkout's own pm test environment, scratch `HERMES_HOME`, API keys unset.

## 3oltan-seo pilot (6411683234)

Offer: MEMORY at ~96% of 4,000 chars, mostly cold procedural detail; will run a harness on live state and
share sanitized evidence. Relevant on main: `memory_tool.py` already routes procedures to `skill_manage`.
The harnesses that exist today are the #654 read/concurrency probes and #659's runner. The K-gate needs a
paired design (K1) before field numbers can certify it.

## Limits

- P1/P2 probes (`probes/test_followup_pr_probes.py`) were not executed: the local policy blocked running
  third-party PR head code on this host. They are ready for an ephemeral hosted runner.
- F1 probes call `_augment_summary_lean` directly. A full-path 300-generation harness is queued as a
  separate offloaded task (see the #654 comment).
- Nothing here certifies the 300+ K-gate or any combined substrate.
