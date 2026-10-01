## What does this PR do?

Docs-only. Each statement below is wrong on current `main`; every correction cites the source that contradicts it. No behaviour changes.

### `hermes portal tools` partner list

- **Was:** website/docs/reference/cli-commands.md:437 — "List every Tool Gateway partner (Firecrawl, FAL, OpenAI TTS, Browser Use, Modal) and which are routed via Nous."; zh-Hans cli-commands.md:299 same list.
- **Source on main:** hermes_cli/portal_cli.py:14-20 _CATALOG: ("web", "Web search & extract", "Nous-managed"), FAL, OpenAI TTS, Browser Use, Modal.
- **Checked on main:** _CATALOG partners = Nous-managed, FAL, OpenAI TTS, Browser Use, Modal (no Firecrawl).
- **Now:** Partner enumeration removed in en + zh-Hans (row now: 'List every Tool Gateway partner and which are routed via Nous.').
- **Why drop instead of correct:** The list is dropped rather than corrected because the catalog's partner names follow vendor routing (749220ef00 replaced Firecrawl with "Nous-managed"). The command's own output is the source of truth.
- Drift introduced by 749220ef00 (#120320).

### `hermes logs` unstamped-line note and zh-Hans timezone

- **Was:** website/docs/reference/cli-commands.md:1282 — "Lines without a parseable timestamp are included when `--since` is active ... Lines without a detectable level are included when `--level` is active." (contradicts :1246 of the same page); zh cli-commands.md:753 same; zh configuration.md:1576 — "影响日志中的时间戳、cron 调度和系统提示词时间注入。"
- **Source on main:** hermes_cli/logs.py:124-139 _LineFilter: an unstamped line returns the carried verdict of the record above; before the first stamp it is dropped when --since/--level is active. hermes_logging.py has no timezone converter (log stamps are machine-local; English configuration.md:2789 already says so).
- **Checked on main:** _LineFilter(min_level='WARNING') over [INFO record, traceback lines, WARNING record, continuation] keeps only the WARNING record and its continuation — traceback under the INFO record is dropped, contrary to the stale paragraph.
- **Now:** Stale paragraph removed (en + zh), current note translated into zh-Hans, zh timezone intro aligned with English.
- Drift introduced by fc4dbe32df (#126176).

### `hermes dump` fallback redaction scope

- **Was:** website/docs/reference/cli-commands.md:1017 — "Credentials in them are redacted: a `fallback_providers` entry's `api_key`, and credentials in its `base_url` ..."; zh cli-commands.md:522 same.
- **Source on main:** hermes_cli/dump.py:181-188 + :191-201 _mask_fallback_keys(): masks any key where agent.redact.is_secret_field_name(k) ('api_key', 'token', 'password', ...).
- **Checked on main:** _config_overrides({'fallback_providers':[{api_key, token, password}]}) -> all three '***'.
- **Now:** Row (en + zh) says every secret-named field is redacted.
- Drift introduced by 536802c00e (#127207).

## Related Issue

Supersedes #127363 (closed unmerged), which covered only the `hermes logs`/timezone part. No open issue tracks these drifts.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `website/docs/reference/cli-commands.md`: `portal tools` row drops the partner list; `dump` "Config overrides" row says every secret-named `fallback_providers` field is redacted; removes the stale `hermes logs` paragraph about unstamped and level-less lines.
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/reference/cli-commands.md`: the same three changes, plus the missing translation of the unstamped-line note under the `hermes logs` options table.
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/configuration.md`: the Timezone intro no longer claims `timezone` changes log timestamps, matching the English page.

## How to Test

1. For each item above, read the cited source lines on `main`; the old text contradicts them, the new text matches. To reproduce the checks from a checkout of `main`:

   ```bash
   python3 -c "from hermes_cli.portal_cli import _CATALOG; print([p for *_, p in _CATALOG])"
   # expect: ['Nous-managed', 'FAL', 'OpenAI TTS', 'Browser Use', 'Modal']

   python3 -c "from hermes_cli.logs import _LineFilter as F; f=F(min_level='WARNING'); L=['2026-09-30 10:00:00,000 INFO a: x','Traceback (most recent call last):','  File \"x.py\", line 1','2026-09-30 10:00:01,000 WARNING a: y','  more']; print([l for l in L if f(l)])"
   # expect only the WARNING line and '  more'

   python3 -c "from hermes_cli.dump import _config_overrides as c; print(c({'fallback_providers':[{'api_key':'k','token':'t','password':'p'}]})['fallback_providers'])"
   # expect all three values '***'
   ```

2. Docs-only, so no tests added. The `hermes logs` behaviour is covered by tests/hermes_cli/test_logs.py (16 passed on this branch). The dump redaction behaviour is covered by tests/hermes_cli/test_debug.py (not run). `portal tools` has no catalog test.
3. Docs CI equivalent: `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py && git diff --exit-code -- website/docs website/sidebars.ts website/i18n` (clean) and `python3 website/scripts/check_doc_links.py` (OK).
4. Not run here: the Docusaurus build (`npm run build:fast`); added lines contain no MDX-sensitive `{}`/raw tags outside code.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass — only tests/hermes_cli/test_logs.py was run; docs-only change
- [ ] I've added tests for my changes — N/A, documentation only
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Cited line numbers checked on main aeff051a18; merges cleanly onto it. 3 files changed, 7 insertions(+), 9 deletions(-).
