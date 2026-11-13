---
name: repository-architecture-audits
description: "Use when auditing architecture, lineage, or extraction donors."
version: 1.12.0
metadata:
  hermes:
    tags: [architecture, git, lineage, frontend, extraction, audit]
---

# Repository Architecture Audits

Use this skill for read-only, evidence-backed audits of repository architecture, feature lineage, API boundaries, extraction seams, and multi-worktree donor universes.

## Core rule: distinguish committed evidence from working-tree evidence

When the user asks for **committed** architecture, treat the index/worktree as potentially dirty and untrusted for content evidence. When the user explicitly asks to preserve or extract worktree-only implementation, inspect dirty and untracked state as a separate evidence class, fingerprint it, and recover it before use.

1. Record `git status --short --branch`, HEAD, local/remote refs, and worktrees. Do not clean, stash, checkout, fetch, or modify anything unless explicitly authorized.
2. Read committed files with `git show <ref>:<path>`.
3. Enumerate committed trees with `git ls-tree -r --name-only <ref>`.
4. Use `git log --all --follow -- <path>` for path history, but do not mistake cross-branch hits for ancestry.
5. Prove ancestry separately with `git merge-base`, `git merge-base --is-ancestor`, and `git branch -a --contains <commit>`.
6. Prefer a small script around Git plumbing when inspecting many refs/files; it keeps evidence deterministic and avoids shell pipelines that truncate or mix unrelated output.

## Audit workflow

### Audit a product integration seam under active worktrees

When a narrow product replacement spans identity data, runtime factories/loaders, presentation assets, manifests, and tests while parallel agents are writing:

1. Freeze the requested product cardinality and named identities as explicit invariants before inspecting implementation. “Use official data” does not authorize a lane to expand a four-item replacement into a broader catalog.
2. Trace the reachable production chain end to end: authored/derived data → normalization/types → runtime lookup key → factory or loader → presentation metadata → ship packaging → focused tests. Record absent seams as findings; do not invent an async binary-asset pipeline when the existing synchronous factory seam is smaller and satisfies the requirement.
3. Inventory every active worktree twice: once at audit start and again before reporting. Include tracked and untracked paths. If a lane changes mid-audit, re-read its final diff and label earlier observations stale.
4. Build two overlap matrices: requested seam files versus active owners, and parallel-lane assumptions versus each other. Different lane cardinalities, role taxonomies, asset lists, or shipping policies are integration blockers even when files do not literally overlap.
5. Distinguish collision avoidance from scope correctness. A conflict-free branch that broadens the roster, shipping surface, provenance policy, or runtime architecture still must be redirected rather than cherry-picked wholesale.
6. Prefer additive or existing-seam work in non-owned files. Defer shared-hotspot adapters until the owning wave lands, then manually rebase the smallest hunk instead of replaying a broad patch.
7. In a read-only audit, verify non-mutation while acknowledging concurrent writes: report the final observed HEAD/status and say that moving changes were observed, not authored by the audit. Do not claim identical pre/post status when other agents advanced it.

See `references/live-product-integration-seam-audits.md` for a compact evidence matrix, drift checks, and collision-safe recommendation template.

### Audit renderer and quality-tier architecture

When asked whether several graphics presets genuinely cover broad hardware, treat preset labels as unproven until they map to effective runtime knobs. Trace the complete path from public type and persisted/default selection through bootstrap ordering, renderer construction, environment and shadow state, LOD/asset residency, materials, postprocessing, simulation, frame loop, diagnostics, and performance gates.

1. Build a preset-to-knob matrix. A selector plus a DPR cap is not a full tier system, and caps may collapse to identical behavior at DPR 1.
2. Separate construction-time renderer choices from runtime state and consumer-owned settings. In particular, profile selection applied after scene, asset, texture, or physics construction cannot reduce startup or residency cost.
3. Quantify loader behavior: all-tier fetch versus lazy fetch, cache/clone versus parse-per-instance, resident triangles versus visible triangles, and fixed-distance LOD versus screen-space or profile-aware selection.
4. Compare evidence thresholds to the requested frame budgets and confirm the harness forced each intended preset. One high-end GPU or a 33.3 ms gate cannot establish broad-PC 60–120 FPS support.
5. Re-inventory active worktrees before reporting. Renderer work often collides simultaneously with app/types, environment/materials, models/LOD, physics, styles, and capture tooling; prefer a subsequent single-owner integration lane after donor consumers stabilize.
6. Report effective knobs and absent controls, not only labels, and identify generated showcase code that is present but unreachable from production.

