---
name: remote-agent-orchestration
description: Use when assigning coding work to remote devices.
---

# Remote agent orchestration

## Procedure

1. Resolve the requested action before selecting a harness: copying a prompt, submitting it to an existing agent, and personally executing its tasks are different deliverables. When the user corrects a copy/handoff request into an execution request, stop treating the remote terminal as a prerequisite; execute within the available authorized environment and carry over the original task scope and holds.
2. Discover the configured host and current terminal state before creating anything. Verify the device and its Linux/SSH environment separately: a phone can be online while the environment hosting its agent is unreachable. For Tern, use `tern remote hosts`, then `tern ssh -o BatchMode=yes -o ConnectTimeout=10 USER@HOST 'tern ls --json'`. Inspect the target pane with remote `tern capture BLOCK`; local pane listings do not establish remote state.
3. Reuse the user's existing idle agent when asked to give it a task. Use `tern send BLOCK paste TEXT`, then `tern send BLOCK keys Enter`. Capture again to confirm prompt acceptance and real work. Do not replace an interactive agent with a new one-shot invocation merely for easier tracking.
4. Inspect installed agent help and execute a short model-plus-tool preflight before assigning a long job. Use the signed-in CLI the user selects; do not silently switch providers. Copy credentials between harnesses only when the owner asks, never printing values. When the owner names a harness and model ("sol on pi"), use exactly that. Setup, credential reuse and survivable launch for pi + Sol + SoL-Pi/rlm: `references/pi-sol-remote-runs.md`. Locate actual runtime paths before proposing installs. Treat an agent's recovered path error as recovered, not evidence that execution stopped.
5. Assign an explicit checkout, isolated write scope, repository-rule read step, concrete deliverable and test commands. Preserve preexisting dirty files; prohibit unintended publishing, unrelated contributions and nested fan-out. Keep cached observations separate from live authorization.
6. Group parallel workers into tabs in one existing session, not separate sessions per task. Use readable text in visible panes; route structured JSON streams to files because token-level events resemble an error flood. Bound each job's elapsed time and writable scope.
7. Verify actual tool results and artifacts, not only process liveness or a wrapper's exit zero. Identify which executable and PID each status belongs to: a containment launcher can report signal termination while its native child exits differently. Assert the required cleanup outcome—reaping, closed pipes/listeners and absent descendants—separately from a particular exit code. Distinguish device execution, cloud inference, local tests, hosted qualification and publication. Rerun lightweight acceptance tests and inspect exact changed files before reporting completion.
8. Clean up owned completed panes and empty sessions promptly. Refresh `tern ls --json`, verify ownership and emptiness, then use `tern close BLOCK` or `tern kill session SESSION` only on known owned targets. Read back the session list and confirm the user's original agent remains. Preserve work files and agent history; names alone do not establish ownership.

## Non-executing code writers via GitHub issues

Use this when the user's writer (e.g. the ChatGPT phone app) can produce lots of code but cannot run it, and this host integrates, tests and fixes.

1. **Consolidate before filing.** Search the owner's open and closed issues on the topic. Fold superseded RFCs and trackers into one RFC: prepend a banner pointing to the new issues, keep the old body, and close the old issue as not planned. Keep open only threads involving external collaborators.
2. **Create two pinned entry issues:**
   - **Roadmap / START HERE:** next task, who-does-what table, current base branch, ordered queue with statuses, short rules, and the host-owned work list.
   - **RFC:** goal, decided architecture, constraints, acceptance, gap matrix with task links, branch map, promotion path, per-feature gate.
3. **Put everything in issue bodies, never in comments.** The writer only reads what it is pointed at. Update state by editing bodies; a body edit is the only reliable channel back to it. Rework instructions go into the task body under "Rework".
4. **One self-contained task issue per feature.** Generate them from one script so the shared workflow block is identical (template: `templates/writer-task-issue.md`). Each contains:
   - why;
   - pinned upstream reference links;
   - exact files and functions with approximate lines (verify them against the base before posting);
   - numbered spec;
   - acceptance bullets to encode as tests;
   - branch name, base, PR title, `Closes #N`;
   - hard rules: forbidden branches, no hand-edited generated files, "say what you couldn't verify".
   Create the issues with placeholder bodies first so cross-references get real numbers, then edit the bodies.
