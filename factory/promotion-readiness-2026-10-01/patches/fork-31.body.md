## What does this PR do?

`GET /api/skills/hub/search` (`hermes_cli/web_routers/skills.py`, the dashboard's Browse-hub search) merges every configured source through `parallel_search_sources`, which appends results in `as_completed` order. It then dedupes by identifier and slices `[:limit]`, but never sorts by trust first. As a result, a fast, high-volume community source fills the page, and builtin/trusted hits that finish later (`official/*`, trusted taps) are cut off.

The CLI path doesn't have this problem. `tools.skills_hub_search.unified_search` stable-sorts by trust before truncating, guarded by `test_unified_search_trust_rank_survives_limit_cut`, and `browse_skills` / `_rank_and_page` sort official-first too. The dashboard endpoint, whose dedupe comment says it "mirrors unified_search", is the only hub listing that cuts in completion order.

This PR stable-sorts the deduped results by the trust rank the endpoint already defines, before the cut. Order within a rank is unchanged.

The defect and the original fix were first produced by Detail's automated bug finder (detail-app[bot]), credited with a `Co-authored-by` trailer on the commit. This PR rebuilds that fix on current `main`, where the router now goes through `tools.skills_hub_search`.

## Related Issue

No upstream issue. Searched open/closed PRs and issues for `search_skills_hub`, `skills/hub/search`, and trust-rank/limit wording. #116108 (open, opt-in relevance rerank) touches only `unified_search`, not this endpoint, and doesn't overlap.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `hermes_cli/web_routers/skills.py`: in `search_skills_hub._run`, sort the deduped values by `-_rank[trust_level]` before `[:capped]`.
- `tests/hermes_cli/test_dashboard_admin_endpoints.py`: `TestSkillsHubSearchEndpoint.test_trust_rank_survives_limit_cut`. Through the real mounted router (`TestClient`), with `parallel_search_sources` patched, 20 community hits arrive before one builtin hit and `limit=10`. The builtin must come first, followed by the community hits in their original order.

## How to Test

1. Check out `ready/fork-31-hub-search-trust-sort-v2` (one commit on `main` @ 330d9d6d) and run `scripts/run_tests.sh tests/hermes_cli/test_dashboard_admin_endpoints.py -q`.
2. Apply only the test hunk to `main` and rerun step 1. The new test fails with `At index 0 diff: 'skills-sh/x/s0' != 'official/cat/s-official'` (42 passed, 1 failed).
3. With the fix: 43 passed, 0 failed. Adjacent: `tests/hermes_cli/test_web_server_skills_profiles.py tests/hermes_cli/test_web_server_skill_editor.py tests/tools/test_skill_bundle_provenance.py tests/tools/test_skills_hub_browse_sh.py` give 38 passed, 0 failed (`test_skill_bundle_provenance.py` holds the CLI-side `test_unified_search_trust_rank_survives_limit_cut`). `ruff check` is clean on both touched files.
4. Negative control: inverting the sort key (ascending trust) makes the new test fail again with the same index-0 diff.
5. Not tested: the full suite, and a live dashboard `/api/skills/hub/search` against real hub sources. The test stubs `parallel_search_sources`.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Only the targeted files above were run, not the full suite.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), targeted test files only

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
