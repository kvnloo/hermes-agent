---
name: issue-queue-agent-integration
description: "Use when an external coder works from issues you integrate."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, orchestration, delegation, integration, parity]
    related_skills: [hermes-tern-parity-orchestration, session-recovery, github]
---

# Issue-queue agent integration

## When to Use
A mobile code-writing agent takes bounded tasks from GitHub issues and opens draft PRs. Discover its actual capabilities first: a ChatGPT GitHub connector may inspect/dispatch Actions even though it cannot clone, run a shell or access local services. A DeepSeek chat without a connector needs a fully pasted packet and returns a patch, not a claimed GitHub write. Hermes qualifies, fixes and demos the PRs; merges/promotions require separate explicit authority. Keep the queue full without duplicating in-flight work. Also use this when the user asks to reach feature parity with a reference product through many parallel feature branches.

## Procedure
1. **Inventory before planning.**
   - Scan every related branch, worktree, open PR and tracking issue. Run read-only subagents in parallel: branch topology, a reference-vs-ours feature matrix, and a decision history (cross-harness ctx history plus GitHub bodies and comments).
   - Back up dirty or local-only work to `wip/*` branches before anything else: temp `GIT_INDEX_FILE`, `add -A`, `write-tree`, `commit-tree`, push. This leaves the worktree untouched.
2. **Consolidate the issue surface.** Exactly three kinds of issue, all pinned or labelled:
   - One **roadmap / START HERE** issue: next task, who does what, current base branch, a queue table with status, rules, a log.
   - One **RFC**: architecture, constraints, acceptance, parity matrix, branch map, promotion policy.
   - **Self-contained task issues.**
   - Close superseded issues with a banner at the top of the body that points to the new ones; keep the old body below it.
3. **Write task issue bodies that stand alone.** The external agent reads bodies only, never comments. Each body carries:
   - why it matters, with reference-source links at a pinned SHA;
   - our files and functions to touch;
   - a numbered spec, and acceptance bullets to write as tests;
   - branch name, base, PR title/body form, and hard rules;
   - a notation legend if it uses shorthand.
   Generate the bodies from a script (a list of dicts → markdown) kept next to the roadmap source file, so revisions are cheap.
4. **Keep the queue non-empty.**
   - Add standing "never idle" track issues: tests, code quality, performance, motion/polish, accessibility. Each lists candidate items and rules for small behaviour-preserving PRs, plus a conflict rule: don't restructure a file an open task PR is changing.
   - When the queue thins, run a parity re-audit and file the next wave.
   - Give the user a one-line re-prompt to paste into the external agent.
5. **Run the integration cycle** (it repeats until done):
   - Watch for new or updated PRs with a shell poller at ≥15 min; it uses no model.
   - The external agent goes idle unless the user re-prompts it. Don't wait: mark tasks "Hermes doing it (skip)" in the roadmap **before** dispatching implementation subagents. That makes ownership visible and avoids duplicate work.
   - Per cycle, one delegate call: a merge subagent for the last batch of green PRs, plus 3–5 implementation subagents for the next tasks, each in its own worktree and branch. Each opens a draft PR into the integration lane with a receipt comment.
   - The merge subagent merges in a stated order with gates after each merge. It verifies the remote tip, fast-forwards the lane and preview atomically, then closes the issues.
   - After each batch, update the roadmap statuses, the base-branch SHA line and the log.
6. **Demo to the user.**
   - Open the integrated build in a Tern pane beside the session's own pane: `tern split <$TERN_PANE> right`, not `@focused`, which may be another tab.
   - Run the build against the user's real profile when they test, so their providers and config load. Back up `state.db` first.
   - Don't restart a pane the user is actively testing; say the next launch picks up changes.

## Repo-owned mobile roadmaps

