---
name: agentic-gitops-integration
description: Use when integrating parallel agent Git branches locally.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, integration, agents, evidence]
    related_skills: [git-isolated-contribution-guards, git-evidence-preservation]
---

# Agentic GitOps integration

## When to Use

Use for authorized local multi-lane branch integration, branch/worktree registries and evidence-bound promotion without publication.

## Procedure

1. Read the shared program and lane ownership before mutation. Capture refs, full heads, worktree registrations, status (including ignored evidence), stashes and tags outside the source checkout. Use explicitly assigned worktrees; never repair another lane's dirty state.
2. Separate generic rollout defaults from the explicit program override. Local-only forbids legacy scripts that fetch, switch shared checkouts, push nightly or dispatch publication. Inspect deployment topology at the owning ref: a channel can intentionally omit a main-owned Pages publisher and contain only a dispatch workflow. When adapting the owner's other repositories, read the fork's actual channel refs and workflow code rather than the upstream checkout; copy trust boundaries and acceptance gates, not repository-specific guards or main-only triggers. Verify refs, workflows and protections are active before calling a channel established.
3. Inventory all local and remote-tracking refs, symbolic aliases, detached worktrees and missing registrations. Verify the canonical branch's current remote SHA before using local tracking refs; another host may have advanced it. Use exact Git ancestry for integrated status, but treat a non-ancestor as unresolved when work was cherry-picked, squashed or surgically consolidated: compare the affected behavior and current files before proposing another merge. Never infer cleanup safety from matching tips, old dates or a stale tracking ref. Keep classification as proposals and preserve the canonical object store.
4. Publish a path-redacted snapshot and deterministic rendered table. Use public labels/opaque worktree IDs instead of absolute host paths. Validate schema/render portably in CI; validate complete ref identities and worktree-to-branch bindings locally. Snapshot tip equality cannot be a permanent CI requirement: committing the snapshot itself moves its branch. Admission must independently pin and compare READY SHA.
5. Keep stable per-branch preview identity after integration; a null URL means not deployed. Runtime preview scenario, branch slot, actual bound port and verified build SHA are separate facts.
6. Store cooperative branch leases in the shared Git common directory, not a versioned per-branch file. Serialize claim/renew/release, require holder identity, preserve release history and never steal an expired lease automatically. A same-UID lease is not security or resource admission.
7. Integrate exact READY tips serially in dependency order. Hold experiments that conflict with owner decisions, even when a union branch contains them. Merge without committing, run the required unit/type/static/contract/runtime gates on the merged tree, record input/base/tree SHAs, then commit. On conflict or failure, preserve logs, abort only the owned uncommitted candidate and report to the owning lane. Fixes belong on its feature channel.
7b. In the owner's Verified-OSS-Loop repos (z0intelligence, z0evals and similar), feature PRs target `preview`. Workers don't merge `main`/`master` on their own initiative; an owner request to promote (next section) authorizes it. The `receipt` check (`.github/scripts/check-receipt.py`) needs a fenced yaml block in the PR body containing `issue`, `base_revision`, a `head_revision` equal to the current PR head, and `tests.red` / `tests.green`.
   - **Red:** the PR's new tests run against the base and actually failing.
   - **Green:** those tests passing at the exact head. A pass recorded at an older SHA is rejected.
   - Read the failing run's log (`gh run view <id> --log-failed`, then the lines after `receipt check failed:`) before diagnosing.
   - Never bypass the check, because it is the owner's exact-head-receipt law.
   - Stacked PRs get retargeted to `preview` once the PR below them merges, and the head-dependent receipts are refreshed after any rebase.
