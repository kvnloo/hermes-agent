---
name: dash-event-log-watch-qualification
description: Use when qualifying Dash event-driven log watching.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [dash, logs, android, systemd, oauth, qualification]
    related_skills: [dotfiles-desktop-work, home-k3s-fleet, dash-summary-transport-qualification, phone-adb-tailnet-qualification]
---

# Dash event-driven log watcher

## When to Use

Use when implementing, deploying or requalifying report-only foreground-gated Dash log monitoring and its bounded Luna transport.

## Procedure

- Discover existing health/watch tooling with resident FFF first, then bounded local search when index results miss evidence. Isolate changes in a new `.files` worktree; never edit or restart the served bridge/Metros.
- Reuse the SHA-pinned Dash `summary-oauth.py` helper for exact-model, tool-free raw Codex requests. Locate its actual worktree before assuming it exists in the served bridge. Fresh authenticated catalog plus a response whose native model matches bare `gpt-6-luna` is the qualification; a gateway disconnect is unknown outcome, not a model refusal and not permission for a fallback.
- Read actual systemd unit names and compare the watcher's subscribed units against every currently served stable/turbo Metro and relay. A renamed or added live service is a coverage gap even when the watcher remains active.
- Audit coverage before describing an attached monitoring agent: verify source ingestion, symptom classification, foreground admission, reviewer invocation, persisted report and owner-visible delivery separately. Report-only journals, Android activity-event tracking, app-error logcat, performance sampling and automatic repair are distinct capabilities; never imply one proves the others.
- Replay the owner's exact error spelling through the actual classifier before trusting zero incidents. Cover React Native `Uncaught (in promise, id: …)`, CursorWindow/oversized-row errors and their native variants explicitly; generic uncaughtException/UnhandledPromiseRejection patterns do not cover those strings. Correlate retained source-log entries with watcher counters, and distinguish missed classification from foreground suppression or unavailable input.
- Observe the current top-resumed package before interpreting a background gate as broken. Reading the owner's report in Telegram legitimately moves Dash to the background; current gate state does not establish whether the original error was admitted.
- Resolve wireless ADB through existing pinned hardware state and reconnect helper. If saved state is stale while a known authorized endpoint is connected, verify it using that helper's `connect` command; never select arbitrary devices or scan other hosts.
- Parse `adb track-devices` output as four ASCII hex length bytes followed by a full payload. The CLI does not provide blank-line-delimited snapshots; prove framing with a real bounded read and deterministic loss fixture.
- Subscribe to activity events before the initial device-clock-watermarked top-resumed snapshot. Reject Expo/websocket evidence, similar package prefixes and pre-snapshot events. ADB loss means UNKNOWN; never let a stale stream reopen admission after transport loss.
- Send only finite diagnostic enums/source labels/counts/timestamps/evidence hashes to inference. Keep raw messages/chats/prompts/URLs/tokens out of both model input and reports. Preserve exact journal cursor and canonical JSON SHA-256 locally for evidence retrieval.
- Bound each burst, one reviewer per seat, global concurrency, persisted hourly starts/reservations, output and wall time. Healthy logs use zero model calls. Provider failures become local unavailable reports and error-triggered cooldown, not idle polling or paid fallback.
- Coalesce healthy journal cursor/status fsyncs with an event-triggered one-shot rather than committing every log line; yield during large bursts so foreground-loss events cannot starve.
- Run CPU suites through `fleet-build --node mbp`; real owned synthetic journal replay is a declared local lightweight service verification, not a production crash. Keep fixture state separate from live state and mark every receipt fixture=true.
- Link only the owned new CLI/unit/config; verify actual systemd state, process tree, config hashes and protected status. Do not use `After=default.target` on a unit wanted by that target, because target dependency ordering can cycle.
- Keep critical alerts local unless a supported Dash notification/inbox adapter is proven by exact readback. Do not claim the owner saw an alert or that fixtures prove live foreground transitions, provider concurrency, production faults or delivery.

Canonical implementation guide: `docs/dash-log-watch.md` in the watcher `.files` branch. Read the live unit/config and worktree registry before changing a deployment; this skill does not authorize service restarts or an unreviewed branch rollout.
