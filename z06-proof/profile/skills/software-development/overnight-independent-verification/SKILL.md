---
name: overnight-independent-verification
description: Use when verifying other agents' claims before sign-off.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [verification, qa, overnight, evidence]
    related_skills: [dash-host-only-qualification, rendered-ui-qualification, upstream-contribution]
---

# Overnight independent verification

## When to Use
The owner asks for an independent check of claims that other agents reported (PRs, deployed services, approval items). Re-run each claim at its exact head, exercise the live services, and rank the defects.

## Procedure
1. Resolve every PR head with `gh pr view --json headRefOid` and create a detached worktree per claim under `/mnt/zer0models/worktrees/verify-<date>/<name>` from the local clone (`git fetch origin pull/N/head`). Never test in the deployed checkout.
2. For each deployed service, prove which code it runs: compare the process start time (`ps -o lstart`), the checkout HEAD commit time, and `git status`. A service started before its head commit is not running that head.
3. Run the gates in the worktree. A full rebuild can outlast the terminal's ~420 s cap, so start it as a background process with notify and poll it. `flock heavy.lock` waits count against `timeout`, so put `timeout` *after* flock acquires (`flock L timeout N cmd`).
4. Exercise live behaviour with throwaway identities only: a new session, a throwaway pairing, or a fresh k8s Job. Revoke or archive in `finally`. Keep tokens in process memory and never print them.
5. Trace sampled ledger or receipt rows back to their raw source before you trust a classifier. The tool name matters: read-only tools (read_file, skill_view, search) echo old text such as "N passed".
6. For approval items (origin replies), verify RED->GREEN yourself. Swap in the pre-fix file from `<sha>^`, run the test, then restore it. Check the comment ids, that there is no existing reply, and the factory tone gate. Never approve or post.
7. Write the report with verdict table -> per-claim evidence -> ranked defects (each with a minimal fix) -> fixes shipped -> cleanup.

## Pitfalls
- `agent-telemetry-refresh.service` runs `refresh.sh`, which takes `heavy.lock` itself. Wrapping `systemctl start` in the same flock deadlocks it.
- `journalctl | rg -i oom` matches "room"/"zoom". Use `\boomd?\b|oom-kill|out of memory`.
- z0live `session_end` enqueues a Hermes summary job. Don't end throwaway sessions; revoke the device instead.
- Your own subagent transcript lands in the profile's state.db, so a grep there can "find" your test text. Check `session_id` before concluding that you wrote into someone else's session.
- The kind default kubectl context is not the factory cluster. Use `KUBECONFIG=~/.kube/k3s.yaml`.
- A PR whose base branch moved can show green CI and still conflict. Run `git merge-tree --write-tree <base> <head>`.
