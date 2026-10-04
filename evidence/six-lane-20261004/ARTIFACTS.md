# Recoverable execution evidence — 2026-10-04

Base source: `24b9f0f8c5df5ec6d3d5c10ad9b27c3346bbc925`.
This downstream-only packet preserves receipts from a disposable execution workspace.
Historical absolute paths in receipts identify that workspace; they are not portable links.
Hosted CI was not run for these checks.

- [H1 CLI/config readiness and independent review](h1.md)
- [H2 reviewed gateway pool-attachment fix](h2.md)
- [H3 fallback consumer proof and owner exclusions](h3.md)
- [H4 tools/provider consumer proof and CUA evidence review](h4.md)
- [H5 session/TUI readiness and H3 independent review](h5.md)
- [CUA evidence reconciliation](cua.md)
- [Delivery status and next choices](README.md)
- [H3 original retry-budget-one reproduction](h3-retry1-original-probe.py)
- [H3 final retry-budget-three control](h3-fallback-consumer-probe.py)

The two H3 probes intentionally preserve different evidence. Original red records agent
selection state and lacks the later client cleanup; final green records request model
arguments and closes its client. Do not present them as a single identical-test red/green
pair. The underlying fallback-hop implementation is already owned by **loveshotsmedia**
([PR129895](https://github.com/NousResearch/hermes-agent/pull/129895)) and **entradox**
([PR130855](https://github.com/NousResearch/hermes-agent/pull/130855)); no implementation is
copied or superseded here. The probes were produced by this execution, with independent H5
review. They do not qualify live xAI/Codex behavior or resolve issue132410.

To reproduce a probe on the recorded base, copy that selected `.py` into a temporary
`tests/agent/test_fallback_consumer_receipt.py` in an isolated checkout, then invoke the
repository's `scripts/run_tests.sh -j 2` with that path and an existing approved test
interpreter. The budget-one file is expected to fail. Do not install dependencies merely
to reproduce this packet. Synthetic requests use loopback URLs; no paid providers are used.

Original verbose logs are omitted. Test summaries are receipts, not independent CI proof.
Existing passing tests do not refute separately owned issues or establish untested live
consumer behavior. No upstream PR, comment, merge, or deployment is authorized by this packet.
