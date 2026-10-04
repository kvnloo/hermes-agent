# Batch4 H3 independent MCP consumer review

Task: review the distinct132397 gateway warmup→agent-consumer synthetic stdio fixture. Preserve previous proof and turnkey72f; no unchanged suite rerun. No product edits or upstream writes by reviewer.

Review pending candidate from hermes_tools. Gates: authored local stdio server only, temporary home/profile, no real credentials/provider/network request, transport interception installed before relevant initialization, production auth guards retained, genuine warmup and later agent consumer, causal negative control. Outcome must distinguish a passing supported path from reproduction/resolution of the original report.

## Pre-test source review

Candidate `/workspace/lanes/h4/tests/gateway/test_mcp_warmup_agent_consumer.py`, baseea81748579ee1732d214ccb75f91d22208ed623d. Inspected shared `tests/e2e/core/parity/fixture_mcp_server.py`: ordinary mode is an authored MCP SDK stdio echo server, PID log only. Requested explicit child env disabling its optional grandchild/death modes. Requested supported `local_runtime.enabled:false` (config_defaults.py2717, bootstrap.py405), alongside existing environment_probe:false and custom loopback placeholder route. No product guard is patched.

Guarded socket connect/connect_ex precede gateway import. Parent fixture asserts no IPv4/IPv6 connection attempts; stdio/Unix transport stays available. Temporary HERMES_HOME and Path.home isolate config; agent skip_memory/context/background_review prevents those feature paths. Warmup metadata resolution and fetch_model_metadata are fixture-local stubs outside the MCP lifecycle seam. Actual gateway discovery, `_warm_turn_machinery_sync`, schema materialization and `AIAgent` initialization remain real. No model request is made.

Declared consumer boundary is agent schema snapshot plus real registry dispatch, **not agent tool-executor or a full conversation**. Healthy row requires the same task/session, one child, before/after RPC echo. Teardown control removes actual transport then observes whether warmup/agent construction rediscover; no lifecycle stub is allowed to manufacture the expected outcome. If rediscovery is production behavior, revise the observation honestly rather than force absence.

Correction to an earlier review message: agent_init.py1378 concerns memory-provider migration, not model-provider installation; skip_memory suppresses that path. Latest21-file localruntime/PM main delta has no direct gateway/run.py/model_tools.py/agent_init.py change, but explicit localruntime disable still documents fixture intent. Pre-test review found no blocking issue after those explicit declarations.

## Final committed-source review

Reviewed commite265fe8633b97facf0807014340911f06e231f67 on freshbaseea81748579ee1732d214ccb75f91d22208ed623d. Test-only87-line addition; no product/auth/provisioning changes. Explicit localruntime disable and child optional-mode zeros are present. No blocking finding for the declared synthetic consumer contract.

Corrections during fixture construction are not product regressions:8192 context violated the real64000 minimum (now supported128000); default tool-search intentionally deferred the direct MCP schema (now supported `tools.tool_search.enabled:false`); placeholder loopback metadata detection caused4 blocked connection attempts (now isolated with static local-server detection, alongside existing metadata stubs). Network guards remain intact and the final healthy/teardown rows assert no connection attempts during the tested parent phase. Auth guards were never disabled.

Worker reports final canonical run2passed5.4s plus clean Ruff/diff; reviewer inspected committed source without duplicating execution. Healthy row: real gateway discovery→real synchronous warmup→real AIAgent direct schema snapshot, same MCP task/session, one child, successful before/after real registry RPC. Teardown row: initial successful RPC then real shutdown→warmup→agent lacks tool, original task absent, no child respawn. This gives a meaningful missing-transport control and does not fake lifecycle behavior.

Claim limits: one temporary non-multiplex profile, direct schema mode with tool_search disabled, authored stdio MCP SDK fixture. It does not exercise default deferred tool search, agent tool executor, model turn, gateway message ingress, full startup scheduling/timing, macOS launchd, profile transition, or third-party servers. No reproduction or fix of132397 established; only this proposed normal warmup handoff is qualified. Child source is explicitly stdio-only; parent socket monkeypatch is not a subprocess-wide network sandbox.

Final command: `HERMES_PYTHON=/workspace/.onboarding/hermes-tests/bin/python bash scripts/run_tests.sh -j2 tests/gateway/test_mcp_warmup_agent_consumer.py`. Worker receipt `/workspace/receipts/batch4-h1-mcp.md` records tool chunka9f7e0/session17931:2passed0failed5.4s (subprocess5.39s), no flaky retry. Final tested source committed without edits ase265fe86; no qualification-only repeat requested by reviewer.
