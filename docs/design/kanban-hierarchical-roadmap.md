# ADR: Hierarchical Kanban Roadmap and Evidence-Backed Progression

- Status: proposed
- Date: 2026-08-18
- Decision owners: Hermes Kanban maintainers
- Related: #88571 (compact Kanban information architecture)
- Scope: architecture only; no public issue or implementation in this change

## Decision

Add an optional, generic scope graph beside Hermes Kanban and render a deterministic roadmap projection over the existing task, dependency, run, review, and event truth.

The ordered entity vocabulary is:

`company → portfolio → workstream(client|product|experiment) → project → epic → sprint → board → task → subtask`

This vocabulary is not a required nesting template. Every entity except a root may have one optional parent. Tasks and boards may have one optional primary scope. Missing levels are valid. Task-to-task execution dependencies remain in `task_links`; scope ancestry never gates dispatch.

Hermes Kanban remains the only execution ledger and scheduler. Keel remains the authority for maturity and approval gates. The roadmap is a read projection and cannot complete tasks, approve gates, award authority, or mutate maturity. Optional model narrative is presentation-only, provenance-labelled, and never written back as task or gate truth.

## Why this shape

The current system already has the right execution primitives:

- `tasks` owns lifecycle state, assignee, tenant, optional `project_id`, run pointer, and failure/health fields.
- `task_links` owns parent/child execution dependencies and already supplies progress rollups.
- `task_runs` owns attempts, outcomes, summaries, errors, and heartbeats.
- `task_events` is the append-only execution history consumed by live UIs.
- board metadata owns the optional first-class Project binding and workspace defaults.
- `projects.db` owns per-profile, repo-oriented Projects; it is not a company/portfolio catalog and cannot become shared roadmap authority without breaking profile isolation.
- `tenant` is a free-form task grouping key and soft namespace, not an authorization or hierarchy record.
- each Kanban board DB is a hard isolation boundary. A worker pinned to a board must not enumerate other boards.

The standalone WebUI already exposes a thin FastAPI projection over `kanban_db`; Desktop reuses the same plugin API through the namespace-scoped REST door. The roadmap belongs in that API and both renderers, not in a new app or service.

The bundled achievements plugin is not reusable as roadmap truth. It scans session prose/tool usage into a separate `state.json`, includes volume-driven and lifestyle badges, and has no task/scope/evidence authorization semantics. Reuse its visual badge vocabulary only. Roadmap achievements must be deterministic definitions evaluated from Kanban/Keel evidence; do not import or mutate achievement-plugin unlock state.

## Storage

### Shared scope catalog

Create one root-anchored SQLite metadata catalog, `<shared-hermes-root>/kanban/scopes.db`. It is not a task ledger, event ledger, or scheduler. It contains only hierarchy identity and display metadata shared by board projections.

```sql
CREATE TABLE scope_entities (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN (
    'company','portfolio','workstream','project','epic','sprint','board'
  )),
  subtype TEXT CHECK(subtype IS NULL OR subtype IN ('client','product','experiment')),
  parent_id TEXT REFERENCES scope_entities(id) ON DELETE RESTRICT,
  slug TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  external_ref TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  archived INTEGER NOT NULL DEFAULT 0,
  UNIQUE(parent_id, kind, slug),
  CHECK((kind = 'workstream') OR subtype IS NULL)
);
CREATE INDEX idx_scope_parent ON scope_entities(parent_id, archived, kind);
CREATE UNIQUE INDEX idx_scope_external_ref
  ON scope_entities(external_ref) WHERE external_ref IS NOT NULL;
```

No scope event stream is introduced in v1. CRUD updates `updated_at`; task lifecycle evidence stays in `task_events`. Cycles, self-parenting, and invalid kind order are rejected transactionally. Valid parent kinds are declared in code and in the JSON contract, not inferred lexically.

Why a narrow shared catalog instead of `projects.db` or one board DB:

- `projects.db` is intentionally per-profile and repo-oriented.
- putting the catalog in the default board would make one execution board a hidden authority for all boards.
- duplicating scope rows into every board produces divergent parallel hierarchies.
- the catalog contains context only. Kanban DBs remain the sole place where work and evidence exist.

### Additive board/task references

Add nullable `scope_entity_id TEXT` to every board's `tasks` table through the existing idempotent additive migration. Add nullable `scope_entity_id` to `board.json`. No cross-database foreign key is attempted; writes resolve the scope against `scopes.db` before committing. Reads tolerate deleted/unavailable references as `scope_state: "unresolved"` rather than failing the board.

`project_id`, `tenant`, and `scope_entity_id` coexist:

