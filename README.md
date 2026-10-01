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

Branches pushed: `ready/*` (41: 23 code fixes, 2 chore bundles, 15 docs bundles, 1 parked HOLD #303). Upstream PR in flight: NousResearch#126847 (/model fuzzy picker).
