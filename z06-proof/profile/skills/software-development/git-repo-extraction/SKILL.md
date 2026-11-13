---
name: git-repo-extraction
description: Use when splitting a subdir to a repo or pushing local work.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, filter-repo, github, dotfiles, publish]
    related_skills: [github, git-evidence-preservation]
---

# Git repo extraction and local-work publication

## When to Use

- Moving an app or tool out of a monorepo/dotfiles into its own repo with history.
- The user says "commit and push" pending work, or believes something was already pushed.

Covers: moving a subdirectory (e.g. an app living inside dotfiles) into its own GitHub repo with history, removing it from the source repo, and committing/pushing the source repo's pending local work.

## Extract a subdirectory with history

1. Inventory first: `git log --oneline -- <dir>`, `git grep -n '<dir>' -- ':!<dir>'` for references, and grep inside `<dir>` for absolute paths back into the source repo (they still resolve if the referenced config stays in the source repo; anything pointing INTO `<dir>` itself, like a venv path, will break — report it).
2. Check ignored/untracked content in `<dir>` (`du -sh`, `git status --ignored <dir>`) before any later `rm -rf`; extraction only carries tracked files.
3. `git clone -q --no-local <src> <dest> && cd <dest> && git checkout <branch> && git filter-repo --subdirectory-filter <dir> --force`. `--no-local` gives filter-repo a real fresh clone.
4. In the new repo: `git branch -m main`, delete every other branch and tag (they came from the source repo), `git reflog expire --expire=now --all && git gc --prune=now`. Add a short README (what it is, how to run, "split from <src> with history", remaining couplings).
5. Secret-scan the whole new history (`gitleaks git .` if present, else grep `git log -p --all` for key/token/password assignments) before the first push.
6. Create private by default: `gh repo create <owner>/<name> --private --source . --remote origin --push --description ...`. Verify with `gh repo view --json url,visibility` and `git ls-remote origin main` == local HEAD.
7. In the source repo: `git rm -r -q <dir>` and commit ONLY that path (`git commit -m ... -- <dir>`) so the user's unrelated dirty files stay untouched. Keep system config the app reads (pipewire confs, bar plugins) in the source repo unless told otherwise; tell the user which pieces stayed.

## Publish pending local work ("commit and push")

1. Never trust the user's (or your) assumption about what is unpushed. Show `git log origin/<b>..<b>` grouped by theme and dates, and list local branches with no upstream: `git branch --format='%(refname:short) %(upstream)'` — work the user believes is pushed is often a local-only feature branch or worktree. Correct the assumption explicitly in the reply.
2. If the unpushed range differs from what the user authorized, say what it actually contains before pushing; push once it is confirmed as the user's own work.
3. For a local-only feature branch the user calls important, check `git merge-tree --write-tree --name-only <base> <feature>` first (exit 0 with no conflict list = clean); stash the dirty tree, `merge --no-ff`, `stash pop`. Also push the feature branch itself with `-u`.
4. Commit the dirty tree as several focused commits (one concern each: feature, fix, chore), staging explicit paths. Exclude tool-generated junk and foreign content: repeated `[safe] directory =` lines a CI runner appended to a tracked `.gitconfig`, third-party repos cloned inside the tree, caches.
5. Before pushing a public repo: grep the outgoing diff (`git diff origin/<b>..<b>` plus new commits) for credential patterns; run cheap gates on touched files (`py_compile`, `bash -n`, JSON load, any script `selftest`).
6. Push, `git fetch`, and confirm `git rev-parse <b> origin/<b>` match. Report the commit list, what was excluded and why.