See `references/renderer-quality-tier-audits.md` for the full layer matrix, bootstrap-order test, LOD residency accounting, frame-budget checks, ownership matrix, and report template.

### 1. Establish repository rules and scope

Read repository instruction files and organization docs first. Identify archived/deprecated roots and explicit source-of-truth rules. If the task is read-only, do not run registration, setup, generation, install, build, or test commands that can write state; note why they were skipped. Treat ignored artifacts as mutations too: package managers and test runners commonly create `.venv`, bytecode, caches, coverage data, or generated manifests without appearing in `git status`. If execution is required, use a disposable clone/worktree or isolated temporary directory outside the protected repository. If a command accidentally writes ignored state, remove only artifacts proven to have been created by that command—never blanket-clean or delete potentially pre-existing ignored files—and re-verify tracked worktree/index state.

### 1.1 Audit personal-data and model-learning pipelines

For repositories that claim personal-data ingestion, provenance, dataset generation, local training/serving, evaluation, or continuous learning, audit each stage as a separately reachable boundary. Do not treat source discovery as ingestion, a redaction helper as a dataset builder, schema columns as outcome capture, model-path environment variables as training, or a health endpoint reporting a stub model as serving.

Before running any scanner, migration, test, or “measurement” command, statically inspect it for SQL writes, fixture seeding, report generation, archive mutation, network mutations, service restarts, caches, and temporary artifacts. Names such as `measure`, `smoke`, and `test` are not evidence that a command is read-only. If execution is valuable, redirect every store and output to a disposable fixture environment; otherwise record why execution was skipped.

Build the evidence matrix and draft findings incrementally rather than waiting until every file has been read. Reserve enough tool/session budget to recheck non-mutation and deliver the report; a complete evidence harvest with no final synthesis is an audit failure.

See `references/personal-data-learning-pipeline-audits.md` for the capability-status matrix, minimum provenance contract, control-plane authority boundary, and exact first-slice acceptance template.

### 2. Inventory all plausible app roots

Across relevant refs, find:

- `package.json` and lockfiles
- Vite/Next/Astro/Webpack/VitePress configs
- HTML/JS/TS entrypoints
- server-rendered or static dashboard roots
- product-local apps versus docs/projection surfaces
- archived ancestors

For every candidate root, report the exact entry chain: HTML or framework route → module entry → mounted root component → build config input.

### 3. Identify build and test tooling

Read package scripts and config from the chosen ref. Report exact commands, framework/runtime versions, test runner, offline versus live/contract tests, and whether default tests can silently skip live checks. Distinguish a repository root helper package from actual app build roots.

### 4. Map frontend surfaces and transport contracts

Trace from entrypoints through local imports. Inventory:

- user-visible modes/routes/components
- browser API usage (storage, media, speech, WebSocket/SSE, etc.)
- API clients and endpoint constants
- JSON Schema/OpenAPI/TypeScript contracts
- same-origin BFF/proxy plugins and their upstream services
- direct imports of repository-owned state or generated data

Server plugins colocated with Vite are backend-for-frontend code, not frontend-only code. Treat them as a contract boundary during extraction.

#### Audit claimed parallel runtimes against production wiring

When documentation describes concurrent lanes, workers, meshes, supervisors, or hot-swappable generations, distinguish reusable primitives from the reachable production architecture:

