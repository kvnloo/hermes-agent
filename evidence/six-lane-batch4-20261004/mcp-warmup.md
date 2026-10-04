# Batch 4 H1: real gateway warmup → agent MCP consumer

Base: `ea81748579ee1732d214ccb75f91d22208ed623d`.
Test-only final commit: `e265fe8633b97facf0807014340911f06e231f67`.
Branch/worktree: `lane/b4-mcp-warmup-current`, `/workspace/lanes/h4`.
Prior published proof `97e24e3e0162b6501b4c85d9d31a328d6c1366d6` preserved; its tests were not rerun.

## Distinct consumer seam

New file `tests/gateway/test_mcp_warmup_agent_consumer.py` exercises actual `_discover_gateway_mcp_tools`, real stdio child handshake/registration, `_warm_turn_machinery_sync` including real run_agent/model_tools imports and tool-definition assembly, then actual `AIAgent` initialization and its direct MCP schema snapshot. Registry-dispatched echo succeeds before/after the healthy transition.

This is **agent schema + registry dispatch**, not agent executor/model turn, full platform startup, macOS launchd, multiplex transition, or third-party-server qualification.

The same temporary home owns all phases. Uses existing authored `tests/e2e/core/parity/fixture_mcp_server.py` with stdio transport, explicit death/grandchild flags zero, temporary PID log, no external server/content/credentials. Python 3.14.7 and existing MCP 2.0.0.

## Isolation

Before gateway imports, socket `connect` and `connect_ex` reject AF_INET/AF_INET6 and record attempts; final rows assert the attempt list is empty. Config sets environment_probe=false and local_runtime.enabled=false. Metadata-only stubs supply gateway model context, model metadata, and local-server type classification; MCP transport, registration, warmup imports/tool definitions, agent initialization, and teardown remain real.

Synthetic custom model uses a declared 128000 context window; direct tool visibility is deliberately selected with supported `tools.tool_search.enabled=false`. No approval/auth guard changes, network connection, install, live model call or paid API.

## Positive and negative observations

- Healthy: same `MCPServerTask` object, live session and ever-connected state survive actual warmup and agent construction; only one child spawn; agent's direct tool names contain the MCP tool; second echo returns expected synthetic text.
- Negative control: initial discovery/echo succeeds, explicit shutdown occurs BEFORE real warmup. Agent no longer offers the tool; connection remains absent; one total child spawn proves warmup did not silently manufacture a replacement. This distinguishes a missing lifecycle resource from the healthy case.

**No #132397 failure reproduced. No runtime fix proposed.** Missing causal evidence remains the reporter's exact process/profile identity and event between successful discovery and parking (reload, reconciliation, child failure or restart). This narrow single-profile Linux proof cannot decide those unobserved transitions.

## Validation and fixture corrections

Canonical command:

```
HERMES_PYTHON=/workspace/.onboarding/hermes-tests/bin/python bash scripts/run_tests.sh -j 2 tests/gateway/test_mcp_warmup_agent_consumer.py
```

Explicit tool filesystem grant: write `/var/tmp` for canonical scratch allocation. Final captured result: `2 tests passed, 0 failed`, runner wall 5.4s; file subprocess 5.39s, no flaky retry. Final source was tested and then committed without edits; no qualification-only repeat. Ruff and git diff --check pass; worktree clean. Hosted CI not run.

Earlier fixture iterations failed, not the product:

1. Synthetic 8192 window was correctly rejected by the real minimum-context guard; changed fixture to128000 without modifying guard.
2. Default tool-search correctly deferred MCP names; fixture now explicitly selects supported direct-tool mode.
3. Strict no-attempt assertion caught four blocked loopback metadata probes to placeholder127.0.0.1:9. No connection established. Static local-server metadata classification now intercepts that unrelated probe; final attempt assertion passes.

Independent reviewer `/root/hermes_agent` reviewed plan and final committed source; no blocking finding. Reviewer did not repeat the suite. No upstream write, PR, push or deployment performed by this lane.
