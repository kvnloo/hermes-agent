## What does this PR do?

"New worktree" with a base branch runs `git worktree add -b <new> <dir> <base>`. When the base is a remote-tracking ref, git makes `<new>` track it. #64627 added `--no-track` to prevent that, but only when the base starts with the literal `origin/`. Both twins have the gate: `addWorktree` in `apps/desktop/electron/git-worktree-ops.ts` and `worktree_add` in the `hermes_cli/web_git.py` mirror.

The base picker lists every ref under `refs/remotes`, so `upstream/main` is offered in a fork layout (`origin` = your fork, `upstream` = the project). Branching from it makes the new branch track `upstream/main`. Review push (`reviewCommit` / `reviewPush` / the `web_git` mirror) then runs a bare `git push` because the branch has tracking. Under the default `push.default=simple`, git rejects that push because the branch name does not match its upstream. If the branch had no upstream, the same code would run `git push -u origin <branch>` and reach the fork.

This PR passes `--no-track` for every base in both twins. git only auto-tracks remote-tracking bases, so the flag changes nothing for a local base. The origin-only best-effort fetch is unchanged.

## Related Issue

No upstream issue or PR found. #64627 (merged) fixed the `origin/main` case only. Searched PRs and issues for `remoteOfRef`, "worktree no-track", "non-origin remote" and "upstream/main worktree".

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `apps/desktop/electron/git-worktree-ops.ts`: `addWorktree` moves `--no-track` out of the `origin/` branch, so it is added for every base.
- `hermes_cli/web_git.py`: `worktree_add` gets the same change (Electron-op parity).
- `apps/desktop/electron/git-worktree-ops.test.ts`: new test `addWorktree: base on a remote not named origin does not set up upstream tracking`. It clones with `--origin upstream`, branches from `upstream/main` and asserts `@{u}` is unset.
- `tests/hermes_cli/test_web_server_git.py`: `test_worktree_add_from_origin_base_does_not_track` is parametrized over `origin` and `upstream` (renamed to `test_worktree_add_from_remote_base_does_not_track`).

## How to Test

1. `cd apps/desktop && npx vitest run --project electron electron/git-worktree-ops.test.ts`
2. `scripts/run_tests.sh tests/hermes_cli/test_web_server_git.py -q`
3. On unpatched `main` both new cases fail. Electron: `+ actual 'upstream/main' - expected ''`. Python: `assert 0 != 0` with `stdout='upstream/main\n'` for `[upstream]`. The `origin` cases pass.
4. With the patch: Electron 29/29, Python 18/18. If I restore the `origin/` gate on `--no-track` alone, in either twin, only the non-origin case fails again.
5. Adjacent: `git-worktree-ops`, `git-review-ops`, `git-repo-scan` and `git-root` vitest files give 52 passed, including the tag-pinned narrow-clone cases. `test_web_server_git.py`, `test_web_git_gh_stderr.py`, `test_worktree_selfheal.py` and `tests/security/test_gitspawn_config_injection.py` give 48 passed. `tsc -p tsconfig.electron.json --noEmit`, `eslint`, `prettier --check` and `ruff check` are clean.

Not changed: the best-effort fetch of the base still only runs for `origin/…`, so a base on another remote uses its last fetched ref. The picker's `isRemote` flag also still only marks `origin/…`. Both are separate from the tracking bug.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Only the targeted files listed above were run, not the full suite.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), git 2.55

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
