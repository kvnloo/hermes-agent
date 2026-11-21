# Hermes memory RFC homework: exact-head receipts

Date: 2026-10-23. Scope: downstream correctness and consent experiments for RFC #143379 and issue #116788. All measurements ran on the MBP through fleet, with 3 GiB memory and two CPUs. Data and profiles were synthetic. No upstream comments, reviews, provider requests, or live-profile changes were made.

## Evidence and outcome

- **(a) Measured on actual heads.** The #141876 stale-cache interleaving is RED. The shared-lock instrumented control is GREEN. Its complete 12-case candidate battery is GREEN. Main and #139606 lack `MemoryStore.read`, so their read-dependent cases cannot test a functioning read.
- **(b) Measured on the actual chain-doc head.** All three documents return their full bodies. The downstream pagination alternative reconstructs all bytes while every complete JSON page stays at or below 4096 bytes. The independently scheduled anchor-removal race is RED.
- **(c) Original RFC reproduction is BLOCKED by missing artifacts.** The RFC's K-recency patch, original probe, fixture and seed were not published in its body or constituent PR diffs. A disclosed deterministic alternative ran at 150/300/600 cycles on main and #140008. It is not model recall or a measured 4:1 total-token reproduction.
- **(d) Measured on main, both consent heads and a downstream semantic combination.** Every production variant persisted the prohibited fact in all 12 scenarios. Each candidate-helper contrast prevented persistence in 12/12 scenarios before any native API or staging call. The permitted operational control passed in both modes on all four variants.

