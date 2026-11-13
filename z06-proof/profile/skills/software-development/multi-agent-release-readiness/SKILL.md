---
name: multi-agent-release-readiness
description: Converge a busy multi-agent repository into one evidence-backed production release candidate.
version: 1.3.5
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [release, production-readiness, multi-agent, worktrees, verification, orchestration]
---

# Multi-Agent Release Readiness

Use this skill when a repository has many agents, branches, worktrees, continuous loops, dashboards, or competing candidates and the user wants a production-ready release, especially under a short deadline.

The release-window principle is **convergence, not indiscriminate expansion**:

> Stop starting unmeasured work. Select the best existing work. Integrate through one release spine. Verify independently. Park everything that does not improve the candidate.

Do **not** mistake this for a general mandate to minimize the agent factory. For users who intentionally operate through broad creative direction and scarce HITL time, the factory is necessary leverage. The durable objective is to hide orchestration complexity behind a low-friction steering surface while preserving aggressive, isolated, measurable overnight exploration.

The complementary-strength model:

- **Human:** scarce time, broad intent, taste, prioritization, high-value judgment.
- **Agents:** continuous research, parallel reversible attempts, measurement, verification, monitoring, and synthesis.
- **Factory:** converts abundant imperfect attempts into a few evidence-backed decisions, then makes accepted outcomes inheritable.

## 1. Establish live truth first

Before writing or activating a release goal:

1. Check stop-line/pause controls and repository health.
2. Read the authoritative priority and claim stores.
3. Inventory current branches, worktrees, owners, active agents, loops, review gates, and dirty state.
4. Identify which dashboards are projections rather than sources of truth.
5. Inspect existing build, test, browser, security, and release-gate commands.
6. Distinguish current state from stale dashboard snapshots.

Never infer production readiness from commit count, agent count, task status, or a dashboard badge.

## 2. Define an honest overnight outcome

Under a short deadline, target **one production-ready release candidate plus a ship/no-ship pack**, not an unattended deployment unless deployment scope and authority are explicit.

A valid outcome is one of:

- `SHIP`
- `SHIP WITH KNOWN LIMITATIONS`
- `NO-SHIP`

A trusted no-ship verdict is better than an unverified release.

## 3. Write the goal as an operational contract

The goal must include:

- One-sentence objective and deadline
- Exact product/release scope
- Definition of “production-ready”
- Morning/release deliverables
- Mandatory gates
- Critical user journeys
- Harness roles and authority boundaries
- WIP and concurrency caps
- Integration order
- Explicit non-goals
- Stop/no-ship conditions
- Required evidence and rollback plan
- Human decisions reserved for the release owner

If the repository has a claim protocol, register the goal in the authoritative work graph and create its task/claim record before product edits.

## 4. Mandatory gate model

Use gates appropriate to the repository, generally:

### G0 — Control-plane safety

Stop-line authority, clean ownership, no self-certification, and no uncontrolled loop writes.

### G1 — Git/worktree convergence

One declared candidate branch, one integrator, attributable changes, conflict forecasts, and an explicit disposition for every worktree: `merge | keep | park | discard`. Never delete unmerged user work merely to make the inventory look clean.

#### Coherent checkpoint cadence

When the user asks for frequent commits, treat that as a release-safety requirement—not permission for arbitrary snapshots or generated-artifact dumps.

1. Before broad research, delegation, or another product wave, inspect tracked and untracked state and partition it into product code, tests/contracts, reusable tooling, private experiments, and generated evidence.
2. Finish one coherent vertical slice, run its focused tests plus the repository’s required static/build gates, inspect the staged diff and staged modes, then commit it with a descriptive message.
3. Commit again after each independently verified integration slice or before handing a mutable tree to another agent. Do not let many unrelated product/tooling/experiment changes accumulate behind one eventual catch-all commit.
4. Keep private studies, caches, model files, screenshots, traces, and external experiment outputs outside the commit unless the repository explicitly versions that evidence class.
5. A clean-revision evidence gate must bind to the deliberately selected product revision. Never make a meaningless empty/no-op commit or stage unrelated files solely to turn that gate green.
6. If no checkpoint was created, say so plainly in status reporting; agent activity and passing tests are not substitutes for a commit.

