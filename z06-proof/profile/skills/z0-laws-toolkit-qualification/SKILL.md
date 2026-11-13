---
name: z0-laws-toolkit-qualification
description: Use when qualifying z0 shared laws caches and commands.
version: 1.0.0
author: Nous Research
license: MIT
metadata:
  hermes:
    tags: [z0, bend, verification, caches]
    related_skills: [no-mistakes]
---

# z0 shared laws qualification

## When to Use

Use for changes to the shared Bend toolchain, checker caches, manifest, command,
scaffolds, or unchanged receipts. This is local qualification, not authorization
to publish or enable runtime policy.

## Workflow

Read the consumer's `laws.toml` and z0's `lib/laws/toolchain.json`, `docs/laws/README.md`, and benchmark method before making cache or timing claims. z0 owns verification/install tooling; twins remain consumer runtime code.

- Resume the existing feature branch and inspect staged and unstaged work before editing. Preserve local-only delivery constraints.
- Run `scripts/laws-bench` with explicit owned TMPDIR and `--output`. Distinguish cold checker HOME, cold toolchain installation, OS page cache, and cached-checker CLI timings. Compiler subprocess times are subtracted from the direct verdict; mutation may include another compile. Report sampled logical high-water bytes, not cumulative I/O or a syscall audit.
- Accept sealed caches only after identity and artifact validation. Test stale keys, changed artifacts/symlinks/unlisted files, and changes to every checker-key input. Do not silently repair a rejected cache or weaken tests for speed.
- Exercise actual `init -> check -> prove -> prove` in an isolated consumer. Expect real parity with no skips, then `proven`, then explicit `unchanged`. Change valid Bend file content (a trailing newline works) and require `proven` again. Introduce a false law, require failure, restore it, and require a fresh positive proof. Bend does not accept JavaScript `//` comments.
- `./z0 laws check` supplies the pinned environment and rejects empty/skipped tests. Direct unittest discovery without that environment intentionally skips native Bend tests. For full pinned discovery, enter `laws.verifier.verifier_environment()`, patch `os.environ` with its returned environment plus `Z0_REQUIRE_BEND=1`, and run unittest discovery sequentially in the same process; nested verifier entries share the validated context.
- Use a non-personal, non-`/tmp` scratch path for full repository discovery. Existing fake-host schema tests reject personal home paths when TMPDIR is home-based. Keep the benchmark's explicit home-based TMPDIR separate; do not loosen the schema or skip its test.
- Run `scripts/public-leak-check` after staging new docs, so tracked-file scanning includes them. Check shell syntax and `git diff --check`. State unavailable syscall tracing or hosted CI honestly.
- Local locks are optimization receipts, not attestations. CI must run `prove --all`. Keep `proof_is_permission` and `source_semantics_attested` false.
