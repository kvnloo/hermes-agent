OMP-RFC-DRAFTS

For Kevin's approval. These are two drafts, not upstream posts. Synthetic profiles only. All measurements ran on the MBP through fleet.

## Draft 1 — reply to NousResearch/hermes-agent RFC 143379

I did some homework against the actual heads. [Harness, report and raw receipts](https://github.com/kvnloo/hermes-agent/tree/study/rfc-143379-exact-heads/studies/rfc-143379/exact-heads).

| PR | Exact tested head |
| --- | --- |
| 141876 | `af16e3ab16eed2492552c325ad1777533a8b7004` |
| 116673 | `2c1941aac46efac3b35605d99a8628e75a91c670` |
| 139606 | `5b31ccb7d56ad614da63588ef876584b9f95dd3f` |
| 140008 | `e543544aca215bf7ea838444b6df58bdbbd3e38c` |

- Read restoration: **7/12 GREEN native, 12/12 with the instrumented lock/dispatch control**. In the scheduled race both calls succeed and disk keeps both entries, but a stale read overwrites the same store's cache. The shared-lock control prevents that ordering. The other four RED cases concern batch schema/dispatch ambiguity. Raw trace: [`read-pr141876.json`](https://github.com/kvnloo/hermes-agent/blob/study/rfc-143379-exact-heads/studies/rfc-143379/exact-heads/results/read-pr141876.json).
- The governance head imports here, but read dispatch raises `AttributeError` because `MemoryStore.read` is absent. I did not reproduce the original collection error.
- Chain docs: 131072/1048576-byte bodies produce **163952/1310834-byte tool responses**. The paginated alternative reconstructs the exact bytes with complete JSON pages at most **4096 bytes**. It preserves Finn763's small-anchor/body separation. Its full-file hash per page is an explicit I/O cost. The separate anchor-removal interleaving also leaves an orphan. [Receipt](https://github.com/kvnloo/hermes-agent/blob/study/rfc-143379-exact-heads/studies/rfc-143379/exact-heads/results/chain-pr116673.json).
- At 150/300/600 cycles, the deterministic compressor-boundary alternative retained **7/600, 7/1200, 7/2400** identifiers. Adding last-10 retained **10/600, 10/1200, 10/2400**. Hash-checked archive scans recovered all originals, at growing storage/I/O cost. **These are not model recall or an achieved 4:1 token-ratio reproduction.** The configured ratio is 0.25 and the summarizer selects every fourth identifier. The original K-recency patch, fixture, probe and seed are still missing. Thus I cannot independently reproduce the RFC's 9.6% versus 6.1% at 300 cycles. [Boundary measurements and limits](https://github.com/kvnloo/hermes-agent/blob/study/rfc-143379-exact-heads/studies/rfc-143379/exact-heads/REPORT.md#c-long-sessions-completed-alternative-original-reproduction-blocked).

Reproduce from the linked directory:

```sh
flock /tmp/mbp-turnstile.lock true && flock -s /tmp/mbp-quiet.lock /home/kvn/.local/bin/fleet-build --node mbp --mem 3G --cpus 2 --src "$PWD" --fetch results -- bash -lc 'python3 run_study.py'
```

Thanks to c0wb0yp0tat0 for connecting these mechanisms and Finn763 for the chain-document design. I can contribute a small dispatch/cache-freshness regression PR first, then a bounded-read/cursor PR. I would keep anchor atomicity and governed compaction separate. Could we attach the original K-recency benchmark before closing the long-session criterion? Also, SJC's 83% describes analyzed failed runs, not provenance retention.

## Draft 2 — reply to NousResearch/hermes-agent issue 116788

I tested the persistence boundary with 12 synthetic opt-out proposals per variant. [Full harness and receipts](https://github.com/kvnloo/hermes-agent/tree/study/rfc-143379-exact-heads/studies/rfc-143379/exact-heads). The test submits proposals using the actual unattended-review flags. It does **not** claim that the review model ignores its prompt in 12/12 conversations.

| Variant | USER.md | MEMORY.md | Pending JSON | No prohibited persistence |
| --- | ---: | ---: | ---: | ---: |
| main `fab9b01c915a3118cc8daa6cc1b18c15b3f982d0` | 6 | 6 | 0 | 0/12 |
| 116834 `f678f4c7e5d994f03d8759fe0e950d3407ccca7e` | 0 | 6 | 6 | 0/12 |
| 116846 `96dc75192a82b6c5645a89c2eb894fba97ad2bbd` | 5 | 5 | 2 | 0/12 |
| downstream semantic combination `428beba68ad7ee87644e93fb38bebf988a9fb171` | 0 | 5 | 7 | 0/12 |

Thanks to chelsealong and liuhao1024 for the two safeguards, and alt-glitch for the pointer. USER staging prevents active-profile additions in these cases. The detector catches the repeated-refusal proposals. The remaining distinction is that **staging still saves the prohibited fact**, while omitted refusal text defeats a proposal-only detector.

The trusted-source candidate rejected **48/48** prohibited writes before any real API, staging or mutation call. All **8/8 permitted operational controls** still used real storage. The cases include paraphrases, compaction, mixed batches and forged tool consent. Only the synthetic host supplies the authenticated source bindings today. This is **not an implemented production consent pipeline**.

Commands, under the same MBP fleet wrapper as above:

```sh
venv/bin/python harness/consent.py --checkout checkouts/staging --output results/consent-pr116834.json
venv/bin/python harness/consent.py --checkout checkouts/nosave --output results/consent-pr116846.json
venv/bin/python harness/consent.py --checkout checkouts/combination --output results/consent-combination.json
```

The combination deliberately replays both consent policies onto pinned main, with both exact heads as ancestors. It is not an untouched upstream branch. [Integration recipe, counts and limits](https://github.com/kvnloo/hermes-agent/blob/study/rfc-143379-exact-heads/studies/rfc-143379/exact-heads/REPORT.md#d-consent-before-persistence).

I can contribute these boundary regressions first. Then I can help with a pre-persistence consent hook once the host-owned source mapping is agreed. It should reject explicit denials before pending approvals and retain that denial across compaction. Model-selected source IDs and a tool's `trusted` field should not grant consent.