### Independent review on a moving dirty candidate

A read-only reviewer may be inspecting the same checkout that another agent is still editing. Treat that as a moving evidence target, not a stable diff:

1. Inventory both tracked and untracked files; `git diff` does not include untracked content, so read or no-index-diff every untracked file explicitly.
2. Fingerprint the reviewed file set before running gates and compare it afterward. If any file changes mid-review, discard stale conclusions, re-read the current diff, and rerun affected checks.
3. Do not let typecheck/lint success override a failing focused test. Inspect whether the fixture actually reaches the state named by the test; an unreachable-path test is still a red candidate gate.
4. For async lifecycle fixes, review cleanup ownership as well as cancellation. A stale callback or `finally` must not clear state owned by a newer operation; require identity/generation guards rather than a shared boolean alone.
5. In review-only scope, do not repair files. Return the requested fail-closed verdict against the final observed fingerprint.

See `references/read-only-moving-diff-review.md` for a compact checklist and lifecycle-race examples.

### G2 — Build/static correctness

Clean-install production builds and canonical type, lint, schema, and unit checks for every release component.

### G3 — Critical journeys

Automated browser or integration coverage of the release’s primary user paths at supported desktop/mobile breakpoints. Include blank-screen, fatal-console-error, navigation, and core-action checks where relevant.

### G4 — Runtime/operational safety

No P0 security, secret, data-loss, destructive-default, unrestricted-control-plane, transient-path, or undocumented dependency risk.

### G5 — Product truthfulness

Fresh commit-scoped evidence; no claims for mocked, unreachable, absent, or worktree-only features; measured performance claims only.

### G6 — Release evidence

Immutable candidate SHA, commands/results, known limitations, rollback, lineage, failure history, and concise ship/no-ship recommendation.

Agents must return `NO-SHIP` rather than silently weakening a mandatory gate.

## 5. Overnight execution waves

1. **Stabilize and select:** freeze inclusion, snapshot state, choose candidate/base/integrator/verifier.
2. **Establish red baseline:** run canonical gates before merging more work; convert failures into atomic blockers.
3. **Integrate proven value:** accept only changes that clear a blocker or improve a mandatory gate.
4. **Heal blockers:** one writer per hotspot; atomic claims; independent verification; bounded retries.
5. **Full verification:** rerun the complete gate on the frozen candidate SHA.
6. **Handoff:** freeze edits and prepare a five-minute decision pack.

Do not leave too little time to rerun the full gate after the final change.

### Bounded-run convergence discipline

Apply the same convergence model even when one agent is repairing one worktree. A large “integration-ready” request can fail operationally if implementation consumes the whole execution budget and leaves a mid-refactor tree for verification.

1. **Resolve the canonical toolchain before broad edits.** Read repository instructions, locate the authoritative root/workspace lockfile, and make the documented focused runner executable first. Do not improvise an isolated workspace install when repository scripts require a root install.
2. **Treat dependency setup as a gate, not background trivia.** If later validation depends on an install still running, restrict parallel work to inspection or a small independently checkable slice. Do not open a cross-file refactor that cannot yet be typechecked.
3. **Converge vertical slices continuously.** Test → implementation → integration → focused test → package typecheck/build. A test file plus partially wired production code is not a completed slice.
4. **Reserve the final quarter of the run for proof and repair.** Canonical tests, build, browser/screenshots where requested, Python or cross-package regressions, diff review, and cleanup are first-class deliverables.
5. **At the first budget warning, freeze expansion.** Finish or roll back the active slice, restore compile consistency, record exact verification state, and avoid starting another subsystem.
6. **Report readiness by the progress truth ladder.** “Implemented but not typechecked” must never be summarized as integration-ready. If interrupted, identify the tree as mid-refactor and list the exact files/commands requiring convergence.

This sequencing does not reduce scope; it prevents a broad task from ending with more unverified surface than it started with.

