---
name: activitywatch-local-sync
description: "Use when planning local ActivityWatch device sync."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [activitywatch, syncthing, android, research, privacy]
    related_skills: [github, grounded-citations]
---

# Local ActivityWatch sync research and planning

## When to Use

Use for release/compatibility research and approval-gated planning of local-only ActivityWatch desktop and Android sync.

## Procedure

- Query public GitHub release APIs for desktop ActivityWatch and aw-android separately; select non-prerelease releases rather than the newest tag. Do not substitute Research Edition or beta builds for standard stable.
- Treat aw-server-rust and aw-sync as desktop-release components. Check whether the Rust repo actually has standalone releases; resolve the desktop tag's Rust submodule SHA and packaging before naming downloads. aw-sync's crate/CLI version is not the desktop release number.
- Cross-check sync docs against release-pinned source. READMEs can retain obsolete two-level versus Android three-level discovery limitations after code and the official blog are fixed. Inspect sync_run/discover_peers and daemon mode; disclose disagreements.
- Distinguish ActivityWatch imports from file transport. aw-sync stages data in a dedicated directory and does not send it over the network. Share that directory, never the live production datastore. Android may push only while desktop can pull and push.
- Plan server replacement as a controlled cutover, not an additional launcher. The awatcher bundle embeds a server. Its unbundled aw-awatcher replaces both AFK and window watchers. Never infer --no-server selects another backend: consult its documented meaning.
- Preserve the existing DB, SQLite sidecars and configuration before approved schema upgrades. --no-legacy-import suppresses Python import, not Rust schema migrations. Never promise that upgrading repairs a poisoned datastore; never delete/recreate data without authorization.
- Check Syncthing's official Community Contributions page for the current maintained Android integration. The original Android app is discontinued; label community forks distinctly from official core.
- For local-only sync, disable global discovery, relaying and NAT traversal. Pair only approved peers/folders. Local discovery broadcasts device IDs on the LAN; use explicit local addresses if unacceptable. Review telemetry and crash reports separately. Update checks may remain, so settings do not prove zero internet traffic.
- Require manual user grants for Android permissions. ActivityWatch usage access differs from optional browser accessibility, media notification access and widget exact alarms. Its sync directory uses a folder picker; Syncthing native access may require broad All files access. Camera and SSID location can be optional; verify the selected release.
- During read-only research, do not install apps, grant ADB permissions, alter services/firewalls, write sync data or migrate databases.

## Approval-gated executable preparation

- When phone transport is blocked, qualify desktop transport with disposable peers and synthetic official-shaped exports; never substitute that receipt for Android/LAN sync or backend ingestion.
- Generate a fresh Syncthing home with `generate --no-port-probing`, harden it before the first `serve`, and keep unpaired folders paused. Use explicit loopback/private TCP addresses; disable local/global discovery, relays, NAT/STUN, usage/crash reporting and upgrades. Replace dormant default URLs as well because omitted values may restore upstream defaults. Keep keys, configs, logs and fixtures in restricted private state.
- Read the effective running configuration and certificate peer identity through the local API, then trace the owned processes' actual network syscalls. Do not infer internet isolation merely from input config. Keep trace payload strings suppressed and distinguish bounded observations from future traffic guarantees.
- Obtain OS-assigned loopback listener addresses from the running instance before wiring the second fixture peer; do not probe a port and release it before binding. Handle TERM/INT and verify process-group and listener cleanup, including a real cancellation test.
- Validate literal Syncthing IDs and checksums before pairing; ActivityWatch UUIDs are different identifiers. Require exact configured/approved peer address agreement and explicit boolean permission attestations. Preparation must never grant Android All files access or silently repair malformed identifiers.
- For an authorized USB fallback, copy only the dedicated official exported `hostname/device_uuid/test.db`, require remote-before/local/remote-after hashes to match, and run the staged official `aw-sync status`. An explicit unreachable loopback port permits offline status inspection without querying the live AW backend. Read-only immutable SQLite inspection is restricted to that copied export, after tool classification and integrity checks, and must emit only approved identity/count/timing fields—not arbitrary app history.
- Keep service templates uninstalled and without an Install target; use absent approval-file conditions and a paused transport until parent review. A template or consent manifest is not evidence of runtime permission, pairing, or live backend compatibility.

## Evidence to return

Exact release pages and assets; OS/API requirements; official/community/experimental status; manual permission gates; sync direction; source conflicts; what was not tested. Re-query releases each session instead of preserving version numbers as timeless facts.
