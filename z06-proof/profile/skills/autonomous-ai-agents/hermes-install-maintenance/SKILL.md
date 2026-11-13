---
name: hermes-install-maintenance
description: "Use when `hermes update` or gateway restart misbehaves."
---

# Hermes install maintenance (update failures, checkout repair)

Complements the bundled `hermes-agent` skill (which owns CLI/config reference). This one is the procedure for a broken or stuck update, plus filing the upstream issue.

## Locate the checkout first
- `$HERMES_HOME` may be a profile dir (`~/.hermes/profiles/<name>`), and the Hermes home root is NOT a git repo. The git checkout is `<root>/hermes-agent` (root is often a symlink; use `readlink -f`). Run git there, not in the home dir.
- `git fetch origin`, then `git status -sb` and `git rev-list --left-right --count HEAD...origin/main` show dirtiness and how far behind it is.

## Diagnose a failing/hanging `hermes update`
1. Reproduce it: `timeout 170 hermes update 2>&1 | tail -40`. Note the last printed step; a hang after "Local changes detected — stashing before update..." is the stash step.
2. The updater autostashes with `git stash push --include-untracked` (hermes_cli/update_cmd_stash.py). Plain `git stash` saying "No local changes to save" does NOT reproduce it, because tracked files are clean; untracked files are what get swept.
3. Look for huge untracked files: `git status --short`, then `ls -la` and `du -sh` on them. Sparse files (core dumps such as `core.<pid>` written by a crashed Electron desktop app into `apps/desktop/`) have TB-scale apparent size but tiny disk use; the stash reads the apparent size and never finishes. `file <name>` identifies core dumps and the crashing binary.
4. After killing a hung update, check there is no `.git/index.lock` and no stray git process before retrying.

## Diagnose a slow (still progressing) `hermes update`
The update receipt (`~/.hermes/logs/update_receipts/latest.json`) records step outcomes but no durations, and the desktop half's output goes to the caller's terminal rather than `update.log`. Rebuild the timeline yourself before guessing:
1. Find the live updater and its stage with `ps -eo pid,ppid,lstart,etime,pcpu,args --sort=start_time`. The desktop half runs as `hermes_cli/source_completion.py --desktop --finish-update`. Children such as `electron-builder` and `vite` show the current phase.
2. Date each phase from artifact mtimes (`ls --time-style=+%H:%M:%S`):
   - `apps/desktop/build/install-stamp.json`: npm ci finished.
   - `build/native-deps.prepared.json`: native deps ready.
   - `apps/desktop/dist/`: renderer/electron build finished.
   - `build/packager/linux-x64/electron.zip` and `release/linux-unpacked/`: electron-builder packaging.
3. Check machine contention before blaming the build: `nproc`, `loadavg`, `/proc/pressure/{cpu,io,memory}`, and the top CPU processes. Other agents' build jobs on a shared host can double phase times, and so can btrfs compression on a nearly full disk.
4. The usual dominant costs are a full `npm ci` (wipe and reinstall the whole workspace tree on every update) and an unconditional Electron desktop build, even for users who only need the CLI.
5. Run `hermes update` from an agent tool without a short timeout, or as an async/background job. A tool timeout kills the update partway through, the work is lost, and the rerun starts from scratch.
6. When experimenting with speedups, work in a `git worktree` or clone with its own node_modules. Never `npm ci` in the live checkout or run a second `hermes update` beside a running one: the update lock refuses it, and a half-reinstalled tree breaks the install.

On hosts whose login shell is fish (the MBP), `ssh host 'VAR=$(...)'` and bash globs fail. scp a bash script to `/tmp` and run `ssh host 'bash /tmp/x.sh'`.

## Fix
- Move (not delete) the offending untracked files out of the repo, e.g. into `<root>/crash-dumps/` on the same filesystem (instant rename). Confirm `git status --short` is empty, then rerun `hermes update`. Offer deletion separately.
- Do not run `git stash -u` or `git clean` on the checkout to "test": it can hang the same way.

## Restarting gateways after an update
- Symptom of a needed restart: a client (mobile app Model/effort sheet, `/model`) refuses to switch with a stale-module message. The checkout moved but the running gateway still has old modules loaded, so switching would import new provider code into an old process. Confirm with `hermes update --plan` (lists each running service, its PID and loaded revision).
- A bare `hermes gateway restart` acts on whatever `HERMES_HOME`/sticky profile resolves to, which may not be the multiplexed gateway the clients use. Name it: `hermes -p default gateway restart`, or `hermes -p default update` (pull + drain + restart). Check `~/.hermes/active_profile` and `echo $HERMES_HOME` when a restart "does nothing".
- From inside an agent turn the restart guard refuses gateway restart/stop commands (it assumes the caller is a gateway child). Run it detached instead: `systemd-run --user --unit=hermes-update-$(date +%s) --collect hermes -p default update --yes`, then follow `journalctl --user -u 'hermes-update-*'`. Do not wait on it in a foreground tool call: the drain waits for active turns up to `agent.restart_after_turn_timeout` (default 30 min) and the tool times out; the journal lists the turns it waits on.
- The update may not restart the dashboard (`hermes-web.service`): when `update --plan` still lists it, `systemctl --user restart hermes-web.service` and check loopback returns 302. A lingering "did not restart gateways" warning can come from a separate API-only host that doesn't publish its code identity; restart that unit rather than the main gateway again.

## Post-update warnings: report, don't silently fix
- Old leftover `hermes-update-autostash-*` stashes: list them and point to `git stash show -p` / `apply` / `drop`; never drop without asking.
- Service unit warnings (e.g. missing `RestartPreventExitStatus=78`, suggesting `hermes gateway install`) and "fleet version check returned no rows": surface to the user.
- A pre-update snapshot skipping `state.db` (over 1 GB) means no DB backup exists.

## Filing an upstream issue
- Repo is NousResearch/hermes-agent; run `gh auth status` first.
- Search duplicates: `gh issue list -R NousResearch/hermes-agent -S "<keywords>" --state all`.
- Confirm the cause in source (grep the command, cite file:line) before writing it up.
- Body: Summary, observed repro steps, cause, suggested fix, environment (OS, hermes version string). Write it to a temp file and use `gh issue create --body-file`. Title style `[Bug]: ...`. Report the issue URL.
