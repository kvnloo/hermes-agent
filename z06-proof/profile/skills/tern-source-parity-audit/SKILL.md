---
name: tern-source-parity-audit
description: Use when comparing native Tern frontend parity.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [tern, tsp, research, parity]
    related_skills: [hermes-openui-tern-evidence, github]
---

# Source-backed Tern parity audits

## When to Use

Use for source-backed comparisons between native Tern applications, especially OMP and Hermes, including recent upstream feature and SDK adoption gaps.

## Procedure and evidence rules

- Freeze the exact frontend worktree SHA, installed Tern/agent versions, upstream source SHA, and package version separately. A current upstream source tree is not proof of identical code in an installed executable.
- Resolve the SDK at the workspace dependency root before assuming package-local node_modules. Compare npm metadata with source exports: SDK main can add kinds while the published version remains unchanged.
- Separate Tern host capabilities, TSP SDK transport, application event/data projection, and optional Luau plugins. An available node or OMP role does not create the missing backend contract.
- Inspect native document shape as well as role names. Host work folding may require top-level main children; nesting tools inside assistant columns can change behavior despite compatible roles.
- Inventory actual production node emissions, events, roles and source anchors programmatically. Exclude tests, persist batch evidence, and verify matrix/ranking counts and cited path/line starts.
- Check local feature worktrees before proposing a rewrite. Read their actual acceptance notes: a deny/empty-answer safety stub is not interactive approval or secret-prompt parity, and an aggregate merge is not a real-window receipt.
- Treat media, attachment chips, file hyperlinks, Markdown fence rendering and generated artifacts as separate capabilities. Native Markdown may render an SVG fence without the application implementing automatic chart generation.
- Read OpenUI issue status literally. A source-grounded RFC or retired experiment must not be described as shipped native integration; keep parsed bounded data distinct from executable Luau/JS.
- Check retention as a joint settle/eviction/reload design. Sending settle while continuing to rebuild all old nodes can conflict with gone events. Detached windows legitimately stop ACKing; do not blindly port a timeout that bypasses credits.
- Label source findings, CLI verification, static replay and live-window tests separately. Use the existing shared UX fixture, all chat skins and viewport widths for later qualification; surface-play cannot prove live gateway actions, and headless shot/serve normally omit installed plugins.
- Qualify operational sheets through exact session-authorized RPCs, not slash output. Hermes MCP list/status/catalog authority is profile-scoped; cached tools must follow owned/adopted connection-ledger keys, including lazy registrations. Report only safe auth-presence labels: even nominally redacted config summaries may expose credentials in URLs or launch arguments. SSH inventory is the current profile's terminal target, not an invented OpenSSH/OMP host database; unsupported management must send no mutation.
- Keep side-thread history in canonical backend state with typed thread/turn identities and monotonic revisions. A completion event can beat its submit response; a resume can remint the live UI session id while the conversation remains the same. Test both fences, exact cancellation readback, lost-worker recovery and per-thread draft preservation under approval preemption. Native pane scroll commands target owned node ids; do not invent a JSX `scroll` prop the installed SDK does not expose.
- Prove provider parity against the active profile's canonical `list_authenticated_providers` and actual `model.options` response, then feed a credential-free receipt into a connected-SDK picker test asserting every provider scope and returned model item. Include exhausted/pool-only, OAuth, key, custom and empty locked cases; do not infer authentication from model count. Strip endpoint URLs, raw discovery errors, credential extras and account labels before native inventory transport. Expose gateway-owned pending model selections separately so recent-model cycling advances during a streaming turn without calling a queued model active. A gateway import redirects ordinary stdout to stderr: preserve the original output stream before importing it in standalone JSON receipt probes.
- Re-score merged work against the exact behavioral sub-contract, not issue closure: explicit rich-print helpers are not automatic ordinary-print adaptation, JSON code is not a JSON tree, read-only inventory is not management, and send/stop is not revive. Track truthful unsupported states as residual scope rather than crediting full depth.
- Re-inventory custom actionable nodes after late feature composition. An accessibility PR can correctly convert its older inventory while newer voice, blob-preview, model-hub or history-load controls still emit pointer-only text/row actions; qualify source semantics and signed-in OS AX separately.
- Separate credited pending source from the actual lane head. Snapshot exact PR files and identify their SHA when asked to treat them as landed; never silently assert a merge or combined test result. Compare new upstream commits against the prior audit tip as well as releases, because a later release can publish features already audited on main.
- Keep research read-only except requested reports and owned scratch snapshots. Do not configure agent-command, install plugins, open microphones, or adopt user browser blocks just to establish feature availability.
