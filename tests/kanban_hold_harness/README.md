# Hold-to-drag review harness

Private, loopback-only browser harness for exact commit `dc6f0284831c4ef656ececbcc75acdf7c960ff9d`.
It exports that commit into a disposable directory, seeds a disposable board, dynamically allocates a loopback port, and records a byte sentinel for the canonical board before startup.

```sh
cd <hermes-agent-worktree>
npm install --prefix tests/kanban_hold_harness
python tests/kanban_hold_harness/start.py --keep-home
# In a second shell after live.json appears:
npm --prefix tests/kanban_hold_harness run matrix
```

`live.json` contains the URL, PID, disposable DB/home, exact asset hashes, log and canonical sentinel. Browser evidence is written under `artifacts/`. The runner instruments the page only with an init script; product assets are exported byte-for-byte from the exact commit. Stop the launcher with Ctrl-C. It rechecks the canonical DB sentinel and never binds a public address or port 8450.

The matrix intentionally fails closed on the first violated oracle. A failure is review evidence, not permission to weaken the assertion. The reviewer should preserve the output plus the disposable home named by `live.json`.