For a QA-owned lane that must permit canonical product identity/data while continuing to reject private or ripped assets, use `references/policy-boundary-qa-lanes.md`. It provides paired allow/deny fixtures, canonical runtime-oracle checks, sibling-lane red-state rules, and a closure ledger that protects the requested commit.

For a canonical data-producer lane whose sibling adapters/tests/policy gates are expected to remain red temporarily, use `references/canonical-data-producer-lanes.md`. It covers focused API caches, offline byte-deterministic generation, provenance/normalization metadata, owned-vs-integration failure classification, and evidence-based adjudication of reviewer claims.

For inherited finish-or-revert work, use `references/closure-only-repair-pass.md`. It adds a mandatory gate matrix, clean-baseline discipline, profile-safe preference persistence, stage-specific retry proof, and product-truth checks for voice/streaming claims.

### Closure-loop breaker

Repeatedly delegating the same broad “finish everything and verify” prompt after a worker exhausts its tool budget creates an expanding chain of `NOT READY` reports rather than convergence. Treat the first incomplete closure as a decomposition signal:

1. Convert every residual item into a finite gate matrix: exact command, expected evidence, owner, and whether code may change.
2. Separate implementation repair from verification. A verification-only worker must not add features; a repair worker owns one proven red gate.
3. Run cheap deterministic gates first and reserve browser/build/install work for a dedicated closure budget.
4. After two incomplete passes on the same lane, stop re-dispatching the same shape. The integrator must either execute the remaining deterministic gates directly, split them into smaller independent lanes, or present the concrete blocker.
5. Do not let “agent completed” notifications substitute for candidate progress. Count unresolved gates and unverified changed files, not completed workers.
6. If approval policy blocks a temporary verifier, do not mutate product code to satisfy the verifier or loop on equivalent commands. Preserve the blocked evidence, use an already-authorized canonical gate when available, or report the exact approval boundary.
7. Keep user updates outcome-first: `ready`, `not ready because <gate>`, or `blocked by <decision>`. Avoid narrating every temporary server/process lifecycle unless it affects the user-facing candidate.

See `references/tool-budget-closure-loop.md` for a reusable gate ledger and handoff pattern.

### Execution continuity and update cadence

When the user authorizes autonomous or overnight execution, registering a goal, creating a worktree, or writing a plan is **setup—not a stopping point**. If prerequisites are satisfied, launch the first executable wave immediately in the same turn.

Maintain continuity deliberately:

1. After setup, dispatch or begin the first bounded implementation slice; do not end with “the next step is…” while workers are idle.
2. When a background lane completes, reconcile or verify it and start the next unblocked slice unless a real human decision is required.
3. If work must continue beyond the current interactive turn, establish a durable background agent/process/job rather than implying that the chat itself keeps executing after a final response.
4. Send concise progress updates at meaningful state changes: base selected, lanes dispatched, lane verified, candidate integrated, preview ready, blocker found, or human decision needed.
5. Lead each update with the actual candidate worktree state—not task metadata or agent activity—and distinguish lane completion from integration.
6. Never silently alter the declared base, integration sequence, or product baseline. Surface the proposed deviation, its consequences, and wait for approval before acting.
7. If a wrong-base or regressed preview is discovered, stop extending it; remove or quarantine it as directed, recreate the integration spine from the agreed base, and only re-share after parity verification.

A final response should either deliver a completed result, request an unavoidable decision, or report that durable execution has been launched. “Plan created” is not completion when the user asked the factory to keep working.

### Stable HITL preview contract

Treat a phone/HITL preview as a release artifact, not as a convenient URL to whichever dev server is already running.

