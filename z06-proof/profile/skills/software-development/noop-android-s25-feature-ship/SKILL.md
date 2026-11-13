---
name: noop-android-s25-feature-ship
description: "Use when shipping NOOP Android UI to the owner's S25."
version: 1.0.0
metadata:
  hermes:
    tags: [noop, android, adb, s25, oura, compose]
    related_skills: [rendered-ui-qualification, phone-adb-tailnet-qualification]
---

# NOOP Android feature -> owner's S25

## Repo + branch
- Upstream is `ryanbr/noop` (Fanboynz; 400+ open issues, ~2,900 PR numbers). GitHub's fork parent `muftiarfan/noop` is dormant (last push 2026-06); never sync or compare against it. `kvnloo/noop` main is a pure fast-forward mirror of `ryanbr/noop` main (`git push origin <ryanbr sha>:refs/heads/main` after an ancestry check; `gh repo sync` targets the wrong parent).
- Factory/GitOps (RFC kvnloo/noop#103): ChatGPT wave `chatgpt-driver/noop-1103` reports on kvnloo/oss-factory#302; channels tool `data/operations/noop-channels/noop-channel` (status/sync/compose/build/install/verify/tick, timer `noop-channels.timer`) composes `channels/nightly` (demo flavour, side-by-side, S22) and `channels/preview` (full `com.noop.whoop.debug`) from `channels/base` + `channels.json`. Prefer adding a feature to preview over hand-made `integrate/s25-*` branches.
- GitHub Actions on kvnloo/noop is disabled at GitHub's side since ~2026-10-22 (dispatch 422 "Actions has been disabled for this repository" while the permissions API says enabled); only the owner can fix it in Settings or via support. Don't promise PR checks; verify off-GitHub.
- Repo `/mnt/zer0models/noop-oura` (origin = kvnloo/noop, upstream muftiarfan/noop). Read `AGENTS.md`: tokens only (Palette/Metrics/NoopType), one concern per PR, iOS/macOS parity or say why not, estimates labelled.
- Other workers often hold the main worktree: create your own `git worktree add -b <feat> /mnt/zer0models/<name> origin/<base>`. Unset upstream after (`git branch --unset-upstream`) and push with an explicit lease: `--force-with-lease=<br>:<old-sha>` (plain lease says "stale info").
- Rebase right before every install: the base branch moves under you, and installing a stale base regresses the other worker's fix on the device.
- Commit as `Kevin Rajan <7121943+kvnloo@users.noreply.github.com>` using `git -c user.name=.. -c user.email=..` on commit AND rebase (groot has no identity, so a rebase stops halfway).
- New UI copy goes in `res/values*/<feature>.xml` for en+de/es/fr/it/pl/pt-rPT/ru/zh. Check with `python3 Tools/i18n_audit.py --ci <base>`, `Tools/doc_comment_lint.py` and `Tools/parity_ratchet.py --base <base>`.

## Gesture / sensor detector work
- Tune detectors only from labelled recordings of the owner wearing the device. Before redesigning:
  1. Ship a default-off raw recorder: timestamps, raw frames including ones that fail to decode, and a mark button or volume-key marker for ground-truth taps.
  2. Send the owner the protocol through the parent: normal taps, light taps, negatives while moving, and idle use.
  3. Then measure decode rate, sample rate, the noise floor while worn, and recall plus false positives per minute.
- A fixed threshold tuned off-body misses on-finger taps. "Works mostly when I take it off" points to threshold or noise-floor scaling, not a broken pipeline.
- Bounded arming windows expire silently, which reads to the owner as missed taps. Show a countdown, and auto re-arm while the setup screen is open.
- Keep raw personal sensor recordings in scratch with mode 700. Commit only synthetic or derived fixtures.
- Oura ACM facts (Ring 4, measured): 49.65 Hz, 2 samples per 0x33 frame. Byte 3 is a frame sequence counter, so lost frames are countable. BLE delivers frames in bursts on a ~30 ms grid, so derive timing from samples, not from arrival ms. Taps ring at ~25 Hz for 100-200 ms but barely move |a|, so use jerk |dx|+|dy|+|dz| instead: idle median ~28, typing ~167, tap peak 800-4000. Double-tap impacts are 140-320 ms apart.
- Evaluate a detector offline before shipping it:
  1. Replay the old detector first and confirm it reproduces the recorded `g` rows.
  2. Score with marks as windows (taps sit 0.3-2 s before each mark; the first mark can sit 5 s late).
  3. Treat the tail after the last mark as negative typing, but only once the owner confirms that's what it was.
  4. Run k-fold CV over a SMALL grid. A large grid ties everywhere and overfits 20 labels.
  5. Keep a Python line-by-line port of the Kotlin as the oracle for both the eval and the synthetic test fixtures.
- Install source: the S25 runs an integration build. Cherry-pick the feature commits onto it, push it as `integrate/s25-<date>` and build that. A build from the feature branch alone would remove other workers' features from the phone.
- Builds and tests go through `fleet-build` from the repo's `android/` dir (mbp, waits for capacity, signs with fork-debug). A filtered test run takes ~9 min.
- The recorder writes `files/diagnostics/oura-acm/acm-<ms>-<label>.csv`. Pull them with `adb exec-out run-as com.noop.whoop.debug cat <path> > local`. Row types:
  - `f` frames: raw hex plus two XYZ samples;
  - `m` owner marks, pressed AFTER the tap, so the true tap sits 0.3–2 s earlier;
  - `g` detector gestures;
  - `p` per-impulse diagnostics.
  Owners often skip label changes and keep recording through typing. Treat the stretch after the last mark as the negative set, and estimate tap intensity from impulse amplitude instead of relying on labels.
- Keep owner recording sessions to about 3–4 minutes. The owner abandons longer ones. Use ~4 reps per class with ~2 s between cues, and a Skip button. Drop negative blocks (walking, handling, typing) he has already recorded. Resume from his saved position instead of restarting.
- Guided recording (setup screen, debug section): "Start guided recording" opens `acm-<ms>-guided.csv` and walks `OuraGuidedPlan.BLOCKS` with spoken and beeped cues, resuming from the saved block. It pauses Always listen, and its gestures are only logged, never sent to the broker. Block boundaries and cue timestamps replace hand marks, so label from the plan, not from `m` rows. To add gesture classes (scroll, rapid patterns), append blocks there, ordered by importance.
- Gate gesture capture on the decoded motion-frame format, not on a hard-coded ring generation. NOOP re-labels the ring from its hardware id after product-info arrives (`BLB_04B` = Oura Ring 4 even when Bluetooth names it Gen3).
- Android allows only one GATT write in flight per connection. Commands written back to back get refused silently, and the driver stalls in a phase such as `FetchingHistory`. Queue writes one at a time with a bounded busy-retry, and log dropped writes, before you suspect the protocol.

## Build
- Routing (owner rule): never queue Gradle on groot behind heavy.lock. Default: from `android/`, run `fleet-build --fetch app/build/outputs/apk/full/debug --out DIR -- ./gradlew assembleFullDebug` (MBP, signs with the fork key). For custom resources, run directly on mbp: `cd /workspace/.files-k3s && scripts/fleet run --node mbp --mem 7G --cpus 6 --src <worktree> --fetch src/android/app/build/outputs/apk/full/debug/app-full-debug.apk -- bash -c 'cd android && ./gradlew --no-daemon --max-workers=4 -Pkotlin.compiler.execution.strategy=in-process -Dorg.gradle.jvmargs=-Xmx4g assembleFullDebug'`. The default 2 GB job cap kills Gradle (exit 143). Fetched files land in `~/.local/state/fleet/runs/<job>/`. Run non-Gradle checks the same way.
- Groot fallback (only when mbp has no java): `ANDROID_HOME=/home/kvn/android/sdk`, `--max-workers=2 -Xmx3g`.
- JVM tests fail at config time with `roomSchemaOracle ... doesn't exist` after any KSP rerun. Prefix with `:app:syncRoomSchemaSnapshot --rerun`, and don't put assemble and test in the same invocation.
- Signing: the tracked `android/fork-debug.keystore` (androiddebugkey/android) is the signer of the fork's `oura-z0live-*` release APKs (SHA-256 4511d903...). Before installing, verify with `apksigner verify --print-certs` against the pulled installed base.apk. Never uninstall or clear data: the ring key lives in NOOP's data.

## Install + prove on device
- Other workers install INTEGRATION builds that stack several feature branches (e.g. `local/s25-hermes-agent-integration` in `/mnt/zer0models/noop-hermes-agent-s25`). Before installing a standalone APK, pull the installed base.apk and grep its dex for each branch's marker classes (`unzip -p x.apk 'classes*.dex' | grep -a -o 'Lcom/noop/ui/<Class>;'`). If it holds other features, don't overwrite it. Check that your commit cherry-picks cleanly onto the integration head in a throwaway worktree, then hand it to the integrator.
- Since 2026-10-21 the S25's `com.noop.whoop.debug` (556, 12.1.0-debug) was `feat/oura-walk-labelled-recording` (c3b73423) + `feat/agent-api-z0bridge`, built from no committed branch. That combination is now `integrate/s25-20261103-hc` (worktree `/mnt/zer0models/noop-s25-hc-integrate`, manifest conflict = keep WAKE_LOCK). Compare APK class lists (`unzip -p x.apk 'classes*.dex' | grep -ao 'Lcom/noop/[A-Za-z0-9/_]*;' | sort -u`, then `comm -23 installed new`) before any install; source-file greps miss `*Kt` classes.
- Before an install: snapshot `databases/noop_whoop.db` + `-wal` and `shared_prefs/*.xml` via `run-as` into a 0700 private dir, and count `pairedDevice` so you can prove the pairings survived.
- Health Connect permissions, including `android.permission.health.READ_HEALTH_DATA_IN_BACKGROUND`, can be granted over adb with `pm grant com.noop.whoop.debug <perm>`. A new WorkManager job is only enqueued once MainActivity runs, so open NOOP on the focus-safe display after installing, not on display 0.
- `fleet-build` fetch can fail with `tar: Unexpected EOF` after BUILD SUCCESSFUL; the APK is still in the retained stage on mbp: `scp agentjob@mbp:/home/agentjob/.local/state/fleet/kueue/<job>/src/android/app/build/outputs/apk/full/debug/app-full-debug.apk .` (user `kvn@mbp` gets Permission denied).
- WorkManager jobs live in `no_backup/androidx.work.workdb` (not `databases/`); `SystemIdInfo.system_id` is the JobScheduler id. `cmd jobscheduler run -f <pkg> <id>` on a periodic job before its period elapses is skipped by WorkManager in ~3 ms, so it cannot prove a background run.
- `fleet-build`'s memory-safe `--gradle-args` are applied only when CMD starts with `./gradlew`. Wrapping it in `bash -lc '... ./gradlew ...'` drops them, and the repo's own JVM settings then OOM-kill the job at 5–6 GB (compileKotlin/dex, 2026-11-03). Inside a wrapper, pass `--no-daemon --max-workers=2 -Pkotlin.compiler.execution.strategy=in-process -Dorg.gradle.jvmargs=-Xmx3g` yourself.
- `fleet run --mem 7G` exits 75 ("lane has 7165MiB left for a 7168MiB job") on mbp's lane; use `--mem 6G`. Two parallel default `fleet-build` jobs get OOM-killed (143): serialize assemble then tests.
- Strap-log burst lines carry features only (no raw samples), so a raw-signal gate (e.g. the |a| stillness gate, `still=` in the log since 2026-10-21) cannot be replayed on old real-use windows; score it on guided raw files and say so.
- `fleet-build --out DIR` can exit 2 after a successful job (a script parse error); the artifacts are still in `~/.local/state/fleet/runs/<job>/src/...`. Use plain `fleet run --mem 7G` if you need a clean exit code.
- Run `env -u ADB_SERVER_SOCKET adb -s 100.117.226.39:36065 ...`, and wrap installs in `flock .../scratch/s25-noop-install.lock`. Use `adb install -r` only.
- Install as soon as the build is verified, even while the owner is using the phone. `install -r` is background work: it doesn't take over the screen, and it keeps the app's data. Only UI steps wait for him. Never poll in a loop for the owner to go idle before installing: it can run for many minutes, the worker gets interrupted with nothing installed, and the owner is left waiting on the feature. Install, then notify him with the one-line steps for anything that needs a tap (re-arm, toggle on).
- An install restarts NOOP, which drops any armed ring capture. Say so in the same message, and include the re-arm step or switch Always listen on.
- Before any input: check `dumpsys activity activities | grep topResumedActivity`, `usagestats` USER_INTERACTION recency and audio recording (voice chat). Afterwards restore the owner's previous app (`am start -n <pkg>/<activity>`), and close views that hold keepScreenOn.
- Navigation:
  - Live Body Console: bottom bar `More` -> `Body` group -> `Live`.
  - Devices: `More` -> scroll the page down to the `DATA` group (fsd `scroll up` = finger moves up) -> `Devices`. Device actions there are only Rename/Remove; there is no reconnect button. Don't use the Today header as a route: the top-right ring opens Settings, and the top-left Bluetooth button preceded Bluetooth switching off once. After any Today-header tap check `settings get global bluetooth_on`; restore with `cmd bluetooth_manager enable`.
  - Oura gesture setup: `am start -n app.lawnchair.play.debug/app.lawnchair.zer0.voice.z0live.Z0LiveActivity` -> "Oura ring setup (NOOP)". Its "open NOOP devices" button pushes NOOP's main activity onto the same task. To get back, send `input keyevent 4` until `topResumedActivity` is `OuraGestureSetupActivity`. Don't overshoot: that pops the setup activity and loses the screen.
  - Find element bounds with `uiautomator dump` (or phone_exec `screen()`), then `input tap`.
- Do on-device steps yourself over adb (pairing, arming, navigation). Don't hand the owner a list of taps: he expects the agent to drive the app, and asks back when it doesn't. Exception: if he is using the phone right now (recent USER_INTERACTION, or a foreground app you didn't open), don't drive the UI; notify him with one-line steps instead.
- One-time secrets such as pairing links: fetch them inside the script, `input text` them into the field (escape `&` and `?`), and print only presence and length. Never echo the value.

## Diagnose on device (before theorising)
- The debug build allows `run-as com.noop.whoop.debug`. `files/strap-log/*.log` holds NOOP's own BLE and driver log (connect, auth, history fetch, gesture arm/decode counts, refusal reasons). App logs don't appear in logcat, so pull this file first, read the lines around the failure, and map them to the guard in code (`search_files` for the message). Keep pulled logs in scratch and delete them after.
- `dumpsys bluetooth_manager | grep -i -A3 oura` shows bond, ACL state and which package owns the link. A connected ACL does not mean NOOP's driver is authenticated or in `Streaming`; the strap log tells you which phase it's in.
- If the strap log's newest file has stopped (no `Oura:` lines for minutes, or Devices shows the ring as "Last seen Nh ago") while `dumpsys bluetooth_manager` still shows an LE link, the official Oura app has probably reclaimed the ring. It does this after NOOP restarts, for example after an update install. Run `am force-stop com.ouraring.oura`, wait about 20 s, and confirm NOOP logs auth and history `caught up` before you arm. Arm then succeeds. Tell the owner to keep the Oura app closed (or its Bluetooth off) while testing, because it reclaims the ring again whenever it runs in the background.
- NOOP drives one wearable at a time. Strap-log `Not connecting the WHOOP ...: a different device is active` means the Oura is the active device and the WHOOP is blocked on purpose; it is not a fault.
- `Oura: disconnected (status=147)` every ~10 s is a GATT connection timeout: the ring is not reachable (flat battery, out of range, or held by another app or phone). No software step fixes it. Tell the owner to put the ring on its charger next to the phone, and keep the Oura app closed.
- After Bluetooth goes off and on, NOOP rescans for the WHOOP but does not reissue the Oura connect. Restart the loop with `am force-stop com.noop.whoop.debug`, then relaunch MainActivity right away on the focus-safe display. The relaunch also re-enqueues the WorkManager jobs that force-stop cancelled.
- "Ring gestures don't work": walk the chain before touching the detector.
  1. Strap log: are bursts classified (`DOUBLE_TAP` / `TRIPLE_TAP` lines)? If not, is a capture armed at all? Armed capture lives in NOOP's process, so a NOOP restart or install silently disarms it.
  2. Broker journal (`journalctl --user -u z0live.service`): do `POST /v1/gesture` requests arrive?
  3. Broker verdict: read `gesture_events.result` read-only from `broker.db` in the service's `Z0LIVE_DATA` dir. `no_active_target` means no surface heartbeated presence in the last 15 s (Lawnchair Standby dozes). Check `gesture_presence.seen` and the `Z0LIVE_GESTURE_ADB` adb fallback.
  4. Device credentials: check the device rows in `devices.json`. Re-pairing one app's capability must not revoke the gesture device's credential.
- Owner's locked gesture map: double tap with no call starts a call, double tap during a call toggles mute, triple tap ends the call. Implement it as commands to the live session, not as activity relaunches (a relaunch toggles the call). The adb fallback may only start a call, debounced. False positives come from walking and handling the phone, so validate on real negative recordings rather than desk taps.
- A guard that refuses silently (no write logged after "armed" is pressed) means a precondition failed before any command was sent. Find which one before changing thresholds.
- Evidence: `screencap -p`, plus `screenrecord --time-limit 12`. Make a montage with `ffmpeg -vf fps=1,crop=..,scale=360:-1,tile=6x2` and view it. Raw Oura live HR/R-R is noisy (e.g. 144 -> 34 bpm, 1300 ms missed beats), so check that the UI does not animate noise as if it were signal.
