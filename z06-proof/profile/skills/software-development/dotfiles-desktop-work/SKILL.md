---
name: dotfiles-desktop-work
description: "Use when changing the owner's dotfiles or desktop services."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [dotfiles, hyprland, noctalia, systemd, workspace-copilot]
    related_skills: [focus-safe-desktop-automation, session-recovery]
---

# dotfiles-desktop-work

Use when changing the owner's dotfiles, Hyprland or Noctalia desktop, user services, host configuration, or workspace-copilot next-action behavior.

## Rules

1. Recover prior intent, history and measured experiments before designing. Inspect git status -sb, git worktree list, relevant history and deployed symlink targets. Preserve other sessions' edits. Use a fresh branch/worktree from origin/dev for new .files work rather than assuming /workspace/.files is current.
2. Change the smallest owned seam. Keep the existing engine fallback, require a measured holdout win for a new learned path and retain an off switch. Follow references/workspace-copilot-next-action.md for WORKSPACE_RERANK=0, whole-session time-safe training, incumbent scores and the three-day freshness gate; accept a blank stay chip.
3. Test with env -u PYTHONPATH /usr/bin/python3 -m pytest -q tests/<files>. Compare failures in a detached origin/dev worktree before assigning blame. Prove live activation from the running service's own output and client behavior, keeping source integration, installed release and active process separate.
4. Resolve the actual unit installer before deployment. Put source units in config/systemd/user/ and codify onboarding plus config/host/groot.toml rows where applicable. Use the owning stamped installer instead of ad hoc live links. Disclose daemon-reload effects on running tool-scope RuntimeMaxSec, then read status and journal rather than relying on exit zero.
5. Remove tools everywhere through source, manifest rows, deployed paths, harness hooks and declared workflows. Archive leftover state and hook backups under /mnt/zer0models/workspace/zer0/data/operations/<tool>-removal-<date>/ before deletion. Verify absence after reload and keep unrequested services and user state untouched.
6. Stage exact paths, explicitly add new files and preserve unrelated work. Use the shared $(git rev-parse --git-common-dir)/claude-commit.lock for authorized commits, include the Co-Authored-By trailer and split features from plumbing. Push only when asked. Keep stash, reset and clean out of shared-tree work, and preserve branch ownership.
7. Keep passwords outside agent-readable text. For supported fresh T3 ACP processes use the terminal's in-process masked sudo flow; otherwise use an authorized durable idempotent root script through compositor-session polkit, or give the owner the exact SSH sudo command when no safe prompt exists. Mirror tracked /etc edits into config/host/etc/ and the manifest so future applies preserve them.
8. Install reboot-sensitive updates only in the owner-initiated maintenance reboot flow; stage downloads ahead. Prefer packaged pacman-offline-prepare.timer and paccache.timer with automatic reboot disabled. Check disk, authentication and resolved cache RequiresMountsFor, drain or defer unknown workloads, and preserve package transactions from hard memory/time kills and blanket source-fork update loops.
9. Preserve focus and owner control. Run only explicitly requested Hyprland actions, verify their actual effect and use Lua dispatchers on 0.56. Keep window creation, compositor reload and Tern window reopening with the owner unless scoped authority says otherwise. Kill exact owned PIDs/scopes rather than name patterns.
10. Use references/live-host-coverage-audit.md for a real live-versus-declared inventory across package managers, file-level config links and deployed checkout lag. Capture package changes on install events with user .path units, regenerate only the captured package file and keep config adoption allowlisted. Preserve secrets in config/state and keep etckeeper history local-only; obtain an auto-push decision separately.
11. Follow references/groot-memory-pressure.md for zone-watermark, PSI, cgroup, IO and gateway diagnosis. Keep agent-oom-guard.service the sole oom_score_adj writer; preserve harness roots and use kernel child-first ranking instead of whole-cgroup oomd kills. Use groot-admit --need-mb N -- CMD, treat exit 75 as no capacity and preserve memory guards while auditing both parent and per-tool CPU ceilings. Verify new-scope cpu.max and ancestors after deployment. Avoid swapoff under pressure, respect shared-owner restart boundaries and measure counters before reporting tuning gains.
12. Follow references/tern-remote-hosts.md for per-machine generated hosts, pinned peer keys and QUIC-aware checks; distinguish list changes from a reopened sidebar. Follow references/live-wallpapers-and-phone-theme.md for canonical wallpaper manifests, content-URI imports and event-driven color sync, preserving phone data and UI ownership. For authorized server-mode on --yes, verify linger and remote access, run root failsafe first, disclose next-console-login restoration and measure MemAvailable before/after.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
