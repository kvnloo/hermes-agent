---
name: public-lineage-static-island
description: Use when publishing private visual archives as static web.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [web, privacy, performance, archives]
    related_skills: [showcase-site-feature-work, test-driven-development]
---

# Public visual lineage, bounded static runtime

## When to Use

Use for a public static edition of a local visual review archive, especially when privacy, content-addressed images, bounded rendering and measured mobile budgets must all hold.

## Procedure

1. Project private archives into a finite public schema; never redact and copy the original object. Synthesize short captions from validated identifiers. Normalize date-source and phase labels through explicit allowlists and fail on unknown categories. Keep file modification times distinct from creation receipts.
2. Pin history to the current-selection manifest digest and validate per-theme counts, unique version IDs and exact current membership before encoding. A deduplicated representative and a later CURRENT occurrence may have different pixels: publish both derivatives and label which date/hash belongs to the representative.
3. Encode two thumbnail sizes and an on-demand medium with exact dimensions, no image metadata, and filenames hashed from output bytes. Budget unique keys, not every occurrence. Put derivatives in the designated asset repository on its own local branch; never push implicitly.
4. Use an explicit bounded DOM window with fixed row geometry, retained keyed cards, passive scroll plus a single rAF, and layout/paint containment. Preserve native modal focus, cold deep links, keyboard traversal across unmounted rows and empty/error states.
5. For an exported Next static island with no client components, a targeted postbuild can remove its framework runtime and inline its small built CSS. Preserve only script tags whose opening tag has the exact standalone module src: searching entire script contents accidentally retains RSC payloads containing that URL. Require ordinary document anchors for all incoming navigation; Next client routing would bypass the finalized HTML. Test basePath and asset-origin variants.
6. Test text geometry with a Range, not just document.scrollWidth: a global overflow-x:hidden can conceal a clipped headline. Inspect desktop and mobile screenshots after automation.
7. Measure total transferred route JS, Lighthouse simulated-mobile LCP/CLS, and raw scroll trace cadence separately from callback CPU cost. Low callback work is not a 120 Hz pass. Label local asset mirrors and software-rendered emulation; never describe them as deployed CDN or physical-device proof.
8. Give every Lighthouse invocation a pre-created mkdtemp profile under TMPDIR. A missing profile can launch Chrome before the launcher fails to write its pid, leaving an owned orphan that then blocks retries with SingletonLock. Kill only the exact owned instance, never other browsers.
9. For time scrubbing, precompute numeric time/order/scene-state tables from the public projection. Keep a bounded recycled state/chronological window: flipping opacity on hundreds of laid-out cards can create a large style/compositing spike even with zero geometry reads. Test equal timestamps explicitly; binary search alone can make left-arrow navigation stick. Preserve an optional version cursor in deep links and distinguish capture time from undated owner decisions.
10. Fingerprint imported static-island modules before hashing the entry module; hashing only the entry leaves mutable dependency URLs behind an immutable entrypoint. Verify native touch hit-testing separately from deterministic range-input traces, and retain independent scroll and scrub admission rather than substituting one for the other.
11. Sparse clones made with --no-checkout need their index populated before sparse reapply. Check staged status before adding assets; never commit a mass deletion caused by an uninitialized index. Use only exact owned paths for staging.
