---
name: hermes-linked-native-reconciliation
description: Use when reconciling linked Hermes PR evidence.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, upstream, evidence, native-tests]
---

# Linked Hermes native reconciliation

## When to Use

Use for owner-preserving multi-PR queue reconciliation and exact-head native evidence replay.

Load upstream-contribution/Hermes gates, hermes-agent and systematic-debugging. Read exact-source root/test guidance.

## Inventory and permissions

- Union shared queue nodes, explicit references, archived receipt references and every authored-open PR. Keep issue/PR, historical-row and artifact populations distinct; deduplicate/count in code.
- Query exact head/base, state, draft, review commit IDs, complete comments/threads, and check suites via `object(oid: headSHA)`. Verify pagination and declared totals.
- Keep empty ACTION_REQUIRED suites: zero jobs is not CI success. A successful review bot or old synthetic merge is not exact-current-head product CI.
- Count drafts and ready PRs separately; never assume drafts evade a cap.
- Keep denied issues read-only through every route. Downstream writes require explicit allowlist, current-head check, exact-payload dedupe and full-body/author readback. An old publication is not new authorization.

## Native execution

- Extract immutable exact-head archives into owned scratch and hash archives. Build fresh dev+test environments with `python -m pm.build_env --source ... --out ... --group dev --group test` under disposable home/runtime roots.
- Reuse an isolated environment only when both pyproject.toml and uv.lock match the build source byte-for-byte.
- Use scripts/run_tests.sh with HERMES_PYTHON, retries zero and bounded timeout. Read-only-bind host root; write only owned scratch, privately bind /tmp and /var/tmp, and unshare network. Bubblewrap normally enables isolated loopback; inspect before changing launchers.
- Archive missing Git metadata may make stock precompile complain while tests continue. Report the warning and actual discovered/executed counts; never report setup failure as behavioral proof.
- Recover historical fixtures byte-identically. Run owner tests separately, layer supplemental tests only in scratch, then restore replaced owner tests. Compare every archive regular file against extracted source and record changed originals.
- Owner and supplemented test counts overlap; do not sum them as unique coverage.
- Inspect the exact runner's help before selecting concurrency flags: current `run_tests_parallel.py` uses `-j`, not `--workers`. Preserve argument/setup failures separately from behavioral RED.
- Bound subprocess groups, not only npm launchers: a timeout that kills npm can leave Vitest workers running. Launch owned gates in new process groups and terminate only that group on timeout.
- Test sandbox worker liveness independently of candidate-only PID fields; record worker/child/grandchild PIDs from the real command. Missing new attributes are not proof of a leaked live worker.
- Test completion notification delivery during the kill grace window as well as after return. Queue replacement can pass owner tests yet duplicate an event already drained by the consumer; preserve unrelated events and redaction as separate controls.

## Tern activity donors

- See `references/tern-activity-rebase.md` when cherry-picking an older Tern activity feature onto a newer parity dock; preserve donor authorship, newer lifecycle owners and behavior tests.

## Snapshot schedule proof

- Establish passing owner/core controls first. Exercise real storage, another writer thread/connection, and official backup/import entry points.
- Use events around original inventory/snapshot functions. Cover publication before inventory, after inventory/before snapshot, and after snapshot. The last case must exclude the later row; do not mistake expected exclusion for loss.
- Record source media presence, snapshot row/reference, archived media, backup return, and restored model-facing content. Repeat with fresh homes and retain witnesses.
- Separate owner implementation credit, prior reviewer findings and new schedule evidence. Supplemental proof is neither a production fix nor recovery of missing originals.
- Limit claims to exercised host/mode; no inferred Windows, live daemon, all backup modes, mainline regression or production frequency.

## Restorable source bundles

- Prove restoration in a separate owned repository; `git bundle verify` alone does not prove a shallow bundle can be cloned. Preserve shallow-boundary metadata as a hashed sidecar, install it in the new repository before `git bundle unbundle`, then reconstruct every base plus tracked patch plus untracked-source archive and compare changed-file hashes. Resolve `git rev-parse --git-path` relative paths against the repository, not the launcher cwd. If boundaries are unavailable, hold the bundle as incomplete rather than claiming an ordinary clone works.

## Output

Produce ranked machine/human ledgers, native receipts, archive-source integrity, exact permitted append readbacks, and parent-only novel existing-carrier payloads. Keep missing original private packets on HOLD even if a separate diagnostic succeeds.
