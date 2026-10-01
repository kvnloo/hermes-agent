# claude/ledger — factory evidence for kvnloo/hermes-agent

Coordination ledger written by the Claude worker (oss-factory control plane: downstream fork = message bus). Code lives on branches; this branch holds only evidence and plans.

| Path | What |
|---|---|
| `factory/promotion-readiness-2026-10-01/PROMOTION_QUEUE.md` | Ranked upstream promotion queue (73 READY of 120 Hermes-ledger candidates) |
| `factory/promotion-readiness-2026-10-01/PROTOCOL.md` | Reproof protocol every item followed (RED on main / GREEN / negative control / adjacent) |
| `factory/promotion-readiness-2026-10-01/verdicts/fork-<N>.json` | Per-fork-PR verdict + evidence |
| `factory/promotion-readiness-2026-10-01/branches/` | One patch per `ready/*` branch (also pushed as branches) + `INDEX.tsv` |
| `factory/salvage-wave-2026-10-01/WAVE.md` | Draft upstream salvage wave: 9 issues, one A/B-verified carrier each (not yet posted) |
| `factory/salvage-wave-2026-10-01/clusters-W*.json`, `evidence/` | Per-cluster candidates, A/B results, regression tests, logs |
| `factory/frontier-2026-10-01/catalog.json` | Phase-1 frontier sweep: Hermes architecture brief, 64 ranked feature candidates, 56 runnable experiments, 29 measured datapoints |
| `factory/frontier-2026-10-01/critic.md` | Completeness critic: unread sources, overstated evidence, corrections |
| `factory/frontier-2026-10-01/readers.json` | Raw outputs of the 14 phase-1 readers |

Staged for manual promotion (fork issues): #402 salvage wave · #403 superseded-PR close wave 2 · #404 40 staged PRs with promote commands.

Branches pushed: `ready/*` (41: 23 code fixes, 2 chore bundles, 15 docs bundles, 1 parked HOLD #303). Upstream PR in flight: NousResearch#126847 (/model fuzzy picker).
