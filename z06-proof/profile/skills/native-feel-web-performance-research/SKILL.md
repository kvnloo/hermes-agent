---
name: native-feel-web-performance-research
description: Use when researching native-feel web performance.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, performance, web, latency]
    related_skills: [grounded-citations, agent-reach]
---

# Native-feel web performance research

## When to Use

Use for source-backed research into touch latency, high-refresh rendering, deep-zoom viewers and site-specific performance budgets.

1. Inspect actual source, asset policy, accepted traces and verifier limits first. Pin build and asset revisions; distinguish intended from supported surfaces.
2. Separate physical input-to-photon, handler CPU, submission, rAF cadence and actual presentation. A 120 Hz panel does not guarantee 120 Hz page updates; headless traces cannot certify physical latency.
3. Read current implementation plus PR merge/revert history. Historical performance optimizations may be reverted or superseded. Native microbenchmarks do not establish browser speedups.
4. Split tile acquisition, decode, upload/paint and publication queues. Count warming in aggregate request limits. Track decoded reservations, blobs, floor/front/back buffers and GPU textures separately.
5. Move existing pixels immediately without waiting for network, settle, React or workers. Preserve pointer ordering, cancellation and anchors. Predictions are reversible previews, not authoritative state.
6. Separate cold-network, disk-cache-warm and decoded-cache-warm trials. Anchor HQ latency to the user event, not queue eligibility; include failures and timeouts.
7. Label proposed budgets versus attained results. Pair aspirational targets with immediate non-regression gates. Retain max, missed-frame fraction and streaks; INP and LoAF do not fully cover continuous motion.
8. Check static-export/image configuration before prescribing image optimizers. Use responsive assets, early LCP discovery and deferred below-fold work. Preserve semantic HTML and focus/find fallbacks when windowing.
9. Retrieve primary API docs, exact source and implementation history. Register citations as retrieved; mechanically render and verify the source ledger. Keep private histories out of public ranking/publication.
10. Deliver ranked sources, surface/branch ownership, measurable budgets, real-device/lifecycle experiments, approval gates and NOT RUN dimensions. Research does not authorize an engine rewrite.

## Pitfalls

- JS-driven CSS transforms still depend on JS update cadence.
- Async image APIs do not guarantee upload/publication is free.
- Content visibility skips rendering, not transfer or DOM construction.
- GPU migration can regress; compare equal-quality workloads and fallback costs.
- For read-only archive research, inspect the installed reader and disable auto-start paths that could migrate or restart services.
