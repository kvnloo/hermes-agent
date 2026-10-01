## What does this PR do?

`contributors/README.md` says both GitHub noreply forms auto-resolve with no mapping file. The Contributor Attribution Check only skips the id+login form: `.github/workflows/contributor-check.yml:51-52` matches `\+.*@users\.noreply\.github\.com`, then requires `contributors/emails/<email>` or a legacy `AUTHOR_MAP` entry. `scripts/audit_pr_attribution.py` does the same (`ID_NOREPLY_RE` at line 44, `is_mapped()` at lines 64-77). A contributor who commits with the bare `<login>@users.noreply.github.com` form and follows the README skips the file and fails the check.

Release-note attribution (`scripts/releases/authors.py:63-66`, in `resolve_author()`) does guess `@<login>` from a bare local part, so the old line holds there, but not for the Contributor Attribution Check or `audit_pr_attribution.py`. The audit script's docstring (lines 19-22) gives the reason that guess needs checking: the local part is usually the GitHub login but is user-controlled.

This narrows the auto-resolve rule to the id+login form and says the bare form needs a file, which `audit_pr_attribution.py --fix` creates. Over 200 bare-noreply mapping files already exist under `contributors/emails/`, which is the path the gate requires. Docs-only; no other doc repeats the claim (`git grep` over `*.md`/`*.mdx`). The line has been inaccurate since `contributors/README.md` was added in 597615ade4 (#66373); the CI gate already skipped only the id+login form at that point.

## Related Issue

No issue. Replaces my earlier #127376 (closed, same change). Related: #9718 and #27789 propose making the CI gate accept bare noreply emails instead. This PR documents current behaviour; if either of those lands, this change should be dropped.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `contributors/README.md`: limit the "auto-resolve, no file needed" rule to `<id>+<login>@users.noreply.github.com`; say the bare `<login>@users.noreply.github.com` form needs a mapping file and that `scripts/audit_pr_attribution.py --fix` creates it.

## How to Test

1. Read the cited lines on `main` (`.github/workflows/contributor-check.yml:51-52`, `scripts/audit_pr_attribution.py:44,64-77`); the old README text contradicts them, the new text matches.
2. On `main`, check how the audit script and the CI rule treat each form:
   ```
   cd scripts && python3 -c "from audit_pr_attribution import is_mapped; print(is_mapped('123456+probe@users.noreply.github.com'), is_mapped('probe-nonexistent@users.noreply.github.com'))"
   ```
   prints `True False`. CI rule:
   ```
   echo probe@users.noreply.github.com | grep -qP '\+.*@users\.noreply\.github\.com' || echo not-skipped
   ```
   prints `not-skipped`.
3. No test, docs build or link checker covers `contributors/README.md` (it is not part of the Docusaurus site), so verification is steps 1-2.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass — not run; docs-only change, no tests cover contributors/README.md
- [ ] I've added tests for my changes — N/A, documentation only
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Merges cleanly onto `main` da1a583417.
