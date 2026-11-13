---
name: 99-native-provider-qualification
description: "Use when qualifying 99 provider or picker changes."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [neovim, lua, upstream, providers]
    related_skills: [upstream-contribution, github, test-driven-development]
---

# 99 native qualification

## When to Use

Use for exact-head provider, picker compatibility and local title-dispatch qualification in ThePrimeagen/99.

## Procedure

- Read current ThePrimeagen/99 AGENTS.md, complete PR comments/reviews/inline threads, and competing file deltas. Existing CursorAgent citation, picker migration and title-suppression PRs remain their authors' carriers; prepare stacked local repairs or independent receipts, not duplicate PRs.
- Pin master and the exact carrier separately. CursorAgent normalization may exist only in the carrier. Reproduce through `_retrieve_response` with a real temporary result file, then `QFixHelpers.create_qfix_entries`; helper-only assertions do not lock retrieval wiring. Cover search/vibe and visual passthrough separately. Mixed citations plus valid outside-fence quickfix lines must preserve both while rejecting code-fence false positives.
- When unifying citation and outside-qfix scans, test the same location represented in both formats through `_retrieve_response`, the real search/vibe observer, and `vim.fn.getqflist()`. Citation keys such as `path:line:col` do not deduplicate complete raw qfix strings. Use one complete normalized-line deduplication domain and positive controls for the same file/line with different columns or notes; a location-only key over-deduplicates valid results. Include indented Markdown fences beside a valid citation: removing an early return can expose an inherited fence-scanner limitation only in mixed responses. Test both closed and unclosed indented fences and indented citation bodies, using Neovim trim rather than redesigning the downstream parser. Compare each identical fixture on the untouched owner and candidate before calling it a regression.
- Preserve the opening fence delimiter character and run length when filtering outside quickfix lines; close only with the same character, at least that length, and no trailing non-whitespace after Neovim trimming. A prefix-toggle scanner leaks tilde fences and falsely closed longer/backtick examples when mixed citations remove the old early-return protection. Replay the reviewer's unchanged mixed fixtures on both original owner and held head before classifying inheritance; add valid outside entries after real closers and mutation-check character, length, trailing text, longer closers, trimming, dedupe and retrieval wiring through scheduled search/vibe consumers. Keep the separate Windows-string observation distinct from behavioral assertions and native-platform qualification.
- Verify gate-only cleanup by formatting the behavioral parent's bytes with StyLua `--verify` on stdin and comparing with final blobs; isolate any literal-splitting adaptation and compare complete evaluated provider argv arrays across revisions. Preserve original test-first commit ancestry and run its exact tests against original production bytes.
- Run native `make lua_test` and `make pr_ready` separately and save exits/logs. `pr_ready` stops at lint, so report later unexecuted targets. Pin Neovim, Plenary, StyLua and Luacheck versions. Compare carrier/base gate failures before assigning blame. Keep inherited format/lint cleanup in a separate commit; verify prompt literal wrapping preserves the complete command array.
- Discover user-local tools first. If Luacheck is absent but Lua 5.1 headers/GCC exist, a scoped pinned source install works: Luacheck 1.2.0 depends on argparse 0.7.1 and LuaFileSystem 1.8.0; review their rockspecs and record exact commits in a tools lock. Compile only lfs.c into an owned lib/lfs.so, invoke pinned luacheck/bin/luacheck.lua through Lua 5.1 with scoped LUA_PATH/LUA_CPATH, and expose it via a project-local PATH wrapper. Never alter global config or install system packages.
- Qualify picker migration with unchanged old `require("99.extensions.telescope")` and `require("99.extensions.fzf_lua")` export probes on base and carrier. Separately exercise native model/provider selection, explicit provider forwarding, opts-only calls and cancellation through a controlled `vim.ui.select`. Do not add competing compatibility adapters when the migration already has an owner.
- For OpenCode title latency, generate argv with the actual 99 `_build_command`. Use the installed native OpenCode binary if the package launcher reports missing postinstall; inspect existing platform packages before declaring the CLI unavailable. Verify native `--version` and checksum, not just npm metadata.
- Run any local model fixture in `bwrap --unshare-net` with a real loopback HTTP server inside the namespace, isolated HOME/XDG paths, an explicit clean environment, disabled model fetch/autoupdate/default plugins, and an enabled-providers allowlist containing only the fixture. Use `@ai-sdk/openai-compatible` and a non-secret fixture key. Record omitted-title, empty-title and explicit-title controls, request counts, observed output, process exits and bounded start-to-exit latency. Artificial response delays are fixture parameters, never live-provider savings. CLI completion is not full 99 temp-file/UI completion; label the measured boundary.
- For final independent acceptance, audit producer mutation receipts by re-parsing raw named outcomes and checking source/log hashes, then replay each mutation in a fresh Neovim process. Load a mutated provider module into `package.loaded` before importing the consumer spec; this exercises actual retrieval and scheduled consumers without editing source on disk. Run the unchanged suites again unmutated and check protected source/evidence manifests. Keep framework observations (especially Windows-string probes) separate from behavioral case counts.
- Strip ANSI escapes only in the parsed view of Luacheck/Plenary logs; retain original raw bytes and hashes. A colorized `Total:` line can otherwise cause a receipt-validation assertion to fail despite a completed green gate.
- Preserve negative controls, exact tested SHAs, original author credit and a restorable Git bundle. Restore the bundle into a fresh owned checkout and rerun official gates. Keep local correctness, fork publication, upstream ownership and authorization separate.
