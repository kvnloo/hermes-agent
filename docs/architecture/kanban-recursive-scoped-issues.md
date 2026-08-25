# Recursive scoped issues in Hermes Kanban

Status: accepted architecture; first implementation slice described below

## Decision

Hermes Kanban remains the only execution-lifecycle ledger. The existing `tasks` row is the universal issue record; user-facing compatibility keeps the word “task” where changing it would break callers. Every issue has a typed `kind`: `company`, `portfolio`, `product`, `project`, `feature`, `task`, or `defect`. Existing rows migrate to `task`.

Hierarchy and execution dependency are separate relations:

- `tasks.parent_id` is the single recursive containment parent. It affects breadcrumbs and filtering, never dispatcher readiness.
- `task_links` remains the many-to-many execution dependency graph. It continues to gate `todo`/`ready`, claims, handoffs, and descendant invalidation.

A physical board remains the hard dispatch, workspace, attachment, and worker-visibility boundary. The default topology is one board per product. Company boards contain company, portfolio, cross-product, and intake issues. A project gets a separate board only when it needs an independent execution boundary.

A stable reference is `<board-slug>:<issue-id>`. Local APIs may accept an unqualified ID only when a board is already pinned. Cross-board hierarchy is projection-only in this slice: a worker pinned to one board cannot resolve or mutate another board, and no issue row is copied. A later aggregate reader may join qualified references across board databases, but lifecycle mutations must still be sent to the referenced board’s authoritative writer.

Structured identity is stored on issue rows, not inferred from title/body or attributed from board activity. `product_id` is a portable product identity; `project_id` retains its existing Hermes Projects meaning. A board may provide a default product identity, but an explicit issue value wins. Board membership alone is routing and does not prove product attribution.

## Evidence

- Hermes `hermes_cli/kanban_db.py` already makes each board a separate SQLite database and pins dispatcher workers with `HERMES_KANBAN_BOARD`/`HERMES_KANBAN_DB`; `task_links` currently means completion-gating dependency.
- `/workspace/zer0/services/zer0-pm/core/src/lib.rs` and its contract tests use one recursive Issue record, one containment parent, independent typed edges, and fail-closed cycle detection.
- `/workspace/zer0/portfolios/chief-of-staff/company-registry.json` provides portable product IDs and board placement separately.
- `META-ARCHITECTURE-REALIGNMENT.md` and current chief-of-staff repository rules make Kanban the sole lifecycle authority and Paperclip a non-authoritative historical projection.
- The L6 portfolio audit finds that shared board routing is not ownership and that arbitrary central-board activity must not be attributed to every product.

GitHub open-PR/issue inspection was attempted on 2026-08-25 but the local `gh` client had no authentication. No collision claim is made from that failed probe; exact local HEAD at design start was `324a12d712af2ca6e2b310a9c37c76bf497222aa`.

## Migration and compatibility

The migration is additive and idempotent:

1. Add `kind TEXT NOT NULL DEFAULT 'task'`.
2. Add nullable `parent_id TEXT` and `product_id TEXT`.
3. Add indexes for kind, parent, and product filters.
4. Existing rows therefore read as `kind='task'`, root hierarchy, and no product attribution.

No existing `task_links` rows are converted: they remain dependencies, preserving dispatcher behavior. Existing create/list/show/tool/API clients continue to work because new fields have defaults. New writers validate kinds, parent existence, self-parenting, ancestry cycles, and product IDs before mutation. Reparenting is atomic and evented. Archiving or reopening an issue does not rewrite hierarchy; deleting an issue is refused while it has hierarchy children, preventing orphans.

Rollback is code rollback only: older binaries ignore additive columns and indexes. Do not drop columns on rollback; preserving typed identity and hierarchy data is safer than destructive schema reversal.

## Surface contract for the first slice

- DB: typed issue fields, qualified references, hierarchy mutations and subtree reads.
- CLI/tool/API: expose fields without adding a new model tool; extend existing create/list/show contracts.
- Dashboard/Desktop plugin: render kind, product scope, and hierarchy breadcrumb using the existing Kanban plugin route and API namespace; do not create a core Desktop route or another task store.
- Filtering: exact `kind`, `product_id`, and `parent_id` filters are board-local.
- Cross-board references: formatting/parsing is supported; mutation or ambiguous unqualified lookup without a pinned board fails closed.

## Deferred intentionally

A cross-board aggregate projection endpoint, organization registry synchronization, arbitrary typed relation catalogs, multiple containment parents, and board auto-creation are not part of this slice. Each would add authority or migration complexity without being required to prove recursive scoped issues on one authoritative board.
