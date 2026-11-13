---
name: rendered-ui-qualification
description: "Use when calling UI work done. Run real turns, view renders."
version: 1.0.0
metadata:
  hermes:
    tags: [qualification, e2e, ui, vision, testing, tern]
    related_skills: [hermes-tern-parity-orchestration, dogfood]
---

# rendered-ui-qualification

Use when qualifying UI changes, reproducing owner-reported frontend bugs, running exploratory testers, or preparing a UI completion or merge claim.

## Rules

1. Map each owner requirement to its implementation seam and acceptance evidence. Integrate delegated work through real imports, mounts, metadata, fallbacks and parent constraints. Import a requested library and compare its own reference render; identify any engine-only integration explicitly.
2. Read the overall pipeline and raw stage receipts. Verify inherited failures against the unchanged base. Report passed, skipped and total counts separately, and separate authored checks, executed gates and native acceptance.
3. Replay the owner's actual journey from session evidence. For agent frontends, run a real model turn through populated transcripts, tools, streaming and retained drafts across close/reopen. For other sites, exercise navigation and persisted state. Label fixtures, snapshot replay and synthetic audio separately from physical continuity.
4. Capture about 80, 100 and 160 columns and applicable phone widths. Inspect every PNG, including small text. Cover the entire phone page with overlapping viewport slices and contact sheets; log active-tab and sticky-section state per slice. Fix defects, recapture, then recheck desktop.
5. Qualify the exact delivered URL or APK with its build SHA, console and reachable owner-device path. Report emulation versus physical-device coverage and every missing real-device check. Reopen stale Android Chrome artifacts with a build-specific query parameter; an existing-tab VIEW intent is only activation.
6. Preview from the worktree or a separate installation on the owner's real profile with a per-invocation model override. Start a new background-tab session. Preserve the active plugin, session and keyboard focus; reserve reinstall for turn end with owner approval. Capture with `tern capture <block> --surfaces` or `tern ctl shot NAME`, using `[A-Za-z0-9_.-]+`, and drive the preview with `tern send <block> keys ...`.
7. Match evidence to the defect. Use before/after images for visual-only changes and a focused regression plus rendered replay for interaction, state or data-flow bugs. Test natural owner wording, visible effects and actual navigation clicks. Guard one-time localStorage seeding with sessionStorage so reload tests preserve data.
8. Measure overflow per element with getBoundingClientRect, and inspect intentional scroll containers separately. Keep mobile interaction results visible, fixed rails padded with targets at least 40 px, and footer hints nonwrapping by priority. Use `minmax(0, 1fr)` for shrinkable grids and `flex: 0 0 auto` for intrinsic dialog stages; assert content ends before bottom navigation.
9. Await bounded observable state before dependent clicks and after dialog closure, including scroll unlock and restored focus. Use real-time CDP input and screenshots for canvas gestures; surface render-loop exceptions. For long injected suites, acknowledge immediately and inspect the retained completion receipt before starting another run.
10. Use third-party free test models only on public sites. Keep private authenticated content outside that route unless separately authorized. Select general test models from measured normal free routes with working tools; reserve paid models and special-purpose helper routes from general test turns. Probe image input plus tools for exploratory web agents. Use labelled sandbox demo connectors instead of owner account credentials, and keep desktop captures off unrelated tabs.
11. Run a screenshot-backed findings-only tester army each wave and before a main merge request. For web requests naming the army, use tester-army's `e2e explore`, not substitute Playwright tests. Follow references/tester-army.md for isolation and concurrency; reproduce each finding on the same build before fixing it. Classify provider failures as coverage gaps and preserve interrupted exit codes.
12. Audit past failures by source under `nice -n 19 ionice -c3`, one heavy query at a time, no GPU or reindex, capped outputs and redaction. Use bounded ctx CLI searches rather than broad MCP fan-out. Preserve append-only JSONL evidence and rank preventive journey gates by severity and recurrence; report thin coverage.
13. Prove voice-plus-pen linkage with scenario-matched fake-mic audio and recording-clock strokes. Assert server word-to-mark links and crops, then inspect thread, popover and phone renders. Require HTTPS or localhost for microphone access, and stop only the dedicated browser PID. Follow references/voice-pen-e2e.md.
14. Diagnose T3 preview exit 137 using cgroup and kernel evidence. Try `T3CODE_BUNDLED_DEV=0` with the repo's Node and a bounded heap inside the existing envelope. When pressure relief keeps stopping Vite, switch to off-host web export and a small static proxy rather than repeated restarts or raised limits. Check tailnet routing and the transformed module before sharing an unconsumed pairing URL.
15. Keep capture/import into a new container independent of current-container constraints; back up endangered raw captures first. Limit camera overlays to about 15 percent, keep progress glanceable with details hidden, and derive cheap search results during render rather than background-throttled rAF. Pause new feature merges when real use reveals bugs; deliver a working rendered prototype when the owner asks to see an idea.
16. Treat information architecture as an acceptance criterion; the owner judges a page by whether its organization is sane at a glance. For every tree or grouped list, add a test built from production-shaped data (real counts and mixes, such as many profiles, several harnesses and hundreds of chats) that walks the tree and asserts each level holds one kind of node, nothing is lost or duplicated, and sibling labels share one naming scheme. Run the test against the old code first to prove it fails. Then check that some e2e journey actually expands every kind of top-level container, because a suite that only opens the easy case (phones, empty hosts) passes while the real view is a mess. Before claiming that a tested build is current, check whether the owner's build already contains the latest commit for that file (`git log --all -- <file>`, then `merge-base --is-ancestor` against the served SHA).
17. When prototyping alternative views, put them behind one switcher with shared filters. Default to the simplest view and deep-link each one (`?view=`). Apply rule 16's one-kind-per-level check to every view, including grouped work trees where loose tasks tend to end up beside features.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