1. Explicit `scope_entity_id` wins for roadmap placement.
2. Else task `project_id` resolves to a `project` entity whose `external_ref` is `hermes-project:<project_id>`.
3. Else board `scope_entity_id` is inherited for projection only.
4. Else board `project_id` maps as above.
5. Else a non-empty legacy `tenant` appears under a synthetic, read-only `legacy-tenant:<value>` grouping in the current board only.
6. Else the task is `unscoped`.

Synthetic legacy groups are never persisted automatically. A user may explicitly migrate one into a real entity. No task row is rewritten during database migration.

Task/subtask remain tasks. A task with children is not automatically an epic; `task_links` may express execution decomposition independently of scope. UI may label a child task “subtask” when it has a parent, but no second task table is created.

### Migration and rollback

1. Initialize `scopes.db` idempotently.
2. Add nullable `tasks.scope_entity_id` and its partial index to each opened board DB.
3. Extend board metadata defaults with `scope_entity_id: null`.
4. Expose legacy projection fallbacks without writing entity rows.
5. Only explicit create/link actions persist scope entities or references.

Old CLIs and workers ignore the new task column and board JSON field. New readers accept legacy DBs. Clearing references restores pre-feature behavior. Removing `scopes.db` leaves all task/run/event truth intact and renders a recoverable “scope catalog unavailable” state.

## Authorization and isolation

Board remains the hard boundary.

- Worker/tool calls use their environment-pinned board and may resolve only the scope chain attached to that board/task. They cannot list sibling boards or aggregate scopes.
- Existing dashboard auth remains the HTTP/WS gate. V1 has no multi-user ACL and must not imply one.
- Roadmap API receives the set of board slugs the caller is authorized to read. For today’s local dashboard this is all non-archived boards; for board-pinned worker routes it is exactly one.
- Every aggregate is computed after board authorization and task visibility filters. Hidden children contribute neither counts nor denominators. Parent existence never leaks a hidden child count.
- `all` is a server-resolved virtual scope, not an entity row. It aggregates only authorized visible roots.
- Tenant remains a soft filter, never an authorization predicate.
- A reference to an entity outside the caller’s visible board set may return the entity’s breadcrumb only if that entity is attached to a visible record; sibling/child enumeration remains filtered.

## API

Extend the existing Kanban plugin API; do not add a service.

### Catalog

- `GET /scopes?parent_id=&kind=&include_archived=false`
- `POST /scopes`
- `PATCH /scopes/{id}`
- `GET /scopes/{id}/breadcrumb`

Mutations validate kind order, cycles, subtype, stable IDs, and archived-parent rules. Deletion is archive-first; hard deletion is refused while referenced.

### Bindings

- `PATCH /tasks/{id}` accepts `scope_entity_id` (`""` clears).
- board create/patch accepts `scope_entity_id`.
- `/board` adds `scopes`, per-task `scope`, and resolved board breadcrumb without removing tenants/projects.

### Roadmap projection

`GET /roadmap?scope_id=<id|all|unscoped>&window=7d&include_archived=false`

Response follows `docs/design/kanban-hierarchical-roadmap.schema.json`. It includes:

- exact scope and visible child entities;
- status distribution and health;
- transparent momentum components;
- critical dependency path (“quest chain”);
- current external/HITL/trust blockers (“boss gates”);
- Keel maturity projection with evidence references or explicit unavailable/unknown state;
- evidence-backed quality achievements;
- freshness/provenance and warnings.

No N+1 board reads: open each authorized board once, batch tasks/links/runs/events, then aggregate in memory. A 60-second client cache is acceptable; `task_events` invalidates affected roadmap queries. Scope catalog edits invalidate all roadmap breadcrumbs. The response identifies the highest source event ID per board, so staleness is observable.

### Optional narrative

`POST /roadmap/narrative` is explicit and default-off. Request contains a complete deterministic roadmap response plus desired time horizon. The auxiliary model receives the approved roadmap-reporting contract:

- start `Roadmap — <time horizon>`;
- order workstreams by importance with truthful green/yellow/red markers;
- preserve created/queued/running/blocked/reviewed/approved/activated distinctions;
- show critical paths as arrow chains;
- request at most one immediate decision;
- never add task state, approvals, evidence, or metrics not present in input.

Response fields: `text`, `generated_at`, `provider`, `model`, `prompt_contract_version`, `input_projection_hash`, `window`, and `warnings`. It is not cached into task/event/scope truth and is never auto-regenerated.

## Deterministic metrics

All formulas use only authorized visible records and return raw components.

### Status

A scope status is:

