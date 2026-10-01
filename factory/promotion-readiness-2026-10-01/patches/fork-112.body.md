## What does this PR do?

When a bulk kill races the reader thread, the completion notification that the CLI/TUI drain delivers says the process exited on its own, when in fact the kill stopped it.

`kill_process` can block in the SIGKILL grace window. Meanwhile the reader thread sees the SIGTERMed exit and finalises the session first. The reader's `_move_to_finished` builds the `completion_queue` notification from `completion_reason="exited"` with no `termination_source`. #112156 (salvaging #111615 for #111598) fixed the durable receipt by saving it again after the kill stamps the session. The queued notification was never corrected. A `kill_all` / CLI `/stop` (`consume_output=False`, so the notification is delivered) therefore reaches the agent as:

```
[IMPORTANT: Background process proc_… exited (exit code -15, SIGTERM).
```

It should say `terminated by kill_all (exit code -15, SIGTERM)`. In a real `Popen` + reader thread + `kill_all` run on current main, 9 of 10 trials got the stale label.

The fix removes the race at its source instead of patching the queue afterwards. Before it signals, `kill_process` records its source on the session (`_kill_source`), and it clears the marker when the call returns. `mark_exited` already lets a kill's stamp win over an observed exit. It now treats an exit observed while a kill is still signalling as that kill (`-15`, `killed`, source), which are the same values `kill_process` stamps afterwards. The reader's receipt and its queued notification carry the kill attribution from the first write. No queue drain/re-put, no reordering, and no new lock nesting. The completion enqueue path calls `_redact_process_result`, which can re-enter `process_registry.get()` (non-reentrant `_lock`) and run `transform_terminal_output` plugin hooks, so it stays outside the registry lock.

## Related Issue

Follow-up to #111598 / #112156: same race, live notification surface.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `tools/process_registry.py`
  - `ProcessSession._kill_source`: private, non-persisted marker. It is set only while `kill_process` is signalling.
  - `ProcessSession.mark_exited`: an exit observed while `_kill_source` is set is recorded as the kill.
  - `ProcessRegistry.kill_process`: sets `_kill_source = source` right before `_signal_kill` and resets it in `finally`. Early returns, an incomplete kill with survivors, and errors all leave no stale marker behind.
- `tests/tools/test_process_registry.py`
  - `test_kill_receipt_rewritten_when_reader_finalises_first`: the reader's first save must now record the kill too. Previously it pinned the stale intermediate `("exited", "", 0)` record.
  - New `test_kill_notification_keeps_kill_attribution_when_reader_finalises_first`: in a deterministic reader-wins race through `kill_process(source="kill_all", consume_output=False)`, `drain_notifications` returns one event with `killed / kill_all / -15` and text containing `terminated by kill_all`.

## How to Test

1. `scripts/run_tests.sh tests/tools/test_process_registry.py -q`
2. RED on current main (`f8489405`) with only the test changes applied:
   - `assert ('exited', '', 0) == ('killed', 'process.kill', -15)`
   - `assert ('exited', '', -15) == ('killed', 'kill_all', -15)`
3. GREEN with the fix: both tests pass. Negative control: deleting only `session._kill_source = source` makes both fail again with the same assertions.
4. Real race, as a throwaway probe that is not committed: 10 trials of `sh -c "sleep 30"`, each with a real reader thread and a real `kill_all`. Main: 9/10 queued notifications read `exited`. With the fix: 10/10 read `killed / kill_all`. Negative control: 10/10 read `exited`.
5. Adjacent files, all green with the fix: `test_process_registry.py`, `test_notify_on_complete.py`, `test_kill_verify_tree_death.py`, `test_persist_on_release.py`, `test_process_checkpoint_readopt.py`, `test_process_registry_list_exit.py`, `test_process_registry_lazy_restore.py`, `test_completed_process_results.py`, `test_zombie_process_cleanup.py`, `test_process_heartbeat.py`, `test_process_wait_clarity.py`, `tests/gateway/test_abandoned_turn_process_cleanup.py`, `tests/gateway/test_completion_delivery.py`, `tests/hermes_cli/test_process_notification_display.py`. Result: 235 passed, 4 skipped (Windows-only), 0 failed.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Not run: only the targeted files listed above.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A (`mark_exited` docstring)
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A. The change is pure in-process state with no new OS calls. The real-Popen probe was POSIX-only and is not committed.
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Real-race probe (10 trials each):

```
main:  TRIALS=10 stale=9  [('exited', ''), ('exited', ''), … ('killed', 'kill_all'), …]
fix:   TRIALS=10 stale=0  [('killed', 'kill_all') × 10]
```
