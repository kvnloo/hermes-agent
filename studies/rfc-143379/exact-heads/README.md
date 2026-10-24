# Exact-head Hermes memory homework

This downstream study extends the isolated package at `a1234179fea1493fb9c565f829221491e907cc08`. That package is evidence of isolated models, not actual Hermes behavior. This directory executes imported modules from complete, pinned upstream checkouts.

## Reproduce on the MBP

From this directory, use the owner's fleet wrapper:

```sh
flock /tmp/mbp-turnstile.lock true && flock -s /tmp/mbp-quiet.lock /home/kvn/.local/bin/fleet-build --node mbp --mem 3G --cpus 2 --src "$PWD" --fetch results --out /workspace/cache/tmp-rfc/receipts -- bash -lc 'python3 run_study.py'
```

Setup downloads exact Git commits and pinned public Python dependencies. Every measurement uses synthetic data and temporary profiles. No provider calls or live Hermes profiles are part of this study. The read, consent, and long-session harnesses deny network operations during measurements. The chain harness exercises only the local memory API without an added network audit hook. The downloaded checkouts and virtual environment are disposable and are not committed.

`run_study.py --only NAME ...` limits measurement execution. Setup still prepares all pinned checkouts. Existing checkouts are reused. Raw JSON receipts retain exact head identities, errors, source fingerprints where applicable, and individual assertions. RED means an acceptance property failed. It does not mean the experiment failed to run. BLOCKED retains the actual exception and does not become GREEN.

## Scope boundaries

- `read_dispatch.py` runs actual upstream dispatch/store methods. Its candidate control wraps existing methods with a shared per-store lock and a dispatch correction. The equivalent proposed source patch is `read_dispatch.patch`. Missing upstream methods are never supplied by the control.
- `chain_bounds.py` runs the actual chain-document API. `chain_page_candidate.py` is a separate downstream pagination alternative, not an upstream patch. Its complete compact JSON and decoded payload each fit 4096 bytes. It scans the full source hash on every page, so bounded output does not imply bounded I/O.
- `long_session.py` runs the actual compressor boundary with a replaced deterministic summarizer. It sets `summary_target_ratio=0.25` and retains every fourth distinct identifier. That is not a measured total-token 4:1 ratio. Fixed-K and source-archive variants do not have equal total storage budgets. Archive recovery scans hash-checked originals and is recoverability, not model recall.
- The RFC author's K-recency patch, original fixture, probes and seed were not available in the RFC or its constituent PR diffs. The RFC's reported 300-cycle baseline 9.6% and K=10 6.1% therefore remain an unreproduced comparison. These downstream measurements do not validate the RFC's checked long-session criterion.
- `consent.py` bypasses the review model and submits prohibited proposals through the actual unattended-write API. It measures the persistence guard, not the probability that a review model follows its prompt. Each of 12 prohibited scenarios has a production run and a candidate-helper contrast. The permitted operational control must still persist through the real API.
- `consent_gate.py` requires a trusted host adapter to bind writes to authenticated sources and consent. The fixture provides that adapter. Production caller integration is **not implemented** by this study. Do not treat model-selected source IDs or a tool's `trusted` field as authority.
- The combination uses native `ours` merges to preserve the exact main and both PR heads as ancestors. `consent_combination.py` deliberately overlays their semantic consent changes onto pinned main. This is a disclosed downstream integration, not an unmodified upstream head or evidence that upstream branches merge without conflicts. The resolver retains main's patch/remove behavior and reuses the PR detector.

## Pinned upstream commits

| Label | Commit |
| --- | --- |
| main control | fab9b01c915a3118cc8daa6cc1b18c15b3f982d0 |
| #141876 | af16e3ab16eed2492552c325ad1777533a8b7004 |
| #116673 | 2c1941aac46efac3b35605d99a8628e75a91c670 |
| #139606 | 5b31ccb7d56ad614da63588ef876584b9f95dd3f |
| #140008 | e543544aca215bf7ea838444b6df58bdbbd3e38c |
| #116834 | f678f4c7e5d994f03d8759fe0e950d3407ccca7e |
| #116846 | 96dc75192a82b6c5645a89c2eb894fba97ad2bbd |

See the report and `results/` for exercised commands and measurements. No upstream comments, reviews, merges, releases, or live-profile changes are authorized by this package.

## October 24 peer-review follow-up

See [REVIEW_FOLLOWUP_2026-10-24.md](REVIEW_FOLLOWUP_2026-10-24.md) for the stale-onboarding-import versus actual memory-dispatch distinction, the exact-head merge-conflict matrix, and the deliberately fail-closed 300+ cycle K=10 evidence gate.

Offline harness tests: `(cd harness && python3 -m unittest -v test_review_followup test_long_gate)` (7/7 in a synthetic Git/score environment). These are **not** new actual Hermes-head or model-compression measurements. The existing MBP exact-head receipts in REPORT.md are unchanged. No upstream write.
