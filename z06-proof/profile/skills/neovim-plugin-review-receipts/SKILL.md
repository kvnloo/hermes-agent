---
name: neovim-plugin-review-receipts
description: "Use when executing Neovim plugin PR reviews."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [neovim, reviews, testing, evidence]
    related_skills: [upstream-contribution, github, test-driven-development]
---

# Neovim plugin review receipts

## When to Use

Use for independent execution of Neovim plugin PRs, cursor/event regressions, or generated-code correctness reviews.

Use `upstream-contribution`, `github` and its code-review reference first. Preserve author ownership and any parent-only publication restriction.

1. Save PR body, complete paginated issue comments, submitted reviews, inline comments, changed-file metadata and diff. Reconcile REST counts with PR metadata and GraphQL connection totals; include resolved/outdated thread state. Compare proposed feedback against existing concrete cases, not only matching words.
2. Discover existing checkouts and native nvim/Lua/JVM/compiler tooling in bounded roots before cloning. Use isolated detached exact base/head checkouts; never alter an installed plugin to conduct a review. Record plugin dependency commit SHAs and source tree hashes.
3. Drive actual plugin APIs on real Neovim buffers, real Tree-sitter queries and actual extension listeners. A headless buffer switch, public refactor operator call or `qa!` exercises production behavior but is not physical keyboard or GUI proof.
4. Isolate HOME and all XDG data/state/config/cache paths. Precreate `stdpath('data')` when a plugin uses non-recursive mkdir; otherwise a startup data-path error can masquerade as a product regression. Start each replay with a new data home so persisted marks cannot contaminate controls.
5. For cursor persistence, assert in-memory updates and event identity/order, then read the real data file after Neovim exits. Distinguish instantiated lists from lazy/unread lists. Cover explicit list items while another buffer is current and custom non-file contexts, not only implicit current-file additions.
6. Inspect upstream fixture cleanup before running the suite. Lua `os.tmpname()` may use fixed `/tmp` regardless of TMPDIR. On Linux, use a private bwrap mount namespace binding an owned scratch directory onto `/tmp`, a read-only host root, private HOME/XDG paths and only owned outputs writable. Never invoke broad repository clean targets against host `/tmp`.
7. Strip ANSI escape sequences before programmatically counting tests, retaining unmodified raw logs. Framework exits alone do not prove execution; assert expected per-file counts and zero failures/errors.
8. For generated code, compile the valid original fixture, invoke the actual refactor, save exact generated output and compile it separately. Expected-output string tests can bless invalid code. Separate documented placeholder types from unexpected lost parameters, immutable argument assignments and redeclarations.
9. Record parser grammar commit and build command. Prefer a project-local pinned compiler release over a global install. For grammars with C scanner/parser sources, compile both with the source include directory into a private `parser/LANGUAGE.so` runtime path and hash the binary.
10. Keep inline expression-generator tests separate from the full LSP-backed inline operation. Never invent missing LSP responses. State NOT_RUN for the full suite and describe only the generator/refactor paths exercised.
11. Re-read exact remote base/head and complete discussion before finalizing. Confirm sources remain clean, verify result matrices programmatically, and retain commands, logs, generated files, dependency locks and concise unsent notes. Do not count documented or already-reviewed behavior as novel.
