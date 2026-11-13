---
name: focus-safe-desktop-automation
description: Use when agents or services may open native GUI windows.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [desktop, automation, hyprland, focus, systemd, reliability]
    related_skills: [recurring-operational-root-cause, computer-use, workspace-copilot]
---

# Focus-Safe Desktop Automation

## Desktop modes — law O15 (supersedes the blanket Sway-only rule)

Kevin's rule, proven as law O15 in `z0intelligence/bend/ops_fsm` and gated by `z0-guard desktop`:

| What you want | Solo (cron, subagent, unattended, testing on your own) | Collaborating (Kevin live in this chat AND his ask points at his screen: "my monitor", "open it in zen", "see my screen", "together") |
|---|---|---|
| **Look** at his live desktop without moving anything | allowed | allowed |
| **Open** a window/URL on his live desktop | refused: use owned headless Sway | allowed, no extra approval prompt |
| **Keyboard/mouse**, focus or workspace changes on his live desktop | refused | allowed when he asks for it ("click", "type", "log in", "you do it") |
| Anything on your owned headless Sway | allowed | allowed |
| Live desktop looks unreachable | report the gap; never fall back to his desktop | **locate it and retry** (`z0-guard desktop --resolve`, `hyprctl instances`, `grim -o`, `tern capture`); never answer "I can't see your monitor" |

Looking without moving, preferred order: `tern ls` + `tern capture BLOCK --scrollback` for Tern panes, then `hyprctl -j clients`/`-j monitors` and `grim -o OUTPUT file.png` with the live env. No `focuswindow`, no cursor moves.

Before opening or driving anything, ask the gate (it prints the surface and the live env):

```bash
z0-guard desktop --kind see|open|input [--interactive] --utterance "<Kevin's message>" [--live-ask yes] [--input-ask yes] --resolve
# prints surface (where to do it) and live_allowed; add --surface live to get exit 3 when his desktop is off-limits
```

Pass `--interactive` only when Kevin is live in this chat. Pass `--live-ask yes` / `--input-ask yes` when the conversation clearly set up collaboration but the current message is short ("just open it rn"). A desktop driver that reports zero windows or `capture: false` has the wrong display bound: resolve the live session (HYPRLAND_INSTANCE_SIGNATURE, WAYLAND_DISPLAY, XDG_RUNTIME_DIR=/run/user/1000, AT_SPI_BUS_ADDRESS) instead of reporting it unavailable.

If the installed `z0-guard` has no `desktop` command yet (O15 not deployed), apply the table above directly; the same decision is `z0int.fsm.ops.desk_allows`.

The headless Sway requirements below still apply to solo GUI launches and tests.

## Trigger

Use whenever a worker, watchdog, service, test harness, capture job, browser, game, media tool, or native application may create or relaunch GUI windows on a shared desktop.

## Core contract

The user's active workspace, focus, typing, and window arrangement are production state. Background (solo) automation must not alter them; O15 collaboration above is the exception. Successful process startup is not success if a window appears on the working desktop, steals focus, opens a modal, changes workspace, or moves an existing window.

## Workflow

1. **Observe before acting.** Use the approved workspace-observation interface when available; on Hyprland, record monitors, active workspaces, clients, application classes, and current focus without capturing private window content.
2. **Isolate every agent-opened GUI app or window by default.** While Kevin is working, any browser, Electron app, native tool, preview, dialog, capture surface, E2E/TDD window, or other agent-launched GUI must run on an isolated nested/headless display or Hyprland headless output, never a physical-monitor workspace. Use a reusable user-local Xvfb/Weston/Cage/headless-output artifact with its own socket, runtime dir, cache, and user-data dir. Do not launch on the host compositor merely because the application can. Reuse an already verified rootless binary/package before requesting sudo. If isolation is unavailable, block instead of opening the window.
3. **Protect Kevin's host workspaces.** Workspaces 1 and 2 are hard no-touch zones for agent windows, tests, captures, or focus. OBS workspace 8 also remains untouched. If a test genuinely cannot run nested/headless, use only another inactive workspace, place it silently by stable class, and record before/after monitor workspace and focus proof.
4. **Separate user apps from agent probes.** Keep the user's normal application placement intact. Assign any unavoidable host-native probe to a dedicated inactive isolation workspace by stable application class.
5. **Persist routing.** Use compositor rules with silent placement and no initial focus. A launch-script dispatch or one-time move is insufficient because startup races and relaunch paths can bypass it.
4. **Choose focus policy carefully.** Use `no_initial_focus` for applications the user may later interact with. Use `no_focus` only for disposable test harnesses that should never receive user focus.
5. **Trace relaunch ownership.** Inspect process ancestry, systemd units, `Restart=`, timers, watchdogs, cron, launch wrappers, and task retry policy. Do not blame the foreground application when a supervisor is recreating it.
6. **Fail closed.** A health check may alert or block, but must not automatically restart a native GUI on a shared workstation unless the user explicitly opted into that behavior. “Bounded recovery” is still disruptive recovery.
7. **Verify with a disposable probe.** Launch a short-lived window with the exact target class. Assert that the active workspace is unchanged, the probe lands on the isolation workspace, focus stays with the user, and the probe is closed afterward.
8. **Run an explicitly approved foreground sequence transactionally.** Record the active window first; focus the exact target window (not merely its grouped application), verify that it is visible and accepts input, perform one action, capture the target again, and restore the prior focus unless the user asked to keep the target foreground. For grouped Hyprland windows, confirm `activewindow.address` equals the intended client after `focuswindow`; an `ok` dispatch alone does not prove the correct group member became active. If a desktop driver reports `foreground_unavailable`, do not inject into the globally focused widget—establish exact target focus first, then retry the same bounded action.
9. **Verify semantic state, not input delivery.** Treat `effect: unverifiable`, successful synthetic keystrokes, and compositor `ok` as delivery receipts only. Re-capture after every state-changing click or keystroke and confirm the expected control, page, or dialog changed before continuing. In browser-like Electron surfaces, visually confirm a real address bar is focused before typing a URL; otherwise text may become an application prompt and trigger an unintended task.
10. **Prefer visible controls over assumed shortcuts for state creation.** When creating a new chat, project, task, or document, click the labeled control and verify the blank state. Do not infer success from a generic shortcut such as `Ctrl+N`, because Electron apps may bind it differently or preserve the current thread.
11. **Resume narrowly.** Restart only the workers that need to continue. Tasks that do not require GUI evidence must be explicitly restricted to terminal/files.
12. **Prove recurrence resistance.** Verify compositor reload, app relaunch, supervisor failure, and reboot/update ownership paths before claiming the interference is fixed.

