# Later delivery addendum — 2026-10-05

This append-only note follows checkpoint `82254ca8d22115277e88ffbe4a966d0f2131a710`. Its existing 25 files remain historical evidence and must not be rewritten. The mutable ledgers now contain **42 Hermes, 17 OMP and seven CUA branch records**, including overlapping evidence and owner children rather than unique fixes.

## OMP: hide unavailable Git history actions

[724e6bd](https://github.com/kvnloo/oh-my-pi/commit/724e6bd64c8acad2bad0ddc1602db7c4895b222e) addresses one part of **pashifika**'s [#14347](https://github.com/can1357/oh-my-pi/issues/14347): selected committed-history rows no longer advertise stage/discard actions that already do nothing. Default history selection, keybindings and Git actions are unchanged; this does not resolve the full UX request.

The real overlay/component render consumer covers committed, staged and unstaged rows in both focus states with an inert Git model. Exact-base negative: one failure with two passing controls. Final: three passing cases, 30 assertions; TUI lint/format/type checks and diff check pass. No real Git mutations, terminal-host qualification or native rebuild is claimed; the existing addon was reused only as an import/render prerequisite. Independent source review and API/Git identity verification passed. Hosted snapshot: **zero checks, statuses and runs — CI_NOT_RUN**.

## CUA: thin lifecycle README entry point

[b853d52](https://github.com/kvnloo/cua/commit/b853d52de41b1aaddaf806d7aa260902fada1134) partially addresses **f-trycua**'s [#2086](https://github.com/trycua/cua/issues/2086). Four duplicated Sandbox lifecycle sections now point to canonical guides, with the cloud TTL distinction retained. Direct endpoint connection and surrounding package-specific guidance are unchanged. No contributor implementation was copied; the human request is credited.

This is documentation curation, not a runtime lifecycle fix or completion of every README requested by #2086. Diff check and independent link/source review passed; no runtime test or documentation generator was run. Remote SHA/tree/sole-parent identity is verified. Hosted snapshot: **one check, zero statuses and one workflow run; pending at recorded verification**. The `validate` check and `CI: Image API` run `37336360076` were in progress with null conclusions (job `111852031727`). This unrelated Image API workflow does not qualify the README; no hosted success is claimed.

## Literal Hermes PR cap snapshot

At **2026-10-05 15:39:14 UTC**, the read-only upstream snapshot contained **18 OPEN kvnloo Hermes PRs: 13 non-draft and five draft**. Drafts count as open. The standing limit is **three OPEN PRs**, so this snapshot is 15 above it; there is no alternate non-draft interpretation. The added draft #133347 belongs to another active lane and is not a delivery from this note.

Selecting the three to retain and explicit per-PR disposition remain parent/user decisions coordinated with existing owners. This note authorizes no closure, draft transition, new PR or external outreach. Owner adoption of downstream work is separate from opening a parallel PR. Discord reviewer interest remains unavailable. The counts are dated facts, not a claim that states cannot subsequently change.

## Hermes CLI: discovered plugin command inventory

[4cb7c57](https://github.com/kvnloo/hermes-agent/commit/4cb7c576a3dd18117d1a47ce9735858151716dc7) is a test-only direct child of **teknium1**'s original [#113700 owner head](https://github.com/NousResearch/hermes-agent/commit/3e125352c2940b98ad01be1d3b56d5d09a6aa7d4), addressing Kevin's request for a plugin-added command regression. It preserves the owner implementation and ancestry.

A real temporary enabled plugin passes through disk discovery/import, CLI registration, live parser construction, command inventory handler and JSON output. The test observes top-level and nested plugin commands; no plugin command execution or full main() startup is claimed. A meaningful discovery-omission control fails; restored production passes the single selected test. Scoped Ruff and diff checks pass. This owner tree has no scripts/check, and neither modern 11-check nor current-main integration qualification is claimed.

Supported Python 3.12 received exactly three authorized official pure wheels—rich 14.3.3, markdown-it-py 4.0.0 and mdurl 0.1.2, totaling 407,758 bytes—matching owner-lock hashes. Existing distributions were preserved; no project dependency files or production code changed. Independent review and exact API/Git verification passed. Hosted snapshot at 16:04 UTC: **zero checks, statuses and runs — CI_NOT_RUN**.

No tests were repeated for this metadata.

Local provenance: h4-omp-render-intake/remote-verification.json and README.md; git-hints14347/independent-review.md; cua-2086-remote/verification.json; cua-older-consumer-intake/2086-independent-review.md; promotion-cap-current/snapshot.json and README.md; commands113700/README.md, independent-review.md and remote-verification.json. Exact identities are in deliveries.json. These are downstream delivery records, not unique-fix counts or upstream acceptance.
