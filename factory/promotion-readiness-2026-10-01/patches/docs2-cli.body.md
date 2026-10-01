## What does this PR do?

Docs-only. Each statement below is wrong on current `main`; every correction cites the source that contradicts it. No behaviour changes.

### docs(cli): drop stale partner list from portal tools row

- **Was:** website/docs/reference/cli-commands.md:437 — "List every Tool Gateway partner (Firecrawl, FAL, OpenAI TTS, Browser Use, Modal) and which are routed via Nous."; zh-Hans cli-commands.md:299 same list.
- **Source on main:** hermes_cli/portal_cli.py:14-20 _CATALOG: ("web", "Web search & extract", "Nous-managed"), FAL, OpenAI TTS, Browser Use, Modal.
- **Check:** Probe on main: _CATALOG partners = Nous-managed, FAL, OpenAI TTS, Browser Use, Modal (no Firecrawl).
- **Now:** Partner enumeration removed in en + zh-Hans (row now: 'List every Tool Gateway partner and which are routed via Nous.').
- **Mirrors:** zh-Hans cli-commands.md:299 fixed in the same commit.
- Drift introduced by 749220ef00 (#120320).

### docs: correct stale hermes logs filter & timezone notes (en + zh-Hans)

- **Was:** website/docs/reference/cli-commands.md:1282 — "Lines without a parseable timestamp are included when `--since` is active ... Lines without a detectable level are included when `--level` is active." (contradicts :1246 of the same page); zh cli-commands.md:753 same; zh configuration.md:1576 — "影响日志中的时间戳、cron 调度和系统提示词时间注入。"
- **Source on main:** hermes_cli/logs.py:124-138 _LineFilter: an unstamped line returns the carried verdict of the record above; before the first stamp it is dropped when --since/--level is active. hermes_logging.py has no timezone converter (log stamps are machine-local; English configuration.md:2789 already says so).
- **Check:** Probe on main: _LineFilter(min_level='WARNING') over [INFO record, traceback lines, WARNING record, continuation] keeps only the WARNING record and its continuation — traceback under the INFO record is dropped, contrary to the stale paragraph.
- **Now:** Stale paragraph removed (en + zh), current note translated into zh-Hans, zh timezone intro aligned with English. tests/hermes_cli/test_logs.py passes on main.
- **Mirrors:** zh-Hans cli-commands.md and configuration.md fixed in the same commit.
- Drift introduced by fc4dbe32df (#126176).

### docs(cli): correct fallback_providers redaction scope in dump config overrides

- **Was:** website/docs/reference/cli-commands.md:1017 — "Credentials in them are redacted: a `fallback_providers` entry's `api_key`, and credentials in its `base_url` ..."; zh cli-commands.md:522 same.
- **Source on main:** hermes_cli/dump.py:181-188 + :191-200 _mask_fallback_keys(): masks any key where agent.redact.is_secret_field_name(k) ('api_key', 'token', 'password', ...).
- **Check:** Probe on main: _config_overrides({'fallback_providers':[{api_key, token, password}]}) -> all three '***'.
- **Now:** Row (en + zh) says every secret-named field is redacted.
- **Mirrors:** zh-Hans cli-commands.md:522 fixed in the same commit.
- Drift introduced by 536802c00e (#127207).

## Related Issue

Supersedes our own parked docs PRs #127363 (closed to keep the review queue short); no open issue tracks these drifts.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `website/docs/reference/cli-commands.md`
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/reference/cli-commands.md`
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/configuration.md`

## How to Test

1. For each item above, read the cited source lines on `main`; the old text contradicts them, the new text matches.
2. Behaviour the docs describe, run on this branch: tests/hermes_cli/test_logs.py tests/hermes_cli/test_anon_surfaces.py -> 22 passed.
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

Verified on `main` f848940560; merges cleanly onto eb8d21f482. Branch `ready/docs2-cli` @ b68897f77bc5, 3 files changed, 7 insertions(+), 9 deletions(-).