1. Trace the real launcher chain through supervisors, subprocess creation, entrypoints, imports, and transport adapters.
2. Build a stage/concurrency map showing which operations truly overlap, which share locks, which are serialized, and which tasks are detached.
3. Search production code for imports and constructors of every claimed lane/coordinator. A tested module with no production caller is a prototype, not an active subsystem.
4. Inspect release allowlists, manifests, packaging metadata, and installed bundle closure. Exclusion from the production artifact is stronger evidence than README prose.
5. Treat runtime-emitted configuration such as `state: planned`, `not-configured`, or disabled feature flags as explicit implementation-status evidence.
6. Trace cancellation end to end across coroutine cancellation, remote provider interruption, blocking worker threads, HTTP streams, player subprocesses, and supervisor kill deadlines. `asyncio.to_thread` cancellation does not stop the underlying blocking call.
7. Audit resource ownership globally, not only inside the preferred launcher. Compare every service lock, fallback lock, direct supervisor, systemd unit, and recovery path. A safe hot-swap protocol does not protect a recovery path that activates a replacement before proving the failed owner released the resource.
8. Classify observability by sensitivity: transcript-free health, aggregate metrics, content-bearing debug/event logs, and active-generation provenance are separate contracts.
9. Verify that a published mirror can collect tests and assemble its declared runtime from its own tree or declared package dependencies. Do not confuse a monorepo-shaped release builder with a standalone repository.

For a compact worked checklist covering voice-style duplex pipelines, see `references/parallel-runtime-architecture-audits.md`.

#### Audit whether current work is on the critical path

When a repository has repeated autonomous waves and a green ledger, reconstruct the ordered product transaction from its mission, build order, and definition of done. Classify each link as `reachable`, `stub`, `documented-only`, or `unmeasured`; the first non-reachable link is the critical-path boundary. Compare recent path-specific commit churn with that boundary: hardening routing rules, fixtures, serializers, or reports is not forward product progress when ingress wiring, real inference, executor action, outcome capture, or causal evaluation remains missing.

Inspect decisive gates individually rather than trusting top-level green. A skipped product-defining gate, missing verdict receipt, or stub-only latency result cannot support the corresponding product claim. Audit evaluation construction for treatment leakage: one agent authoring both conditions, an intentionally weak baseline, revealing filenames, hand-built enriched output, or document-only judging proves packaging value at most—not learned identity or real executor improvement.

Verify runtime provenance independently of endpoint health. Identify the listener PID, command, cwd, executable, container/service state, source mount or image, and served revision when available. A healthy alternate host process while the expected container is stopped is a provenance gap, not proof of the documented deployment path.

When another agent is actively writing, keep the live checkout read-only. Avoid tests that mutate databases, reports, caches, migrations, or runtime focus; run compile, syntax, and pure probes in a disposable clone, then compare pre/post HEAD and status fingerprints.

See `references/critical-path-execution-audits.md` for the transaction-boundary method, biased-evaluation checks, runtime-provenance checklist, and active-agent-safe verification pattern.

#### Choose the smallest existing UX seam

Before proposing new shell infrastructure, build a surface-capability matrix for the host's existing routes, in-page modes, sidebar contributions, panes, title/status bars, badges, and command surfaces. For each candidate, record discoverability, global visibility, reactive-data support, persistence, and core-file cost.

Prefer a combined pattern when it satisfies both awareness and action with existing seams: a compact global indicator for cross-route awareness plus an in-page mode inside the authoritative product for grouped detail and actions. Avoid creating a second top-level product noun or duplicate state ledger merely because a route contribution is easy. If a sidebar data contract cannot update badges reactively, do not force a sidebar section into a large core component when a live status-bar contribution already exists; request a generic host capability only after the plugin-first version proves the gap.

#### Complementary Hermes product surfaces (state vs scope)

When designing a new Hermes Desktop surface next to Kanban/Projects/Starmap, separate **authorities** before picking UX:

| Surface | Authority | Default seam |
|---------|-----------|--------------|
| Kanban | Project **execution state** (tasks, lanes, workers) | Desktop plugin + `/api/plugins/kanban` + board SQLite |
| Spatial / project docs | Project **scope/knowledge** (PRD, FRD, roadmap, specs, decisions) | Plugin-first page + durable doc store scoped by `projects.db`; layout is projection |
| Projects sidebar | Workspace path grouping | Core sidebar (`app/chat/sidebar/projects/`) |
| Starmap | Learned-profile graph overlay | Core `/starmap` (borrow zoom/pan only) |

Do not fork a second task ledger into the canvas. Link spatial nodes to kanban task IDs / project IDs. Prefer the Kanban plugin SDK pattern (`ROUTES_AREA`, `SIDEBAR_NAV_AREA`, statusbar pill, opt-in `defaultEnabled`) over growing core routes. Donor design may come from zer0 PM tldraw/XYFlow canvas, but Hermes MVP should not assume a full tldraw core transplant. Inventory paths and canvas-as-projection doctrine: `coding-session-continuity` → `references/zeros-product-prior-art-recovery.md`.

