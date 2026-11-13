---
name: phone-harness-android-fast-tree
description: Use when driving Android via phone-harness or adb.
---

# phone-harness-android-fast-tree

Use when driving Android through phone-harness or adb, reading its UI tree, or preparing a quiet phone handoff.

## Rules

1. Complete authorized phone flows yourself. Preserve the owner's foreground use: recent USER_INTERACTION, an unexpected foreground app, or active phone use permits background work only. Carry this boundary into every worker brief. Use fresh, scoped owner clearance for a launch window; revalidate device identity and readiness. Pause for irreversible or data-losing steps; an unanswered interruption request grants nothing.
2. Use fast_android.py through agent_helpers.py in ~/.hermes/profiles/clean/plugin-data/phone-harness/agent-workspace. Set PH_AGENT_WORKSPACE per terminal command. Read through persistent openatx u2.jar with dumpWindowHierarchy(false, 50, true), set uiAutomationFlags=1 after startup, and keep the idle stop at 300 s.
3. Re-read until two dumps agree after input within 1.5 s. Stop with fast_tree_stop() before stock uiautomator, Maestro or Appium; diagnose killed dumps through /data/local/tmp/ph-u2/server.pid and .fast_tree_failed. Stop only exact PIDs whose /proc/<pid>/cmdline matches the owned process.
4. Use PH_FAST_TREE_VIA=adb for remote ADB_SERVER_SOCKET transports when forwarding binds remotely. Retain fast_tree_last_xml() and checkable, checked, password and package fields. Hash screenshots on-device with adb exec-out 'screencap | md5sum' for wait_stable.
5. Use an expected label or a short initial delay followed by a tree read instead of wait_stable at every step. Poll expected changes every 0.5-1 s inside one script, or 2-3 s for long jobs, printing changes only. Put observe/choose/act in one tool call when using jev_choose_action.
6. Assert current_app(), target recipient/model/harness label and focused field immediately before typing or key events. Abort on mismatch. After Send, confirm an empty composer and the new bubble within about 1 s; retry Send once for text still in the field, then report the result.
7. Search Settings through its own search UI. Select rendered result rows, excluding the editable query and nodes above the results header. Use only labels observed on the current screen; recover an unindexed path from the owner rather than scrolling for a guessed label. Enter dialer service codes through tree-selected keypad keys, including the final #.
8. Investigate vague app failures through debuggable state with adb shell run-as <pkg> ls files and cat files/<log>, then trace the exact guard or route in source before more taps. Fetch secrets inside the phone script, escape & and ? for adb shell input text, and confirm only length or masked bullets.
9. Preserve chat-only recall authorization in every brief. Reuse burst.py without weakening launch_queue.py admission or adding external tracking writes. Claim each tag before Send, use only the authorized serial, launch independent turns without waiting for replies, harvest owned tags, and leave ambiguous sends unreplayed.
10. Bind copied ChatGPT returns to the literal owned tag after only a recognized Worked for duration prefix; retain full text and observed title aliases. Collect through visible Copy or Scroll to the bottom controls. Treat unsafe swipe paths and ambiguous Follow up states as pending; check copyable read-only answers and the final empty home composer.
11. Deliver quiet handoffs through references/notifications.md. Exclude secrets and private conversation text from lock-screen-visible content. Inspect cmd notification post --help, quote remote arguments with shlex.join, and verify exact tag/key and title/body within a bounded wait. Report a plain notification separately from a tested tap action, preserving the owner's foreground app and notification permissions.
12. Prefill media shares through the single SEND intent in references/share-intents.md using a size-checked MediaStore content URI and --grant-read-uri-permission. Use scoped foreground clearance, inspect the resumed activity and screenshot, and stop before the owner presses Post. Keep pushed quoting scripts temporary and remove them afterward.
13. Resolve the adb serial live before each phone action or benchmark item, never once at startup or from a pinned `ip:port`. Wireless debugging changes port when it reconnects, so a pinned serial reads as "offline" while the phone is reachable. Pick from `adb devices -l` by model (for example `model:SM_S938U`) with state `device`, preferring the tailnet `ip:port` over `_adb-tls` entries. In loops and watchers, treat an unreachable phone or adb transport errors (`adb shell failed`, `not attached`) as a wait, not a failed attempt, or a reconnect will burn retry budgets and empty queues. Watchers must check by model, not by a stored port.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