## Hyprland pattern

```ini
# User-interactive background application
windowrule = match:class ^(APP_CLASS)$, workspace WORKSPACE silent
windowrule = match:class ^(APP_CLASS)$, no_initial_focus on

# Disposable agent test harness
windowrule = match:class ^(TEST_CLASS)$, workspace WORKSPACE silent
windowrule = match:class ^(TEST_CLASS)$, no_initial_focus on
windowrule = match:class ^(TEST_CLASS)$, no_focus on
```

Reload with `hyprctl reload`, then verify the active workspace and matching client placement. Never use a full desktop reload wrapper when a compositor config reload is sufficient.

## Service recovery rule

For a GUI service on a shared workstation, default to:

- `Restart=no` while the causal crash is unresolved;
- watchdog alert/block rather than `systemctl restart`;
- a persistent compositor rule as defense in depth;
- a separately tested, explicitly user-approved recovery path after the runtime crash is fixed.

## CLI tools that open a browser

`hermes mcp login` calls `webbrowser.open` when `DISPLAY` or `WAYLAND_DISPLAY` is set and the session is not SSH. That steals Kevin's desktop. For OAuth waiters, do not xdg-open: set a dummy `SSH_CLIENT` and unset display vars (see secure-provider-onboarding `references/mcp-oauth-loopback.md`). If isolation is unavailable, block rather than open Zen/Chrome on workspaces 1–2.

## Pitfalls

- Killing every worker when only one GUI-capable worker is disruptive.
- Resuming workers before persistent workspace containment is tested.
- Assuming a window rule exists because the window happened to land correctly once.
- Routing by mutable window title when a stable application class exists.
- Applying `no_focus` to an application the user must operate manually.
- Treating a timer's bounded retry count as permission to create popups.
- Fixing the relaunch loop while leaving the underlying crash unresolved.
- Dismissing a modal repeatedly instead of tracing the supervisor and crash marker that recreate it.
- Using `focuswindow` on an isolation client to tile or screenshot it. That can move compositor focus onto the headless output; restore only by the pre-run physical window address, never `focusmonitor`.
- Treating `hyprctl dispatch closewindow` as process death. Re-query clients and kill the PID if the class is still mapped.
- Launching via `hyprctl dispatch exec` with a bare binary name. The compositor PATH is not an interactive shell PATH; use a small executable wrapper with absolute paths (shebang helpers still need that PATH — wrap `env`).
- Nested Sway (`WLR_BACKENDS=wayland`) is a Hyprland client (class often `wlroots`). Pin it with a silent windowrule on an isolation workspace; Super stays on Hyprland. Existing Hyprland windows cannot be moved into that compositor — that is a new process on the nested `WAYLAND_DISPLAY`. Do not relaunch the authorized headed Blender for seat demos. Nested injectors must use that `SWAYSOCK` and `seat-agent1`, not host `hyprctl`/seat0. Nested does not need sudo or a VT flip; unpack a user-local compositor if distro install requires root.
- Ignoring compositor ANR dialogs (`hyprland-dialog`). They can map onto the user's active workspace even when the hung app is on a headless output; close them immediately by class without focusing the isolation window.
- Using deprecated `windowrulev2` syntax. Use current `windowrule = match:class ...` form.
- Switching to a physical workspace to inspect the demo. Capture the headless output with `grim -o <OUTPUT> <png>` instead.

## Verification checklist

- [ ] Active workspace and focus recorded before the test.
- [ ] Exact application class identified.
- [ ] Persistent silent workspace rule loaded.
- [ ] Disposable matching-class probe landed correctly.
- [ ] Active workspace and focus remained unchanged.
- [ ] Relaunch owners and retry paths enumerated.
- [ ] GUI auto-recovery disabled until causal repair is proven.
- [ ] Current application state preserved when safe.
- [ ] Reboot/update/relaunch path covered before final acceptance.

See `references/hyprland-gui-relaunch-incident.md` for a concrete process-tree and systemd diagnostic recipe.
