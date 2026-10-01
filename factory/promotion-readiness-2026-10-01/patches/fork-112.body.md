## What does this PR do?

When a bulk kill races the reader thread, the completion notification that the CLI/TUI drain delivers says the process exited on its own, when in fact the kill stopped it.

`kill_process` can block in the SIGKILL grace window. Meanwhile the reader thread sees the SIGTERMed exit and finalises the session first. The reader's `_move_to_finished` builds the `completion_queue` notification from `completion_reason="exited"` with no `termination_source`. #112156 (salvaging #111615 for #111598) fixed the durable receipt by saving it again after the kill stamps the session. The queued notification was never corrected. A `kill_all` / CLI `/stop` (`consume_output=False`, so the notification is delivered) therefore reaches the agent as:

```
[IMPORTANT: Background process proc_… exited (exit code -15, SIGTERM).
```

It should say `terminated by kill_all (exit code -15, SIGTERM)` (`terminated by cli.stop` for `/stop`). In a real `Popen` + reader thread + `kill_all` run on main at `f8489405`, 9 of 10 trials got the stale label.

The fix removes the race at its source instead of patching the queue afterwards. Before it signals, `kill_process` records its source on the session (`_kill_source`), and it clears the marker when the call returns. `mark_exited` already lets a kill's stamp win over an observed exit. It now treats an exit observed while a kill is in progress as that kill (`-15`, `killed`, source), which are the same values `kill_process` stamps afterwards. The reader's receipt and its queued notification carry the kill attribution from the first write. No queue drain/re-put, no reordering, and no new lock nesting. The completion enqueue path calls `_redact_process_result`, which can re-enter `process_registry.get()` (non-reentrant `_lock`) and run `transform_terminal_output` plugin hooks, so it stays outside the registry lock.

## Related Issue

Follow-up to #112156, which fixed the durable-receipt half of the secondary bug in #111598 ("kill is recorded as `exited`"). The queued completion notification has the same race and is not covered by an existing issue.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `tools/process_registry.py`
  - `ProcessSession._kill_source`: private, non-persisted marker, set from just before `_signal_kill` until `kill_process` returns.
  - `ProcessSession.mark_exited`: an exit observed while `_kill_source` is set is recorded as the kill.
  - `ProcessRegistry.kill_process`: sets `_kill_source = source` right before `_signal_kill` and resets it in `finally`. Early returns, an incomplete kill with survivors, and errors all leave no stale marker behind.
- `tests/tools/test_process_registry.py`
  - `test_kill_receipt_rewritten_when_reader_finalises_first` (added in #112156): it asserted that the reader's first save records `("exited", "", 0)`. Because the reader now records the kill from its first write, that assertion becomes `("killed", "process.kill", -15)`. The final-save assertion is unchanged.
  - New `test_kill_notification_keeps_kill_attribution_when_reader_finalises_first`: in a deterministic reader-wins race through `kill_process(source="kill_all", consume_output=False)`, `drain_notifications` returns one event with `killed / kill_all / -15` and text containing `terminated by kill_all`.

## How to Test

1. `scripts/run_tests.sh tests/tools/test_process_registry.py -q`
2. RED on main at `f8489405` (this branch's base) with only the test changes applied:
   - `assert ('exited', '', 0) == ('killed', 'process.kill', -15)`
   - `assert ('exited', '', -15) == ('killed', 'kill_all', -15)`
3. GREEN with the fix: both tests pass. Negative control: deleting only `session._kill_source = source` makes both fail again with the same assertions.

   The branch merges cleanly onto main at `aeff051a`. The kill/notification path is unchanged between the two, but the tests were not re-run on `aeff051a`.
4. Real race, as a throwaway probe that is not committed: 10 trials of `sh -c "sleep 30"`, each with a real reader thread and a real `kill_all`. Main at `f8489405`: 9/10 queued notifications read `exited`. With the fix: 10/10 read `killed / kill_all`. Negative control: 10/10 read `exited`.
5. Adjacent tests, all green with the fix:

   ```
   scripts/run_tests.sh tests/tools/test_process_registry.py tests/tools/test_notify_on_complete.py tests/tools/test_kill_verify_tree_death.py tests/tools/test_persist_on_release.py tests/tools/test_process_checkpoint_readopt.py tests/tools/test_process_registry_list_exit.py tests/tools/test_process_registry_lazy_restore.py tests/tools/test_completed_process_results.py tests/tools/test_zombie_process_cleanup.py tests/tools/test_process_heartbeat.py tests/tools/test_process_wait_clarity.py tests/gateway/test_abandoned_turn_process_cleanup.py tests/gateway/test_completion_delivery.py tests/hermes_cli/test_process_notification_display.py
   ```

   Result: 235 passed, 4 skipped (Windows-only `platforms("windows")` tests), 0 failed.

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
