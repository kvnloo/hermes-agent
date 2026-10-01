## What does this PR do?

Fixes three stale pointers in the area `AGENTS.md` files that agents load as working context.

| # | Doc on main | What it says | What the code does |
|---|---|---|---|
| 1 | `cron/AGENTS.md:114-115` | "`kanban_db.connect` is its own connection helper" | The helper is `hermes_cli/kanban_db_connect.py:668` `connect`. `hermes_cli.kanban_db` does not re-export it: its tail import (`kanban_db.py:4490-4494`) pulls `_INITIALIZED_PATHS, init_db, write_txn` only, and `hasattr(hermes_cli.kanban_db, "connect")` is `False`. |
| 2 | `cron/AGENTS.md:125-127` | worker liveness uses "the start-time fingerprint (`gateway.status.get_process_start_time`) recorded at claim time" | `worker_started_at` is `kanban_db_dispatch._process_fingerprint` (`hermes_cli/kanban_db_dispatch.py:367-378`), the restart-stable `"<instantiation epoch>|<start time>"`, written at spawn by `_set_worker_pid` (`:1468-1482`). The raw start time alone is exactly what that docstring says is unsafe across reboots. |
| 3 | `tools/AGENTS.md:69-74` | "Keys today: `browser, clarify, ..., messaging, moa, rl, ...`" and per-platform selection via "`tools.<platform>.enabled/disabled`" | `toolsets.TOOLSETS` on main has no `messaging`, `moa` or `rl`, and has keys the list omits: `coding`, `setup`, `computer_use`, `connections`, `project`, `video_gen`, `x_search`, `bot_room`, `context_engine`, `desktop_ui` and the `hermes-<platform>` bundles (printed from `sorted(toolsets.TOOLSETS)`). Per-platform selection is `platform_toolsets.<platform>` (`hermes_cli/tools_config.py:592`, `:724-735`); there is no `tools.<platform>.enabled/disabled`. The paragraph now describes the families and points at `toolsets.TOOLSETS` rather than copying a list that will rot again. |

Line references are against main at `f848940560`; the cited files are unchanged on main at `aeff051a18`.

Docs only; no behaviour change. Out of scope: code comments in `hermes_state_wal.py` (`:33`, `:185`, `:515`) still say `kanban_db.connect()`. Left for a follow-up to keep this AGENTS.md-only.

These drifts were first flagged by Detail's doc-drift check (kvnloo/hermes-agent#88, kvnloo/hermes-agent#90, kvnloo/hermes-agent#119). This consolidates them and also corrects the write site (at spawn by `_set_worker_pid`, not at claim time) and the per-platform config key, which those drafts kept.

## Related Issue

No upstream issue. Supersedes my closed #127379 (the toolsets paragraph, row 3). This version also replaces the wrong `tools.<platform>.enabled/disabled` key with `platform_toolsets.<platform>` and adds the two `cron/AGENTS.md` corrections. Open #109744 and #111838 edit the delegation section of `tools/AGENTS.md`, not the toolsets paragraph.

## Type of Change

- [x] 📝 Documentation update

## Changes Made

- `cron/AGENTS.md`: `kanban_db_connect.connect`; fingerprint source, format and write site.
- `tools/AGENTS.md`: toolset families instead of the rotted key list; `platform_toolsets.<platform>`.

## How to Test

1. `python -c "import hermes_cli.kanban_db as kb; print(hasattr(kb, 'connect'))"` → `False`; `python -c "import toolsets; print(sorted(toolsets.TOOLSETS))"` shows the current keys.
2. Read the cited `kanban_db_dispatch.py` and `tools_config.py` lines.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Docs only; not run.
- [ ] I've added tests for my changes. N/A, docs only.
- [x] I've tested on my platform: Linux (CachyOS). Ran only the How to Test one-liners; docs only, no other testing.

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