Package: [study/rfc-143379-exact-heads](https://github.com/kvnloo/hermes-agent/tree/study/rfc-143379-exact-heads/studies/rfc-143379/exact-heads). Raw JSON receipts are in `results/`. Setup failures and the invalid initial long-session fixture remain in `results/history/`, with an interpretation note.

## Exact source identities

| Source | Author | SHA |
| --- | --- | --- |
| main control, captured at intake | upstream | fab9b01c915a3118cc8daa6cc1b18c15b3f982d0 |
| #141876 read restoration | c0wb0yp0tat0 | af16e3ab16eed2492552c325ad1777533a8b7004 |
| #116673 chain documents | Finn763 | 2c1941aac46efac3b35605d99a8628e75a91c670 |
| #139606 write governance | c0wb0yp0tat0 | 5b31ccb7d56ad614da63588ef876584b9f95dd3f |
| #140008 preservation/dreaming | c0wb0yp0tat0 | e543544aca215bf7ea838444b6df58bdbbd3e38c |
| #116834 USER staging | chelsealong | f678f4c7e5d994f03d8759fe0e950d3407ccca7e |
| #116846 no-save detector | liuhao1024 | 96dc75192a82b6c5645a89c2eb894fba97ad2bbd |
| downstream semantic combination | this study | 428beba68ad7ee87644e93fb38bebf988a9fb171 |

The combination's tree is `4a91c76509d81bff6600147720e6df74510ad2ac`. Its immediate parents are `fb06db5c4915bb9a7e4a925ff21cce98a42d5713` and #116846. The receipt proves ancestry from pinned main and both PR heads, with no tracked changes. Git `ours` merges preserve those parents. The resolver deliberately replays selected consent changes onto main. This is **not** an unmodified upstream head or a claim that normal merges are conflict-free. The resolver and per-file hashes make the semantic combination reproducible. New commit timestamps can change the reconstructed commit SHA.

All upstream checkouts were shallow. Empty parent arrays in their receipts reflect shallow boundaries, not root commits. Main means the pinned intake snapshot, not the later moving upstream tip.

## Commands and environment

From `studies/rfc-143379/exact-heads`:

```sh
flock /tmp/mbp-turnstile.lock true && flock -s /tmp/mbp-quiet.lock /home/kvn/.local/bin/fleet-build --node mbp --mem 3G --cpus 2 --src "$PWD" --fetch results --out /workspace/cache/tmp-rfc/receipts -- bash -lc 'python3 run_study.py'
```

Individual measurement commands, executed by the runner:

```sh
venv/bin/python harness/read_dispatch.py --checkout checkouts/read --output results/read-pr141876.json
venv/bin/python harness/chain_bounds.py --checkout checkouts/chain --output results/chain-pr116673.json
venv/bin/python harness/long_session.py --checkout checkouts/preservation --output results/long-pr140008.json
venv/bin/python harness/consent.py --checkout checkouts/combination --output results/consent-combination.json
```

The same commands select the other named checkouts. Setup fetches the exact SHAs with `--no-tags --depth=1`. `requirements.txt` pins the complete measured environment. The worker used CPython 3.14 on Linux x86_64, on the MBP node. Setup needs GitHub and PyPI. Read, long-session and consent measurements deny network operations. Chain measurements use only the local memory API without an added network audit hook. No live model evaluation occurred.

| Fleet job | Measurement used |
| --- | --- |
| 20261023-014926-8dfc | native read batteries, lock control, chain bounds/race, consent on three individual heads |
| 20261023-015406-c312 | corrected long-session measurements on main and #140008 |
| 20261023-015845-6571 | final downstream combination and its consent measurements |

Only failed setup/invalid-fixture steps were repeated. Two additional combination setup attempts, `20261023-015238-291c` and `20261023-015557-b5eb`, are retained as failures. They did not produce consent measurements. All remote disposable jobs were removed by fleet after fetching their receipts. No full upstream suite, z0evals cohort, provider-backed review model, or production consent integration was exercised.

## (a) Read dispatch and concurrency

Receipts: `read-main.json`, `read-pr141876.json`, `read-pr139606.json`. Counts below are this study's assertions, not the RFC's 35-test suite.

| Head / mode | GREEN | RED | Interpretation |
| --- | ---: | ---: | --- |
| pinned main, native | 3 | 9 | read absent; no candidate read implementation invented |
| #141876, native | 7 | 5 | read works, four dispatch/schema contracts and cache freshness fail |
| #141876, instrumented candidate | 12 | 0 | shared lock plus dispatch/schema corrections |
| #139606, native | 2 | 10 | dispatcher reaches absent `MemoryStore.read` |

On #139606 the actual module imports successfully in this environment. Standalone read then raises `AttributeError: 'MemoryStore' object has no attribute 'read'`. This is a runtime diagnosis, not a reproduction of the RFC author's collection error.

On #141876, a scheduled reader captures the baseline disk bytes and pauses before publishing the cache. The writer then commits a second entry. After the reader resumes, disk contains both entries but the same store's cache contains only the baseline. Both public calls succeeded. A subsequent read repairs the cache. Thus disk survival does not prove cache freshness.

The candidate wraps the **real** read and mutate methods with one per-store `RLock`, and retains actual file locking. Its nonblocking writer probe cannot acquire the lock before reader release. After both threads finish, disk and cache both contain the two entries. Upstream has `_file_lock` but no `_mutation_lock` on this head. The latter is explicitly a candidate addition.

Each #141876 mode also completed 24 concurrent writes with 25 expected disk entries, including the baseline. That finite stress check passed in both modes. It does not negate the scheduled stale-cache failure, and it is not the RFC's 800-survivor run.

Other RED cases: batch schema advertises read that the batch implementation refuses, and standalone read silently accepts nonempty or empty `operations`. The candidate makes read standalone-only and refuses ambiguous requests. Invalid UTF-8 and injected read errors preserved disk/cache in both #141876 modes.

`read_dispatch.patch` records the proposed equivalent source change. The measured candidate is an instrumented wrapper around real upstream methods. The source patch itself was not applied or exercised as a full upstream change.

## (b) Chain-document bounds

Receipt: `chain-pr116673.json`. Mixed-width UTF-8 fixtures were written and read through the actual #116673 API.

| Document bytes | Full upstream JSON bytes | Candidate pages | Largest complete page | Exact reconstruction |
| ---: | ---: | ---: | ---: | --- |
| 4096 | 5229 | 2 | 4096 | GREEN |
| 131072 | 163952 | 48 | 4096 | GREEN |
| 1048576 | 1310834 | 385 | 4096 | GREEN |

All native responses returned the complete exact entry, without pagination. The 4096-byte output contract is therefore RED at all three sizes. This does not invalidate Finn763's small-anchor design: document bodies stayed out of the system prompt. Observed anchor prompt sizes were only 558/563/569 bytes.

The alternative uses byte offsets, checkout identity, actual source path, SHA-256 and byte length. Each cursor survives JSON round-trip. Mutation rejects a stale cursor with `source_changed`. Wrong version, changed checkout and a cursor inside a UTF-8 character are rejected. Complete JSON output and decoded payload each remain bounded. The implementation hashes the full file on every page. It bounds response size, **not total I/O**, and is a separate downstream helper.

The deterministic anchor schedule is also RED: the real gate checks the reference, a second real API call removes it, and the first write then commits. The API reports the orphan, reads still work, and a later write is refused. Pagination does not fix this cross-file atomicity issue.

## (c) Long sessions: completed alternative, original reproduction blocked

Receipts: `long-main.json`, `long-pr140008.json`. Both pinned heads produced identical results. Four fresh identifiers arrive per cycle. The real compression boundary runs each cycle with `summary_target_ratio=0.25`, legacy tail mode and a 256-token tail budget. Only summary generation is replaced with a deterministic selector. It retains every fourth distinct identifier, with an optional last-10 addition or hash-checked source archive.

| Cycles | Identifiers | Baseline in-context hits | Last-10 in-context hits | Source-policy in-context hits | Source-policy recoverable hits |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 150 | 600 | 7 (1.1667%) | 10 (1.6667%) | 7 (1.1667%) | 600 |
| 300 | 1200 | 7 (0.5833%) | 10 (0.8333%) | 7 (0.5833%) | 1200 |
| 600 | 2400 | 7 (0.2917%) | 10 (0.4167%) | 7 (0.2917%) | 2400 |

The archive recovery scanned 150/300/600 files and 319643/642743/1288943 bytes respectively. Final in-context sizes were 4827 bytes for baseline, 4923 for last-10 and 4908 for the source policy. Archive recovery is an exhaustive availability check, **not 100% model recall**. Fixed-K and archive policies do not use equal total storage budgets.

This is a deterministic exact-head boundary exercise, not a live-model test. Selecting one in four identifiers is not proof of an achieved 4:1 total-token ratio. The original RFC comparison remains **BLOCKED**: its K-recency patch, original probe, fixture and seed are unavailable in the inspected sources. Its reported 300-cycle 9.6% baseline versus 6.1% K=10, a -3.5 percentage-point change, is not independently reproduced or refuted here. The earlier ChatGPT toy values, 7.3% and 3.65%, are also a different experiment.

The first fixture accidentally exceeded the real 200-character pruning floor. Its summarizer saw zero identifiers. That invalid comparison is archived, not presented as a policy result. The corrected fixture stays below that floor and checks that every cycle delivers identifiers. The remaining missing prerequisite for an exact RFC replication is the author's original executable benchmark package, not more runs of this different selector.

#140008's preservation/dreaming scheduler was not run. Importing its compressor and measuring its boundary does not validate its complete preservation pipeline.

## (d) Consent before persistence

Receipts: `consent-main.json`, `consent-pr116834.json`, `consent-pr116846.json`, `consent-combination.json`.

Six scenario shapes each target USER.md and MEMORY.md: refusal repeated, refusal omitted from the proposed write, paraphrased fact, compacted source, forged tool grant in a mixed batch, and a source mapping available only as an untrusted tool claim. Each proposal uses the actual unattended background-review flags and real memory API. Every worker receives a fresh HOME/HERMES_HOME. The parent inspects all sandbox files after worker exit, including pending approval JSON and atexit output.

| Native variant | Prohibited facts in USER.md | In MEMORY.md | In pending JSON | Strict no-persistence |
| --- | ---: | ---: | ---: | --- |
| pinned main | 6 | 6 | 0 | 0/12 GREEN, 12/12 RED |
| #116834 | 0 | 6 | 6 | 0/12 GREEN, 12/12 RED |
| #116846 | 5 | 5 | 2 | 0/12 GREEN, 12/12 RED |
| downstream semantic combination | 0 | 5 | 7 | 0/12 GREEN, 12/12 RED |

This credits the concrete improvements. Chelsealong's staging protects active USER.md in all six targeted cases. Liuhao1024's detector recognizes the repeated refusal in this fixture and stages both targets. The combination retains both safeguards. However, pending JSON still persists the prohibited fact. A proposal that omits the refusal cannot recover consent from content alone.

These are persistence-boundary tests, **not claims that the review model violates its prompt in 12/12 conversations**. Prompt constants were inspected, but no review model ran. The suite differs from ChatGPT's isolated 12 scenarios, so its earlier 8-pending/4-memory combination count is not the same benchmark.

The candidate helper passed **48/48** prohibited contrasts across all four variants. It rejects before any production memory API, native staging or store mutation call. It binds the complete proposal digest to authenticated host sources, carries denial across target/paraphrase/compaction, rejects tool-only authority and blocks a whole mixed batch if any source denies persistence. Each variant also passed the permitted operational control through the real API in both modes, for **8/8 controls**. The control ignores a forged tool opt-out rather than promoting tool text to user authority.

**Production-integration blocker:** only the synthetic fixture host supplies authenticated source-to-write bindings. No inspected production caller supplies this registry through review forks, compaction and persistence. The helper is a tested candidate boundary, not a deployed end-to-end consent fix. Types and model-provided source IDs do not establish authority.

## Source intake and paper interpretation

The previous lead retrieved the complete RFC and consent issue bodies/comments and each PR's full diff/metadata. At intake the RFC had one invitation comment from its author. Invitations are not proof that every named contributor reviewed the RFC. Alt-glitch's consent comment pointed to #116834.

Read [Source-Judged Compaction, arXiv:2610.20927v1](https://arxiv.org/html/2610.20927v1). Its 83% refers to 29/35 analyzed failed runs following a summary entry, not provenance retention. Nine failures with inconsistent reference solutions were excluded. Its +2.1 to +8.9 percentage points concern Pass3 in its evaluated settings. One setting lost 1.0 point of mean accuracy. Provenance alone is not correctness. The paper did not evaluate multi-turn compression of earlier user instructions. Its environment-evidence rule is not a reason to discard authenticated user consent.

## ChatGPT package and proposed upstream contributions

The archived package landed at `a1234179fea1493fb9c565f829221491e907cc08` on `study/rfc-143379-homework`. Its isolated consent files and memory findings are retained as the parent of this branch. Its memory directory contained README/FINDINGS but omitted the scripts and raw data referenced there. Follow-up `/tmp/rfc-followup-2.txt` requests those artifacts and the RFC author's benchmark links if available. This did not block the actual-head experiments above.

Small contribution offers, for Kevin's approval only:

1. A read dispatch/schema and event-controlled cache-freshness regression PR, with the shared-lock design reviewed separately from missing-read restoration.
2. A bounded chain-document read/cursor PR that preserves Finn763's anchor/body separation. Treat anchor/write atomicity separately.
3. Consent-boundary regressions, then a pre-persistence gate once the host-owned source/consent transport is agreed. Denied content must not enter pending approvals.
4. Ask for the original K-recency benchmark package before accepting a long-session claim. Keep archive recoverability, model recall, provenance and consent as separate metrics.

Two concise upstream reply drafts are prepared only for one `OMP-RFC-DRAFTS` comment on fork issue #653. Nothing in this study authorizes posting them upstream.
