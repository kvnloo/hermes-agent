---
name: maestro-local-android
description: "Use when automating Android setup with local Maestro."
---

# Local Maestro Android automation

Use the installed `maestro` CLI or local stdio MCP interface, never cloud automation for private devices. Check `command -v maestro`, `maestro --help`, `maestro test --help` and `adb devices -l`; pin the exact authorized device ID. Load activitywatch-local-sync for telemetry setup.

Set `MAESTRO_CLI_NO_ANALYTICS=1` for every invocation. The installed CLI 2.11.0 Analytics class recognizes this variable. Do not invoke cloud, login, record, screenshot, AI analysis or AI extraction commands. `maestro mcp --no-viewer` exposes local stdio inspection and flow execution without launching a desktop browser; discover its schemas through JSON-RPC initialize and tools/list before use. MCP run capture behavior is not yet qualified.

Read the current hierarchy before each action. Filter hierarchy in Python before returning tool output: omit systemui notification/status nodes, private filenames and unrelated app text. Do not dump an unfiltered hierarchy into model context. Prefer resource IDs, and verify semantic state after actions. Store approved flows and restricted receipts under XDG state/activity-telemetry/maestro, not a Git repository.

IMPORTANT: `maestro test` automatically captures a screenshot on failure in this installed build. A screenshot-free mode was not verified. Under a strict no-screenshot constraint, do not execute additional test flows until capture is demonstrably disabled; use hierarchy inspection with bounded authorized ADB actions instead. If an unexpected failure capture is generated, delete only that owned artifact without viewing/uploading it, disclose it, and do not claim no capture occurred. Successful flows observed produced commands/manifest/logs but no screenshot files. Device-logcat artifacts may contain sensitive data and require restricted permissions and retention review.

Avoid `launchApp` defaults: official docs say all permissions are allowed by default and the app is stopped by default. Do not clearState, clearKeychain, reset unrelated app permissions, or force-stop an authorized collector. Use explicit ADB component launch to preserve permissions and service state when permission-neutral Maestro launch semantics are unqualified.

For ActivityWatch Android:
- With explicit user authorization, set only GET_USAGE_STATS through `adb shell cmd appops set --user 0 net.activitywatch.android GET_USAGE_STATS allow`, read it back, and add/read back deviceidle whitelist. This does not prove Samsung background reliability.
- Onboarding uses `net.activitywatch.android:id/nextButton`; inspect CONTINUE versus FINISH first. Usage GRANT disabled on the permission screen confirms the app recognizes access. Leave browser Accessibility and notification-listener/media access off. Runtime POST_NOTIFICATIONS is distinct: approving it permits the collector's visible service notification, not notification content access.
- App uses a hidden native options menu: `adb shell input keyevent 82` revealed Settings and Sync Settings on MainActivity. If already in SyncSettingsActivity do not open/reselect the menu. Inspect resumed activity first.
- Edge swipes at 1% and 4% invoked Samsung back navigation, not the native drawer; do not repeat them.
- Sync settings IDs: switch_sync_enabled, btn_choose_sync_dir, tv_sync_dir_status, tv_last_sync_status, tv_next_sync_status.
- Create only `/sdcard/Download/ActivityWatchSync`, select Download then ActivityWatchSync via storage picker, use folder button and approve only the exact dedicated-folder access dialog. Never grant root phone storage to ActivityWatch.
- Enabled Android sync is push-only and schedules its own export. UI success and a three-level `{hostname}/{device_id}/test.db` export can be checked with staged official `aw-sync --sync-dir DIRECTORY status`. Copying the official export through ADB for verification is not direct source DB scraping, but is also NOT Syncthing synchronization or PC ingestion. Do not rename test.db based on suspicion; aw-sync status recognizes it with a scaffolding warning.
- App-switch tests should launch exact resolved components, not assume package-only intents resolve. Verify topResumedActivity after each launch. Clock on Samsung resolved `com.sec.android.app.clockpackage/.ClockPackage`; the package-only MAIN/LAUNCHER invocation failed. Export timestamp must cover the actual test, not just historical usage backfill.

Check keyguard/input restriction before an app-switch test. If the handset is locked, stop UI actions and request manual unlock; do not bypass the lock. A later official export can validate an earlier recorded Clock/Settings sequence by exact timestamps and durations, but label those as prior-session events rather than a fresh interaction in the current run. Keep raw hierarchy and unrelated app text out of receipts and do not send private device observations to external decision services.

Report installation, collection, export, transport and ingestion separately. Recheck the foreground service at the end as well as the start: an installed/running app process and preserved Usage Access do not prove the foreground collector survived Android process killing. If it disappears, inspect package-scoped `dumpsys activity exit-info` and report timestamped reason/status fields only; do not infer a cause beyond observed SIGNALED/LOW_MEMORY reasons or silently relaunch behind a locked keyguard. Never bypass API authentication or extract app credentials to solve a 401. Preserve original source data ownership and the PC's single-watcher/server rule.
