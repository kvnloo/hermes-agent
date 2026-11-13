---
name: phone-focus-safe-apps
description: Use when you need ChatGPT, Grok or any phone app.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [android, adb, chatgpt, grok, tasker, virtual-display, phone]
    related_skills: [android-agent-virtual-display, owner-context-sweep, phone-goal-vs-exec]
---

# Use any app on the owner's phone without touching his screen

## When to Use
- Reading or searching the owner's ChatGPT or Grok app history (recall of documents he made there, application drafts, research chats).
- Driving any other app on his S25 (setup flows, Tasker, settings) while he keeps using the phone or has it locked.

Standing permission from the owner: he may be using the phone or not, you can use his S25 apps through the virtual display "as long as im at home. when im traveling battery percentage matters but at home it doesn't." Never ask first. Run the gate, then go.

**Exception: Google AI apps (Gemini app, gemini.google.com).** Never script prompts into them on his main Google account. Google's terms bar automated access, and a ban takes down the whole account (Gmail, Drive, Photos), which he will not risk; a lost ChatGPT account is acceptable to him, a lost Google account is not. Gemini work goes through the official `agy` CLI. When he wants the Gemini app's separate quota, he pastes prompts by hand; prepare them as in token-thrifty-agent-routing `references/owner-run-app-quota-tests.md`. He signs in himself; you never handle Google credentials.

## 1. Gate: home/away and battery (one command)
```
cd /mnt/zer0models/workspace/zer0/data/operations/chatgpt-driver/focus_safe
python3 presence.py s25      # exit 0 = go, 3 = refused; JSON says why
```
- Home = Tasker's `z0 Home` profile wrote `home <epoch>` to `/sdcard/Tasker/z0/presence.txt`, OR the phone's Wi-Fi is `MyPvtNetwork` (`cmd wifi status`). At home battery is ignored, even at 2%.
- Away: allowed only if charging or battery >= 50% (`AWAY_MIN`). If refused, say so and wait; do not lower the bar.
- The Tasker profile (Wi-Fi Connected, SSID MyPvtNetwork, Active=Any; enter/exit tasks write the file) is canonical in `focus_safe/tasker/z0_Home.prf.xml`, exported from the phone after it fired. Re-import that file rather than hand-writing Tasker XML.

## 2. Drive the app (Python library, adb only)
```python
import sys; sys.path.insert(0, "/mnt/zer0models/workspace/zer0/data/operations/chatgpt-driver/focus_safe")
from fsdisplay import FocusSafe
with FocusSafe("s25") as fs:                     # trusted display, flags 0x1ddc9, geometry = display 0
    fs.start("ai.x.grok/.main.GrokActivity")     # or com.openai.chatgpt/.MainActivity
    fs.tap_text("Show navigation drawer"); fs.tap_text("Search"); fs.type("Witcheer")
    print(fs.texts()); fs.screenshot("/tmp/x.png")
    reply = fs.copy_via(node)                    # Copy button -> text; owner's clipboard restored
```
- Run with `env UV_CACHE_DIR=/workspace/cache uv run --with uiautomator2 python ...`.
- Every input re-checks `mTopFocusedDisplayId`; `FocusStolen` aborts if the owner's focus ever leaves display 0. Report that check ("owner focus stayed 0") with the result.
- Locked/asleep phone: `FocusSafe` wakes it behind the keyguard and holds only the panel off (`PanelPower hold`) for the session, because a sleeping phone sleeps every display and screencaps come back black. Display 0 stays dark and locked; the ALWAYS_UNLOCKED agent display keeps rendering. `close()` releases the hold.
- Multi-step exploration (onboarding, settings): `python3 fsd_session.py s25 <name>` in the background, then `python3 fsd_session.py --send <name> 'tap_text OK' 'shot' ...`. Commands: start, tap, long, tap_text, tap_has, type, key, back, scroll up|down, texts, shot, wait, quit. Look at the `shot` PNG when the text dump is ambiguous (checkbox states, dialogs). Always `quit` at the end.
- ChatGPT chats: `cg_capture_fs.py OUTDIR "Exact chat title" ...` (all texts top to bottom + every Copy button). Find titles first by typing short keywords into the app's own Search box and reading the result list.
- Grok chats: search the drawer with a SHORT keyword (a full title returns nothing), then `tap_text(title)`; capture by scrolling to the top, then collecting texts while scrolling down.

## Pitfalls
- Never use `adb shell input -d N` or `vdisplay.Display.tap` here: that path moves the owner's global focus. Only `FocusSafe` injection is safe.
- ElementTree leaf nodes are falsy, so `find(a) or find(b)` silently drops a match; compare with `is None`.
- Apps resume inside the last screen (ChatGPT reopens the last chat), so back out until `Menu` exists before navigating.
- `type()` is ASCII through the virtual keyboard map. For other text set the clipboard (`fs.d.set_clipboard`) and restore it.
- Single-task apps already open on display 0 can move onto your display; launches use NEW_TASK|MULTIPLE_TASK. If he is in that exact app, wait.
- Tasker does not evaluate profiles while its editor UI is open: after Apply, use `More options -> Exit`, then check the file. An imported Wi-Fi Connected state with Active=Yes never fired; Active=Any does.
- Fresh Tasker install: pre-grant with adb (`pm grant --user 0` FINE/COARSE/BACKGROUND location, NEARBY_WIFI_DEVICES, READ_MEDIA_*, WRITE_SECURE_SETTINGS; `appops set --user 0` SYSTEM_ALERT_WINDOW and MANAGE_EXTERNAL_STORAGE; `dumpsys deviceidle whitelist +pkg`) so the onboarding checkboxes and file picker work, then click through onboarding on the focus-safe display. Import via long-press on the PROFILES/TASKS tab. To debug what Tasker sees, import a one-action task that writes `%WIFII` to a file and press Play.
- fsd `scroll up` swipes the finger upward, revealing content BELOW; `scroll down` moves back toward the top. When a scroll seems to do nothing, you used the wrong direction.
- fsd `key` takes integer keycodes only (`key 4`); use the `back` command for Back. `tap_text` taps the first node whose text matches, which can be a label in another section; read `texts` after every tap to confirm you landed where you meant.
- Close the session with `quit`, then confirm `topResumedActivity` on display 0 is still the owner's app.
- `pm list packages` without `--user 0` fails on this phone (secure-folder user 150).
- adb serials: use the mDNS name `adb-R5CY93G2WNH-ovNXpU._adb-tls-connect._tcp`; the tailnet `ip:port` changes whenever wireless debugging restarts, which silently orphans anything (services, scripts) pinned to the old port.
- The S22's Grok app is not signed in (age gate). Use the S25 for Grok.

Mechanism details and the factory lane: skill `android-agent-virtual-display`.
