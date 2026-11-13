---
name: linux-compositor-window-capture
description: "Use when a Linux GUI window must be found on Hyprland."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [linux, hyprland, wayland, window, capture, screenshot, grim]
    related_skills: [computer-use, focus-safe-desktop-automation]
---

# Locating and capturing Linux GUI windows (Hyprland)

## Trigger

Use when the user asks about a native or browser window on a Hyprland desktop, or when `computer_use` / cua-driver reports zero windows (`list_windows` empty, capture errors) on a Wayland session. The compositor still has the window; query it directly before reporting it unreachable.

## Procedure

1. **Get the instance signature and Wayland socket.** Shells not spawned by the compositor (gateway, services, agent sandboxes) lack `HYPRLAND_INSTANCE_SIGNATURE` and `WAYLAND_DISPLAY`, so `hyprctl` prints nothing/"not set" and `grim` fails with "failed to create display". Ask Hyprland for the live instance instead of picking a directory:
   ```
   hyprctl instances -j        # -> instance, pid, wl_socket
   export HYPRLAND_INSTANCE_SIGNATURE=<instance> WAYLAND_DISPLAY=<wl_socket> XDG_RUNTIME_DIR=/run/user/$(id -u)
   ```
   Do not use `ls /run/user/$(id -u)/hypr/ | head -1`: stale instance directories from earlier logins sort first and give "Couldn't connect to .socket.sock". If `hyprctl instances` is unavailable, loop over the directories and keep the one where `hyprctl -j clients` returns JSON.
   An agent harness may point `XDG_RUNTIME_DIR` at a private agent display (e.g. `/run/user/1000/agent-display` for headless Sway). Its desktop tool then reports zero windows and no capture. That is the wrong display, not an empty desktop.

2. **List clients with stable fields.**
   ```
   hyprctl clients -j | python3 -c "import json,sys; [print(c['address'], c['class'], '|', c['title'], '| ws', c['workspace']['name'], '| hidden', c['hidden']) for c in json.load(sys.stdin)]"
   ```
   Match by `class`, which is stable. Titles change with page navigation, so use them only to tell tabs apart.

3. **Capture the monitor the client is on.** If `hyprctl clients` shows the client on a monitor's active workspace (`monitor` id → `hyprctl -j monitors` name), just `grim -o <name> file.png` without changing focus. That covers "can you see the pane on my left / my monitor"; for Tern panes `tern ls` + `tern capture BLOCK --scrollback` reads the text with no pixels at all. Under law O15 any agent may look this way; focusing is input. Focus first only when the window is hidden or on an inactive workspace AND Kevin is live in the chat and asked you to drive (`z0-guard desktop --kind input --interactive ...`):
   ```
   hyprctl dispatch focuswindow address:0x<address>
   grim -o <output-name> /path/to/capture.png
   ```
   Get the output name by matching the client's `monitor` id to `hyprctl -j monitors` (not the focused monitor, which may be a different screen). Capture the output, not the full desktop, so unrelated windows stay out of the image.

4. **Restore focus.** `focuswindow` moves the user's focus. If the user was working elsewhere, re-focus their previous window by its address after the capture.

5. **Drive input yourself when the task needs clicks and O15 allows it** (collaboration plus Kevin asking for input; solo/unattended agents never drive his desktop). Check `test -w /dev/uinput` and `python3 -c "import evdev"`. If both pass, use `scripts/vinput.py` (key/type/click_at/scroll) and read `references/wayland-gui-driving.md` for coordinate mapping, OCR-based targeting, and the cursor-warp pitfall. If `/dev/uinput` is not writable, say so and ask the user to act rather than promising clicks.

## Pitfalls

- For a recording studio on a virtual monitor (headless output, live wallpaper, rootless wf-recorder capture, teardown), follow `references/headless-recording-studio.md`.
- Declaring a window missing after checking only the desktop-capture tool. Enumerate `hyprctl clients` first.
- Matching by title. Titles change; class and address do not.
- Capturing the whole desktop when one window matters. It exposes other open windows.
- Focusing without restoring the user's focus afterward.
- Stopping at "I can see it but can't click" or handing the user a manual option menu when `/dev/uinput` is writable. Build the input path (scripts/vinput.py) and finish the task; the user expects the work done, not a blocker report.
- Clicking at coordinates from an earlier capture. Re-OCR the live screen first; layouts shift after every state change (see the reference).
- Retrying `computer_use` calls that return the same error. After one repeat, switch to the compositor route in this skill.