1. **Never expose the same hot worktree that autonomous agents are actively editing.** Vite/HMR or equivalent watchers will reload the human's phone during review, invalidate pinned state, and make controls appear broken or unresponsive.
2. Serve HITL from a frozen candidate snapshot, dedicated preview worktree, or paused-write integration revision. If APIs require a live dev server, preserve the frozen source/runtime identity rather than falling back to a static mock.
3. Record and display the exact preview revision, worktree, branch, dirty fingerprint, launch ID, route, and service ownership. The preview's runtime identity must match the artifact identity accepted by Review.
4. Gate invitation to the human on preview stability: HTTPS 200, no reload loop, HMR/WebSocket stability if enabled, service APIs connected, candidate provenance aligned, and the target control enabled.
5. Exercise the exact user action before sharing the link. For annotation/voice controls, pin a valid Review Session, verify artifact alignment, click the control, and confirm input reaches persistence—not merely that the page renders.
6. Disabled HITL controls must explain the unmet prerequisite in visible copy. Do not leave a pen/mic button looking inert while Review is connecting, unpinned, drifted, or provenance-blocked.
7. Keep autonomous writers off the preview source until the review window closes. New work continues in donor lanes and is promoted into a new frozen preview generation only after verification.
8. If the user reports reloads or inert controls, stop asking them to retry. Reproduce against the exact phone URL, inspect service/provenance state, and stabilize the preview before returning it.

### Fixed-port runtime ownership preflight

A strict port can already be occupied by a healthy **wrong-worktree** server. A hashed production asset and HTTP 200 prove build mode, not candidate identity. Before every browser or production-preview gate on a fixed port:

1. Resolve the listener PID, parent PID, command line, launch time, and working tree before stopping or trusting it.
2. Compare the served entry-script hash/name and canonical runtime identity markers against the candidate's freshly built `dist`; do not accept `productionBuild: true` alone.
3. Stop an existing listener only after identifying its owner, then launch the candidate server from the declared integration worktree and verify readiness again.
4. Pass the exact URL explicitly to the harness and record port, PID, worktree, branch/HEAD, dirty fingerprint, and served asset hash in evidence.
5. If a functional loop passes from a dirty candidate but the harness correctly fails revision cleanliness, keep that failure red. Report the result as **functional integration evidence**, not revision-bound release evidence; never weaken or bypass the clean-revision gate to manufacture green.

Use `references/stable-hitl-preview.md` for the pre-share gate and a root-cause workflow for reload/inert-control reports.

### Plan-change gate

Treat the agreed integration plan as a change-controlled artifact, especially its base branch, product baseline, merge sequence, ownership model, and preview target.

Before any action that deviates from it:

1. Quote the existing decision in one line.
2. State the proposed deviation and why it appears necessary.
3. Show the user-visible consequence, including visual/product regression risk.
4. Offer the least-destructive alternative.
5. Obtain explicit approval before creating the divergent worktree or sharing its preview.

Do not silently reinterpret a safety rule into a product decision. For example, “do not develop in a dirty worktree” means create isolation from the selected baseline; it does not mean replace that baseline with `main`. If implementation reveals that the declared plan is impossible, stop at the decision boundary rather than making an unannounced substitution.

After creating the candidate worktree, immediately assert and report its exact source ref and commit. Before sharing a preview, compare its visible shell and critical journeys against the agreed baseline. A mechanics proof on another base may be useful, but must be labeled as an experiment and never presented as the planned candidate.

### Moving-baseline drift

A branch name is not a durable baseline. Another harness may advance the selected product branch after the integration worktree was created.

1. Record both the selected source ref and resolved commit when the user approves the baseline.
2. Monitor that source ref before each integration wave and before preview handoff; report when its head advances.
3. Do not silently rebase, merge, or call the older snapshot “current `<branch>`.” Ask whether the contract means the pinned commit or the newly advanced branch head when the difference affects visible product state.
4. Build a compact drift report: old/new commit, changed product surfaces, candidate overlap, and visual parity risk.
5. Continue isolated donor work while awaiting a taste decision, but do not mutate the canonical spine across the unresolved baseline boundary.

This prevents a technically correct worktree from becoming a stale product baseline while parallel agents continue advancing the named branch.

### Harness ingress integration under active agent work

When wiring an intent/context gateway into a coding harness while another agent owns the live checkout, treat **context delivery** as a contract to prove—not an assumption based on a hook event existing.

