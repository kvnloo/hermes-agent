---
name: bookmark-sync-taste-evidence
description: Use when syncing bookmarks or finding a liked/saved post.
version: 0.1.0
author: Kevin Rajan (kvnloo), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [bookmarks, research, visual-design, evidence]
    related_skills: [agent-reach, grounded-citations]
---

# Bookmark sync and visual taste evidence

## When to use
Use for authorized personal bookmark refreshes and evidence-backed preference profiles. Also use it to find a half-remembered post the owner liked or bookmarked; follow `references/x-personal-history.md` for that. That file covers history surfaces, signed-in global X search (including the search-404 fix), visual video scanning and reporting. Read-only throughout. Do not assume saved items are endorsement or publish private collections.

## Procedure
1. Discover the real corpus, not just a similarly named public skill repository. Enumerate the user's accessible repositories and organizations, inspect candidate READMEs, and check local Git remotes. Report local-only state explicitly.
2. Preserve the old export. Read the installed sync CLI help and source/config before claiming a large requested count is honored. A CLI may cap requested results silently.
3. Use existing configured authentication without printing secrets. If absent, stop that source and report the missing authentication. Do not invent a new credential path.
4. If the native CLI caps results, use a supported count override where available. Otherwise, with the user's export authorization, inspect the installed client's pagination contract and use a read-only bounded helper without editing installed packages. Private client APIs require compatibility checks on upgrade.
5. Pace requests, stop on rate limits/errors, checkpoint each page and deduplicate by immutable ID. Record page count and the actual stopping condition. A repeated cursor with an empty page is endpoint termination, not independent proof of an account-wide total.
6. Reconcile old/current sets programmatically: overlap, new-to-export, archive-only and union. Preserve missing old links; absence does not establish deletion or unbookmarking.
7. Make topic classification reproducible and label lexical estimates honestly. Retain unclassified and visual-only posts. Separate platform, author, topic and media-type counts; explain overlapping categories.
8. Inspect actual representative media with vision. For video, extract timestamped early/middle/late samples and keep source URLs and hashes. Do not infer sound or full-speed motion from frames. For X image URLs returning 404, test an explicit supported size query such as `?name=large` before declaring the image unavailable.
9. Bound media downloads without silently truncating files. Read one byte beyond a size budget and fail explicitly if exceeded; a truncated MP4 may partly decode and produce misleading evidence.
10. Distinguish user-specific statements, prior review opinions, installed generic design recipes, observed artifacts and bookmark inferences. Resolve conflicting recipe defaults in favor of explicit user evidence and the surface's actual purpose.
11. Produce a cited profile plus a machine-readable inventory and curated selection. Count/dedupe/sort in code; verify requested selection length, source membership, citation targets and media hashes. Do not commit or publish unless explicitly authorized or required by a confirmed normal workflow.

## Pitfalls
- A completed checkpoint directory may cause a helper to exit immediately; use a fresh output directory for a later refresh.
- A prototype's initial music/brand/theme selection is not proof the user approved it.
- A generic anti-slop skill's font/palette bans are not a personal taste survey.
- Remote image availability and screenshot compression are not aesthetic evidence.
- Keep raw exports and derived selections private; do not send private corpus passages to external ranking services.

## Verification
Use real exports and receipts, not requested counts. Verify current unique IDs, archive overlap, missing entries, stop reason and output hash. Verify every curated URL maps to a source record and every local citation exists. State visual sampling and audio-listening limits explicitly.