Inspect open PRs before recommending files. Distinguish **literal overlap** (same files), **architectural overlap** (old versus current extension seam), and **product overlap** (two competing authorities or inboxes). A plugin-local implementation can eliminate merge conflicts while still conflicting at the product level with an open parallel feature.

### 5. Trace lifecycle and resurfacing semantics end to end

When the requested UI reacts to completed, failed, reviewed, or otherwise terminal work, separate the architectural layers before recommending a seam:

1. **Authoritative workflow state:** trace the mutation function, allowed source states, timestamps, run/attempt records, dependency effects, and cleanup side effects.
2. **Immutable occurrence identity:** find the append-only event or revision that distinguishes repeated occurrences. A task reopened and completed twice usually needs `(scope, event_id)`, not only `task_id`, as the inbox identity.
3. **Delivery state:** identify subscriptions, cursors, claims, retries, and terminal unsubscribe behavior. A delivery cursor is not automatically a user-facing read/dismiss receipt.
4. **Presentation receipt state:** determine whether seen/dismissed state already exists, its user/profile/device scope, and whether it must synchronize. Do not overload workflow transitions such as archive merely to hide a UI item.
5. **Transport:** trace producer → durable event → serializer → REST/WS/SSE/RPC → client. Label process-local lifecycle hooks and synthesized text notifications as internal or lossy unless the client receives a structured contract.

When deriving a minimal recipient port, express the result as an occurrence/control/receipt model rather than copying donor fields:

- key repeatable attention occurrences by durable event/revision identity, not only entity ID or wall-clock time;
- make settlement acknowledge an occurrence baseline so later occurrences reactivate naturally;
- make snooze record both a deadline and the event baseline/generation it suppresses;
- derive timer wake from durable deadline state and early wake from qualifying occurrences after the snooze baseline;
- compare Woke/Done against an occurrence-aware visit receipt. If timestamps are unavoidable, verify that opening an item writes actual visit time or the wake timestamp—not an older entity `updatedAt`.

Prove clearing semantics with one integrated path, not only helper tests: timer/early wake → rendered signal → visit mutation → signal absent. A timer wake with no server event is especially likely to remain uncleared if the receipt writer reuses pre-deadline entity state.

Before adopting an event ID as a durable receipt baseline, audit its entire retention lifecycle: time-based event GC, terminal-task deletion, legacy schema rebuilds that may renumber IDs, and cross-board ID reuse. Either retain the latest qualifying attention occurrence per surviving entity, persist an independent stable generation, or repair/reset receipts transactionally when IDs are rebuilt. Do not add a foreign key from a receipt baseline to an event row that legitimate GC may delete.

For a recipient that already has authoritative tasks and an append-only event log, the smallest synchronized backend seam is usually one receipt/control overlay table in the same scoped database—not a second task ledger. A practical row combines `seen_through`, `settled_through`/`settled_at`, and `snoozed_through`/`snoozed_until`; the board/scope may remain implicit when each board already has its own DB. Add viewer scope only when the host has a real operator identity contract. On a shared board in a single-owner product, a documented global receipt is safer than inventing a profile/device key that silently fragments acknowledgement.

Use command-style mutations (`visit`, `settle`, `unsettle`, `snooze`, `wake`) with explicit occurrence semantics. A settle/snooze action launched from a rendered row should carry the exact occurrence baseline the user saw; the server validates that it belongs to the entity and is not a future/foreign cursor, then acknowledges only through that baseline. Never blindly replace it with the latest event at commit time—a raced event can otherwise be acknowledged unseen. A visit/open action may snapshot current server state when the act of opening itself defines what became visible. Reuse an existing event stream for invalidation when possible; derive timer wake from the deadline so restart safety does not depend on a one-shot timer event.

Choose the read transport by product scope. If the existing board endpoint is single-scope but the requested inbox is explicitly cross-board/cross-workspace, a focused read-only aggregate projection endpoint is justified; it is not a second task ledger as long as all rows and receipts come from the authoritative board databases. Do not force an all-scope inbox through N client-owned board queries merely to avoid one projection route.

