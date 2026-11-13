---
name: android-agent-virtual-display
description: "Use when running Android apps off the owner's screen."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [android, adb, scrcpy, virtual-display, phone-harness]
    related_skills: [phone-harness-android-fast-tree, focus-safe-desktop-automation]
---

# android-agent-virtual-display

Use when running or inspecting Android apps on agent-owned secondary displays while preserving the owner's screen and input focus.

## Rules

0. Owner standing permission (2026-11-05): on both the S22 and the S25 Ultra, run parallel agent tasks on focus-safe virtual displays (`fsdisplay.FocusSafe`, one display per lane) without asking. Never drive display 0 for agent work there (phone_exec/phone_goal and plain `am start` land on the owner's screen). Proven: `operations/phone-parallel-20261105/canary.py` ran 3 lanes (2 on S25, 1 on S22) with mTopFocusedDisplayId=0 and the owner's window unchanged before/after.
0b. Android allows one UiAutomation registration per phone. Lanes on one device share a single uiautomator2 handle (fsdisplay keeps one per serial behind a lock). `AccessibilityServiceAlreadyRegisteredError` means another server holds it (e.g. phone-harness's `com.wetest.uia2.Main -p 9118`); stop only a server you own, never another lane's.
1. Choose hidden, Samsung pop-up or visible overlay mode from the owner's intent. For everyday app work, consider the packaged `phone-focus-safe-apps` home/battery gate at `chatgpt-driver/focus_safe/fsdisplay.py`. Reserve visible overlays for an explicit request to watch.
2. Read current device identity with `adb devices` and check wakefulness, display-0 `FocusedWindows`, `mTopFocusedDisplayId` and input `FocusedDisplayId` before launches or input. Preserve the owner's screen and keyboard focus. Give ad-hoc sessions their own display, FIFO, logs and screenshot directory; leave `~/.local/state/agent-display/s25.json` to its factory owner.
3. Use the focus-safe mechanism whenever the owner may be active. Create a trusted display with OWN_FOCUS and STEAL_TOP_FOCUS_DISABLED, full flags `0x1ddc9`, and inject events with the display ID. Ordinary `input -d N` still steals global focus. Inspect the platform flag/permission path before declaring isolation impossible.
4. Use `/workspace/zer0/data/operations/t3-generative-ui-spike/android/focus-safe/FocusSafeDisplay.java` and its owned `session.py` for mechanism work. Keep a separately named scrcpy-server jar, record logical and SurfaceFlinger IDs from the new session log, and check both focus values after each command. Quit or kill only the exact processes you own.
5. Use plain scrcpy only when its focus effects are acceptable. Start with `scrcpy -s <serial> --new-display=1080x2340/420 --no-audio --no-window --max-fps=2 --video-bit-rate=200K --record=/dev/null --record-format=mkv --start-app=<package>`. Keep the video sink and control enabled. Record its child PID and account for `--start-app` taking top focus.
6. Launch with `am start --display N`, read trees with `uiautomator dump --windows`, and resolve `screencap -d` against `dumpsys SurfaceFlinger --display-id`, not the logical ID. Prefer deep links for navigation. Match display-0 size/density including overrides, verify screenshots change after input, and reproduce with correct geometry before reporting UI defects.
7. Keep apps already used on display 0 and shared microphone, speaker or camera actions outside assumed isolation. Ask for the owner's single action when necessary. Use new-document or multiple-task instances only where supported. Preserve the owner's clipboard around composer checks and avoid moving HOME or single-task recents onto your display.
8. Use a private finger-event jar for pointer-type-aware web tests and confirm `pointerType` before interpreting touch failures. Use `swipe x y x+2 y+2 1000` for long press. Re-read wireless-debug serials after reconnects, and replace a hung driver with separately named owned FIFO/log files rather than interfering with another lane.
9. For an owner-requested Samsung viewer, use `dev.z0.agentscreen/.MainActivity` with `--windowingMode 5`, read its new display ID from AgentScreen logs, and launch supported fresh tasks with `-f 0x18000000`. Empty its display safely before replacing the process. Keep hidden-display content destruction enabled rather than moving its apps onto the owner's screen at teardown.
10. For an overview, use `/workspace/zer0/experiments/agent-screen/overview/overview_server.py` as a read-only mosaic and `.OverviewActivity` as the viewer. Preserve every lane's display ownership and IDs. Treat retained black/dozing frames as stale observations rather than proof work continued.
11. Treat panel-dark operation as a separate power/security workflow. Distinguish `agent_dark.py` behind the keyguard from manual `PanelPower hold` on an unlocked phone. Under `flock /tmp/<dev>-ui.lock`, sample wakefulness, keyguard, panel power, screen lock and resumed tasks, inspect a screenshot, then restore panel state using owned processes. Verify on battery before claiming timeout prevention; check dispatch logs and STOP files before claiming overnight work.
12. Continue runnable installed-binary and JS-hot-reload journeys when build admission is held. Keep native-rebuild gates separate and inspect existing recovery timers/receipts before escalation. Qualify wallpaper/composition behavior on display 0 separately. Canary any new factory app lane before enabling it, and retag queue briefs only under `.queue-claims.lock`.

13. OmaLauncher breaks out of virtual displays. Its Terminal tile opens `.TerminalWindow` (not exported, `omarchy://window/...`) on display 0 even when `.MainActivity` runs on your display, which puts a terminal on the owner's screen and takes the IME. Never tap the Terminal tile from a virtual display. The Tern tile is untested: it likely shares the same window, so try it at most once, with a display-0 check right after the tap and immediate removal, and only when the owner has suggested or allowed it. If it happens, remove only that task with `am stack remove <taskId>` (read the id from `dumpsys activity activities | grep TerminalWindow`) and tell the owner. Getting into the guest (sshd 8022) when it isn't running needs the owner to open the Terminal tile once.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
