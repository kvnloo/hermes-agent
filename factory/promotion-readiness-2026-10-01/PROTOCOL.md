# Promotion-readiness protocol (kvnloo/hermes-agent → NousResearch/hermes-agent)

Goal: for each assigned downstream fork PR, decide whether it is worth promoting upstream and, if so, leave a clean, proven, single-commit branch + patch + PR body ready. **Nothing is published.** Output = evidence + verdict.

## Paths
- Blobless bare repo (upstream `main` + fork refs `refs/fork/*`): `S=$S`; repo `$S/h.git`. Refresh main first: `git -C $S/h.git -c credential.helper= fetch -q --filter=blob:none https://github.com/NousResearch/hermes-agent.git +refs/heads/main:refs/heads/main`. Record the main SHA you tested on.
- Your worktrees: `$S/ready/<BATCH>/fork-<N>` via `git -C $S/h.git worktree add --detach <path> main` (remove them when done: `git -C $S/h.git worktree remove --force <path>`).
- Outputs (durable): `D=$ARTIFACTS/promotion-readiness-2026-10-01`; per item write `$D/verdicts/fork-<N>.json`, and for READY items `$D/patches/fork-<N>.patch` (`git format-patch -1 --stdout`) + `$D/patches/fork-<N>.body.md`. Create local branch `ready/fork-<N>-<slug>` in `$S/h.git`.
- Hermes' audit for each item is in your batch JSON (`$D/batches/<BATCH>.json`); full ledger at `~/.hermes/profiles/clean/reports/hermes-upstream-consolidation-20260930/` (DOWNSTREAM_AUDIT.md explains holds and contamination).
- In zsh, quote refspecs: `"main:path"` (unquoted `$VAR:h...` is a zsh modifier).

## Running tests (Python)
`PY=<hermes-home>/hermes-agent/venv/bin/python`. ALWAYS isolate: `HOME=$S/testhome-<BATCH> HERMES_HOME=$S/testhome-<BATCH>/.hermes HERMES_PYTHON=$PY bash scripts/run_tests.sh <test files> -q` from the worktree root (mkdir the testhome first). Run only targeted files (the item's tests + sibling files of the touched module), never the whole suite. ~40 s per file is normal. A failure that also fails on plain `main` is pre-existing: record it, don't chase it.
## Running tests (TypeScript: ui-tui / apps)
In the worktree: `ln -sfn <hermes-home>/hermes-agent/node_modules node_modules; ln -sfn <hermes-home>/hermes-agent/ui-tui/node_modules ui-tui/node_modules` then `cd ui-tui && npx vitest run <files>` and `npm run typecheck`. (Desktop: same pattern with `apps/desktop/node_modules` if present.)

## Hard rules
- No `git push`, no GitHub writes (no PRs/comments/labels/edits), no edits to existing fork branches. `gh` read-only only.
- Never touch the real `~/.hermes`; never run `live`/`integration`-marked tests or anything that spends money or calls external services.
- Never merge a contaminated comparison wholesale. 59 bot leaves carry unrelated `hermes_cli/kanban_db.py` + `tests/hermes_cli/test_kanban_external_receipts.py`: exclude those (and anything else unrelated to the PR's stated claim).
- Respect ownership: if an external contributor has an OPEN upstream PR or claim for the same defect, verdict `EXTERNAL-OWNED` (we support, we don't compete). Do not compete on issue lanes #127373/#127374/#127375/#127332/#127228.

## Per-item procedure
1. **Read** the fork PR (`gh pr view <N> -R kvnloo/hermes-agent --comments`) and its diff (`git -C $S/h.git diff $(git -C $S/h.git merge-base main refs/fork/<head>) refs/fork/<head>`). State the single claim/invariant in one sentence.
2. **Current-main need:** read the cited code on current `main`. If already fixed (by anyone), verdict `SUPERSEDED-ON-MAIN` with the commit/PR that fixed it.
3. **Dedupe/ownership:** search upstream (`gh search prs/issues --repo NousResearch/hermes-agent` state all) for the same symbol/file/issue; check the item's `origin_refs`. Open external PR → `EXTERNAL-OWNED`; our own upstream PR already open/merged → note it.
4. **Rebuild** on a fresh worktree of current `main`: apply only the intended production + test hunks; resolve drift by hand; keep it minimal (AGENTS.md: smallest footprint, extend don't duplicate, no new non-secret env vars, 1–2 behaviour-contract tests, no change-detectors).
5. **Prove:** (a) RED: tests only on `main` → fails for the stated reason (paste the failing assertion); (b) GREEN: with fix → passes; (c) NEGATIVE CONTROL: break the key line of the fix → the test fails again; (d) ADJACENT: sibling test files of the touched module pass (or fail identically on `main`). For docs: quote the doc text and the source lines that contradict it on `main`; for dead-code removal: show zero references on `main` (`git grep -n` across repo incl. tests, plugins, website/docs, string/getattr/monkeypatch uses) and run the tests that import the module.
6. **Package (READY only):** one commit, conventional subject (`fix(scope): ...`), body = why + what; author `Kevin Rajan <7121943+kvnloo@users.noreply.github.com>` (use `git -c user.name=... -c user.email=...`). PR body following `.github/PULL_REQUEST_TEMPLATE.md`, with honest test results and `Refs`/`Fixes` links; delete "For New Skills".

## Verdict JSON (`$D/verdicts/fork-<N>.json`)
`{"fork_pr":N,"title":..., "claim":..., "verdict":"READY|READY-AFTER|NEEDS-REWORK|SUPERSEDED-ON-MAIN|EXTERNAL-OWNED|DUPLICATE-UPSTREAM|NOT-REPRODUCIBLE|HOLD", "main_sha":..., "evidence":{"red":...,"green":...,"negative_control":...,"adjacent":...,"source":...}, "upstream_overlap":[...], "branch":"ready/fork-N-slug"|null, "files":[...], "size":"+a/-d", "depends_on":..., "notes":...}`
READY means: need confirmed on current main, no owner conflict, RED/GREEN/NEGATIVE/ADJACENT all recorded. Anything less is not READY. Be honest about NOT_TESTED boundaries.

## UPDATE (mandatory, applies immediately)
- **Never use `git stash`.** All worktrees share one bare repo and therefore ONE `refs/stash`; stashes have already crossed between batches. Save with `git diff > file`, restore with `git apply file`.
- **/tmp is a 12 GB tmpfs and nearly full.** Create all NEW worktrees under `$ARTIFACTS/promotion-readiness-2026-10-01/wt/<BATCH>/fork-<N>` (same `git -C $S/h.git worktree add --detach <path> main`), prefer sparse checkouts when you only need a subtree, and `git worktree remove --force` each worktree as soon as its item is done. Don't leave node_modules copies (symlink only).
