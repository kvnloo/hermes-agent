---
name: isolated-gui-interaction-trials
description: Use when driving a native GUI on an isolated display.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [desktop, hyprland, dogfood, timing, xwayland]
    related_skills: [focus-safe-desktop-automation, computer-use]
---

# Isolated GUI interaction trials

## When to Use

Use when dogfooding or timing a native app on an isolated display, including Kevin's Hyprland session, without touching his physical workspaces. Isolation lifecycle stays in `focus-safe-desktop-automation`. This skill is the interaction and measurement contract on top of that isolation.

## Procedure

1. Record the focused window address and each physical monitor's workspace before launch. Restore that address after every probe. Remove the headless output when finished. Workspaces 1 and 2 stay untouched.
2. After `hyprctl output create headless`, read that output's active workspace and launch onto it. A silent rule for a different workspace can map the client where `grim -o` still captures an empty desktop. Confirm the client monitor before treating a blank frame as an app failure.
3. Read the live class from `hyprctl clients` before writing a windowrule. Qt on Wayland often reports the interpreter; the same app on XWayland often reports the script name. A rule for the other class does not contain the window.
4. Keep Qt platform and GL integration as per-process environment. Do not reload the user's compositor or switch their session to fix one app. A black GL viewport with a live UI shell means check the context class before rebuilding. If a later click kills the process inside that redraw, it is the same context class, not a seat failure. Wayland often hands OpenGL ES to an app that requires desktop GL. Headed versus headless does not change that. Do not move the trial onto the user's physical session to "fix" it.
5. Drive an XWayland client with `xdotool mousemove --window <xid>` using window-relative coordinates. `grim -o` pixels are not Hyprland coordinates when the output origin is offset. Menu popups are separate X windows; click the popup id, or the click misses and dismisses the menu.
6. A bare key arriving is not proof a modifier chord arrived. Re-capture and require the expected dialog or state before continuing. `effect: unverifiable` and a successful key send are delivery receipts only.
7. If the protocol names a shortcut and that chord does not change the UI, stop that arm. Do not click a menu item and record it as the shortcut. A substitute is a different path.
8. Close leftover dialogs before a chord trial. A mapped dialog can take key focus, so the chord never reaches the target and the miss looks like a dead binding.
9. For a timed comparison, write each mode's path before the first measured trial. One step is one click, one chord, one contiguous text entry, Enter, one panel switch, or one menu selection. Do not count characters. One unmeasured warm-up per mode, then counterbalance so one mode is not always first. Time only the interaction. Screenshot, vision, process start, and focus restore sit outside the timed region. Use a fresh app config/home so prior receipts are not in the run. Do not lengthen the slower path beyond what a knowledgeable user would do.
10. If a modifier chord does not change the UI on the host compositor's XWayland client, stop injecting into Hyprland. It cannot attach a virtual keyboard to a seat other than the user's, and an agent must not file that on the Hyprland tracker. Relaunch on a headless Sway (`WLR_BACKENDS=headless`, `WLR_HEADLESS_OUTPUTS=1`, host `WAYLAND_DISPLAY`/`DISPLAY`/`SWAYSOCK` unset). Create `seat-agent1` with `swaymsg` first. Bind the virtual keyboard to that seat by name; the name event arrives only on a second `wl_display_roundtrip`, so keeping the first or last seat attaches to the wrong one. A new virtual keyboard does not deliver until that seat has entered the focused surface — sleep after keymap upload and before the chord (`wtype -s`), then require the dialog. Exit 0 is not delivery. Xwayland does not consume virtual-keyboard events from any Sway seat. If the app must stay an X client of that Sway, inject the shortcut with XTest on its private `DISPLAY` after `windowfocus`, never `xdotool --window` — Qt drops non-spontaneous XSendEvent for `QShortcut`. Do not record an XTest run as a `seat-agent1` run.

## Native terminal integration trials

Use an ordinary live application window on the isolated display when testing terminal plugins or native surface protocols; offscreen scenario renders and mocked node trees do not establish live plugin or frontend behavior. Separate plugin-load, semantic-interaction, inspected-pixel and latency evidence in the verdict. A ready plugin with no load problems establishes only the load gate, not end-to-end readiness.

Follow `references/native-terminal-runtime.md` for disposable Tern state, daemon and control isolation, plugin verification, and evidence collection.

## Phone-size web checks

To see a web app as it looks on Kevin's phone in a real browser, run Chrome on a headless output with CDP device emulation: `references/phone-browser-viewport.md` (Chrome's ~500 px minimum window width makes emulation mandatory, and grim captures carry the compositor's colour filter).

## Pitfalls

- Treating a blank `grim -o` frame as an app failure before checking which workspace that output is actually showing.
- Assuming the script name is the window class.
- Clicking the main window to hit an open XWayland menu.
- Relabeling a menu click as the shortcut under test.
- Leaving focus on the headless output after a probe that had to focus the client for input. Restore the pre-run physical window by address.
- Sending the chord the instant a virtual keyboard is created. The seat has not entered the surface yet, so the request succeeds and the client never sees the key.
- Binding the first or last `wl_seat`. The seat name arrives only after a second roundtrip; the other seat is the wrong one.
- Recording XTest on Sway's private X display as a `seat-agent1` result. Xwayland does not consume virtual-keyboard events.
- Calling a redraw crash a seat bug. If the backtrace is in the app's GL path after the input arrived, the seat worked. Say that split in one plain paragraph when asked what is blocking. Do not propose a headed rerun when the same OpenGL ES context already appeared on the physical session.