- Reuse one existing START HERE/mobile roadmap issue per repository, keep its number/comments/history, label it `mobile-lane`, and pin it only when a slot is free. Never replace a canonical promotion queue or evict another pin. In GraphQL, `pinnedIssues.nodes` contains `PinnedIssue` wrappers: query `nodes { issue { number } }`.
- Inspect the actual declared PR-target tree and workflows, not just the default branch or a kitchen scan. A preview/integration branch may lack modern modules and CI already present on main. Treat missing targets and CI as explicit dependencies; never quietly retarget to main or port unrelated runtime code.
- Curate 5–12 source-linked S/M cards with exact allowed paths, why, measurable Actions acceptance/job/commands, branch/base, dependencies, exclusions and a DeepSeek-ready flag. A YES flag requires a packet of complete exact-revision files and synthetic inputs before use; links alone do not make a paste-in task self-contained.
- Keep card data/status in one marked generated block and human notes/history outside it. Use a dry-run-first refresher, exact-target readback, an optimistic concurrent-edit guard and content-sensitive timestamps so unchanged reruns are byte-identical. Test that human notes survive and the second apply writes nothing.
- Discover lane issues by their label or canonical registry locator instead of keeping a second project registry in the refresh script. Record missing active identities in the existing canonical registry, keep unassigned topology explicit, and preserve earlier registration proposal credit.
- Distinguish merged PR delivery, closed-unmerged retirement, open-PR rework, closed-source re-pick and stale cards. Only a merged prerequisite can release dependent work; a checked closed-unmerged card is never accepted delivery. State reconciliation does not replace weekly human re-curation or hardware/runtime qualification.

## Rules
- Route routine work (qualification, merges, e2e, audits) to subagents on cheaper models. Keep the main model for planning and judgement. Poll no faster than 15 minutes.
- Feature PRs never rebase onto each other or resolve conflicts between tasks; the integrator does that at merge time.
- Never present stub or fake evidence as acceptance. Keep evidence classes separate (unit, headless host, real window, live provider). When an environment gate (for example sign-in) blocks a class, report it as blocked and ask the user for the one-time unblock.
- If a platform limit makes a task impossible (for example an SDK that can't distinguish key release), merge the safe fallback, keep the issue open with the reason, and don't fake the behaviour with timers.
- Anything touching main or upstream is a draft PR that waits for the user's explicit OK.
- Always push with `--no-follow-tags`. A global `push.followTags=true` publishes unrelated local release tags.
- Merging into a shared composition file: union both sides' registrations and render-context arguments; never pick one side. Regenerate generated contracts with the repo generator instead of hand-merging them.
- Classify a test failure as pre-existing only after reproducing it on an archive of the exact pre-merge base, with the same interpreter, at reduced concurrency. Keep the original failing receipt.

## Factory flood reconciliation

- Join dispatch receipts to each brief's actual `repo` and `issue`, then to the result comment's exact first-line tag. Research briefs often return comments in the coordination repository rather than implementation PRs; do not count those as missing code deliveries.
- Keep `sent`, failed and unconfirmed dispatches separate. Use `dispatch_t0` only as an attempted-send timestamp when `at` is absent. A matching result can exist for an unconfirmed send; never blindly redispatch it.
- Link resulting PRs through the result envelope's branch/head identity, not every PR URL cited by a research report. Save the raw observations and compute totals and overlaps programmatically at an explicit census cutoff.
- Check workflow-dispatch runs in addition to PR rollups. A stacked PR can show only successful documentation drift while its manual full CI failed; preserve both facts. Supply a fetched exact integration-base SHA, not an assumed local branch ref.
- When a shared REST quota is exhausted, inspect the reset once and avoid immediate retries. Read-only GraphQL issue comments and CheckRun steps can provide fresh evidence if their separate quota remains available; do not equate unavailable logs with successful tests.
- For date-dependent offline billing fixtures, freeze only the fixture clock inside the verified contract window and add exact-expiry rejection controls. Never extend production pricing/authorization expiry to make CI green.
- When a newly reachable CI step exposes manifest drift, compare the generated classification to the committed manifest and use the repository generator. Do not disable the classification gate or guess entries by hand.
- Fix flaky timing tests by making them deterministic (counters, fake clocks), with a negative control. Never loosen thresholds.
