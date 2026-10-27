# Phase 0 — Upstream refresh (2026-09-19)

main SHA: `afaa53e5fe8c99d52bb0df512638a3223e30da99`
worktree: `/mnt/zer0models/workspaces/hermes-cu-perf` branch `fix/cu-perf-critical-path`

| PR | State | Head | Merge | Notes |
|---|---|---|---|---|
| #108914 Bot Screen | OPEN | 56cf995545db | MERGEABLE/BLOCKED | canonical CU substrate; #115633 MERGED into it |
| #114532 run_goal/Jev | OPEN | 925e9f79122e | CONFLICTING | rebase after #108914 |
| #113020 DecisionProvider | OPEN | 3285578ced41 | MERGEABLE/BLOCKED | semantic contract |
| #113389 capture projection | OPEN | 91822a8cd774 | UNKNOWN | do not preselect |
| #115485 MCP dead-stdio | OPEN | dd6858dd254e | UNKNOWN | CARRIER (opened first; ehz0ah no-block; KeyArgo verified) |
| #115513 MCP dead-stdio | OPEN | 2116f762e978 | UNKNOWN | duplicate of #115483 fix — do not maintain |
| #115657 MCP dead-stdio | OPEN | f97a007704ba | MERGEABLE/BLOCKED | third duplicate; adds mark_suspect+reconnect_event |
| #115591 session lock | OPEN | 42f293c31075 | UNKNOWN | Phase 3 |
| #115701 wake reconnect | OPEN | 6847f8aebbb5 | MERGEABLE/CLEAN | Phase 2 carrier (salvage #112834); whyyagswhy verified |
| #115276 vision gates | OPEN | 1950d96b6a20 | UNKNOWN | Phase 8 adjacent |
| #105566 bounds_scale | OPEN | 8af9ec382e2a | UNKNOWN/CLEAN reviews | Phase 6 |
| #115633 lease janitor | MERGED | 527e559dc700 | into #108914 | Phase 4 base |
| #115590 empty-response | OPEN | 0f61f45c614d | UNKNOWN | Phase 11 candidate only |
| #112834 wake (old) | OPEN | — | superseded by #115701 | |

Issue #115483 still OPEN — fix not on main.