8. Rebuild the served artifact at the resulting integration SHA. Bind the requested loopback port without replacing another listener; when the parent already serves a named out directory, rebuild that directory in place and leave its server untouched. Verify exact exported bytes, HTTP and served build identity before claiming the endpoint. Independently authorized content/discovery branches must not inherit an unrelated performance hold: advertise only available routes, preserve fallback links and report withheld-route Lighthouse 404s rather than inventing scores. Hand off any long-running owned server to the parent when operating as a subagent.
9. Preserve the declared measurement contract unless the coordinator explicitly authorizes a versioned method replacement. Headless rAF cadence is not application work or physical refresh proof. For authorized trace-work gates, group main-thread rendering spans by real Chrome frame boundaries and union nested intervals; retain rAF cadence, thread CPU, GPU path and LoAF separately. Use native scripted scrolling: rAF scrollTop writes can themselves force layout after asynchronous image loads. Validate with an intentionally bad control plus repeated interleaved baselines; pin owned descendants to sampled least-busy physical cores or reject overloaded runs. Pinning is not exclusive reservation. If repeatability fails, label timing unqualified, preserve all raw trials and revert unproven production experiments—never retrofit thresholds to pass.
10. Attribute forced layout before changing the renderer. Ordinary traces may retain only an enclosing FunctionCall; preserve every event and run a separate `disabled-by-default-devtools.timeline.stack` diagnostic to resolve the actual getter. Even one scrollTop read before this frame's writes can flush asynchronous image invalidation. Removing the scroll handler or using observer-supplied geometry can eliminate synchronous reads without satisfying the rendering-work gate: keep p95, max, LoAF and repeatability as independent requirements. Static content-visibility grids can increase layout/prepaint costs; measure rather than assuming they are faster. If switching to headless shell, rerun both arms on that exact binary and record executablePath/version/GPU state; historical full-Chrome timing is not a matched baseline.
11. Report current device limitations, denied protected-file edits, unexecuted hosted CI and remaining owner publication actions plainly. Do not route around a denied agent-instruction edit through another tool.

## Consolidate scattered work into RFCs and issue waves

When the owner asks to organize a repository like their other forks, build the working GitHub structure, not just a proposed taxonomy. Use this order:

1. Inventory open and closed issues/PRs, remote branches, registered worktrees, local-only commits, installed artifacts and running services. Read current discussions before classifying ownership. Verify timers with the actual unit/cron registry; a script or standing brief does not prove recurring execution.
2. Create one pinned program index, a small set of direction-owning RFCs, and a pinned START HERE merge-wave tracker. Reuse existing issues as RFCs where their scope already fits. Add bounded follow-up cards only for concrete gaps. Do not create a second scheduler or duplicate the existing queue.
3. Put every branch and PR in a lane with its exact head, base/dependency, wave, evidence and next gate. Give a substantial branch without a PR its own reviewable PR. Distinguish experiment unions from independently valuable code using `git merge-base --is-ancestor` and range diffs; if a consolidated PR contains both source lanes, land it once and close the source PRs as included only after its merge.
4. Order the CI foundation first, independent feature lanes next, cross-lane integrations after them, and bounded follow-ups last. Specify stack retargeting after each lower PR merges. Build `integration/wave-N` from exact input heads with additive merges, and record both conflicts and resolutions in the tracker. Green input PRs do not substitute for checks on the combined tree.
5. Run the pipeline before reporting the structure ready. For a repo shipping a compiled CLI and committed web bundle, cover tests, applicable typechecks, generated-bundle drift, compiled startup and a protocol handshake when implemented. Install dependencies with the pinned runtime and frozen lockfile; upload the binary with a checksum. Keep native-host acceptance and installed-byte qualification separate from CI.
6. Fix failures on their owning feature branches, merge lower-stack fixes upward, and re-integrate. Check source and tests for duplicate declarations after conflict resolution: an automatic hunk choice can retain two independently added copies of the same cache or registration. Never treat `-X theirs` as proof of a semantic union.
7. Link the RFCs, waves and PRs in both directions, apply a small label vocabulary, and update the tracker as work lands. Keep public issues path-redacted and credential-free; retain host-specific evidence in the canonical private store. State the single next owner gate plainly. Do not silently turn organization approval into deployment or upstream publication approval.

