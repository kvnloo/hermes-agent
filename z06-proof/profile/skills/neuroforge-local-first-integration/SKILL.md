---
name: neuroforge-local-first-integration
description: Use when integrating Neuroforge learning and telemetry.
version: 0.1.0
---

# Neuroforge local-first integration

Keep code in the discovered Neuroforge repository and private state/runtime/cache under `/mnt/zer0models/sft-svlm/data/neuroforge`. Keep behavioral/learning analytics in the existing `/mnt/zer0models/sft-svlm/data/telemetry/activity/state/analytics/projection.duckdb`; never create a second production projection. Use separate worker worktrees and exclusive file ownership. Only the analytics lane writes that database.

## Integration gates

- Inspect commits, owned-path diffs, clean status and receipts before parent integration. Workers share Git administration; commit with an explicit per-command author if repository identity is unavailable, rather than altering global Git configuration. Never push or publish private content without authorization.
- Validate Anki through stock Anki on marked disposable collections. Keep scheduling solely in Anki. A package import or synthetic review is not human dogfood. Preserve real card settings/history; require approval for real collection writes.
- Serve the Anki bridge read-only on an explicit loopback address; inspect `/health`, `/v1/notes`, `/v1/due`, `/v1/practice`. Do not reinterpret Anki's raw due values or treat snapshot queues as independent schedules.
- Exercise the actual game HTTP producer -> private test outbox -> actual normalizer/importer -> in-memory test store. Assert stable UUIDs, privacy, zero duplicate replay and practice-vs-evaluation separation. Never place untagged synthetic records in live outboxes.
- Pin spatial positions/IDs/bindings across themes and saves. Preserve KMind MPL license and copied-file provenance. GPU draw receipts do not prove visual appearance or learning efficacy.
- Compare live AW event end times with projected watermarks. A successful incremental import can still miss revisions to long-started heartbeat intervals; test timestamp-filter boundaries and distinguish stale inactive-state history from current collector liveness.
- Qualify AW backend migration on online SQLite backups, preserve device identity and rollback receipts, and use one backend plus an unbundled watcher. Do not execute a replacement merely because copied migration passes.

## Terminal-only progression gates

- Keep optional quest practice open even before dependency connections; derive cosmetic unlocks from recorded activity, not answer choices, confidence, or claims of mastery. Give assisted and independent practice the same credit and retain prior credit across retries.
- Add progression to the existing versioned save rather than a second persistence/analytics path. Keep the discovery key stable, migrate older payloads only in memory on read, preserve the original as backup on write, and never reinterpret old self-reports as new quest completions.
- Validate bounded per-quest drafts and summaries against the public catalog, including run identity, round sequencing, duplicate replay and impossible count chronology. Keep fixed spatial IDs, bindings and the layout generator independent of theme, quest order and content expansion.
- Under a no-GUI boundary, boot the actual entrypoint in a Node-emulated DOM with CSS imports handled by a module hook, graphics context creation returning null, inert interval registration, and fixture-only fetch. Exercise native control handlers through the real reducer/save path; label focus/semantic tests as DOM tests, not actual keyboard or visual evidence.
- Read back the real built artifact through an owned loopback listener bound to port zero, compare file bytes/hashes, and close that listener in a finally block on both success and invalid-build failure. Never attach to or restart parent-owned services to prove static integration.

## Desktop safety

After a desktop-takeover report, stop all GUI launches and continue terminal-only tasks. Wayland-nested Sway can create a host window; its name is not containment evidence. Require a genuinely headless backend and remove host DISPLAY/WAYLAND/SWAYSOCK/DBus/Hyprland routes. Discover `hyprctl instances -j` if ordinary queries fail, then inspect the exact instance without titles. Never change focus without a recorded prior target; never terminate unrelated sessions by process name.
