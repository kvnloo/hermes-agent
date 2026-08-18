# Hold-to-drag review harness

Private, loopback-only browser harness for the exact product commit declared by
`EXACT_COMMIT` in `start.py`.
It exports that commit into a disposable directory, seeds a disposable board, dynamically allocates a loopback port, and records a byte sentinel for the canonical board before startup.

```sh
cd <hermes-agent-worktree>
npm ci --prefix tests/kanban_hold_harness
python tests/kanban_hold_harness/start.py --keep-home --readiness-timeout 120
# In a second shell after live.json appears:
npm --prefix tests/kanban_hold_harness run matrix
```

`live.json` is atomically published only after the complete HTML body and exact assets are ready. It contains the URL, PID, disposable DB/home, exact asset hashes, separate stdout/stderr logs and canonical sentinel. Browser evidence is written under `artifacts/`. The runner instruments the page only with an init script; product assets are exported byte-for-byte from the exact commit. Stop the launcher with Ctrl-C. It rechecks the canonical DB sentinel and never binds a public address or port 8450.

Startup progress identifies backend, HTTP, and asset phases. `--readiness-timeout` controls the total bound. A startup failure removes stale `live.json` and atomically writes `<home>/failure.json` with command/status, logs, process tree, port checks, and asset expectations. Failure homes are never deleted. `--keep-home` always preserves; otherwise cleanup occurs only after the matrix success marker or an explicit `--cleanup-on-exit`.

The matrix intentionally fails closed on the first violated oracle. A failure is review evidence, not permission to weaken the assertion. The reviewer should preserve the output plus the disposable home named by `live.json`.
