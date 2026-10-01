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
| `factory/frontier-2026-10-01/{selection,judges}.json`, `FACTORY.md` | Phase-2 selection (14 features), lens judgements, factory blueprint (gates P1–P12, cost tiers, owner decisions OD-0..OD-9) |
| `factory/frontier-2026-10-01/staging/<id>/` | Per staged branch: `STAGING.md` manifest, receipts, harness, upstream-ready text (`PR_BODY.md` / `body.md`) |

Staged for manual promotion (fork issues): #402 salvage wave · #403 superseded-PR close wave 2 · #404 40 staged PRs with promote commands.

Branches pushed: `ready/*` (41: 23 code fixes, 2 chore bundles, 15 docs bundles, 1 parked HOLD #303). Upstream PR in flight: NousResearch#126847 (/model fuzzy picker).

Frontier staged branches (`staged/<id>`, one commit on upstream main each, independently verified; status STAGED unless noted — none is PROMOTION_READY yet, P5 needs the F14 guard set): postmortem-logcalls-zero-hit (#407), observer-hooks-doc-drift (#408), cu-capture-mode-projection (#409), cu-repeat-input-dedup (#410), prefix-parity-journeys (#411), plus nine from fix rounds 3–4: plugin-catalog-entries (HOLD), anthropic-context-editing, factory-replay-gate, edit-fuzzy-wrong-region, tool-result-projection-support, memory-prefetch-metric, compaction-anchor-retention, compaction-hook-salvage, compressor-media-extraction.

Publishing rules for `staging/<id>/`: `private/` dirs, bytecode and files over 5 MB are never published; an item's own `[evidence].public_scope` wins where it declares one (plugin-catalog-entries publishes exactly its 38 listed files). Published copies have absolute local paths and the local host name rewritten (`$S`, `$ARTIFACTS`, `$MNT`, `~`, `<local-host>`), so a sha256 pin on a raw log or helper script that held such a path matches the unscrubbed local original, not the published copy. Receipts themselves were scrubbed at build time and keep their pinned bytes.
