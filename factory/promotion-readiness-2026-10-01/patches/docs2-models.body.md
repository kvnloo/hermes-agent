## What does this PR do?

Docs-only. Each statement below is wrong on current `main`; every correction cites the source that contradicts it. No behaviour changes (one docstring is touched).

### docs: cover gpt-6.1-sol omit-disable recovery in reasoning-mandatory note

- **Was:** website/docs/user-guide/configuration.md:1492 — "a thinking-off auxiliary call ... goes out at the lowest effort (`low`) instead of the disable. Hermes knows ahead of time when the route's model catalog marks the model mandatory ... or when the route already answered an earlier disable that way"
- **Source on main:** agent/auxiliary_reasoning_floor.py:109-125 known_reasoning_floor() lifts to low only for floored routes / catalog-mandatory; plugins/model-providers/openrouter/__init__.py:93-95 returns None (omit) when openai/ and 'none' not in codex_supported_efforts(model); agent/reasoning_effort.py:42 NO_DISABLE_TIER_PREFIXES = ('gpt-6.1-sol',).
- **Check:** Doc describes only the lift-to-low recovery.
- **Now:** Paragraph distinguishes the two recoveries. tests/hermes_cli/test_gpt6_tiers_registration.py::test_openrouter_omits_disable_the_openai_ladder_rejects and the aux floor tests pass on main.
- **Mirrors:** No zh-Hans copy of this paragraph.
- Drift introduced by bf87ae620e (#128248).

### docs: cover gpt-6 Sol/Luna & gpt-6.1 Sol in Codex autoraise scope

- **Was:** website/docs/developer-guide/context-compression-and-caching.md:273 and :354 — "gpt-5.4/5.5/5.6 and gpt-6 Astra"; agent/auxiliary_client.py:606 docstring — "gpt-6 Sol/Terra/Luna"
- **Source on main:** agent/auxiliary_client.py:605-623 _is_codex_gpt54_or_gpt55(): families gpt-5.4, gpt-5.5, gpt-5.6, gpt-6-sol, gpt-6.1-sol, gpt-6-luna + any 'astra' (no terra); agent/reasoning_effort.py:39 GPT6_TIER_PREFIXES = ('gpt-6-sol', 'gpt-6-luna').
- **Check:** Probe on main: _is_codex_gpt54_or_gpt55(m, 'openai-codex') True for gpt-6-sol / gpt-6-luna / gpt-6.1-sol / gpt-6-astra, False for gpt-6-terra; docs name Astra only.
- **Now:** Row and section enumerate gpt-6 Sol/Luna/Astra and gpt-6.1 Sol; docstring drops Terra. tests/agent/test_codex_gpt55_autoraise_notice.py passes on main.
- **Mirrors:** No zh-Hans copy of these lines.
- Drift introduced by 8ad4dc8d67 (#128248).

### docs(providers): `max` on an api.openai.com custom entry is not gpt-5.6-only

- **Was:** website/docs/integrations/providers.md:1396 — "a custom entry pointed at `api.openai.com` keeps OpenAI's per-model ladder (`max` is a gpt-5.6-only level there)"
- **Source on main:** agent/transports/codex.py:394 returns codex_supported_efforts(model) for that route; agent/reasoning_effort.py:32 CODEX_GPT56_EFFORTS (none..max) covers gpt-5.6 and GPT6_TIER_PREFIXES gpt-6-sol/gpt-6-luna (:39), :36 CODEX_ASTRA_EFFORTS (low..max) covers gpt-6-astra and gpt-6.1-sol (NO_DISABLE_TIER_PREFIXES, :42).
- **Check:** codex_supported_efforts on main: gpt-5.4/gpt-5.5 -> ...xhigh; gpt-5.6-sol, gpt-6-sol, gpt-6-luna -> ...max; gpt-6-astra, gpt-6.1-sol -> low..max.
- **Now:** "(`max` exists there only for gpt-5.6, gpt-6 Sol/Luna/Astra and gpt-6.1 Sol)".
- **Mirrors:** zh-Hans providers.md has no such paragraph.
- Residual of an earlier GPT-6 docs pass; the obsolete GPT-6 Terra tier is deliberately not carried.

## Related Issue

Supersedes our own parked docs PRs #127381 (closed to keep the review queue short); no open issue tracks these drifts.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `agent/auxiliary_client.py`
- `website/docs/developer-guide/context-compression-and-caching.md`
- `website/docs/integrations/providers.md`
- `website/docs/user-guide/configuration.md`

## How to Test

1. For each item above, read the cited source lines on `main`; the old text contradicts them, the new text matches.
2. Behaviour the docs describe, run on this branch: tests/hermes_cli/test_gpt6_tiers_registration.py tests/agent/test_auxiliary_reasoning_catalog_floor.py tests/agent/test_auxiliary_reasoning_floor.py tests/agent/test_codex_gpt55_autoraise_notice.py -> 12 passed.
3. Docs CI equivalent: `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py && git diff --exit-code -- website/docs website/sidebars.ts website/i18n` (clean) and `python3 website/scripts/check_doc_links.py` (OK).
4. Not run here: the Docusaurus build (`npm run build:fast`); added lines contain no MDX-sensitive `{}`/raw tags outside code.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass — targeted files only (listed above); docs-only change
- [ ] I've added tests for my changes — N/A, documentation only
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Verified on `main` f848940560; merges cleanly onto eb8d21f482. Branch `ready/docs2-models` @ 69a146992b3f, 4 files changed, 5 insertions(+), 5 deletions(-).
