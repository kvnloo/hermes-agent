---
name: source-backed-learning-lab
description: Use when building a source-backed learning data page.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [data, provenance, web, performance]
    related_skills: [source-backed-process-editorial, test-driven-development]
---
# Source-backed learning artifacts

## When to Use

Use for turning production histories, prompts, judge verdicts and owner decisions into public learning pages and agent-readable datasets.

## Procedure

- Separate artifact observations, explicit attempts, component/integration variants, baseline rejudges and editorial case studies before counting. A deduplicated gallery is not an experimental denominator.
- Re-read a concurrently produced dataset's final schema before freezing ingestion. Discovery rows can later split into artifact-history and explicit-round files; do not retain obsolete filtering silently.
- Normalize into indexed SQLite with explicit source hashes, foreign keys, uniqueness and explicit lineage only. Preserve null outcomes and timestamp bases. Rebuild twice from frozen inputs and compare bytes, then run integrity and foreign-key checks.
- Publish allowlisted fields, not scrubbed raw transcripts. Redact before clipping. Keep native owner messages as withheld metadata until selected excerpts are reviewed; source-scoped locks do not approve whole scenes.
- Distinguish verbatim prompt excerpts, review rules and editorial method summaries. Hash the full primary prompt only when available; otherwise identify the hash as excerpt-level provenance.
- Export small content-hashed aggregates separately from on-demand indexed records and year/undated partitions. Include byte lengths, SHA-256, interpretation rules, entity notes and source IDs in a manifest.
- Keep historical judge consistency, historical owner agreement and new calibration separate. Correlated repeated votes do not increase independent pair count. Report bounded acceptance spans and right-censoring; plateau truncation can lose later successes and does not prove saved cost.
- Build the human story from primary-verified claims with native disclosures and comparison images. Put denominators and unknowns beside charts, not only in a footer.
- Prefer server-rendered story content and a bounded progressive explorer over a chart framework. If deliberately eliminating framework hydration from a static export, enforce a strict single-route boundary: no React client components or client router navigation, ordinary anchors only, preserve JSON-LD, test the real export and a nonempty base path, and leave other routes untouched.
- Measure compressed scripts actually requested, mobile Lighthouse LCP/CLS, and browser interaction-event durations under CPU emulation. Label these as lab measurements, not physical 120 Hz or field-INP proof.
- Assemble root agent guides after companion branches are integrated. Check sitemap targets in the combined export and document project-subpath robots limitations. An offline GEO scorer validates attribution rules, not live retrieval performance; never fabricate model responses for a benchmark receipt.
