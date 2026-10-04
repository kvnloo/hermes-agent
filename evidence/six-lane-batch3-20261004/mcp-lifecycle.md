# Batch 3 H3 — MCP startup/turn transition audit

Current upstream inspected: `20bd00439cfc2e8d6d296f28fba0cdeeb6cdda49`.
Prior published consumer proof `97e24e3e0162b6501b4c85d9d31a328d6c1366d6` preserved unchanged. No tests rerun, no new test or source change, no installation or upstream write.

## Distinct call paths checked

All files below are byte-identical between prior base `24b9f0f8` and current `20bd004` (verified with Git diff). The prior repeated-discovery consumer remains bounded evidence; this audit does not silently extend it to full startup.

1. CLI `_command_has_dedicated_mcp_startup` excludes `gateway run` from inline CLI MCP startup. This predates the report and is also present at its `db45b44` revision.
2. `GatewayRunner.__init__` (`gateway/run.py:3490-3501`) sets multiplex mode before startup discovery. `start_gateway` invokes `_discover_gateway_mcp_tools(runner.config)` (`:5970`) before `runner.start()` (`:5975`). The discovery wrapper (`:1908`) binds each served profile and copies context into its executor.
3. `GatewayRunner.start` later schedules `_start_startup_warmup` (`gateway/run_startup.py:1607`). `_warm_turn_prerequisites` (`:161`) uses `_run_boot_probe_in_launch_scope` (`:136`) and `_warm_turn_machinery_sync` (`gateway/run.py:964`). That function imports the agent/model modules and obtains tool definitions, then runs environment/model-context metadata probes. Those unrelated probes are why a full warmup test cannot honestly be represented by the prior two discovery calls.
4. `model_tools.py:151-164` explicitly DOES NOT perform MCP discovery at import; it discovers ordinary plugins. `agent/turn_context.py:544` invokes `refresh_agent_mcp_tools` between turns only after MCP is already present. `tools/mcp_tool_agent.py:96-138` rebuilds the agent tool snapshot using `get_tool_definitions` and the live registry; it does not construct a transport.
5. First-turn profile binding (`gateway/run_turn.py:2274`) uses the same `_profile_runtime_scope` as gateway boot discovery. The MCP connection key (`tools/mcp_tool.py:651`, `tools/mcp_tool_scope.py`) is profile-scoped when the process serves routed profiles, otherwise bare name. A new scope/process identity can legitimately produce another connection; the public report does not identify those identities for its two log waves.
6. Explicit reload (`gateway/run_turn.py:2580-2611`) really shuts down then rediscovers. Profile reconciliation (`gateway/run_profile_reconcile.py:336` → `tools/mcp_tool_discovery.py:634`) may remove or add servers when configuration/scope membership changes. Those are meaningful replacement paths, but the report supplies no reload/config/scope event between its waves.

## What this establishes

The normal startup→turn schema preparation graph does not contain the hypothesized unconditional second MCP connection pass. Replacing it with a broad mocked warmup test would not supply the missing causal transition. Therefore no new test volume or runtime fix was added.

This is NOT a general cannot-reproduce verdict. The public #132397 report still has no comments as of this inspection (updated_at remains 2026-10-03T19:18:19Z). Its macOS/launchd process, nine external servers, and malformed handshake observation have not been replicated here. No external MCP connection or malformed-payload experiment was performed.

## Exact evidence needed next

A synthetic case or redacted reporter trace must establish:

- Whether both log waves come from the same OS process and gateway incarnation.
- The owning profile/registry scope and server name for each wave.
- A concrete transition: explicit reload, profile reconcile/config edit, child exit/reconnect, process restart, or a reproducible SDK handshake failure.
- The temporary/home-scoped `logs/mcp-stderr.log` for the affected child, and exact lifecycle state changes, rather than absence of text in `gateway.error.log`.

Only then select the matching production path and build its local positive/negative control. Existing owners of stderr surfacing, pre-handshake crash parking, and retry changes remain respected. Root has been offered independent review of another lane's concrete candidate instead of redundant MCP testing.
