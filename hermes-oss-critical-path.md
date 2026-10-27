# Hermes OSS critical path — 2026-08-17

## Canonical board / isolation

- Root cause proven: Desktop `kanban-mobile-shell.spec.ts` launched Python with `{...process.env, HERMES_HOME: sandbox}`. A dispatcher worker's inherited `HERMES_KANBAN_DB=/home/kvn/.hermes/kanban/boards/zer0-company/kanban.db` has higher resolution precedence than `HERMES_HOME`, so the fixture seeded the canonical `zer0-company` board at Unix time `1787014905..4907`.
- The incident is larger than the five visible ready cards: read-only DB inspection found 14 `created_by=desktop-e2e` cards, including already triage/review/done/archived fixtures. Evidence was not deleted. Explicit forensic-disposition comments were attached to the five named live cards; no task links exist for those cards.
- Fix in this worktree: `apps/desktop/e2e/fixtures.ts` now strips every inherited `HERMES_KANBAN_*` variable before launching the app. `apps/desktop/e2e/env-isolation.spec.ts` asserts fail-closed behavior for BOARD, DB, HOME, TASK and WORKSPACES_ROOT overrides.
- Verification: `npx playwright test e2e/env-isolation.spec.ts` → 1 passed; `npx tsc -p tsconfig.e2e.json --noEmit` → passed. Whole Desktop typecheck remains red on a pre-existing unrelated `ComposerActionsScope.update` error in `src/app/chat/hooks/use-composer-actions.test.ts:294`.

## Live gateway / activation

- `hermes-gateway.service` is active/running, PID 3436769, since 18:26 CDT; executable `/workspace/hermes-home/hermes-agent/venv/bin/python -m hermes_cli.main gateway run`, cwd `/workspace/hermes-home`.
- Live source HEAD is `c94454a20980da6fb7e73c92771279447a3253db` (`fix(kanban): integrate dispatch health fairness stack`), listening on `127.0.0.1:8642`. This confirms the dispatcher-health stack is activated.
- Live source does not contain the reviewed `/chat pm|brainstorm|copilot` or `/orchestration ...` command implementation. Activation is therefore **not proven / not active at this HEAD**; do not claim otherwise.
- Live checkout has preserved foreign modifications: `plugins/kanban/dashboard/dist/{index.js,style.css}` and untracked `plugins/memory/memory_tencentdb`; untouched.

## Draft PRs

- #88716 `fix(webui): make Kanban usable on mobile`: OPEN, Draft, head `bd3b7baedbe7d48f61a333c5e04c6363dba9ff1d`, branch `fix/webui-kanban-mobile-dashboard`, no reported checks. A private fixture preview listener exists on `127.0.0.1:18765`; this is not Captain validation and not publication readiness.
- #88752 `feat(kanban): add settle, snooze, and wake attention lifecycle`: OPEN, Draft, head `6d5f34c45e9154fa47df6fef6d8866d15176c6fe`, branch `feat/kanban-attention-lifecycle`, no reported checks. No independently certified private Tailnet preview was proven in this run.
- Both must remain Draft until Kevin validates phone UI and code. No upstream push, merge, or public-state mutation was performed.

## Bounded next path

1. Independent review of this E2E isolation patch; then apply the same shared sanitizer to every fixture-side Python subprocess and add DB realpath/inode/marker assertions before any destructive seed.
2. Archive all 14 proven synthetic cards through an operator/API surface that supports archive while preserving their forensic comments/events (worker toolset exposes no archive mutation).
3. Activate the already-reviewed chat/orchestration command commit into the managed live checkout, restart once, and run exact command canaries.
4. Rebuild/restart private previews for exact heads #88716 and #88752; phone smoke at 320/360/390/430 and attach exact-head evidence.
5. Captain validation; only then consider Ready/publication. Factory and unrelated paused work remain paused.