Require integrated coverage for repeated completion after settlement, early wake only after post-snooze qualifying events, restart-safe timer wake, visit clearing both timer and early wake, multi-viewer and multi-scope isolation, hard-delete cleanup, event-GC retention, and concurrent event-versus-receipt ordering.

For plugin-based products, distinguish four independently gated layers: core feature/CLI, backend or dashboard extension discovery, runtime plugin enablement, and Desktop/client extension registration. Prove the exact install/enable command from the matching manifest and registry; a directory name or dashboard-only manifest does not prove `plugins enable <name>` is valid. Also verify plugin IDs across namespace-by-construction clients: a differently named frontend extension may be unable to reach the existing backend namespace.

Audit apparently supported states for reachability, not just declaration. A status present in a schema, board column, or dispatcher is dormant if no supported writer can enter it, or if its required runtime asset is absent. Inspect authored source and shipped/generated bundles when either can drift.

See `references/hermes-kanban-desktop-integration.md` for a worked lifecycle/event/receipt audit.

#### Triangulate recently announced UI features

When the user describes a new product feature colloquially, reconstruct it before mapping or copying it:

1. Translate the description into candidate product terms, but keep the user's wording as a hypothesis until first-party evidence names the behavior.
2. Collect exact first-party social posts with date, quote, URL, and media. Treat social-search summaries as discovery leads; validate consequential claims against the direct post and inspect screenshots/video rather than relying on captions.
3. Identify the authoritative repository, read its instructions and license, and anchor the announcement to merged PRs/commits and release/nightly timing.
4. Use PR bodies as a navigation map, then verify the current implementation, contracts, migrations, and tests in source. Later commits may have changed an announced rule.
5. Separate the transferable UX grammar from the donor's data model. Map lifecycle semantics, occurrence identity, receipts, and transports into the recipient architecture before recommending code reuse.
6. Report the product's actual terminology and explicitly resolve near-matches such as dismiss vs. settle, archive vs. acknowledge, or task vs. thread.
7. Build a behavior matrix that keeps **attention signal**, **workflow/lifecycle destination**, **deferral state**, and **presentation receipt** separate. A `Done` badge, persisted settlement, snooze deadline, and visited/dismissed receipt may be four independent states even when a social post compresses them into “done.”
8. Classify every linked PR/issue as merged, open, draft, superseded, or release-contained. Prove shipped availability with ancestry plus release/tag evidence; an open fix or issue diagnosis is not current behavior.
9. Verify “clears on visit/dismiss” end to end: identify the signal timestamp, receipt timestamp, storage scope, and exact comparison. A source comment or screenshot alone does not prove the receipt can clear every wake path.
10. State what media proves narrowly: screenshots establish visible labels/layout, while transitions, persistence, ordering, and automatic resurfacing require source or video evidence.

See `references/t3code-attention-inbox.md` for a worked social-post → PR → source → recipient mapping of Settle, Snooze, Done, and Woke.

### 6. Trace lineage without overclaiming

Build a compact commit timeline from path-specific history plus commit metadata. Verify:

- whether feature-named refs point to distinct commits or merely alias one tip
- whether the richest feature branch is merged into the current integration branch
- whether similarly named branches actually contain the expected UI
- whether newer PM/backend commits touch frontend paths at all

A branch name or commit subject is a clue, not proof. Changed paths and object contents are proof.

#### Exhaustive multi-agent donor-universe audits

When the universe is too large for one pass, freeze one timestamped manifest before delegation and run two independent evidence paths:

1. a deterministic census of every ref, unique tip, registered worktree, reachable commit, dirty path, and harness-store root;
2. read-only reasoning agents assigned explicit non-overlapping members from that frozen manifest.

Never let each agent recompute its own live shard, and never use whole-tree keyword counts as branch-novelty evidence. Validate novelty with tip deltas, blob identities, ancestry, and dirty-path content. Require structured reports with coverage, evidence class, confidence, gaps, and contradictions; ingest completed reports incrementally so a tool/session ceiling cannot strand valid evidence. Inventory unreachable/rescue objects separately because an object ID in a database does not protect it from garbage collection.

See `references/exhaustive-donor-audit-fanout.md` for the 20-agent partition, additive SQLite schema, transcript privacy rules, cross-review protocol, and completion checklist.

### 7. Converge overlapping systems before designing extraction

