# Promotion queue — kvnloo/hermes-agent → NousResearch/hermes-agent

Built 2026-10-01 from a full reproof of Hermes' 120 "promotion candidate needing reproof" fork PRs (PROTOCOL.md). Every READY branch is one commit on upstream main, authored by kvnloo (noreply), and merge-checks clean on main `cfdcea4f22`. Patches: `branches/<name>.patch` (+ `branches/INDEX.tsv`); per-item evidence: `verdicts/fork-<N>.json`; PR bodies: `patches/*.body.md`.

| Verdict | Count |
|---|---:|
| READY | 73 (23 code items + 4 chores in 2 bundles + 46 docs corrections in 15 bundles) |
| SUPERSEDED-ON-MAIN | 24 |
| EXTERNAL-OWNED | 15 |
| HOLD | 4 (#36, #65, #73, #303) |
| NEEDS-REWORK | 3 (#32, #55, #111) |
| NOT-REPRODUCIBLE | 1 (#99) |

**Gate:** ~3 open upstream PRs at a time (public commitment on #99773). Currently open: #126847 (model picker) + #129524/#129525/#129526/#129556 (perf). Promote one item per freed slot, in order.

## Tier 1 — highest user impact, no upstream owner

| # | Branch | Size | Why it matters |
|---|---|---|---|
| 47 | ready/fork-47-ratelimit-missing-remaining | +54/-10 | A missing `x-ratelimit-remaining-*` parses as 0 → `/usage` shows 100% used and can falsely trip the Nous breaker |
| 112 | ready/fork-112-kill-race-notify-attribution | +45/-4 | Kill racing the reader mislabels the completion (9/10 real-process trials wrong on main). Fork head deadlocked the registry; rebuilt |
| 56 | ready/fork-56-queued-paste-payload | +248/-33 | Collapsed paste lost when submitted while busy / before a session; queued paste starting with `!` gets shell-executed on drain. Refs #99032; complementary to kokhlo's #99042 (comment there first). Operator input is inside the trust boundary per SECURITY.md §3.2 → public PR is fine. Follow-up: `{!…}` inside the paste label preview (`edgePreview`) still executes |
| 107 | ready/fork-107-reused-tool-id-settled-turn | +85/-6 | Desktop: a reused tool-call id overwrites the previous turn's row (fork's claimed repair was incomplete) |
| 49 | ready/fork-49-tile-stale-readonly-recovery | +150/-4 | Desktop tile locked read-only by a stale recovery after a successful resume (cut from +484) |
| 22 | ready/fork-22-langfuse-tool-subagent-eviction-clock | +40/-0 | Live turn evicted mid-tool → second root trace in Langfuse |

## Tier 2 — solid narrow fixes

#44 raft turn-id leak (+42/-3) · #45 Discord overflow skips recovery ledger (+41/-2) · #28 corrupt messages b-tree returns bare 500 instead of 503 + doctor hint (+77/-1) · #33 security-guidance never scans schema-shaped `skill_manage` ops (+35/-2) · #46 dashboard implicit-resume notice never shows (+37/-19) · #50 `save_over_limit` ignored (+26/-2) · #58 TTS lease released by a tile that never took it (+195/-2) · #29 stale `adoptedRunningTurn` forces redundant hydrate (+77/-1) · #34 late-opening probe socket reported as timeout (+22/-0) · #37 TUI step-up "can't reach billing" unreachable (+36/-6) · #39 worktree from non-`origin` remote tracks it (+64/-15) · #31 hub search cuts before trust-sort (+27/-1) · #52 xlsx hyperlink font loses link style (+31/-2) · #59 `evm compare` names a failed-gas chain "most expensive" (+76/-3)

## Tier 3 — low priority / owner's call
#27 manage-subscription URL leaks portal query (latent; billing owner's call) · #66 stale weather fetch overwrites newer (low impact)

## Perf (after the open perf PRs settle)
#302 ready/fork-302-dock-collapsed-clock (+132/-2, prod +5/-2): collapsed dock 10→0 renders/10 s; fork head froze finished-process rows, rebuilt. Merges cleanly with all four open perf PRs.

## Docs — 15 bundles, one at a time (each correction quotes stale text + contradicting source; link check + generator check clean)
Order: `docs2-contributors` (#304 noreply README — canonical lane) → `docs-mcp` → `docs2-gateway` → `docs-desktop` / `docs2-desktop` → `docs-agents` → `docs-cli` / `docs2-cli` → `docs-bot-mode` → `docs-memory` / `docs2-memory` → `docs-computer-use` → `docs2-update` → `docs2-models` → `docs2-skills`.
Note: `docs-bot-mode` and `docs2-gateway` edit different lines of `bot-mode.md` (+ zh mirror); they apply together cleanly — fine to ship separately or fold.

## Chores — 2 bundles
`ready/chore-gateway` (8 files, +20/-113: dead shim/helpers, cron guards that could never fail now patch the real function) · `ready/chore-agent` (+1/-22).

## Support, not compete (no queue slot needed; one concrete comment per thread)
| Ours | Their PR | What we'd offer |
|---|---|---|
| #155 | #123448 | through the real dispatch path `notify="false"` is still refused in foreground (string converted after the check); our test |
| #43 | #54617 | `compare_digest` on str raises TypeError for a non-ASCII signature → 500; bytes comparison + test |
| #54 | #99721 | the 7-line name-release loop it misses |
| #40 | #73117 | second half: `get_subprocess_home` ignores the scope |
| #38 | #85253 | also invalidate in the connection-switch wipe (two connections sharing profile key "default") |
| #48 | #81164 | tracked-file regression test + the identical bug in `hermes_cli/web_git.py` |
| #23 | #96941 | rich_text body/list/quote/table-cell regressions |
| #51 | #119346 | fixture migration off `'profile': 'default'` |
| #30 | #126106 | (weak) one-time dedup warning |

## Retire (fork PRs; superseded / not reproducible / duplicate lanes)
SUPERSEDED-ON-MAIN: #12 #13 #14 #16 #17 #18 #19 #20 #21 #24 #26 #35 #42 #62 #67 #71 #72 #74 #75 #76 #77 #78 #82 #83 · NOT-REPRODUCIBLE: #99 · duplicate lanes: #80 #116 #125 (→ #304), #391 (→ #307), #286 (obsolete), #113 #114 (→ external owners), #115 (after chore-gateway lands), #121 (→ #399).
