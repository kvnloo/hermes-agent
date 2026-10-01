## What does this PR do?

"New worktree" with a base branch runs `git worktree add -b <new> <dir> <base>`. When the base is a remote-tracking ref, git makes `<new>` track it. #64627 added `--no-track` to `addWorktree` in `apps/desktop/electron/git-worktree-ops.ts`, but only when the base starts with the literal `origin/`. The `worktree_add` mirror in `hermes_cli/web_git.py` copied the same gate.

The base picker lists every ref under `refs/remotes`, so `upstream/main` is offered in a fork layout (`origin` = your fork, `upstream` = the project). Branching from it makes the new branch track `upstream/main`. Review push (`reviewCommit` / `reviewPush` / the `web_git` mirror) then runs a bare `git push` because the branch has tracking. Under the default `push.default=simple`, git rejects that push because the branch name does not match its upstream. If the branch had no upstream, the same code would run `git push -u origin <branch>` and reach the fork.

This PR passes `--no-track` for every base in both implementations (the Electron op and the `web_git` mirror). With git's default `branch.autoSetupMerge=true`, only a remote-tracking base is auto-tracked, so for a local base the flag is a no-op. Under `always` or `inherit` a local base would be tracked too (with `inherit`, e.g. local `main`'s `upstream/main` is copied), and the flag keeps that branch standalone as well.

Not changed: the best-effort fetch of the base still only runs for `origin/…`, so a base on another remote uses its last fetched ref. The base picker's `isRemote` flag also still only marks `origin/…`. Both are separate from the tracking bug.

## Related Issue

No upstream issue or PR found. #64627 (merged) fixed the `origin/main` case only. #75600 (merged) added `remoteOfRef` for the convert-a-branch path; the new-branch-from-base path still gates `--no-track` on `origin/`. Searched open and merged PRs and issues for `remoteOfRef`, "worktree no-track", "non-origin remote" and "upstream/main worktree".

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `apps/desktop/electron/git-worktree-ops.ts`: `addWorktree` moves `--no-track` (and its comment) out of the `if (base.startsWith('origin/'))` block, so it is passed for every base.
- `hermes_cli/web_git.py`: `worktree_add` gets the same change (Electron-op parity).
- `apps/desktop/electron/git-worktree-ops.test.ts`: new test `addWorktree: base on a remote not named origin does not set up upstream tracking`. It clones with `--origin upstream`, branches from `upstream/main` and asserts `@{u}` is unset.
- `tests/hermes_cli/test_web_server_git.py`: `test_worktree_add_from_origin_base_does_not_track` is parametrized over `origin` and `upstream` (renamed to `test_worktree_add_from_remote_base_does_not_track`).

## How to Test

1. `cd apps/desktop && npx vitest run --project electron electron/git-worktree-ops.test.ts`
2. `scripts/run_tests.sh tests/hermes_cli/test_web_server_git.py -q`
3. To see the failure, restore the two source files from `main` while keeping the new tests (`git checkout main -- apps/desktop/electron/git-worktree-ops.ts hermes_cli/web_git.py`) and rerun steps 1–2. The new Electron test fails with `+ actual 'upstream/main' - expected ''`, and the Python `[upstream]` case fails with `assert 0 != 0` (`fresh@{upstream}` = `upstream/main`). The `origin` cases pass.
4. With the patch: Electron 29/29, Python 18/18. If I restore the `origin/` gate on `--no-track` alone, in either implementation, only the non-origin case fails again.
5. Adjacent: `git-worktree-ops`, `git-review-ops`, `git-repo-scan` and `git-root` vitest files give 52 passed, including the tag-pinned narrow-clone cases. `test_web_server_git.py`, `test_web_git_gh_stderr.py`, `test_worktree_selfheal.py` and `tests/security/test_gitspawn_config_injection.py` give 48 passed. `tsc -p tsconfig.electron.json --noEmit`, `eslint`, `prettier --check` and `ruff check` are clean.

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