When several repositories implement overlapping PM, agent-control, review, runtime-observation, or experimentation responsibilities, do not start with a merge plan.

1. Assign each repository or subsystem one role: **authority**, **executor**, **extension/projection**, or **donor/evidence lab**.
2. Build a concern-level authority matrix for tasks/goals, agents/runs, workspaces, approvals, learning, experiments, and observability.
3. Prefer one authoritative product based on its combined persistence, governance, installability, extension seams, user experience, and contributor ecosystem—not kernel elegance alone.
4. Explicitly reject duplicate task ledgers, approval stores, agent registries, and event authorities. Derived telemetry must identify itself as non-authoritative and link back to canonical events.
5. Rank donor ideas by integration leverage: differentiated value, low authority conflict, thin real-data vertical slice, measurable outcome, and reusable framing.
6. If a credible plugin SDK exists, prove the feature as an installable plugin first; request only demonstrated missing host capabilities upstream.
7. Gate code reuse on licenses and provenance. An absent license grants no public redistribution permission, and copyleft-to-permissive copying requires a valid relicensing basis.
8. Require a final decision for each donor family (`COPY`, `REIMPLEMENT`, `EVIDENCE_ONLY`, or `DO_NOT_COPY`). Findings without decisions are not extraction-ready.

See `references/control-plane-convergence-and-open-source-extraction.md` for the authority matrix, plugin-first contribution ladder, license gate, and phased open-source plan.

#### Audit deterministic external controllers against the canonical scheduler

When an external planner, policy engine, or deterministic controller needs tight integration, trace the complete authorization path before proposing an adapter: canonical work item and assignment → compare-and-set checkout/work lock → wake request → queued/claimed run → final budget/dependency/hold checks → adapter invocation → terminal result and lease cleanup. Keep work ownership leases separate from sandbox/environment leases. Distinguish execution adapters, run-bound task bridges, event-driven projections, and compatibility re-exports; they have different authority and credential contracts.

Prove idempotency mechanically. A field named `idempotencyKey` is only correlation metadata unless source also shows durable lookup or uniqueness, transactional serialization, and replay behavior. Resolve full REST paths from the application mount prefix, identify the first potentially billable endpoint, and trace long-lived scoped keys separately from ephemeral run-bound credentials. The smallest safe slice should create/read one canonical item, request one host-owned wake, execute through one adapter, mutate through the run-bound bridge, and observe completion from canonical run/event APIs—without a second queue, task ledger, lease registry, or retry loop.

See `references/deterministic-external-control-plane-audits.md` for the evidence sequence, authority matrix, idempotency tests, Paperclip worked map, and minimal vertical-slice template.

#### Audit context, memory, and learning bridges without creating a second control plane

When an authoritative scheduler delegates context expansion or post-run learning to a memory/identity service, model the bridge as two directional contracts rather than one broad integration:

1. The pre-run context response may enrich executor inputs but must not claim scheduler-owned goals, assignments, approvals, budgets, runs, workspaces, evidence, or disposition. Reject authority fields recursively, including naming aliases.
2. Bind every packet to canonical product/project/run provenance, cap the serialized packet, and confine write paths after realpath/symlink resolution. Missing descendants require nearest-existing-ancestor resolution; broken symlinks fail closed.
3. Enforce lifecycle order mechanically: governance clearance → checkout → context expansion → spawn → durable evidence → durable final disposition → learning. Learning from harness output before authoritative finalization is a control-plane violation.
4. Make final learning replay-safe with a stable run-final key, canonical payload comparison, persist-before-ack semantics, crash/replay tests, bounded summaries, explicit redaction confirmation, receiver-side secret/size validation, evidence references, and a closed outcome enum.
5. Give actionable intake a separate company/project/harness-scoped credential and a closed operation allowlist. Claimed scopes cannot grant assignments, approvals, budgets, merge/publish, or other governed actions.
6. Treat mocked adapter greens as local evidence only. Require a real dual-service gate before declaring the integration merge-ready, and re-run reviews after the final patch because asynchronous reviews may describe stale snapshots.

See `references/context-learning-bridge-contracts.md` for an executable-oracle checklist, adversarial cases, and verification ladder.

### 8. Compute the extraction boundary

Starting from each target frontend entrypoint, calculate the transitive local-import closure. Categorize files into:

