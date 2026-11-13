---
name: fork-ledger-cleanup
description: Use when cleaning fork branches/PRs against upstream.
---

# Fork ledger cleanup (eval-gated)

Eval-gated deletes, fast-forward merges, model-resolved salvage. Used on kvnloo/hermes-agent 2026-11-03 (1315 branches, 156 PRs, 221 issues). Workspace and scripts: `/mnt/zer0models/hermes-audit/` (README.md there). Public ledger: kvnloo/hermes-agent#701.

## Procedure
1. Full bare mirror outside any shared checkout (`git init --bare`; fetch upstream main to `refs/up/main`, fork heads to `refs/fork/*`). The shared hermes-agent checkouts are partial clones; pushes from them hang. Snapshot every ref+SHA before mutating.
2. Metadata via GraphQL (`gh pr/issue list --state=open`; the local gh wrapper needs `--state=X` with `=`). REST core is often exhausted by other loops.
3. `classify.py`: ANCESTOR / PATCH_EQUIV (`git cherry`) / CLEAN / CONFLICT (`merge-tree --write-tree`) / ORPHAN. Then `landed.py` added-line coverage in upstream main (>=0.95 = landed).
4. Containment: branch tip contained in another surviving branch (`for-each-ref --contains`) = redundant. Stacked lanes (Tern on `feat/tern-omp-parity`) produce many of these.
5. Eval on Avrea (`gh workflow run verify.yml -R kvnloo/fleet-runner`, matrix <=32 shards, scripts via a gist): per branch, its changed tests/ overlaid on upstream main, and on branch merged into main. Red on main + green merged = READY.
6. Deletion rules (only these): ancestor/patch-equivalent/>=95% landed; contained in a surviving branch; source-changing branch whose own tests pass on main. Never: test-only pins (they pass on main by design), branches pushed <48 h ago (active loops), open-PR bases, main. Close an open PR instead of deleting its head, with a comment citing the evidence and SHA.
7. FF: `gh repo sync` for fork main; for clean branches >48 h old, `merge-tree` + `commit-tree` a merge of main and push without force.
8. Salvage conflicts with `salvage.py`: the model returns JSON resolutions per hunk only; the script splices them so code outside hunks is git's own merge; gates = no markers, py_compile, identifiers added by either side still present. Push resolved merges FF, re-eval, revert any still-red ones with lease, delete ones that now pass on main.
9. Rebuild the ledger (`ledger.py`) and post one ledger issue plus one comment on the canonical promotion queue issue. No per-item comments.
10. Reconcile before reporting: diff the pre-audit snapshot against live `git ls-remote --heads` (snapshot stores `refs/fork/<b>`; map to `refs/heads/<b>` first). gone == ledger's deleted count and live total == ledger rows, or fix `ledger.py` and `gh issue edit --body-file` the ledger issue (log the edit in `actions.log`). Report heads that appeared during the audit as unclassified, not as covered.

## Small forks: promote, close, and keep docs sync-friendly
For a fork whose open PRs are agent micro-fixes stacked on an integration branch (kvnloo/hermes-tern shape):
1. Check which open PR heads are already in the integration branch (`git merge-base --is-ancestor <head> <integration>`, plus `git log --grep '#N'` for squash/equivalent integrations). Usually nearly all are.
2. Promotion PR integration → main as a draft with: exact-head check status, the list of contained PRs, and `Closes #N` only for issues a contained PR addresses. Exclude trackers/RFCs and any issue a PR body says it does not fully resolve ("does not resolve", "remains", "follow-up"): list those as left open. Merge it when the owner accepts his preview build; "merge in the changes I've accepted" means the build he runs daily (his preview channel), not every open PR.
3. Fast-forward main by pushing the verified integration SHA (no force, `--no-follow-tags`). GitHub marks only PRs whose base is main as merged; PRs based on stacked branches stay open, so close each with a comment citing the main commit. Issue closing from the PR body lands over a minute or so; re-count before reporting.
4. Delete branches only when fully contained in main/integration and not an open PR head or base; save name+SHA to a JSON file first so any can be restored. Squash-merged PR branches are not ancestors: confirm the PR is merged, then delete.
5. Docs: keep `README.md` byte-identical to upstream except one short note at the top pointing to a fork doc (`FORK.md`), and put fork features, behavior differences, install, branch roles, merge-upstream steps and security additions there. New files never conflict; every edited upstream hunk is a future merge conflict. Rewrite moved text plainly; agent-written fork READMEs tend toward dense hedged prose.

## Resuming an interrupted run
- `actions.log` (one JSON line per mutation, key `act`) is the source of truth for what already happened; count it by `act` before redoing anything.
- `ps -p <pid>` any background job from the cut-off turn; local worktree cleanup can be left running, never re-issue pushes/deletes without checking the log and the remote.
- Unresolved salvage = queue entries with no `salv/logs/<branch_with_underscores>.json`.

## Pitfalls
- Resolver quotas: opencode free models and agy Gemini both hit hard limits mid-run (agy 429 resets in ~110 h). Check `burn-pace --json` first; when all frontier lanes are hard-throttle, stop and leave `salv_resume.sh` for later.
- Concurrent `git merge` in worktrees of one repo with rerere enabled fails silently (no conflicts reported); pass `-c rerere.enabled=false`.
- A whole-file model rewrite (opencode run on the worktree) dropped upstream imports outside the hunks; never let the model edit files directly.
- Test overlay 'RED' with ImportError/no-attribute is often missing-feature (correct red), not drift; decide with the merged run, not the main run.
- `pkill -f 'python3 salvage.py'` also kills the calling shell; kill by PID.
- Derived ledger counts must net out reversals: deletions = delete_branch + PR-closes that deleted the head − restore_branch; salvage pushes − salvage_revert. Otherwise the published summary drifts from the remote by the number of undo actions.
- Classify a branch as test-only (no source paths in its diff vs main) BEFORE applying the passes-on-main delete rule; deleting a pin then restoring it costs a push and a ledger correction.
- Removing many full worktrees is slow; `rm -rf` the dirs then `git worktree prune`, in the background.
