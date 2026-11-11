# Hermes continuous/duplex voice — issue, PR, and donor audit

Frozen: 2026-09-12 (live `gh` + `origin/main`)
Repository: NousResearch/hermes-agent
Live `origin/main`: `1c671beab29164d8931c5d01c5739502267089d8`
This worktree: `continuous-voice/t_c3c960f4` @ `fdb5ea295e5` (ahead 4 / behind 7202 of main)
Method: read-only. Reuses t_089c5bdb (2026-08-27) and t_c992ea57 ADR; every named head and status was re-fetched. No GitHub write, no new PR, no merge.

## Executive decision (binding for later slices)

**Do not improve GitHub PR #95147 in place as it currently sits.**
**Do not open a competing core ABC / Discord / Desktop duplex PR.**
**Take selected pieces from #95147, and treat landed GPT-Live on main as the existing first Desktop vertical slice.**

Rationale, live vs the 2026-08-27 archaeology:

1. Maintainer already shipped an opt-in full-duplex Desktop slice on main: `f923faa0b88` + `20816c13cdd` (`voice.voice_chat_mode: gpt-live`, default remains `chained`). Hermes stays the agent; the voice model has no tools. Duplicating this as a “first slice” would violate reuse.
2. GitHub #95147 head is now `e426eb62df3e989a035f58fe4a1a9eb4e89a7e28`, **CONFLICTING/DIRTY** against current main, no longer draft, and the file list is contaminated with unrelated `scripts/desktop-update/windows.ps1` + a Windows SelfTestUi test. It is not a clean merge vehicle.
3. RFC author TheSmokeDev asked maintainers (on #95147 and #77111) to treat **#101808** as the canonical #77111 core slice (ABC + orchestrator + bundled OpenAI provider + `hermes realtime`). Heard-boundary work was invited *on top of* #101808, not as a second ABC.
4. #95147’s valuable waist (provider/session ABC, Hermes-owned tools, `HeardAudioBoundary`, fake two-provider tests, later exactly-once dispatch) is still the best *contract* donor. Reuse it by cherry-pick/`-x` onto current main or as a follow-on to whichever ABC maintainers accept — not by force-pushing more onto the dirty head.
5. Discord VC duplex is still **not** on main. GPT-Live is Desktop WebRTC/`POST /v1/live/sessions`. A Discord slice remains the only justified new implementation, and it must consume current Discord plugin + existing barge-in/PCM donors, not a new stack.

Critical-path sentence for implementers:

Reuse landed GPT-Live (Desktop, opt-in) and current Discord/Hermes authority; do not merge or compete with #95147/#101808/#101034; cherry-pick only #95147’s heard-boundary / exactly-once / identity tests into the Discord adapter path (or onto #101808 if a human later chooses that ABC); prove duplex only in authorized Discord VC after the credential-free contracts exist.

## What changed since t_089c5bdb (2026-08-27)

| Item | 2026-08-27 freeze | 2026-09-12 live |
|---|---|---|
| `origin/main` | `2ea42a44e0` then ADR `6defe7eb6c` | `1c671beab29` (~7202 commits later) |
| Named PR on main? | none | **GPT-Live Desktop is on main** (Teknium, 2026-09-11) |
| #95147 | draft, 3 commits, head `04d9d29c` | open, not draft, 13 commits, head `e426eb62`, **CONFLICTING**, +unrelated Windows files |
| #77111 | open RFC | still open; 24 comments; RFC author now nominates #101808 |
| #101808 | did not exist | open competing core ABC+OpenAI+CLI (TheSmokeDev) |
| #101034 | did not exist | open TUI consumer stacking a copy of the #95147 waist |
| #97325 / hermes-talk | field plugin | docs PR still open; plugin is the live 3-provider consumer |
| #108568 | did not exist | catalog PR for community `hermes-live-voice` (Codex/GPT-Live-1 WebRTC) |
| #106640 | did not exist | Codex OAuth STT/TTS/live voice (andrexibiza + ardaaltinors #77840) |
| Local worktree `t_c3c960f4` | intended implementation owner | **stale**: original 3 #95147 commits + ADR hardening on 16-day-old main. Not an ancestor of live #95147 or of GPT-Live. |

Ancestry vs live main: #95147 head not ancestor; #101808 head not ancestor; GPT-Live commit **is** ancestor.

## PR #95147 — explicit decision

https://github.com/NousResearch/hermes-agent/pull/95147

- Author: kvnloo / Kevin Lo (commits also authored as lesseradmin / veeman961)
- Title: feat(voice): add realtime provider session contract
- State: OPEN, isDraft=false, mergeable=CONFLICTING, mergeStateStatus=DIRTY
- Head: `e426eb62df3e989a035f58fe4a1a9eb4e89a7e28` (`feat/realtime-voice-provider`)
- Files (live): `agent/realtime_voice.py`, `agent/realtime_voice_coordinator.py`, `agent/realtime_voice_registry.py`, `hermes_cli/plugins.py`, `tests/agent/test_realtime_voice.py`, `tests/hermes_cli/test_plugins_realtime_voice_registration.py`, **plus contamination** `scripts/desktop-update/windows.ps1`, `tests/test_desktop_update_windows_progress.py`
- Lineage: started as the six-file #77111 waist. Grew through heard-boundary, event identity, nonblocking exactly-once tools, silent context, bounded lifecycle, SESSION_READY/WARNING. Identity/epoch ledger was then **split out** to https://github.com/kvnloo/hermes-agent/pull/3 so this PR could freeze as foundation.
- Reviews: Enough1122 flagged `id()` identity, silent dispatch errors, inline tool await (author later addressed in subsequent commits). TheSmokeDev field notes (frame-agnostic, optional truncate). Last public comment from TheSmokeDev: treat **#101808** as canonical; welcome heard-boundary as a PR **on top of #101808**.
- vs main: not integrated; conflicts; `register_realtime_voice` is absent on main.
- Harness: coordinator is the only tool/approval path; no vendor transport; no opt-in user flag (interface-only). Reconnect is provider-owned; durable Hermes history still unspecified in this PR.
- Overlap with a continuous-voice slice: **the waist we want**, but the GitHub PR is a polluted, conflicting, politically superseded merge vehicle.

### Decision

| Option | Verdict |
|---|---|
| Improve #95147 in place (more commits on `feat/realtime-voice-provider`) | **No.** Dirty vs main, unrelated files, RFC author asked maintainers to pick #101808, identity work already forked to kvnloo#3. |
| Land a follow-on branch from live #95147 | **Only after** stripping the Windows-update files, rebasing onto **current** main (which now contains GPT-Live), and only if a human merge-order decision keeps this ABC. Do not force-push over TheSmokeDev’s request without that decision. |
| Take selected pieces | **Yes — default.** Cherry-pick/`-x` the realtime-only commits (not `239501833569` / `e426eb62` Windows tests). Preserve kvnloo authorship. Port `HeardAudioBoundary`, event identity, exactly-once tools, bounded ingress, fake two-provider tests. |

Local worktree series `e1133de7f6c`…`fdb5ea295e5` is an **older ADR-shaped hardening** of the original three commits. It is useful evidence, not the live GitHub object. Implementers must not treat this worktree as the branch to push.

## Inventory — issues

### #77111 — [RFC] RealtimeVoiceProvider ABC
https://github.com/NousResearch/hermes-agent/issues/77111
Author: TheSmokeDev. OPEN. Updated 2026-09-11. 24 comments.
Category collision: many duplex PRs need one ABC, not a merge queue.
Live turn: author now asks maintainers to treat #101808 as the canonical core slice; hermes-talk remains the live 3-provider consumer.
Disposition: **EVIDENCE_ONLY** (architecture RFC). Credit in any core ABC commit. Do not close from this program. Human-gated maintainer ping.

### #94462 — Discord voice latency / STT
https://github.com/NousResearch/hermes-agent/issues/94462
Author: kvnloo. OPEN. Unchanged as product evidence.
Disposition: **EVIDENCE_ONLY** acceptance criteria for a Discord slice. Not fixed by GPT-Live (Desktop-only).

### Other open issues (not duplex-core; do not expand into them)
Messaging `is_voice` / bubble bugs (#102221, #101380, #100018, …), Desktop silence/keybind (#83518, #97473), Discord inactivity/auto-TTS (#105974, #101185, #51282), TUI leftover voice mode (#106503). These are half-duplex product bugs. **Do not duplicate their PRs.**

## Inventory — required / named PRs

Disposition key: COPY = preserve commits/authorship; REIMPLEMENT = behavior only into current seams; EVIDENCE_ONLY = tests/ideas; REJECT = do not merge this branch.

### #95180 — Desktop turn lifetimes
https://github.com/NousResearch/hermes-agent/pull/95180
kvnloo, OPEN draft, head still `bee79171eacf6eb810a208ec8d3154a8891bb2e0` (unchanged). 7 files.
Capture generation / StrictMode / abort isolation. Complements GPT-Live and chained Desktop; does not provide provider transport.
Disposition: **COPY independently** after rebase onto current main (now has GPT-Live composer). Not part of Discord slice. Do not merge into #95147.

### #95191 — Android STT / WebUI bridge (superset of #95193)
https://github.com/NousResearch/hermes-agent/pull/95191
kvnloo, OPEN draft. Head **moved** from `3144ceea` to `f843f20d9ddb7d1ac7f74e6d6fb754413cb58c76`.
Disposition: **REIMPLEMENT** exact-origin / generation-scoped callbacks at the authenticated Web bridge. S25 remains later, not this Discord slice. Preserve authorship.

### #95193 — mobile browser voice
https://github.com/NousResearch/hermes-agent/pull/95193
kvnloo, OPEN, no longer draft. Head **moved** to `65539bc3361faf7afca31872db38eae70754052b` (subset of #95191).
Disposition: **REJECT as a separate merge**; keep commits inside whichever Web slice survives.

### #27650 — OpenAI Realtime Discord VC
https://github.com/NousResearch/hermes-agent/pull/27650
Solvely-Colin, CLOSED, dirty, head still `b1b3a57a…`. Direct vendor websocket in gateway.
Disposition: **EVIDENCE_ONLY**. PCM/protocol tests only, with attribution. No vendor transport in core.

### #21504 — realtime Discord voice
https://github.com/NousResearch/hermes-agent/pull/21504
RationallyPrime, OPEN draft, head still `bf905dd9…`. Apparent 507-file delta is stale-main drift.
Disposition: **REIMPLEMENT** PCM conversion, silence-tail, playback-source into **current** Discord plugin. Do not merge wholesale. Unbounded-queue probe still stands.

### #62500 — realtime transcription bridge
https://github.com/NousResearch/hermes-agent/pull/62500
337zzang, OPEN draft, head still `cdc1b080…`.
Disposition: **REIMPLEMENT** browser/server lifecycle UX only after mapping to an accepted ABC. Do not copy parallel server contract.

### #27040 — generic voice_server platform
https://github.com/NousResearch/hermes-agent/pull/27040
tmylk, OPEN, CHANGES_REQUESTED, head still `d59fa949…`. Repeated main merges; noisy 60-file delta.
Disposition: **REIMPLEMENT** later as edge plugin. Not this slice.

### #31604 — Grok voice dispatch
https://github.com/NousResearch/hermes-agent/pull/31604
tuckercoffey, OPEN, head still `ceb235b4…`. Parallel product route / vendor dispatch.
Disposition: **REJECT** dispatch authority. **EVIDENCE_ONLY** for approval-safety tests.

### #81404 — closed ancestor of #101808
https://github.com/NousResearch/hermes-agent/pull/81404
TheSmokeDev, CLOSED unmerged 2026-08-15. Ported forward into #101808.
Disposition: **EVIDENCE_ONLY** lineage. Do not reopen.

## Inventory — new material PRs since 2026-08-27 (must not duplicate)

### Landed on main — GPT-Live Desktop (Teknium)
Commits: `f923faa0b88`, `20816c13cdd` (2026-09-11).
Files: `tools/voice_live.py`, `hermes_cli/web_routers/audio.py`, `tui_gateway/methods_prompt.py`, Desktop `lib/voice-live.ts`, `use-voice-live-conversation.ts`, config `voice.voice_chat_mode` / `voice.gpt_live.*`, tests `tests/tui_gateway/test_voice_live_delegation.py`.
Chain: Desktop mic → WebRTC to OpenAI `gpt-live-1` → `session.delegation.created` → Hermes `prompt.submit(surface=voice-live)` (tools/approvals/history unchanged) → commentary append → spoken paraphrase. Opt-in; chained STT→Hermes→TTS is default fallback. Key never reaches renderer (`POST /v1/live/sessions` server-side). Prompt cache: note rides model input, system prompt byte-stable.
Harness: **exactly the Codex/Hermes authority split we want**, but transport is Desktop WebRTC + Live API, not Discord PCM + Realtime WS, and not #95147 events.
Disposition: **COPY as the existing Desktop slice.** Do not reimplement. Discord slice must not change default `chained` behavior.

### #101808 — competing core ABC (RFC author)
https://github.com/NousResearch/hermes-agent/pull/101808
TheSmokeDev, OPEN, not draft. Head `311446cd91fb245f3acbccdd83bcb0e327159b6a`. +6332/21 files.
Adds `agent/realtime_voice_{provider,orchestrator,registry}.py`, bundled `plugins/realtime_voice/openai/`, `hermes_cli/realtime_voice.py` (`hermes realtime`), docs, large test suite.
Same category as #95147 with a **different type/file vocabulary** and a bundled OpenAI provider in-tree (Footprint Ladder: service-gated plugin + CLI). Live-derived from hermes-talk (OpenAI, xAI, Gemini).
Disposition: **Do not compete.** Human merge-order vs #95147. If maintainers pick this, port #95147 heard-boundary onto it (author’s invitation). This program must not open a third ABC.

### #101034 — TUI realtime consumer
https://github.com/NousResearch/hermes-agent/pull/101034
kvnloo, OPEN. Head `5e690024a0371ed93041d4f5160f9eded8f72628`. Embeds a copy of the #95147 waist plus TUI visualizer/vendor thinking-orbs.
Disposition: **Do not merge as the core spine.** Consumer-only after an accepted ABC. Do not duplicate TUI work in the Discord slice.

### #97325 — docs pointer to hermes-talk
https://github.com/NousResearch/hermes-agent/pull/97325
TheSmokeDev, OPEN, docs-only.
Disposition: **EVIDENCE_ONLY**. Publication/maintainer ping human-gated. Do not expand.

### External plugin: TheSmokeDev/hermes-talk
Live 3-provider duplex (OpenAI Realtime / ChatGPT subscription, xAI, Gemini Live), terminal + Discord VC, tools through Hermes. First real audio consumer of the #77111 split.
Disposition: **COPY as external plugin / field evidence.** Do not vendor into core. Discord slice should compose current in-tree Discord plugin rather than wrapping talk unless a human chooses that.

### #108568 — plugin-catalog hermes-live-voice
https://github.com/NousResearch/hermes-agent/pull/108568
Synero, OPEN, catalog-only. GPT-Live-1 over Codex app-server WebRTC; overlaps landed GPT-Live.
Disposition: **EVIDENCE_ONLY / catalog.** Do not in-tree a second Live frontend.

### #106640 — Codex OAuth STT/TTS/live voice
https://github.com/NousResearch/hermes-agent/pull/106640
andrexibiza; preserves ardaaltinors #77840 STT commit. 68 files. Subscription audio, not the #95147 ABC.
Disposition: **EVIDENCE_ONLY** for Codex-OAuth credential routing. Do not merge as the duplex spine.

### #103279 — server-owned `/v1/audio/converse`
https://github.com/NousResearch/hermes-agent/pull/103279
Terastar-Sakura, OPEN draft. Parallel converse loop in gateway/web_server/`tools/voice_converse_loop.py`.
Disposition: **REJECT as second conversation authority.** EVIDENCE_ONLY for WS session lifecycle tests.

### #103173 — live streaming STT (desktop dictation)
TimeLord2010, OPEN draft. Dictation, not duplex agent.
Disposition: **EVIDENCE_ONLY**. Out of slice.

## Inventory — overlap PRs (contract only; still unmerged)

Reuse evidence, do not merge wholesale, do not file duplicates:

| PR | Why it overlaps | Use |
|---|---|---|
| #94113 ElevenLabs Desktop realtime STT | parallel session manager | adapter after ABC, not a manager |
| #54462 API realtime orchestration | second coordinator | reject second orchestrator |
| #75014 streaming TTS playout | playback cursor | source of truth for heard ms |
| #92334 Desktop drain-all on barge-in | cancellation | rebase #95180 against it |
| #80996 TTS echo guard | acoustic admission | reuse, not transport |
| #75325 Discord conservative barge-in | Discord duplex admission (592 comments) | **fresh-port epoch/PCM split** into current plugin |
| #92762 Discord barge-in interrupt | playback stop | compose with #75325/#87300 |
| #87300 Discord receiver after RESUME | reconnect | current Discord consumer must compose |
| #42611 bounded Discord live transcription | backpressure cap | consumer bound policy |
| #57448 / #81488 Google Meet Realtime | protocol/PCM pump | Meet-only |
| #94059 SSH audio bridge | remote capture | edge only |
| #46028 / #45863 WhatsApp calling sidecars | remote duplex | edge only |
| #80896 / #81695 / #83572 / #84099 / #94387 | capture/endpoint/mic lifetime | constrain capture; not core |
| #91140 Discord VC vs voice messages | surface taxonomy | do not conflate with duplex |
| #101186 Discord auto-TTS in VC | playback path | compose, don’t replace |
| #109076 Discord stale disconnect ack | recovery | compose |

#75325 is the richest in-tree Discord barge-in donor; still OPEN and not on main. Fresh-port, do not merge the 22-file churned branch.

## Preserved local / workspace candidates

| Object | Status | Disposition |
|---|---|---|
| Worktree `t_c3c960f4` `e1133de7f6c`…`fdb5ea295e5` | ADR hardening of original 3 commits on 16-day-old main | **EVIDENCE / salvage tests only.** Rebase from **current** main; do not push this branch. |
| kvnloo/hermes-agent#3 identity/epoch | stacked draft split from #95147 | **COPY later** onto accepted ABC; do not grow #95147 |
| Desktop `bee79171` | == #95180 | COPY independently |
| Web `3144ceea` → live `f843f20d` | == #95191 | REIMPLEMENT bridge |
| Android `836dd8cee870f020d3db0ce355846f9f947fe242` | on-device STT companion | later S25; not Discord slice |
| xAI plugin `338d3745…` (not `f8d6be0`) | standalone | COPY as external plugin against accepted ABC |
| provider-core `ef6ba68b…` | superseded by #95147 | EVIDENCE_ONLY; never cherry-pick onto later coordinator |
| Discord lane `t_b5da5a35` | collaboration | EVIDENCE_ONLY; no third Discord PR |

## Codex / Hermes harness implications

| Pattern | Tools | Approvals | Transcript | Reconnect | Opt-in / fallback |
|---|---|---|---|---|---|
| **GPT-Live on main** | Voice model has **no** tools; every real request is a normal Hermes turn (`prompt.submit`, surface `voice-live`) | Existing Hermes policy | User row = spoken words; note prepended to model input; system prompt byte-stable | New Live session; no provider resume | `voice.voice_chat_mode`; default `chained` |
| **#95147 coordinator** | Provider proposes; coordinator dispatches Hermes callback, exactly-once per call_id (later heads) | Same callback/approval path | Final transcript not yet a durable Hermes turn contract | Provider-owned; host session_id intended | No user flag (core-only) |
| **#101808 orchestrator** | Bundled OpenAI Realtime function calls → `handle_function_call` on daemon thread, per-call timeout | Normal approval prompts | Provider transcripts + Hermes history | Capability-gated cancel-by-id; no durable resume claimed | `hermes realtime` CLI; plugin registry |
| **hermes-talk** | Hermes tools mid-call | Hermes | Provider + host | Plugin-owned | Plugin install; not default |
| **Vendor-direct Discord (#21504/#27650)** | Mixed/gateway-owned | Weak / vendor | Provider conversation | Stale adapters | Would clobber current plugin |
| **#103279 converse WS** | Own loop | Risk of second session | Own | Own | Reject second authority |

Invariants this program must not break:

- Prompt cache: no mid-conversation toolset/system-prompt swap (GPT-Live already uses the HUD-note seam).
- One tool/approval authority: Hermes. Voice models may speak and propose; they must not execute.
- Default path unchanged: `voice.voice_chat_mode: chained` and Discord STT→Hermes→TTS stay the fallback.
- No new core model tool for voice.
- No new `HERMES_*` env for behavioral flags; config.yaml only (`voice.*` already exists).

## Existing tasks / artifacts to reuse (do not redo)

| Task | Artifact | Reuse |
|---|---|---|
| t_089c5bdb | `/workspace/hermes-home/kanban/boards/hermes-agent/attachments/t_089c5bdb/hermes-duplex-voice-donor-audit.md` | Baseline archaeology; this document supersedes status/heads |
| t_c992ea57 | `…/t_c992ea57/HERMES-CONTINUOUS-VOICE-ADR.md` | Authority split still binding; **provider/surface choice must be updated** for GPT-Live-on-main |
| t_7848a838 | realtime SOTA report | Provider comparison; sibling t_763aa397 should reuse not rewrite |
| t_c09450fd | Grok lineage report | xAI unknowns |
| t_547e0a9a | UX canary matrix | Discord/S25 evidence packets |
| t_c3c960f4 | this worktree + comments | Implementation owner **after** architecture; do not start a second graph |
| t_30b59355 | architecture child of this audit | Consume **this** file; do not re-audit |
| t_178d1369 / t_fad21e7f | implement / prove | After architecture; Discord or reuse GPT-Live Desktop proof — do not both as “first slice” |

## Graphs / PRs that must not be duplicated

Do not open: another RealtimeVoiceProvider ABC; another OpenAI Realtime Discord VC; another Desktop GPT-Live/WebRTC frontend; another TUI realtime visualizer; another converse WS; another Grok dispatch UI; another voice_server platform; a third Discord barge-in PR; catalog clones of hermes-talk / hermes-live-voice.

Do not ping maintainers or publish. Merge remains human-gated.

## Gaps architecture/implementation must still fill

GPT-Live on main covers Desktop opt-in duplex **delegation**. It does **not** close the original Discord vertical slice. Remaining gaps:

1. **Transport (Discord)** — current plugin is half-duplex. Need real PCM in/out on the **current** adapter (VoiceMixer, RESUME #87300), not #21504’s stale tree. GPT-Live WebRTC does not apply inside a bot VC.
2. **Barge-in** — local-first silence of playback, then remote cancel. Donors: #75325, #92762, #80996, GPT-Live interruption policy (Desktop only). Need echo-safe admission so TTS does not false-trigger.
3. **Heard-boundary** — monotonic playback receipt per `(response_id, item_id, epoch)`. Best code: #95147 / this worktree coordinator + #75014 cursor. GPT-Live approximates “heard” as spoken commentary, not PCM ms.
4. **Exactly-once tools** — call_id dedupe, grouped settlement, approval deny/timeout, no inline block of the audio iterator. Live #95147 later commits and #101808 orchestrator both have this; Discord slice must use Hermes `handle_function_call`, not provider-native tools.
5. **Durable transcript reconciliation** — one final user turn per turn_id; revisions replace; unplayed assistant audio is not history. Still missing as a Hermes session projection on all unmerged ABCs. GPT-Live persists user words via normal submit.
6. **Metrics** — stage latency, interrupt, endpoint, tool dispatch; redacted (no PCM/PII). Not on main for Discord; GPT-Live has no stage ledger.
7. **Fallback** — opt-in off or realtime failure → existing Discord STT→Hermes→TTS. GPT-Live already falls back to chained when no key.
8. **Reconnect/dedupe** — two layers: Discord voice RESUME (#87300) and provider WS. No vendor resume handle as identity. Stale generation/epoch rejection (kvnloo#3).
9. **ABC merge-order (human)** — #95147 vs #101808 vs “no ABC, GPT-Live-style delegation only.” This program must not decide by opening a PR.
10. **Real-device proof** — private Discord VC + acoustic recorder, or Desktop GPT-Live if the program’s proof surface is allowed to change. Synthetic audio is not acceptance.

## Contributor-credit ledger (do not drop)

- TheSmokeDev: #77111, #81404, #101808, #97325, hermes-talk
- kvnloo / Kevin Lo: #94462, #95147, #95180, #95191/#95193, #101034, local Android/xAI candidates, this worktree series
- Teknium: GPT-Live on main (`f923faa0b88`, `20816c13cdd`)
- Solvely-Colin: #27650
- RationallyPrime: #21504
- 337zzang: #62500
- tmylk: #27040
- tuckercoffey: #31604
- RichardHojunJang: #75325 Discord barge-in
- AustinKelsay: #75014 playout cursor
- andrexibiza / ardaaltinors: #106640 / #77840 Codex audio
- Synero: hermes-live-voice catalog
- Enough1122: #95147 review (`id()` / inline dispatch)

Cherry-pick/`-x` where code survives. Where reimplementation is required, name the PR/author in the commit body.

## Inspection caveats

- Live metadata, heads, comments, and file lists for all named issues/PRs were re-fetched 2026-09-12. Overlap search used `gh pr list --search voice|realtime` (open state, first pages) plus the 2026-08-27 named set.
- #21504/#27040/#75325/#46028 branch-wide file counts are not feature boundaries (merge drift).
- No new focused tests were run in this audit lane. Prior 12/12 on this worktree and author’s claimed 23/209 counts are labeled as prior/author evidence.
- No maintainer merge-order comment from teknium on #95147 vs #101808 was found in the fetched threads; GPT-Live landing is the only maintainer product decision visible on main.