1. frontend source and assets to extract
2. shared UI/runtime dependencies to vendor or publish
3. tests and schemas to retain
4. BFF/server implementations to leave behind
5. monorepo state imports or hard-coded links to replace with fetched/configured contracts
6. unrelated product, docs, generated projection, and archive roots to exclude

Record file and physical-line counts as sizing evidence, not as architecture proof.

### 9. Preserve dirty and untracked donor state before extraction

When the task is broader than a committed-only audit and worktree-only implementation may be valuable, treat every registered worktree as a first-class donor. Do not silently apply the committed-object rule to dirty source material.

1. Enumerate `git worktree list --porcelain`; record path, branch/detached state, HEAD, tracked status, and untracked status for every entry.
2. Key cached analysis by immutable HEAD plus a dirty-content fingerprint, not by mutable branch name. Include binary diff bytes and bounded hashes of relevant untracked files.
3. Classify donors from changed-path and runtime evidence. Audited overrides should take precedence over conservative name/path heuristics.
4. Before copying code, create a non-destructive recovery package per selected donor:
   - `git diff --binary --full-index HEAD -- .` for tracked/staged state;
   - a path-safe archive of non-generated, non-sensitive untracked files;
   - a manifest containing source path, branch, HEAD, dirty fingerprint, file hashes, and inventory snapshot ID.
5. Preserve committed reachability separately with a verified Git bundle. Ensure every selected donor HEAD is represented by a bundled ref; registered worktree HEAD refs can preserve detached donor commits.
6. Verify recovery in OS-safe temporary clones: checkout each recorded HEAD, run `git apply --check` on its patch, validate archive member paths and hashes without extraction, and compare source status hashes afterward.
7. Build filtered history from the recovery bundle, not by checking out or rewriting donor worktrees. Filter only the target entrypoints and their transitive local dependency closure, then import the filtered objects under archival refs in the standalone repository.

See `references/dirty-worktree-extraction-recovery.md` for the recovery, verification, and filtered-history pattern.

### 10. Verify non-mutation

Before reporting, confirm no files were created or changed by the audit. If the worktree was already dirty, say so and avoid claiming the entire status is your verification; state whether evidence came from Git objects, fingerprinted working-tree payloads, or both. Compare pre/post status hashes for every protected source repository after recovery and extraction preparation.

## Reporting format

Lead with:

- canonical app root(s)
- best evidence ref/commit
- whether that ref is integrated or divergent
- recommended extraction boundary

Then provide sections for tooling, surfaces, contracts, lineage, exclusions, and inspection status. Use exact paths and full commit hashes where consequential. Clearly label inference versus directly observed evidence.

## Pitfalls

- Do not use the current filesystem content as evidence for a committed-only audit when the worktree is dirty.
- `git log --all --follow` searches histories across refs; it does not prove the shown commit is an ancestor of the selected tip.
- Multiple feature refs can point to the same commit. Report that explicitly rather than inventing separate lineages.
- Static generated dashboards and docs canvases are often projections, not the live product frontend or source of truth.
- A Vite plugin that accesses Git, files, processes, or local services must not be copied into a frontend-only repository unchanged.
- Do not call a proposed-task endpoint a claim/PM mutation unless the server contract proves it.
- Do not equate a completion/unread badge with a persisted settled or archived lifecycle state; trace each selector and mutation independently.
- Do not describe an open/draft PR as shipped, even when its body precisely diagnoses the observed gap. Record it as proposed evidence and check ancestry/release containment.
- Do not infer transitions from a static screenshot: visible `Done`, `Woke`, or `Settled` labels prove presentation, not the trigger, sort movement, persistence, or clearing semantics.
- Do not recommend copying an entire product app when only a control/review MPA entry and its import closure are needed.

## Session references

- `references/zeros-pm-frontend-audit.md` — worked example of a dirty, multi-ref monorepo with a Vite BFF and divergent Control frontend.
- `references/hermes-kanban-desktop-integration.md` — worked lifecycle/event/receipt audit spanning SQLite state, dashboard transports, notification cursors, and Desktop plugin namespaces.
- `references/hermes-continuous-voice-audit.md` — reusable audit pattern for multi-surface continuous voice: capture, endpointing, STT/TTS, full-duplex interruption, wake-word mic leases, concurrency, configuration divergence, and read-only verification.