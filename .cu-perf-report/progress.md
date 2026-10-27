# CU Perf Critical Path — Progress

## Base
- main: `afaa53e5fe8c99d52bb0df512638a3223e30da99`
- worktree A (phases 1–3): `/mnt/zer0models/workspaces/hermes-cu-perf` @ `fix/cu-perf-critical-path`
- worktree B (phase 4): `/mnt/zer0models/workspaces/hermes-cu-botscreen` @ `fix/cu-botscreen-cleanup-epoch` (from #108914 `56cf995545db`)

## Commits

### fix/cu-perf-critical-path (onto main)
1. `d5b0a423aa418` Phase1 MCP dead-stdio reconnect (#115485 / #115483)
2. `c1555c3e74f4d`…`8d156f54bebe2` cherry-pick #115701 wake salvage
3. `990f87498ca10` Phase2 trailing-edge wake holdoff
4. `c5a4fec0f0c45` cherry-pick #115591 session lock
5. `4e0a74c25ac55` Phase3 fingerprint-validated prune write-back

### fix/cu-botscreen-cleanup-epoch (onto #108914)
1. `f4c56a98553bb` Phase4 janitor lease revalidation at effect boundary

## Tests
- Phase1: 3/3 dead-stdio + 50 adjacent MCP lifecycle
- Phase2: 94 desktop vitest (holdoff+liveness+gateway suites)
- Phase3: 9 prune/windows + 20 active_sessions
- Phase4: 52 bot_desktop/browser_cleanup/orphan_reaper

## Hyprland / seat0
- Phase1–3: no GUI automation
- Phase4: unit race only; hyprctl suite left workspace 2 / cursor untouched (agent-caused mutations = 0)
- hypr-agent-input plugin: NOT installed on this host (only hyprglass); GUI E2E deferred to gui-e2e-display.sh / skill when GUI required
- AGENT_BROWSER_IDLE_TIMEOUT_MS: left at 24h shared-headed deferral; orphan reaper is the wedged-daemon backstop — do not set to 0 without failure proof

## Carriers selected
- #115485 over #115513/#115657 (opened first; reviewed)
- #115701 over #112834 (salvage)
- #115591 + fingerprint strengthen
- #108914 for Bot Screen

## Next
- Phase5: rebase #114532 run_goal onto current #108914 (merge may conflict)
- Phase6+: after substrate+run_goal green
