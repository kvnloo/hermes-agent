---
name: detent-launcher-fork
description: "Use when building or theming the Detent launcher fork."
version: 0.1.0
author: Hermes Agent
license: MIT
---

# detent-launcher-fork

Use when building, theming, qualifying or releasing the Detent launcher fork.

## Rules

1. Identify both phones with `dumpsys package` and `pm path`. Match installed APK bytes and embedded identity to current remote channel refs and the worktree registry before choosing a base. Use `/mnt/zer0models/workspace/zer0/oss/detent` as the canonical checkout, preserving dirty work.
2. Read current `docs/GITOPS.md`, `.github/channels.json` and delivery scripts. Route feature/fix PRs through preview, then nightly integration, then separately approved stable main. Reserve main's `ci/*` exception for allowed CI/doc paths. Use upstream issues where upstream PRs are disabled.
3. Bind checks and merges to the exact head with `gh pr merge N --merge --match-head-commit <checked SHA>`. Count JUnit results in `checks-reports-<sha>` and explain skips beyond the fast lane's `DETENT_IMPORT_SMOKE` omission. Open and watch preview-to-nightly promotion after landing. Verify the PR's actual integration jobs before declaring nightly green.
4. Integrate the current channel base before qualification. Preserve backup/restore, built-in name selection and imported-theme IDs together. Rebuild and repeat acceptance after any source change. Label base-plus-patch builds exploratory and keep private untracked files outside public payloads.
5. Request Android builds off groot with `fleet-build --android --class build` or the repository CI path. Give fleet-runner requests unique `request_id` values. Produce lab and phone artifacts from one source/run with separate filenames and provenance hashes.
6. Qualify `app.detent.launcher.lab` on the physical S22 before S25 rollout. Back up and restore settings/files, disable test lock-wallpaper writes, and use an owned focus-safe display. Observe the feature plus collection discovery, import, saved-local restart, duplicates, both reveal directions, distant taps and crashes. Validate the matching receipt with `provenance.qualification`; see `references/android-channel-releases.md`.
7. Re-sign the exact checked artifacts with `/mnt/zer0models/workspace/zer0/data/operations/phone-portal/detent/signing/detent-kvn.jks`, alias `detent-kvn`. Retrieve `DETENT_FORK_KEYSTORE_PASSWORD` through bws in one secret-preserving subprocess and a mode-600 temporary file. Use `--ks-pass file:<file>` once, then remove it. Verify payload entries and certificate before `adb install -r`.
8. Install `app.detent.launcher.kvn` on S25 only for the S22-qualified source/run. Preserve preferences, HOME and live wallpaper, and obtain explicit authority for certificate-mismatch recovery rather than uninstalling. Use `GH_SHIM_DIRECT=1` for deploys and confirm the real preview head. Pull installed bytes from fresh `pm path` and verify signed hash and identity. Keep authored, checked, merged, S22-qualified and S25-installed receipts separate.
9. Keep the HOME-role launcher on display 0. Test the non-HOME lab on your own display and preserve both global focus values. Qualify wallpaper transparency on display 0 with owner coordination. Skip lock-wall bitmap writes for system/live themes and verify `WallpaperManager.wallpaperInfo`, not a stale applied key. Follow `references/live-wallpaper-sync.md` for package parsing, `.ts.net` admission and SHA-256 checks.
10. Preserve hold-to-act, bare-rim letter jump and explicit Move selection. Let dwell/pressure reveal options without committing changes. Require deliberate sideways travel before side selection, keep one foreground label owner through hold-to-glass motion, and retain Back cancellation and Undo. Store folder default, member order, tap action and swipe app separately. Read `references/interaction-model.md` for journeys, using the main source's explicitly adopted capsule-pill treatment.
11. Use Elemental UI glass from `/mnt/zer0models/workspace/zer0/products/elemental-ui`, consistent HoldChip/SlideChip controls and hairline glyphs at every folder-name site. Invert selected pills on light themes, keep outer labels short, and curate at most six panes. Remember `mix(a,b,t)` weights the first colour. Inspect cancelled/off-notch holds and mirrored dark/light layouts on S22 before rollout.
12. Keep theme downloads bounded and atomic, publish observable theme changes on the main thread, and deduplicate by source-derived IDs. Preserve imported entries through live reload and resolve saved IDs/names before legacy indices. Decode complete backdrops off-main and track unwrapped motion plus distant-tap destinations. Separate parser/Robolectric evidence from native acceptance.
13. Keep overlays inside DetentRoot providers and consume background touches. Preserve clock tap/hold/drag semantics and accessibility. Treat widget IDs as installation-local resources with allocation, binding, configuration, cancellation and recreation cleanup. Qualify real widget interactions and dark/light rendering before reporting support.
14. Retain private phone evidence outside public source and update `.files/docs/phone-setup/README.md`, `scripts/phone-setup` and `scripts/phone-setup-handoff` to the verified channel. Preserve friends' separate package IDs. Track owned driver PIDs and exact PR heads rather than using broad process matching or stale branch/version notes.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
