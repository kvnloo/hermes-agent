---
name: offline-rate-limit-catalog
description: Use when auditing provider limits from local traces.
version: 0.1.0
author: Kevin (kvnloo), Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [quota, rate-limits, traces, privacy]
    related_skills: [local-usage-sync-audit]
---

# Offline rate-limit catalog

## When to use

Use to catalog rate limits, quota windows, credits, overloads and harness recovery from existing traces. Do not probe providers or change runtime admission unless separately authorized.

## Canonical artifact

Read `/mnt/zer0models/workspace/zer0/data/operations/rate-limits/README.md` using `read_file`. The rerunnable extractor, analyzer and verifier live under its `tools/` directory. Kerdoios remains the live quota authority; the catalog is historical evidence and proposed policy.

## Procedure

1. Inspect source schemas and source coverage before interpreting totals. Preserve offsets and a source registry. Treat assistant messages, job receipts, native task aggregates and physical requests as distinct granularities.
2. Copy live SQLite main/WAL/SHM files to owned scratch before opening. Recover only scratch copies. Reconcile source index counts and index IDs against recovered records; record discrepancies rather than declaring a recovered database exact. Avoid whole-store integrity scans on multi-GB transcript stores when only allowlisted metadata is needed.
3. Persist only allowlisted provider/model identifiers, numeric quota/status/timing fields, fixed classifications and SHA-256 account pseudonyms. Do not retain prompts, responses, raw error bodies, arbitrary headers, credentials, emails or account labels.
4. Use stable byte/row offsets, mutable-row overlap and complete-line checkpoints. Preserve normalized snapshot generations when a runner overwrites raw files. A reparse must not delete the only remaining normalized historical evidence.
5. Classify credit exhaustion, periodic quota, transient throttle, payload/token capacity, model/harness entitlement, native protocol errors, overload, timeout and cancellation separately. A semantic throttle bucket does not establish HTTP 429 unless a status was observed.
6. Keep explicit per-window provenance. Do not turn minute remaining into daily capacity. Quarantine remaining greater than limit and disputed dimension mappings. Never import historical remaining balances into the live ledger.
7. Infer thresholds only from complete enough account-attributed request intervals and failed/successful attempts. Do not infer an owner's concurrency cap from an upstream worker's slots or infer safe concurrency from configured workers. Decode tokens/second is not TPM.
8. Label all recommended concurrency/pacing/cooldown values as measured, inferred or unknown, with evidence. Keep current provider resets and shared account budgets above per-process heuristics. Credit failures need verified balance/plan recovery, not an invented elapsed-time cooldown.
9. Run extraction and verification under the owner's shared heavy lock through `terminal`. Verification must exercise real reruns, partial-line handling, overwrite retention, native Kerdoios parsing, integrity and privacy allowlists. Report live-source changes separately from duplicate insertion.

## Pitfalls

- OMP quota recovery can disagree with both readable indices. An equal row count alone would not prove faithful recovery.
- Groq unsuffixed request headers are mapped differently by generic and provider-specific adapters. Preserve the raw allowlisted headers until the boundary is resolved.
- Cerebras hourly remaining can exceed its stated limit. Quarantine that dimension; do not inflate independent minute/day budgets.
- Nous adaptive retry guidance is response-specific; fixed RPM is not established by that delay.
- Kitchen `no-json` includes permissions and output failures, not just throttling. Raw files can be overwritten while the audit runs.
- Timestamped diagnostic rows can duplicate across logs and retries. Counts are observations, not unique network attempts.
- Root and profile session aggregates can overlap. Do not claim a deduplicated whole-host total without checking identities.
- No retained spend notice means missing evidence. Never manufacture a numerical account-cap example into the catalog.
- `max_concurrency` is measured from the agent-outcomes ledger: p90 agent-run overlap per provider with no throttle within 15 min, using non-interactive runs only, because idle chat windows inflate overlap. A throttle that also fires at concurrency 1 is a daily cap: use `stop_on_quota_error`, not lower concurrency.
- The system journal on this host is volatile, so oomd kill evidence disappears at reboot. Date mass kills from clustered stale delegations in the ledger instead.
- Check the spread of `limits.json` before any scheduler reads it. If every entry has the same placeholder (for example concurrency 1 everywhere), it is a safe floor, not a budget; wiring it in would throttle every lane. Pacing for paid pools comes from `burn-pace`, and free lanes are sized from measured runs. `python -m kerdoios capacity` (kerdoios `feat/live-capacity-20261020`) does this derivation live: it reads `catalog.sqlite` + `kerdoios-historical.json` via `KERDOIOS_RATE_LIMIT_DIR` and labels every limit measured/published/inferred/unknown.
- Split each provider's failures by kind before calling it rate-limited. A pile of `unsupported_model` errors means the harness calls model IDs the provider has retired. Sync routes against the provider's live `/v1/models` instead of adding backoff.

## Related depth

- `references/free-tier-providers.md`: published free-tier limits, terms and gotchas for free LLM APIs and free compute, plus how to run that research without stalling.

## Verification

Use `tools/verify.py` under the shared heavy lock and inspect its generated `verification.json` with `read_file`. It should report passing tests, idempotence on unchanged byte sources, clean catalog integrity, verified evidence links and native historical-state imports. Keep source-quality warnings visible. Continuous collection runs through `agent-telemetry-refresh.timer` (systemd --user, every 30 min, `agent-outcomes/tools/refresh.sh`; status in `agent-outcomes/refresh-status.json`). Versioned copies of the tools live in kvnloo/oss-factory under `factory/telemetry/`, and `install.sh` deploys them. Edit there, then install. Don't fork the data-dir copy.