5. **Ownership: the integrator owns the integration lane.** Tell the writer in the roadmap and the PR body not to push there. Never push to a branch the writer is actively pushing to. Check with `gh pr view --json updatedAt,commits` whether new commits appeared during your scan.
6. **Keep the writer saturated; it must never run out of work.**
   - A phone writer finishes a small task in minutes, so keep 10+ `ready` tasks in the queue.
   - Add a "Never idle" section that points to standing, never-closing track issues (tests, code quality, performance, motion/polish, accessibility). Give each a candidate list and rotate one PR per track per pass (template: `templates/writer-evergreen-issue.md`). Writers may also propose tasks via a spec-only PR, which the integrator turns into task issues.
   - Use a fixed status vocabulary: `ready` / `in PR #N` / `fixing` (don't push) / `needs <writer>` (see "Rework" in the issue) / `merged`.
   - When the integrator takes a task itself, set its status in the roadmap so the writer skips it.
   - Tell the writer never to rebase onto, or resolve conflicts with, other task branches. Every task touches the same hot files; the integrator resolves conflicts at merge time.
   - Tell the writer to pull the base before each new task, and keep the roadmap's base-branch line current with the merged SHA.
7. **Run the integration loop cheaply.**
   - Wake on writer activity with a plain shell poller, not a model loop (`scripts/watch-writer-prs.sh`, interval ≥15 min). It emits a sentinel only when an open PR on the base appears or its head moves.
   - Hand routine qualification, rebases and merges to cheap subagents. Keep the expensive main model for planning and judgment.
   - Never add a short heartbeat on top of the watcher; subagent completions already wake you.
8. **Give the user a one-paragraph prompt to paste into the writer.** It should say: read the roadmap body, do "Your next task", then continue down the queue, then the Never-idle tracks.
9. **Show each feature branch to the user in its own Tern pane** beside the conversation, and run its gate before merging. Recipe: `references/tern-branch-preview-panes.md`, which also covers putting a web app in a dedicated Tern window or session on another monitor.

## Before showing the user "the app"
Compare the default branch with the integration and feature branches (`git branch -a --sort=-committerdate`, `git rev-list --left-right --count main...BRANCH`). Find which branch the running service actually serves before opening anything. Agents often leave the live, wired-up version on an unmerged integration branch while `main` holds a stale static demo. Showing `main` then looks like "the wrong version", and the real fix is integration ownership, not UI work.

## Interrupts and status

- Inspect capture, process/session exit and tool-result history before diagnosing an interruption. Ctrl-C plus an aborted request establishes termination, not who caused it.
- Do not restart canceled workers automatically. Preserve partial artifacts and distinguish execution blockage from unavailable test verification.
- Label asynchronous findings with their project and execution device so an unrelated desktop completion does not appear to explain a phone worker.
- Report results first and limitations once. A recovered error, missing test prerequisite and final interruption are distinct events.

## Fleet membership audit ("why isn't work going to device X?")

Before saying a device can take offloaded work, check every layer that has to include it. Being online in Tailscale does not prove membership in any scheduler.
- **k3s:** `KUBECONFIG=~/.kube/k3s.yaml kubectl get nodes -o wide`. The default kubectl context may point to a different cluster (for example kind), so always name the k3s kubeconfig. Compare the plan's components (Kueue, time-slicing, GPU Feature Discovery, ESO, NetworkPolicy, host-service EndpointSlice) with `kubectl get crd`, `kubectl get netpol,svc,endpointslices -A`, node `allocatable` and the quota usage.
- **Hermes cluster:** query the nodes API with the token from `cluster.yaml`. Grep the cluster log for the device's tailnet IP to see whether it ever sent `nodes/join`. Status polls alone do not mean it joined.
- **Reachability:** if `ssh -o BatchMode=yes` prints a Tailscale SSH `check` re-auth URL, the ACL is in check mode, and only the owner can change it to `accept`. Don't open the URL yourself.
- **Plan vs reality:** find the plan with `ctx search` across harness histories, plus the dotfiles or IaC issue. Report each component as present or missing with evidence. Don't assume claimed components exist (for example self-healing controllers or routers) until you find a running process or manifest. When grepping processes for a short name like `pair`, match whole words; substrings such as "repair" give false hits.

## Resource qualification

Before increasing concurrency, run short bounded 1/2/4-worker probes using the actual runtime and discovered workload schema. Measure elapsed time, aggregate throughput, available memory and swap changes. Include representative read-only archive queries or lightweight tests alongside a CPU probe. Define memory stop thresholds and an outer timeout first; retain raw results in canonical remote storage.

Do not treat brief CPU scaling as a sustained agent ceiling: resident memory, mobile scheduling, foreground app load and thermal throttling differ. If temperature telemetry is inaccessible, state the limitation and avoid a sustained all-core soak. Choose a conservative initial worker count from the measured workload and available memory rather than treating a successful four-process probe as permission for four agents. Increase only after real concurrent task progress without pressure or responsiveness loss. Cloud model inference is not phone-GPU execution unless local inference was actually exercised.
