## What does this PR do?

Docs-only. Each statement below is wrong on current `main`; every correction cites the source that contradicts it. No behaviour changes.

### docs: correct bare noreply email auto-resolve claim in contributors README

- **Was:** contributors/README.md:35-36 — "GitHub noreply emails (`<id>+<login>@users.noreply.github.com` and `<login>@users.noreply.github.com`) auto-resolve — no file needed."
- **Source on main:** .github/workflows/contributor-check.yml:51-52 skips only emails matching '\+.*@users\.noreply\.github\.com' ('GitHub id+login noreply emails auto-resolve'), then requires contributors/emails/<email> or a legacy AUTHOR_MAP entry; scripts/audit_pr_attribution.py:44 ID_NOREPLY_RE, :64-77 is_mapped() short-circuits only on ID_NOREPLY_RE; --fix (resolve_login + add_contributor.py) maps a bare noreply by WRITING a file.
- **Check:** Probe on main: is_mapped('123456+b2probe@users.noreply.github.com') -> True; is_mapped('b2probe-nonexistent@users.noreply.github.com') -> False; CI shell rule replayed: id+login -> skipped, bare -> MISSING. 225 bare-noreply files already exist under contributors/emails/.
- **Now:** README narrows auto-resolve to the id+login form and says the bare form needs a file (audit --fix creates it).
- **Mirrors:** Only copy (git grep 'auto-resolve' / '<login>@users.noreply' across *.md).
- Drift introduced by 8bbedc345f (#126344).

## Related Issue

Supersedes our own parked docs PRs #127376 (closed to keep the review queue short); no open issue tracks these drifts.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `contributors/README.md`

## How to Test

1. For each item above, read the cited source lines on `main`; the old text contradicts them, the new text matches.
2. Behaviour the docs describe, run on this branch: is_mapped() probe + CI shell-rule replay (see red); no pytest target exists for contributors/README.md.
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

Verified on `main` f848940560; merges cleanly onto eb8d21f482. Branch `ready/docs2-contributors` @ 29319c49cd4f, 1 file changed, 5 insertions(+), 2 deletions(-).
