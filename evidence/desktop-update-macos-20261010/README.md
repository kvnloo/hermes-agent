# Native macOS marker-adoption receipt for PR #134551

Evidence-only snapshot, verified 2026-10-10 at 14:23 UTC. Supports [teknium1's consolidated PR #134551](https://github.com/NousResearch/hermes-agent/pull/134551) at `9955c74770259114f14027fd55d104cd2dec3693` and preserves [elvin-du's existing handoff implementation](https://github.com/NousResearch/hermes-agent/commit/8a1dc691161c499a9b3e6c0b12e34eb164b50a76). No implementation or test is added by this packet.

## Existing native CI

Both target jobs ran on macOS 26.6.2 arm64 with CPython 3.14.7 through `scripts/run_tests.sh`.

- RED: [job 114200179903](https://github.com/NousResearch/hermes-agent/actions/runs/38047589100/job/114200179903), run 38047589100, checked out `7f8af627e8cf0b61d882cbf8258b1a20e497f31b`. The generation-2 marker-adoption assertion failed (holder 11984); target slice: 146 files, 481 passed, 1 failed, 171 skipped. This completed macOS job failed; the overall workflow was later cancelled.
- GREEN: [job 114197690460](https://github.com/NousResearch/hermes-agent/actions/runs/38046727803/job/114197690460), run 38046727803, succeeded. It actually tested PR merge `329373c088b366a51284feb6fc5ab227a87a63b9`, rather than the detached owner head. The target file passed (1 test, 3.1s); target slice: 146 files, 482 passed, 0 failed, 171 skipped. The run concluded success.

`source-identities.json` pins the five relevant handoff, marker, lock, test, and OS-workflow blobs. All five are byte-identical between the tested GREEN merge and owner head. RED differs from owner head only in `scripts/desktop-update/posix.sh`: it restores `HERMES_UPDATE_HANDOFF_PID="$$"` and removes the fix comment. Its handoff/marker/lock blobs match the pinned main revision. This isolates support for the current regression delta; it does not establish whole-tree equivalence.

## Coverage boundary

The [owner's test](https://github.com/NousResearch/hermes-agent/blob/9955c74770259114f14027fd55d104cd2dec3693/tests/scripts/desktop_update/test_posix_handoff_pid_export.py) executes real POSIX handoff/marker scripts and real `UpdateLock.acquire()` for generation 2, launched through a short-lived intermediary. The update payload/launcher is fixture code. `UpdateLock(path=...)` omits `install_root`, so this test proves marker adoption, without acquiring the fixture checkout lock.

[Companion PR #135413](https://github.com/NousResearch/hermes-agent/pull/135413) at `4796cf48cb8d715db272c377b5fa39513b8f1f3f` adds distinct first-generation checkout-exclusion coverage against historical parent `6770f2f15d0cb0ef19a63ed33621e5650393e336`; it does not replace generation-2 coverage or independently prove the rebased owner head.

No claim is made for packaged Desktop download/rebuild/replacement/relaunch, Intel Macs, every macOS version, or a full repository suite. No tests, builds, installs, or workflow triggers were performed to prepare this receipt. No later status is inferred from this snapshot.

## Recovery and excerpting

`ci-excerpts.txt` selects original log lines with timestamps and original 1-based line numbers. Only ANSI color escapes are removed and the absolute runner-temp prefix is normalized to `<runner-temp>`; omissions are explicit. Environment dumps, credential payloads, and runner identifiers are excluded. `manifest.json` records packet hashes, run/job outcomes, and hashes/byte counts of the unchanged original log and metadata files retained locally. Raw originals are not included in the publication tree; the public job links and pinned source links are the independent recovery references. The manifest excludes its own hash to avoid self-reference.
