---
name: limitless-stack-operations
description: "Use when working on Kevin's Limitless/NZT sleep-habit stack."
---

# Limitless (NZT) stack: how it is wired

Covers sleep, habits, NOOP data and learning (KMind/Anki).

## Owner constraints (his words, 2026-10/11)
- He can't stick to a strict calendar or a steady sleep routine. Deep work holds 90–180 min in early sessions and 60–90 min later. Bedtime has drifted to about 3 am; his stated goal is "12 or 1am". Ideas arrive near bedtime: capture them, don't start work; agents carry plans overnight.
- Design rule: cues are events (waking, end of a deep block, wind-down), not clock times; starts take 2 minutes or less; a skipped day is unlogged, not failed; add one layer at a time.
- Sequencing authority for the learning side is oss-factory#212 (KMind M0 first). Research ideas live under noop#94, one at a time.

## Privacy routing
- Health, sleep, phone-usage and ChatGPT personal chats go to the Opus parent or local scripts only. Never send them to free models or outside APIs.
- Free or other lanes only get public material (public repo docs, OSS lessons). OpenCode free quota is account-wide; when it is spent, use agy Gemini Flash with the docs pasted inline.
- Private store: `/mnt/zer0models/sft-svlm/data/limitless/` and `/mnt/zer0models/workspace/zer0/data/operations/nzt-protocol-20261103/` (PLAN.md, issues, ChatGPT captures). Keep everything 0700/0600 and out of Git.

## Data plane
- `limitless-sync` (kvnloo/.files#140; `~/.local/bin`, user timer every 15 min; config `~/.config/limitless/config.json`). It records home/away from the phone's Wi-Fi class (no location), copies the AW Android export and NOOP's DB (debug build, run-as), writes `state/digests.jsonl` (unlock-gap sleep proxy, night screen minutes, NOOP sleep/journal, away time), sends one morning Dash line, and walks circadiand `bedTarget` along a weekly 15-min ramp to 01:00.
- Commands: `limitless-sync report 7`, `digest --date D`, `status`.
- circadiand (`~/.config/circadian/config.json`) reads config only at start; limitless-sync restarts it after changing bedTarget.
- NOOP: Health Connect auto-sync is on (6 h). The background worker (noop#104) is installed in the debug build with the background-read permission granted. Confirm a closed-app run from `noop.hcLastSync` in shared_prefs after the period has elapsed. Custom journal items: hot shower within 2 h of bed; cold shower; outdoor light within 1 h of waking.
- Wearables, as they actually behave in NOOP:
  - WHOOP 5.0/MG: live heart rate only. The strap refuses NOOP's pairing handshake, so it never gets a clock and stores no history (no sleep or recovery). Check the upstream release notes before promising otherwise.
  - Oura Ring 4: paired with the debug app and set as its active device. NOOP takes the ring over from the Oura app, so while NOOP holds it the Oura app writes nothing to Health Connect.
  - NOOP drives one device at a time.
- When the owner asks where wearable data went, answer from per-device freshness in the copy:
  - Run `select deviceId,count(*),max(ts) from hrSample group by deviceId`, the same over `event` and `rrInterval`, and read the `pairedDevice` rows.
  - Then read the debug strap log (see skill noop-android-s25-feature-ship).
  - A stream that stops mid-flow with no disconnect logged usually means the ring's battery ran flat.
- Two NOOP installs, two roles. `com.noop.whoop.staging` is where the owner paired the WHOOP 4.0. It is a release build: no `run-as`, no Health Connect permissions, no backup folder, so groot cannot read it. `com.noop.whoop.debug` carries the agent API and is the one limitless-sync copies. When he says "it's syncing in staging", check staging's own state before claiming data: open it on the focus-safe display and read Today ("Strap history synced Nd ago"), Devices ("Last seen N d ago") and the Sleep tab. A running WhoopConnectionService only means the app is waiting, not connected. To get staging's data onto groot, give him the choice: turn on staging's "Share back to Health Connect" (the debug app then imports it), or pair the strap with the debug app instead. Never move the strap or change staging's settings yourself.
- Before analysing sleep, check freshness (newest `hrSample`/`sleepSession` in the copy, and staging's last-seen) and ask which wearable he actually sleeps in. Only the Oura is bonded in phone Bluetooth; the WHOOP talks to NOOP over BLE without a bond.

## Learning
- Lessons source: kvnloo/what-i-learned-from-oss PR #1 (9 lessons). The OSS waves in ChatGPT end with "the chunk to retain"; those feed new cards and lessons.
- AnkiDroid 2.25.3 is on the S25; deck `Download/limitless-oss-lessons.apkg` (45 cards, built in a disposable collection with the neuroforge Anki venv). Never write to his real Anki collection.
- KMind Palace 0.1.1 (stock release) is set up in the Obsidian vault `/mnt/zer0models/sft-svlm/data/limitless/kmind-vault`; his main vault is `~/workspace/obsidian` (leave it alone).

## Open work
- Detent night dial driven by a wind-down broadcast from groot. Coordinate with any live Detent session first.
- Dash capture-only wiring (dash#557): capture-gate, overnight-captures and break-nudge exist but are not imported anywhere.
