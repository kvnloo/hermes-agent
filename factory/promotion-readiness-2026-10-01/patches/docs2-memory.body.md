## What does this PR do?

Docs-only. Each statement below is wrong on current `main`; every correction cites the source that contradicts it. No behaviour changes.

### docs(memory): drop stale hindsight-all lazy-install claim

- **Was:** website/docs/user-guide/features/memory-providers.md:468 — "In local embedded mode the plugin installs `hindsight-all` on first use through Hermes' lazy-install path, which honours `security.allow_lazy_installs`."; zh-Hans memory-providers.md:350 — "本地用 `hindsight-all` ... 需要 `hindsight-client >= 0.4.22`（会话启动时若版本过旧则自动升级）"
- **Source on main:** plugin-catalog/hindsight.yaml:3 sha eb021da3 (bumped by 5e4857bf2e: 'drops the retired tools.lazy_deps call and the hindsight-all dependency ... local_embedded runs on PM-managed Hermes', known_issues removed). Plugin at that SHA (read-only gh api): pyproject dependencies hindsight-client>=0.10.1,<1 and hindsight-embed>=0.10.1,<1; embedded.py _check_local_runtime() imports only hindsight_client + hindsight_embed.daemon_embed_manager and documents that the server runs out of process. tools/lazy_deps.py on main is an old-updater stub.
- **Check:** Doc names a dependency and install path the pinned plugin no longer has.
- **Now:** Sentence replaced with the pinned plugin's behaviour; zh-Hans install text brought in line. The released v1.2.1 pin proposed upstream (#129093, d56c4ac) declares the same two dependencies in pyproject, so the text survives that bump.
- **Mirrors:** zh-Hans memory-providers.md fixed in the same commit (its whole Hindsight install paragraph was bundled-era).
- Drift introduced by 5e4857bf2e (#128442).

## Related Issue

Supersedes our own parked docs PRs #127354 (closed to keep the review queue short); no open issue tracks these drifts.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `website/docs/user-guide/features/memory-providers.md`
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/features/memory-providers.md`

## How to Test

1. For each item above, read the cited source lines on `main`; the old text contradicts them, the new text matches.
2. Behaviour the docs describe, run on this branch: external plugin read at the pinned SHA (gh api, read-only); no in-repo test covers the third-party plugin's install path.
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

Verified on `main` f848940560; merges cleanly onto eb8d21f482. Branch `ready/docs2-memory` @ c9010e911f6f, 2 files changed, 5 insertions(+), 4 deletions(-).