1. Pin a separate worktree to an observed commit and recheck whether the active branch advances during implementation; never chase the moving branch by silently rebasing.
2. Read the installed harness documentation for the exact lifecycle event and output semantics, then run a disposable unique-token probe that proves hook output actually reaches model context.
3. A hook firing is not evidence of injection. If the event is passive or output is ignored, use a verified launcher, SDK, or MCP seam and state whether it covers only the initial prompt or every turn.
4. Build one traceable transaction: prompt → expand → packet validation → provenance-bound context → harness → outcome/learn. Carry one immutable trace ID end to end and fail closed on invalid expansion or missing outcome persistence.
5. Keep evidence honest: process exit is not task completion, correction count, or product success. Label isolated HTTP/subprocess coverage separately from live shared-runtime proof.

See `references/harness-ingress-tracer.md` for the disposable probe, isolated-worktree pattern, minimum provenance, and ad-hoc focused verification gate.

When the harness ingress spans an authoritative work/governance control plane and a separate context/memory/learning service, use `references/cross-service-control-plane-contracts.md`. It pins the authority matrix, transaction ordering, provenance envelopes, realpath/symlink confinement, intake-only scoped auth, replay-safe promotion, adversarial contract-oracle cases, and the distinction between mocked adapter green and dual-service readiness.

## 6. Harness topology

Separate authority:

- **Planner:** decomposition, ordering, inclusion freeze, WIP caps; no product implementation.
- **Scouts:** inspect and reduce uncertainty; no product writes without a claim.
- **Workers:** one atomic task in an isolated branch/worktree.
- **Verifier:** independent evidence; workers do not self-certify.
- **Integrator:** sole writer to the candidate branch.
- **Reconciler:** projections and drift detection only.
- **Human/release owner:** final ship/no-ship, sacred gates, destructive operations, external deployment.

Scale workers only when verification and integration queues can absorb more output.

### Worktree selection when existing work is dirty

Never solve a crowded repository by committing every dirty checkout or bulk-merging every worktree.

**The declared product baseline is a contract, not an implementation detail.** Before creating the integration worktree, state the exact base branch/ref, commit, visible product state, and dirty-state policy. If the user chose a polished feature branch as the baseline, create the clean worktree from that branch's committed head—not from `main`. “Do not develop in a dirty worktree” means isolate from that baseline; it does not authorize silently substituting an older clean base.

Any proposed base change, visual regression, or departure from the agreed integration sequence must be surfaced before acting and requires explicit user approval. Repository cleanliness is subordinate to preserving the selected product state.

1. Reconfirm the declared release/product base and resolve it to a commit.
2. Capture baseline screenshots or journeys for parity checks.
3. Create a clean integration worktree from that exact base commit.
4. Treat dirty worktrees as **source candidates**, not integration spines; snapshot their diffs non-destructively when needed.
5. Measure branch divergence and partition dirty changes into coherent functional slices.
6. Use structural/AST impact analysis before porting runtime symbols.
7. Cherry-pick clean commits or apply reviewed patches slice-by-slice.
8. Verify each admitted slice independently and record provenance.
9. Preserve unrelated or ambiguous user/agent work; do not normalize it into a catch-all commit.
10. Before sharing a preview, compare it against the declared baseline and confirm both visual parity and intended new behavior.
11. When completed donors are dirty but share the declared base, admit tracked hunks path-by-path and copy only explicitly reviewed untracked source/tests/contracts. Exclude donor claim/NOW churn, caches, generated dependencies, and build output unless orchestration reconciliation is itself in scope.
12. Rerun every donor's focused tests on the combined integration spine; lane-green evidence is provenance, not candidate-green evidence.
13. For contextual navigation, capture prior → pushed target → browser Back as machine-readable history/URL state plus screenshots. If rendering is deterministic, hash prior/restored captures to prove exact visual restoration.
14. Before reporting exact paths, remove temporary dependency symlinks/install scaffolding and separate product payload from pre-existing or required integration-spine metadata.
15. Treat worktree creation and integration as separate side effects. `git worktree add <target>` does not change the caller's directory; run the next commit/merge/cherry-pick in a separate tool call with `workdir=<target>` or explicit `git -C <target>`, after asserting target root, branch, and base HEAD.
16. Before committing a parent checkout that contains nested worktrees, inspect staged modes for accidental `160000` gitlinks. Ignore the worktree root before creation and stage explicit paths instead of broad `git add .`.
17. After the first integration mutation, re-read branch, HEAD, and status in both the integration target and original checkout. An unexpected branch name in commit output is a hard stop, not a cosmetic anomaly.

