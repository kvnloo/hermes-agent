# CU Perf Critical Path — Status Report

Date: 2026-09-19

## Exact upstream / base SHA

- `origin/main`: `afaa53e5fe8c99d52bb0df512638a3223e30da99`
- #108914 head at phase-4 start: `56cf995545dbb`

## Worktrees / branches

| Branch | Base | Path |
|---|---|---|
| `fix/cu-perf-critical-path` | main | `/mnt/zer0models/workspaces/hermes-cu-perf` |
| `fix/cu-run-goal-on-108914` | #108914 + phase4 | `/mnt/zer0models/workspaces/hermes-cu-botscreen` |

## Commits created

### On `fix/cu-perf-critical-path` (main-line control plane)

1. `d5b0a423aa418` — Phase1 MCP dead-stdio reconnect (carrier #115485)
2. `c1555c3e74f4d`…`8d156f54bebe2` — cherry-pick #115701 wake salvage
3. `990f87498ca10` — Phase2 trailing-edge wake holdoff
4. `c5a4fec0f0c45` — cherry-pick #115591 session lock / Windows zombie skip
5. `4e0a74c25ac55` — Phase3 fingerprint-validated prune write-back

### On `fix/cu-run-goal-on-108914` (Bot Screen substrate)

1. `f4c56a98553bb` — Phase4 janitor lease revalidation at effect boundary
2. `362e9fb6aa825` — Phase5 run_goal on #108914 with per-leaf canonical executor

## Tests added / results

| Phase | Focused | Adjacent | Result |
|---|---|---|---|
| 1 | `test_mcp_stdio_dead_reconnect_115483` (3) | MCP lifecycle suite (50) | green |
| 2 | `gateway-wake-reconnect-holdoff` (6) | gateway suites (94 total) | green |
| 3 | prune adversarial + metrics (5) + windows zombie (4) | active_sessions (20) | green |
| 4 | janitor check-to-effect race (2) | bot_desktop/cleanup/orphan (52) | green |
| 5 | run_goal lease fencing (3) + decide_loop (12) | decision_lane + bot_desktop (44) | green |

## Hyprland isolated-TDD / non-interference

| Metric | Count |
|---|---|
| seat0 mutations caused by agent | **0** |
| physical cursor movements caused by agent | **0** |
| global focus changes caused by agent | **0** |
| human workspace changes caused by agent | **0** |

Notes:
- Phases 1–5 product races proven with deterministic unit/contract tests (no seat0 path).
- `hypr-agent-input` plugin **not installed** on this host (only `hyprglass`); GUI E2E deferred to `gui-e2e-display.sh` / hyprland-ui-testing skill when a headed fixture is required.
- Phase 4 suite left active workspace `2` and cursor untouched.
- `AGENT_BROWSER_IDLE_TIMEOUT_MS`: left at 24h shared-headed deferral; orphan reaper remains wedged-daemon backstop — **not** set to 0 without failure proof.

## Carriers / duplicates

- MCP: **#115485** (not #115513 / #115657)
- Wake: **#115701** (salvages #112834) + trailing-edge fix
- Session lock: **#115591** + fingerprint strengthen
- Bot Screen: **#108914** (+ integrated #115633)
- run_goal: **#114532** rebased onto #108914 with retained-backend model deleted

## Duplicate primitives deleted / avoided

- Did not keep second MCP reconnect system
- Did not keep drop-only wake holdoff
- Did not keep run_goal retained-backend `execute_authorized_action` as authority
- Did not invent browser-specific security model — reused lease epoch

## DecisionProvider compatibility

- #113020 still open (semantic contract)
- Phase5 decision lane stores action/target/done/needs_vision fields in decide payload
- Shadow-only evaluation (Phase7) **not started**

## Benchmark / wall-clock trace

- Phase9 tracer landed: `tools/computer_use/cu_trace.py` (monotonic, in-memory, contextvar)
- Fake-backend matrix: `.cu-perf-report/phase9/`
- Live Hyprland headed trajectories **BLOCKED**: fixture map steals focus (`noinitialfocus` invalid; no `hypr-agent-input`)
- Live non-GUI attribution: `.cu-perf-report/phase9/live/` — MCP reconnect OK (no busy spin); active main `xai-oauth`/`grok-4.6` → aux_vision (transport_not_attested)

## Remaining known confounders

- Two branches need upstream PR strategy (main-line vs #108914-based)
- Live cua-driver MCP child kill/reconnect exercised (no busy-spin); headed CUA smoke still blocked by focus-on-map
- Windows native wake qualification not run on this Linux host
- hypr-agent-input absent → headed GUI TDD blocked until plugin/skill path available

## NEW critical path (after phases 0–5)

Measured ordering still favors control-plane until Phase9 trace exists. Next vertical slice:

1. **Phase6** — verify/land #105566 coordinate provenance; Hyprland grounding TDD when input plugin available
2. **Phase8** — two-axis media capability (native image routing) — observed ~4–5.4s auxiliary vision cost
3. **Phase9** — wall-clock CU trace (registry/MCP/wake/vision/model tags)
4. **Phase7** — DecisionProvider shadow (no effect boundary)
5. **Phase10–11** — benchmark → let trace pick next patch

## Single smallest next vertical slice

**Phase 10:** controlled tool-result media transport probe for live main `xai-oauth`/`grok-4.6`.
Model-scoped attestation only if positively accepted; else keep fail-closed and measure successful aux-vision RTT under a credentialed profile. No click/readiness/browser patches yet.

## Phase 6 complete
- Commit `fix/cu-run-goal-on-108914`: applied #105566 — no bounds_scale inference
- Tests: TestBoundsScaleRemoved 3/3 green


## Phase 8 sealed (falsification pass)
- Two-axis `resolve_native_tool_result_pixels` with provenance:
  - `model_vision_source` (catalog|config|…)
  - `transport_source` (provider_whitelist|explicit_attestation:…|…)
- Transport attestation narrowed: **not** provider-wide `deepseek` —
  only `("deepseek", "deepseek-flash")` in `_TOOL_RESULT_MEDIA_MODEL_ATTESTATIONS`
- `deepseek-chat` fails closed (no transport attestation)
- Did NOT land #115276 catalog-as-transport conflation
- Tests: vision-related suites green (49+)

## Phase 9 live attribution attempted
- See `.cu-perf-report/phase9/live/SUMMARY.md` + `LIVE_ATTRIBUTION.json`
- Headed GUI: blocked (focus steal on map) — restored immediately; seat0 product paths not exercised
- Non-GUI live: MCP `cua-driver mcp` kill → reconnect, 0 busy-spin; route provenance for active main
- Phase 10 chosen from evidence: grok-4.6 transport probe (model-scoped, fail-closed)