### Executing an approved merge wave

- Treat the owner's go-ahead as the wave's approval; record it on the tracker and proceed without asking again for each listed merge. Preserve separately stated gates outside that wave.
- After merging the CI foundation, merge current `main` additively into the remaining PR branches to trigger checks on their current heads. Propagate this through stacks; when the parent lands, retarget its child to `main` and refresh evidence for the changed base.
- Merge with the freshly verified head pinned (`gh pr merge --merge --match-head-commit <sha>` when merge commits preserve the program's ancestry). Re-read remote merged state and check the resulting default-branch SHA before calling the lane complete.
- After an interrupted push, merge or comment write, read the exact remote target before retrying: the remote may have committed the operation before the client died. For pushes compare `git ls-remote` with the local head; for merges read PR state and merge SHA; for comments inspect recent bodies. Retry only the missing effect, preserving additive history and avoiding duplicate posts.
- Before yielding for checks, persist the landed merge SHAs, outstanding PR heads, stack retargets and next gate in the canonical tracker. Treat a failed tracker write as unfinished bookkeeping; verify whether it landed and repair it before claiming the tracker is current. On a check-completion wake, resume from remote state rather than replaying the previous merge commands.
- Read a failed check's actual log before retrying. If a feature lane exposes an existing defect already fixed by an approved prerequisite lane, land the checked prerequisite and merge that foundation into the failing branch; do not weaken the test or rerun until green.
- Require a successful generator command before interpreting an empty diff as no drift. Fail fast (`set -e` or explicit exit checks), ensure the runtime is on the child script's PATH, then inspect the generated output; a missing runtime can leave the tree falsely clean.
- Enable required-check rules only after those named checks have run successfully on the protected branch. Otherwise protection can deadlock every PR waiting for checks that cannot start.
- With a strict (up-to-date) required-checks ruleset, each merge makes the remaining PRs stale: `gh pr update-branch N` then `gh pr merge N --auto --merge`, and merge them one at a time in tracker order. Auto-merge does not update the branch itself.
- GitHub marks a PR merged automatically when its commits land through a consolidating PR; read state before trying to close it as included.

### Fork tracking upstream and community intake

When the owner asks to keep a fork in step with upstream ("ff if it desyncs") or to check others' unmerged PRs and forks, follow `references/fork-upstream-sync-and-intake.md`: sync-state check, ff-else-merge-PR workflow with dispatched checks, fork survey, and `cherry-pick -x` intake PRs.

## Cross-host status and merge prioritization

Use this workflow for “how far did we get,” “latest release worktree,” and “what should merge next,” even when no merge is authorized. Command recipes: `references/cross-host-inventory.md`.

1. Inspect each requested host directly: worktree registry, recent owning conversations, refs, dirty source and local commits beyond remote-tracking tips. Save complete inventories outside the repo; print only relevant source changes and summarized counts, not dependency/cache noise or entire transcripts. State any host coverage gap explicitly.
2. Pin one canonical remote head, then classify candidates as contained, equivalent/reworked, genuinely missing, or unresolved. A worktree named after the release can be stale; choose the continuation base by verified head, not directory name. Preserve uncommitted work and local-only assertion-strengthening commits rather than treating them as disposable test noise.
3. Compare source, running backend, served frontend, installed native artifact and physical acceptance separately. Resolve the actual running process cwd or source path, not just the service's configured directory or current symlink; a repointed symlink does not move an existing process. Check each host's backend independently even when both phone channels serve the same frontend.
4. Verify CI on the canonical merge SHA as well as relevant feature heads. Retrieve the final receipt/counts and formal result; a PR body saying merge CI is pending may be stale. Keep test-suite skips distinct from skipped conditional CI steps.
5. Rank delivery gaps before adding features when verified source has not reached the executing components. Then order genuinely missing changes by user-facing safety, core functionality and dependencies. For each recommendation give its exact commit, readiness/blocker and whether native rebuild/device proof is required. Do not recommend a wholesale divergent-lane merge that would overwrite newer ownership fixes.
6. Lead the report with the canonical head and what is actually usable, then already-landed work, a short ordered next-action list and concrete blockers. Put the exhaustive inventory in the checkpoint. A status audit does not authorize merges, service restarts, cleanup or phone interaction.

## Promote live work to master

Use this section when stable promotion to `main`/`master` is authorized; it must not override an explicit preview/nightly delivery policy. The owner wants the deployed artifact switched to the qualified merged SHA through the repository's PR path, not draft PRs left indefinitely without a concrete next gate. Recipes: `references/owner-repo-promotion.md`.

1. **Find what is live per component** before reading PR state. Then check each component's real gap: `git rev-list --left-right --count origin/master...<live sha>` and `git merge-base --is-ancestor`. A PR whose head is already contained in the live integration branch has landed; it just targets an unused base. Report the gap that matters (integration branch never promoted), not "N draft PRs".
2. **Running is not tested.** Before promoting, check CI on the exact head, compare the deployed release with the branch tip and unpushed commits, and check host drift. Rerun failing test files locally on both master and the head to separate real regressions from CI-environment failures. Fix real regressions on the live branch, redeploy, then promote; don't push a known-red head to master.
3. **Settle unpushed commits first.** Push them if they are already merged into the integration branch locally and no live process has its cwd there; otherwise stop and ask.
4. **Secret-scan the promoted range** on a fresh bare clone; the repos are public. Classify every hit before reporting it.
5. **Promote by the repo's rules.** Fast-forward where `master` is unprotected. Where a ruleset requires a PR and linear history, squash-merge with `--match-head-commit` and verify tree equality. Never bypass a ruleset; it is the owner's explicit constraint.
6. **Redeploy from the merged master SHA** and prove deployed == master file by file, including hash-named families. Run each affected service once and confirm health.
7. **Divergent implementations: analyze, decide, prove. Don't hand the choice back.** The owner explicitly rejected "here are two designs, you pick" as stopping short. When a live branch and master both rewrote the same modules:
   - Find the shared ancestor branch (`git diff <ancestor> <side> -- <file>` per side) and diff top-level functions with `ast` (`only-master / only-branch / changed-both`, and which side still equals the ancestor). Add/add conflicts are often two maturity stages of one design, not rival designs.
   - Measure live use before weighing them: production callers (`git grep` for the function across src/adapters), live ledgers/audit logs, state dirs that would exist if a path ever ran. Code with zero callers or zero live rows can't justify breaking a path that runs.
   - Read the owner's intent docs and issue bodies (#22/#63/#66-style canon) for the tiebreak, then resolve per function: keep the stricter reviewed contract, keep whatever live callers depend on, make new requirements opt-in when today's callers can't supply them, and test both test sets.
   - Prove equivalence against what runs: replay real calls through old and new code (same evidence/locators), read the live data store with the stricter reader, compare CI failures with master's own CI baseline, secret-scan, then merge and redeploy. Report what was chosen and why.
   - **What runs is not the checkout.** Read `/proc/<pid>/environ` (`PYTHONPATH`) and the unit's `Environment=`: the memory MCP ran an unpushed release dir (`memory-mcp-releases/<sha>`) while its cwd checkout was an older SHA. Push such commits and include them before promoting.
8. **Close superseded PRs** with a comment naming the master commit that contains them. Link every PR you merge or open to the session.

## Metrics and tests

Use disposable real Git fixtures for registry coverage, malformed records, drift, detached trees, shared lease collisions and wrong-holder refusals. Record red/green commands. Compute lead-time only as an explicitly defined Git proxy; portable branch creation dates and issue-to-deploy times are unavailable from ordinary refs. Distinguish branch-tip idle age from branch age and fix/revert subject counts from defect or rework rates. Do not claim causal velocity improvement without comparable before/after measurements.