1. `blocked` if a visible critical-path item has an active boss gate;
2. `at_risk` if health has any red threshold or Keel reports a failing invariant;
3. `active` if any task is running/ready/review;
4. `complete` only when the selected scope has at least one terminal task, all visible non-archived tasks are done, and no unresolved gate exists;
5. `empty` when it has no visible tasks;
6. `unknown` when required reads fail.

A parent status is recomputed from visible descendant work, not copied from children and not manually editable.

### Momentum

Momentum rewards verified outcomes, not card creation or tool volume.

For each task terminal event in `[window_start, window_end]`, count at most one outcome per task revision:

- completed after independent review: `5`
- completed with passing verification evidence but no independent review: `3`
- accepted Keel maturity gate: `5`
- rollback proof or zero-regression quality achievement: `2`
- reopened/request-changes/rework event: `-2`
- reverted failed gate: `-3`

Contribution is `weight × 0.5^(age_days / half_life_days)`, default half-life 14 days. Scope momentum is the sum, rounded to one decimal. Show `score`, `half_life_days`, `window`, and every component. Created tasks, comments, agent/tool counts, runtime, and raw done-card volume score zero. Changing the window never rewrites history.

### Health

Return measurements, not a worker score:

- `flow`: median cycle time for tasks completed in window and throughput as informational count;
- `wip`: running + review count and optional configured limit;
- `blocked_age`: oldest and median active blocked age;
- `rework_rate`: tasks with request-changes/reopen divided by reviewed tasks;
- `quality_rate`: verified completions divided by terminal completions;
- `stale_runs`: running tasks beyond heartbeat threshold.

Thresholds are named config values included in the response. Health color uses worst active threshold, but raw values are always visible. Never rank agents or scopes.

### Quest chain

Build a DAG from `task_links` limited to visible, non-done tasks. Collapse already-done prerequisites. The critical path is the longest weighted remaining path; task weight is explicit estimate if present, otherwise `1`. Tie-break deterministically by priority descending, creation ascending, then ID. If a cycle is detected, return `state: invalid_graph`, the involved IDs, and no invented path.

### Boss gates and levels

Boss gates are active blockers with `block_kind in (needs_input, capability)` or Keel gates that require external/HITL/trust action. Dependency and transient blocks remain health signals unless Keel classifies them as gates.

Levels come only from Keel’s ordered maturity/invariant response. Roadmap stores no XP and cannot advance a level. When Keel is absent, show `unavailable`, never infer level from done percentages.

### Achievements

V1 definitions are code-declared, evidence-backed, and scope/window aware:

- `independent-review`: completion after a distinct review run/verdict;
- `rollback-proven`: immutable rollback evidence reference accepted by Keel;
- `zero-regression`: N consecutive verified completions with no reopen/revert in the selected window.

Each result includes definition ID/version, state, evidence references, evaluator, and evaluated time. A badge is absent/locked when evidence is missing; prose matching never unlocks it. The existing achievements plugin may render the visual but is not a data source.

## UI plan

Use the current compact board component boundaries and plugin API.

1. Add a square-edged breadcrumb/scope switcher to the Kanban header/titlebar. Desktop shows the current chain and an `All` rollup. Mobile uses a drawer.
2. Add one `Board | Roadmap` segmented toggle beside the title/count. Persist presentation per connection + board; it does not alter server state.
3. Roadmap replaces lanes in the same route. It contains a compact summary strip (`status`, `momentum`, `critical path`, `gates`, `next decision`), one progression rail, and child entity rows/cards.
4. Clicking a status, rail gate, child, or evidence count switches to Board and applies a removable scope/evidence filter.
5. A task card may show one scope badge and one combined gate/achievement marker. Existing diagnostics, assignee, progress, and liveness remain higher priority; hide the scope badge when it merely repeats the selected scope.
6. Mobile at 320–430px: summary cards stack, breadcrumb becomes a scope button/drawer, critical path scrolls internally or wraps by node, and no page-level horizontal overflow is allowed.
7. Preserve Hermes’ dark-green/cream identity, square brutalist geometry, semantic status tones, 44px touch controls, visible focus, reduced-motion behavior, and text alternatives. No rounded SaaS dashboard treatment or celebratory animation.

Standalone WebUI and Desktop may keep separate renderers but must share the API contract, formulas, state semantics, and acceptance fixtures. The existing WebUI is a checked-in bundle; implementation must update its source/build pipeline if available rather than hand-diverging behavior.

## Empty, error, and stale states

