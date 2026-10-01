## What does this PR do?

Docs-only: three passages and one docstring describe GPT-6 / GPT-6.1 handling that no longer matches the code; no behaviour change.

- **Reasoning-mandatory note** (`website/docs/user-guide/configuration.md`). It described one recovery: a thinking-off auxiliary call goes out at `low` instead of the disable. `known_reasoning_floor` does that only when the route's catalog marks the model mandatory or the route already refused a disable earlier in the process. Separately, `OpenRouterProfile._clamp_reasoning_to_catalog` omits the reasoning field for an `openai/` model whose `codex_supported_efforts` ladder has no `none`. Today that means gpt-6.1-sol (`NO_DISABLE_TIER_PREFIXES`), whose OpenRouter catalog entry wrongly lists `none`, so the call runs at the model's default effort. The paragraph now describes both paths. The omit path came in with #128248.
- **Codex autoraise scope** (`website/docs/developer-guide/context-compression-and-caching.md`: the `codex_gpt55_autoraise` row and the "Codex gpt-5.x / Astra threshold autoraise" section; `agent/auxiliary_client.py`: the `_is_codex_gpt54_or_gpt55` docstring). The docs said the 272K cap and 85% autoraise apply to gpt-5.4/5.5/5.6 and gpt-6 Astra, and the docstring listed gpt-6 Sol/Terra/Luna. On `openai-codex`, `_is_codex_gpt54_or_gpt55` prefix-matches gpt-6-sol, gpt-6-luna and gpt-6.1-sol, substring-matches Astra, and matches no Terra slug. Both now list gpt-6 Sol/Luna/Astra and gpt-6.1 Sol; the docstring drops Terra. gpt-6 Sol/Luna have been missing from these lines since #119410; #119410 also put Terra in the docstring, and 38c289c014 later removed Terra from the predicate but not the docstring; #128248 added gpt-6.1-sol.
- **`max` on an `api.openai.com` custom entry** (`website/docs/integrations/providers.md`, "Reasoning effort on custom endpoints"). It said `max` is a gpt-5.6-only level there. That route takes its ladder from `codex_supported_efforts`, which returns `CODEX_GPT56_EFFORTS` (`none`..`max`) for gpt-5.6 and gpt-6 Sol/Luna (`GPT6_TIER_PREFIXES`) and `CODEX_ASTRA_EFFORTS` (`low`..`max`) for Astra and gpt-6.1 Sol. It now says `max` exists there only for gpt-5.6, gpt-6 Sol/Luna/Astra and gpt-6.1 Sol. Stale since #119410 gave gpt-6 Sol/Luna the gpt-5.6 ladder; Astra and gpt-6.1 Sol (#128248) also accept `max` via `CODEX_ASTRA_EFFORTS`. The unpublished GPT-6 Terra tier is left out on purpose.

zh-Hans has no copy of any of these passages.

## Related Issue

No issue tracks these drifts. Supersedes #127381 (closed), which listed the unpublished GPT-6 Terra tier and predates gpt-6.1 Sol.

Open #129056 and #129364 edit nearby lines of `context-compression-and-caching.md`, not the lines changed here.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `agent/auxiliary_client.py`: `_is_codex_gpt54_or_gpt55` docstring drops Terra and adds gpt-6.1 Sol.
- `website/docs/developer-guide/context-compression-and-caching.md`: the `codex_gpt55_autoraise` row and the autoraise section list gpt-6 Sol/Luna/Astra and gpt-6.1 Sol.
- `website/docs/integrations/providers.md`: `max` on an `api.openai.com` entry exists for gpt-5.6, gpt-6 Sol/Luna/Astra and gpt-6.1 Sol.
- `website/docs/user-guide/configuration.md`: the reasoning-mandatory note adds the OpenRouter omit path for `openai/` models whose ladder has no `none`.

## How to Test

1. Compare each changed passage with the code it describes: `known_reasoning_floor` (`agent/auxiliary_reasoning_floor.py`), `OpenRouterProfile._clamp_reasoning_to_catalog` (`plugins/model-providers/openrouter/__init__.py`), `_is_codex_gpt54_or_gpt55` (`agent/auxiliary_client.py`), and `codex_supported_efforts` with `CODEX_GPT56_EFFORTS`, `CODEX_ASTRA_EFFORTS`, `GPT6_TIER_PREFIXES` and `NO_DISABLE_TIER_PREFIXES` (`agent/reasoning_effort.py`).
2. Ran on this branch (base f848940560): `tests/hermes_cli/test_gpt6_tiers_registration.py tests/agent/test_auxiliary_reasoning_catalog_floor.py tests/agent/test_auxiliary_reasoning_floor.py tests/agent/test_codex_gpt55_autoraise_notice.py` -> 12 passed. Coverage per passage:
   - Reasoning-mandatory note: `test_gpt6_tiers_registration.py::test_openrouter_omits_disable_the_openai_ladder_rejects` and the two auxiliary floor test files.
   - Autoraise scope: `test_gpt6_tiers_registration.py::test_gpt6_tiers_share_the_codex_900k_contract_with_56` (gpt-6 Sol/Luna get gpt-5.6-sol's compression threshold on `openai-codex`). gpt-6.1-sol on `openai-codex` has no test; checked by reading `_is_codex_gpt54_or_gpt55` and a direct call (True for gpt-6-sol, gpt-6-luna, gpt-6.1-sol and gpt-6-astra on `openai-codex`; False for gpt-6-terra).
   - `max`: `::test_gpt6_tiers_share_the_codex_900k_contract_with_56` (gpt-6 Sol/Luna take `CODEX_GPT56_EFFORTS`) and `::test_gpt61_sol_takes_astra_ladder_without_astra_gating` (gpt-6.1 Sol takes `CODEX_ASTRA_EFFORTS`). A direct `codex_supported_efforts` call gives up to `max` for gpt-5.6-sol, gpt-6-sol, gpt-6-luna, gpt-6-astra and gpt-6.1-sol, and up to `xhigh` for gpt-5.4 and gpt-5.5.
   - `test_codex_gpt55_autoraise_notice.py` was part of the run but only exercises the gpt-5.5 notice.
3. Ran these docs-site-checks steps locally: `extract-skills.py`, `generate-skill-docs.py` with the committed-docs diff (clean), `check_doc_links.py` (OK).
4. Not run: `npm run lint:diagrams` and `npm run build:fast`. The changed lines add no diagrams, `{}` or raw tags outside code.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass — targeted files only (How to Test step 2); docs-only change
- [ ] I've added tests for my changes — N/A, documentation only
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A