For exact commands, gitlink detection, and recovery boundaries, see `references/worktree-side-effect-safety.md`.

A mechanics-only proof built on an older base must be labeled as such and must not be presented as the integrated candidate. Likewise, a contextual shell that reaches a designed loading state must not be described as a fully live downstream artifact. This retains valuable work without laundering mixed provenance, regressing the product, or making diagnosis impossible.

Use `references/integration-base-contract.md` as the pre-worktree and pre-preview checklist. For a concrete path-selective workflow covering dirty verified donor lanes, overlap reconciliation, candidate-side retesting, isolated browser proof, and exact-path reporting, see `references/selective-dirty-donor-integration.md`. When provider/data, runtime/consumer, and QA/policy lanes own different parts of one identifier schema, run the executable set-join and coverage workflow in `references/cross-lane-schema-join-gates.md` before broad tests; independently green lanes can still disagree semantically. When the donor universe is too large or dirty to reason about repeatedly, use `references/forensic-worktree-inventory.md` to build a content-addressed SQLite inventory and selectively pin GitNexus graphs without mutating donor work.

## 7. Human steering surface

When the user wants to steer broad creative work from a phone or voice interface, the dashboard is not optional polish; it is the factory's human control loop.

Optimize for:

```text
one glance → one informed decision → deterministic propagation
```

A decision object should bind:

- task/goal and requested decision
- exact candidate worktree, branch, commit, and dirty-state fingerprint
- launchable product route/state/viewport
- automated verification and risk summary
- guided review criteria at selectable density
- embedded screenshots, recordings, logs, and comparisons
- timestamped voice transcript tied to the active criterion and recording
- approve / needs-work / optional / reject / defer verdict
- resulting task, correction, integration, and learning transitions

Do not force the human to reconstruct context across links. Links are drill-down; common-path evidence belongs in the review surface.

### Observability surfaces are navigation, not decoration

Treat fleet dashboards, Live Pulse panels, status tiles, counts, and data rows as entry points into trusted state:

1. Every material agent, task, worktree, run, loop, session, event, count, and status should be an explicit interactive control or clearly styled as non-actionable. Never make dead metrics look tappable.
2. A detail destination must show identity, current state, source API/store, freshness/staleness, provenance, recent history, owning task/worktree/process, verification evidence, and safe raw-source links.
3. Preserve the existing product shell. Reuse one desktop/mobile inspector and one coordinator/overlay model instead of creating parallel detail UIs.
4. Contextual navigation must push one detail state; Back pops exactly one state and restores the prior dashboard root, scroll/filter/view, and URL/history state.
5. Live process telemetry and canonical task/session projections are different evidence classes. Label source and fallback explicitly rather than blending them into one count.
6. Polling must expose loading, stale, disconnected, and error states; a last-known value without freshness is not transparent.
7. Redact credentials, private paths, unsafe command lines, and sensitive raw payloads at the server boundary while preserving enough provenance to debug.
8. Before claiming parity with an older dashboard, build an interaction matrix from the older implementation: visible datum → source/freshness → click target → detail content → Back behavior. Byte-equivalent current components do not prove parity if the richer behavior lived on another lineage.
9. Verify with exact click-through browser journeys on desktop and phone, including nested inspector coexistence and contextual Back—not only component rendering.
10. Make browser fixtures contract-valid and fail-closed: assert expected API interceptions and exact nonzero fixture cardinalities before iterating rows. Disable or intercept fallback endpoints so a rejected fixture cannot silently substitute mutable live data. A loop over zero rows is not a pass.
11. Treat the last visual CSS edit as invalidating prior browser evidence. Rerun populated desktop and supported mobile journeys after final CSS, then inspect fresh screenshots; measured non-overlap does not overrule a visible collision.
12. Work in vertical tracer bullets and compile after the first integrated root view. Do not spend the full execution window building a broad pure model and uncompiled JSX/CSS/history rewrite; one end-to-end root → list → detail → Back slice must build and run before expanding every entity class.