- `empty`: “No scoped work in this window”; offer switch to Board or broaden scope. Momentum is `0`, not success.
- `unscoped`: explicit virtual row with count and “Assign scope”; never silently drop tasks.
- `scope_unresolved`: task remains visible with its raw scope ID and repair action.
- `partial`: one or more authorized board reads failed. Return successful children plus board-specific warnings; never show parent complete/healthy.
- `stale`: projection age exceeds 60 seconds or any board’s highest event ID advanced. Keep last data, label age, and offer retry.
- `keel_unavailable`: show maturity and gate authority unavailable; do not infer levels.
- `invalid_graph`: show dependency cycle and suppress quest-chain conclusion.
- `narrative_error`: deterministic roadmap remains intact; narrative panel shows retry/dismiss.
- permission/filter empty is distinct from data empty and must not reveal hidden counts.

## Tests and acceptance

### Storage and migration

- Open pre-feature board DB and metadata; verify no row rewrite and null scope.
- Idempotent catalog/task-column migration under concurrent first-open.
- Reject cycles, invalid parent kinds, bad workstream subtype, archived parent, dangling writes, and hard delete while referenced.
- Removing or corrupting `scopes.db` cannot damage task/run/event truth.
- Legacy tenant/project/board fallbacks resolve in documented precedence without persistence.

### Authorization and aggregation

- Board-pinned caller cannot enumerate or count sibling board entities/tasks.
- `all` rollup contains only authorized visible boards; hidden children affect no denominator.
- Partial board failure cannot produce `complete` or green health.
- Synthetic unscoped and legacy tenant groups do not leak across boards.
- Same fixture produces byte-stable metric components apart from generated timestamps.

### Formula contracts

- Outcome dedupe by task revision; creation/tool volume contributes zero.
- Decay/window boundary and negative rework weights.
- Quality denominator, zero-task behavior, and threshold colors.
- Critical path ties, completed prerequisite collapse, and cycle fail-closed behavior.
- Keel unavailable never yields a maturity level.
- Achievement requires structured evidence and distinct reviewer where specified.

### API and compatibility

- Existing `/board`, create, patch, events WS, CLI, dispatcher, and worker-context tests pass unchanged for unscoped tasks.
- Roadmap schema validation; malformed scope/window returns 400, unauthorized scope returns 404 (not 403 existence leak).
- Batch query budget is bounded by authorized board count, not task count.
- Narrative input hash/provenance is exact; narrative cannot mutate any DB.

### E2E, accessibility, performance, visual

- Desktop and WebUI fixtures at 1280×800 and mobile 320×700 / 430×900.
- Board↔Roadmap toggle, breadcrumb, All, unscoped, rail-to-board filter, keyboard focus return, and stale/error retry.
- No page overflow; 44×44px mobile targets; semantic names; visible focus; WCAG 2.2 AA; reduced motion.
- 1,000 tasks / 100 entities / 10 authorized boards: projection p95 under 250ms warm on developer fixture, no N+1, UI interaction remains responsive.
- Capture before/after screenshots with seeded non-empty data. Assert primary panels are non-empty, labels fit, status is not color-only, and mobile text is readable after phone-width downscale.
- Review the illustrative, non-interactive wireframe and its browser renders; these communicate intent but are not implementation acceptance evidence:
  - `docs/design/kanban-hierarchical-roadmap-wireframe.html`
  - `docs/design/kanban-hierarchical-roadmap-desktop.png` (1280×800)
  - `docs/design/kanban-hierarchical-roadmap-mobile.png` (390×844)

## Non-goals

- no nested dispatchers, entity schedulers, duplicate task tables, or second execution/event ledger;
- no automatic hierarchy creation from names, paths, tenant strings, or task links;
- no worker competition, leaderboards, arbitrary XP, streak pressure, volume rewards, confetti, or hidden failures;
- no Keel authority reimplementation;
- no automatic model narrative or narrative-driven mutation;
- no replacement of Projects, boards, tenants, task dependencies, workflows, or the achievements dashboard;
- no broad Kanban redesign beyond the compact controls above;
- no public issue or implementation in this ADR task.

## Alternatives rejected

- **Bespoke company/portfolio/product/epic tables:** rigid, migration-heavy, duplicates one graph.
- **Encode hierarchy in `task_links`:** confuses context with execution gating and can deadlock dispatch semantics.
- **Use tenant strings:** no stable identity, ancestry, referential integrity, or safe cross-board aggregation.
- **Expand `projects.db`:** wrong profile scope and wrong repo-centric authority.
- **Put all hierarchy in board JSON:** cannot represent shared ancestry safely and invites divergent copies.
- **Use achievements plugin state:** session-volume oriented, separate mutable unlock ledger, insufficient evidence/authorization model.
- **LLM-first summaries:** non-deterministic, unauditable, vulnerable to stale or invented progress.
