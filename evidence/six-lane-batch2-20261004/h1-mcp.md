# Batch 2, lane 1 — MCP discovery reuse consumer

Source base: `24b9f0f8c5df5ec6d3d5c10ad9b27c3346bbc925` (parent freshly fetched upstream; unchanged).
Test-only commit: `97e24e3e01` on `lane/h4-provider-consumer`, `/workspace/lanes/h4`.
No runtime fix; no push; hosted CI not run. Python 3.14.7, installed MCP 2.0.0.

## Public report / ownership

https://github.com/NousResearch/hermes-agent/issues/132397 describes macOS/launchd boot discovery succeeding, followed ~35 seconds later by all nine heterogeneous stdio servers parking. It proposes fresh run-phase objects and SDK strictness as hypotheses, not established causes. At inspection on 2026-10-04, issue comments were empty, issue-number PR search returned none, reporter ytrop had no open upstream PR. Related scope already owned: stderr surfacing #73398, pre-handshake crash parking #98770, warmup retry increases #52909/#11646. Those implementations are not duplicated.

## Source finding

`hermes_cli/main.py::_command_has_dedicated_mcp_startup` already excludes `gateway run` from inline CLI discovery. The rule dates to `0c6e133c0434ec856d4aea2b08f216f36c0e7dac` (2026-05-30) and exists in the report's own `db45b44` source. `gateway/run.py::_discover_gateway_mcp_tools` owns actual gateway discovery; `tools/mcp_tool_discovery.py::_select_new_servers` excludes connected/connecting names. Therefore the claimed preflight-to-run recreation is not explained simply by CLI + gateway each discovering.

## New bounded consumer proof

`tests/gateway/test_mcp_discovery_stdio_reuse.py` uses only a temporary home/config and a synthetic local MCP SDK stdio child. No HTTP client, model call, external server, secrets, package install or existing user config involved. Both rows use the real gateway discovery wrapper, real MCP transport/registration, and real registry dispatch.

- **Reuse row:** discover; echo `before`; rediscover; echo `after`. Same `MCPServerTask`, live session, `_ever_connected` retained, and exactly one logged child spawn.
- **Teardown negative control:** discover and echo; explicitly shut down MCP; rediscover and echo. Detector sees a different task and exactly two logged spawns. This demonstrates that the test can distinguish a real connection replacement.

Canonical command:

```
HERMES_PYTHON=/workspace/.onboarding/hermes-tests/bin/python bash scripts/run_tests.sh -j 2 tests/gateway/test_mcp_discovery_stdio_reuse.py
```

Tool invocation granted only additional `/var/tmp` write access to the canonical runner. **2 passed**, 4.7s runner wall; no flake retry reported. Ruff and `git diff --check` pass. Tests ran on identical test content before its commit; commit adds only this test file. Prior batch's 14 passing tests were not repeated.

## Conclusion / next evidence

The normal repeated-discovery path **does not reproduce** the proposed fresh-object failure. The shutdown control replaces the child and still succeeds. This does not reproduce full gateway startup, turn warmup, macOS launchd, a scope transition, or the reporter's server-specific behavior; no claim that #132397 is fixed or cannot reproduce generally.

Before a runtime fix, obtain a bounded reproducer showing the actual lifecycle transition (including whether scope or process identity changes), preferably a synthetic server fixture. Current diagnostics go to the owning home's `logs/mcp-stderr.log`, not `gateway.error.log`; no live logs were accessed. Avoid implementing a generic SDK-tolerance/retry fix without reproducing the causal failure.

Independent review pending. No upstream message, PR, workflow rerun, or deployment.

## Final qualification

Root independently reviewed the synthetic subprocess, real gateway/registry boundary, teardown control, and scope limits. Searched gateway MCP tests and relevant tool discovery/reuse suites for equivalents: existing gateway startup tests fake discovery to check scope/OAuth, while initial-connect revival uses a fake session; neither supplies this healthy real-child repeat-discovery plus explicit-teardown control.

At root request, exact committed head `97e24e3e0162b6501b4c85d9d31a328d6c1366d6` received the canonical command above again: **2 passed**, 4.5s, no flake retry. Worktree clean. Independent review complete; no product-fix claim and no push performed by this lane.