See `references/observability-drilldown-contract.md` for the interaction matrix, API/freshness rules, and regression checklist. See `references/deterministic-observability-fixtures.md` for schema-valid fixture setup, exact-cardinality assertions, fallback isolation, canonical event-detail proof, and final-CSS rerun rules.

The first implementation target should be one real vertical transaction:

```text
candidate → independent verification → exact preview → guided recorded voice review
→ reviewer-confirmed structured verdict → immutable receipt
→ idempotent authoritative task/NOW transition → producing-harness correction event
→ corrected candidate → final approval → integration receipt
```

For needs-work, treat transcript and annotations as unbound candidate evidence until the reviewer explicitly selects exact refs and confirms editable finding text, severity, blocking disposition, criterion, and candidate provenance. Reject stale provenance and conflicting retries. Preview all side effects, and keep merge/auto-approval explicitly prohibited. Preserve approve and defer without silently turning either into integration authority.

Extend an existing dashboard/review-session model before inventing another control plane.

### Specialist autoresearch loop safety

When separate autonomous loops optimize different product faces—such as performance and cinematic quality—treat them as competing specialist lanes, not release candidates:

1. Use one committed orchestration contract and one identity-verified branch/worktree per objective.
2. Give every loop a target metric/preset and a guard metric/preset for the other product face; missing guard evidence is a hard failure.
3. Re-baseline the current accepted HEAD before every harness invocation when the harness forgets its best score across restarts.
4. Inspect upstream KEEP/REVERT ordering. If allowlist validation happens before a tool-capable evaluator and the harness later runs `git add -A`, fingerprint and re-check the repository after evaluation so judge/evaluator edits cannot bypass scope.
5. Prefer a disposable-clone OS sandbox for proposal agents over trying to fingerprint every same-user Git mutation. Keep the real worktree, common Git metadata, and baseline read-only; independently enumerate allowlisted regular files and import only validated deltas.
6. Reject ignored-source injection, repository-policy changes, symlinks, sandbox commits/staging, and newly introduced capture/debug/URL/environment-conditioned behavior. Prove both benign import and adversarial rejection with disposable fixtures.
7. Bound judge scores by strict type/range validation, run tool-capable judges from ignored scratch space, and reject mixed-provenance changes.
8. Derive outer process timeouts from the loop budget and terminate complete process groups; detached capture/dev servers need signal cleanup.
9. Route cinematic and performance evidence through the same normalized shot serializer, including setup-function identity, so integrity checks are strict without becoming permanently mismatched.
10. Keep specialist wins local until a balanced/integration evaluator or HITL review proves the combined preset contract.

Use `references/autoresearch-specialist-loops.md` for the full topology, restart-safe baseline protocol, evaluator/allowlist defenses, process cleanup, and verification checklist.

## 8. WIP controls

Recommended defaults:

- One release candidate branch
- One integrator
- One writer per hotspot
- One active blocker per implementation lane
- No tournament without baseline, primary metric, hard gate, and integration slot
- Stop dispatch when executed-but-unverified inventory grows
- Stop candidate generation when integration blocks
- Do not attach agents when host/capacity policy is red

## 9. Compounding overnight metabolism

The factory compounds only when a cycle outputs more than code. Every accepted cycle should improve the next cycle through tests, rubrics, skills, taste preferences, routing evidence, decomposition lessons, and compact failed-approach memory.

Use bounded cadence rather than one giant overnight prompt:

- **10–15m observe:** completions, stalls, collisions, dead claims, drift.
- **30–45m select:** compare evidence, kill dominated variants, promote finalists, adjust capacity.
- **60–90m inherit:** extract tests/skills/preferences, update routing evidence, re-decompose repeated failures.
- **2–3h re-steer:** test alignment with the overnight goal; move capacity from generation to verification when inventory grows.
- **Pre-wake converge:** stop broad exploration, freeze finalists, rerun gates, assemble exact previews/recordings, and compress to at most a few high-value decisions.

