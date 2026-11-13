---
name: release-fragment-idempotence-qualification
description: "Use when qualifying fragment release retry safety."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, testing, release, upstream]
---

# Fragment release qualification

## When to Use

Use for release-fragment aggregation, interrupted file-consumption retries, or measured Git conflict counterfactuals. Qualify an existing owner's release tool without creating a competing repair.

## Procedure

1. Pin current owner head and integration base; read complete issue, PR comments, reviews and inline threads. Preserve the latest severity decision and suppress repeated diagnoses.
2. Export the unchanged official CLI and its package script into disposable real Git repositories. Commit a published baseline and contributor fragments on separate branches, then switch a release branch. Use distinct credited multiline entries, an unrelated file, and a directory README as preservation controls.
3. Invoke the official package script. In a child-only Node `--import` hook, wrap the minimal `node:fs/promises` syscall seam and call `syncBuiltinESMExports` before entrypoint import. Do not replace the assembler with a simulation.
4. Exercise healthy repeat, invalid batch, failure before output write, process SIGKILL immediately after output write, failure on a later removal, and SIGKILL after the first completed removal. Retry normally without the hook; count every exact entry, verify unrelated bytes and HEAD/ref preservation. A syscall-injected crash is executable interruption evidence, not a natural crash-frequency measurement.
5. Keep expected RED receipts separate from normal-path GREEN. Repeat on supported runtimes. Do not claim an owner fix exists unless the same frozen probe passes on that owner's actual current head.
6. Quantify conflict reduction on a complete pinned cohort, not historical totals. Admit lossless additive changelog migrations only: restore that path to each merge-base version, add the exact introduced prose as a unique fragment through a temporary Git index, and `merge-tree` the synthetic analysis commit against pinned main. Assert every other path is unchanged. Report removed path incidents and wholly conflict-free PRs separately; no estimated minutes saved.
7. Label synthetic analysis commits as non-delivery objects. Archive real fixtures, commands, results and original script hashes durably. Keep implementation/author ownership and publication approval separate.

Browser verification helpers must distinguish a gate's exit from wrapper cleanup. A post-cleanup TCP bind without SO_REUSEADDR can hit TIME_WAIT even when no listener remains; verify the owned processes and listening sockets before diagnosing a leaked server. Do not kill another listener.
