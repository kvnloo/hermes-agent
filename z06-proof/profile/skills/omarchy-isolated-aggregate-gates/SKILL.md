---
name: omarchy-isolated-aggregate-gates
description: "Use when qualifying Omarchy shell aggregates safely."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [omarchy, testing, isolation, upstream]
    related_skills: [upstream-contribution, systematic-debugging]
---

# Omarchy isolated aggregate gates

## When to Use

Use for exact-head Omarchy CLI/shell qualification, aggregate failure diagnosis, and safe baseline comparisons without modifying an installed desktop.

## Procedure

- Read the exact checkout's `AGENTS.md`, `docs/testing.md`, `agents/skills/install-scripts.md`, and relevant task guide before running its official `./test/cli` and `./test/shell`. Preserve the original owner's stack and compare an untouched exact parent under identical conditions.
- Inspect ancestor `package.json` files before attributing missing JavaScript exports to Node versions. Omarchy's guarded CommonJS exports can load as empty ESM exports under an ancestor `type: module`. Prove the same bytes fail/pass across module scopes, then use a short isolated bind such as `/src`; do not alter production modules or add a package.json workaround.
- Use an owned bubblewrap namespace with no network, host GUI sockets, hardware devices, writable host root, or real user HOME. Mount the source read-only and private scratch at `/tmp`; preserve real file modes. Provide only a private HOME matching the namespace's passwd path when tests validate that path. Never expose the real HOME to satisfy it.
- Bound stdout/stderr at the capture layer. Do not impose a small RLIMIT_FSIZE on every child: the Plymouth suite deliberately creates a sparse file larger than 64 MiB to test rejection. A log-size policy must not corrupt fixture inputs.
- A mode-0700 runtime directory is insufficient for update-inhibitor tests: the helper validates the real root-owned parent chain. Record uid maps and stat ownership. Namespace root can qualify the root-compatible lock fixture, but must not be treated as equivalent to non-root sudo-reuse coverage. Do not fake id/stat/sudo or weaken production checks to make a single-UID namespace appear multi-user.
- Keep the suite's own stubs, but do not invent missing `gum`, `mise`, companion-package checkouts, or OS services. Resolve allowed dependencies only from pinned provenance; otherwise name the blocked checks. Inspect actual helper argument contracts before calling fixture failures missing dependencies: `pacman -Q -- "$pkg"` is incompatible with an old stub that interprets `$2` as the package.
- Preserve full bounded logs and parse the official per-file summary. Count skipped files separately; a test file exits on its first failure, so assertion-line counts are not complete suite test totals. Report actual runner FAIL separately from downstream assertions NOT_RUN because prerequisites or earlier assertions blocked them.
- Keep shared heavy-lock admission failures distinct from executed test failures. Honor the host's actual cgroup and CPU limits; do not infer that requested systemd-run flags created a new scope without reading it back.
- A source/fixture qualification proves dispatch and classification only. It does not prove installed Omarchy, physical CPU power savings, enrollment/authentication, compositor operation, or privileged package upgrades.