A failed attempt is useful only if it leaves a disproven hypothesis, regression test, better rubric, smaller decomposition, routing update, discovered dependency, or clearer human question. Otherwise its generating strategy should lose budget.

Primary optimization target:

```text
verified product progress / (human attention × wall-clock time)
```

Do not optimize raw agent, branch, commit, token, or attempt counts.

For a concrete review-session object, voice-feedback compiler, S Pen/annotation evidence model, phone command relay, contextual navigation stack, harness-agnostic conversation runtime, network-effect flywheel, and overnight cadence, read `references/human-steered-compounding-factory.md`.

### Local voice substrate

For guided phone review, preserve browser Web Speech as a fallback but prefer a local, session-aware STT/TTS path when available. Reuse installed services before adding frontend dependencies; keep ML runtimes behind narrow APIs. Validate with a real TTS→STT roundtrip before wiring UI, then bind transcript segments to the active candidate, criterion, and recording timestamp. See `references/local-voice-review-runtime.md` for environment repair, smoke-test, security, and verification patterns.

## 10. Evidence discipline

A release work unit is not closed without:

- Lane/harness identity
- Base and result revision
- Diff scope
- Acceptance commands
- Verification result
- Metric before/after when applicable
- Evidence artifact
- Integration outcome
- Human decisions consumed

Unknown values may remain unknown. Empty “success” records do not count.

Only integrated, independently verified outcomes should update durable skills, routing policy, or evolutionary scores.

### Progress truth ladder

When the user asks for an update, report each layer separately instead of blending architectural work with product progress:

1. **designed** — plan or research exists;
2. **dispatched** — a worker is active;
3. **implemented in a lane** — files exist in an isolated worktree;
4. **lane-verified** — focused checks passed in that worktree;
5. **integrated** — reviewed changes are present on the declared candidate spine;
6. **candidate-verified** — checks were rerun after integration;
7. **previewable** — provide the exact candidate URL and identify what it contains;
8. **committed/promoted** — only when actually authorized and performed.

Lead with the state of the actual integration worktree. Say explicitly when a preview still shows an older candidate, and never present agent activity, task metadata, or a standalone service probe as golden-slice completion.

## 11. Verification after editing orchestration metadata

When changing YAML work graphs and Markdown task frontmatter:

1. Parse both with a YAML parser.
2. Assert the goal ID is unique.
3. Assert critical fields agree across representations (`id`, `status`, `owner`, deadline, spec pointer).
4. Assert the referenced task file exists and required sections are present.
5. Run the repository’s work-graph validator.
6. Run `git diff --check` on changed files.

Use a temporary `tempfile`-created script under `/tmp` when no canonical focused test exists, then remove it. Report this explicitly as **ad-hoc targeted verification**, not suite green.

### Pitfall: YAML timestamp type drift

Quoted and unquoted ISO timestamps can parse as different types. Keep cross-file deadline/timestamp representations consistent, preferably quoted strings when schema expectations are string-valued. A text comparison alone will miss this; parse and compare typed values.

## 12. Anti-patterns

- Treating many `do_this_now` items as parallel priority
- Creating another queue/control plane during a release window
- Building dashboard polish before trusted state transitions
- Spawning more variants while integration inventory grows
- Calling builds green while core journeys are untested
- Treating an HTTP-ready default port as proof that the newly spawned candidate server owns it
- Reporting deterministic fixture browser evidence as a live runtime API smoke
- Letting workers mark their own output verified
- Deleting worktrees without preserving unmerged user work
- Updating learning/gene scores from unintegrated candidates
- Claiming “production-ready” without rollback and provenance
- Confusing targeted metadata verification with product-suite verification

## Reference

See `references/overnight-goal-pattern.md` for a condensed example structure and review checklist derived from a real multi-agent repository convergence exercise.
