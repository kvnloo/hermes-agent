## What does this PR do?

Removes two stale memory-provider statements on `main` (tested at `f848940560`).

| # | Doc on main | What it says | What the code does |
|---|---|---|---|
| 1 | `website/docs/user-guide/features/memory-providers.md:724` and zh-Hans copy `:560` | Supermemory unique feature: "Context fencing + session graph ingest + multi-container" (zh: "上下文隔离 + 会话图谱导入 + 多容器") | The plugin writes each completed turn in `sync_turn` and `on_session_end` only retries failed writes ("Turns were already written as they completed; only retry what failed"), `plugins/memory/supermemory/__init__.py:443-482`. The session-end `/v4/conversations` ingest is gone; the provider section on the same page already says "per-turn conversation capture" (`:596`). bc1d4776db purged the other references but missed this row. |
| 2 | `website/docs/reference/environment-variables.md:201` and zh-Hans copy `:153` | `SUPERMEMORY_API_KEY`: "profile recall and session ingest" (zh: "会话摄取") | Same as row 1: per-turn capture. Module docstring: "profile recall, semantic search, memory tools, per-turn capture". |
| 3 | `website/docs/developer-guide/memory-provider-plugin.md:124` | `platform` examples: `cli`, `gui`, `acp`, `telegram` | No session reports `gui`. `_memory_provider_init_kwargs` forwards the agent's platform unchanged (`agent/agent_init.py:1273-1284`); the TUI gateway resolves `desktop` (Desktop chat panel) or `tui` (`tui_gateway/server.py:1518-1532`), ACP passes `"platform": "acp"` (`acp_adapter/session.py:525`). |

Docs only; no behaviour change.

## Related Issue

No upstream issue. Supersedes nothing upstream. Open PRs touching `memory-providers.md` (#115991, #120224, #127761, #108853) edit other sections.

## Type of Change

- [x] 📝 Documentation update

## Changes Made

- `memory-providers.md` (EN + zh-Hans): drop "session graph ingest" from the Supermemory comparison row. The column is "Unique Feature" and per-turn capture is common to providers, so nothing replaces it.
- `environment-variables.md` (EN + zh-Hans): "session ingest" → "per-turn conversation capture" (zh: "逐轮对话捕获").
- `memory-provider-plugin.md`: platform examples `cli`, `tui`, `desktop`, `acp`, `telegram`. (The zh-Hans copy has no such table row.)

## How to Test

1. `git grep -n -i "session ingest\|session graph\|会话摄取\|会话图谱" -- website/` returns nothing after this change (four hits on `main`).
2. `python3 website/scripts/check_doc_links.py` → `OK: no route-style links in hand-authored docs.`

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Docs only; not run.
- [ ] I've added tests for my changes. N/A, docs only.
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
