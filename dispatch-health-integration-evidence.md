# Dispatch-health integration evidence

## Candidate

- Integration commit: `ef81fd8184a04e621e3c4aab5fc38b0ece85ecca`
- Authoritative base: `4ba38d4769fcf83f3e36cd333da42dc0f7bc7c23`
- Approved lineage tip: `4ba0245a4b8fee6225ddd9c49b7bbe3e75b651d6`
- Combined patch SHA-256: `3b38c6ee9952eba92f63bfc118f01aa095e69435f523fb62ea52201dc27500ec`
- Live activation/restart: not performed

## Semantic mapping

The integration squashes the reviewed linear lineage onto the current authoritative base without unrelated files:

1. `6d15384e36` — OOF-30 coexistence, durable dispatch-health persistence, episode reset/batched writes, and scoped gateway PID attribution.
2. `7a1932a34a` — fixed 128-sample bounded rotation.
3. `ce42242aa2` — monotonic/clock-safe durable rotation keys.
4. `8101d07e03` — global cross-lane fairness.
5. `4ba0245a4b` — one reserved candidate for each enabled nonempty lane before globally reallocating the remaining budget.

`git diff --exit-code 4ba0245a4b HEAD -- <four changed files>` returned 0, proving the integrated file trees exactly match the approved lineage tip.

## Changed-file hashes

- `hermes_cli/gateway.py`: `73c1bd8c9502fbbfd589510cc0add1b0fd348af12d0e9590e6ec24ea6f0a61ac`
- `hermes_cli/kanban_db.py`: `60b38a6e8b9d43ac96a32a00a1957e37eafe7fce2001b1a774e4718813621ec7`
- `tests/hermes_cli/test_gateway.py`: `6c8b60788f98dd483ca6100101c20959849b587f4608004156dbae2f7e3621ae`
- `tests/hermes_cli/test_kanban_dispatch_health.py`: `f5ab0f3c3de65a991fa903d7f72535196ff962f9e3cbaf6ee134c77d144fdaa7`

## Verification

Command:

`HERMES_PYTHON=/workspace/hermes-home/hermes-agent/venv/bin/python scripts/run_tests.sh tests/hermes_cli/test_kanban_*.py tests/hermes_cli/test_gateway.py tests/gateway/test_kanban_*.py -q`

Result: **53 files; 323 passed, 0 failed, 1 Windows-only skipped**.

This matrix covers the repository's Kanban DB/migration, OOF-30 memory and per-profile/host caps, dispatch lock/tick, lifecycle/review/promote/reclaim, restart and contention behavior, leases/CAS/no duplicate claims, gateway dispatch/profile isolation, scoped PID attribution, and the dedicated static/dynamic/clock/future/mixed-lane/SLA/episode/bounded-write dispatch-health cases. The dedicated health suite reports 15 passed and asserts total persisted telemetry remains at most 128 in one batched writer transaction while each enabled nonempty lane progresses.
