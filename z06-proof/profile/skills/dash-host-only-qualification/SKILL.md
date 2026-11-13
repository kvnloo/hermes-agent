---
name: dash-host-only-qualification
description: Use when qualifying Dash integration without a phone.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [dash, acp, qualification, ci, expo]
    related_skills: [local-agent-acp-bridge, rendered-ui-qualification, session-recovery]
---

# Dash host-only qualification

## When to Use

Use when resuming or qualifying the Dash integration lane on the constrained host, with S25/device acceptance explicitly deferred.

## Scope

Qualify an existing Dash integration branch without modifying main/dev or touching a phone. Read the checkout's AGENTS.md, DESIGN.md, `.cursor/skills/verify-dash/SKILL.md`, current PR body and latest recovery checkpoint before commands. Recover prior runtime receipts instead of repeating paid/provider turns.

## Host safety

- Check `free -g` available memory >=4GB before admission. Wrap every install, full suite, mutation, Expo export and browser run in `flock /home/kvn/.hermes/profiles/clean/cache/scratch/heavy.lock nice -n 10 ...` on this constrained host. Never remove the lock or bypass another owner's queued job.
- Background a bounded qualifying job when waiting for the shared lock; poll/wait through process_manage. A timeout waiting for flock is not a failed app test. Never leave a subagent job running unhanded-off at completion.
- During qualification, never start another Metro on 8097 or stop a running dash-pair. Use dynamic bridge ports and owned static-export HTTP children. Kill only owned exact PIDs/process groups. (Handing a build to the owner is different; see below.)

## Gates and CI

For O15 release-lane tasks, read the checkout's `AGENTS.md`, `TESTING.md` and `.claude/skills/verify-dash/SKILL.md` first. If that skill is not on the required base, retrieve its named PR version read-only rather than substituting the legacy verifier. The tester army (`e2e/mbp-army`, Playwright, `scripts/army.sh`) is the only behavioral evidence: do not run legacy unit/mutation/native-journey or ad-hoc browser checks for those tasks. The older gate recipes below apply only when the task's current repository contract still permits them. Preserve a test-only red-first commit and its hosted army evidence before pushing the implementation. Do not absorb unrelated failing release-base journeys owned by sibling cards; report their exact current-head failures separately.

When porting older live-feed code to identity-enrolled Dash, preserve the full enrollment object through hooks and fetchers, mint `executionToken(settings)`, and consider an enrollment paired even when `settings.token` is empty. Stripping settings to address/token or guarding solely on a nonempty legacy token silently disables identity feeds. Native source rows can legitimately deduplicate roster observations: assert the fixture's canonical session identity, not an assumed collector prefix. Seed deterministic activity only in the isolated army source DB, never the app store or a real agent home.

For army bridge fixtures, treat a child with non-null `signalCode` as already exited even when `exitCode` is null. A live-to-unavailable journey intentionally leaves its bridge dead; teardown must not wait for a second `exit` event. Preserve all user-facing assertions when repairing this cleanup failure. After selecting an Orchestra tab, require the whole `orchestra-graph` to be in the viewport before clicking inner controls, then assert the entire first priority card is in view. Text visibility alone allowed a horizontally clipped pager capture to pass. Use viewport readiness, not sleeps, forced clicks or debug setters. For modal evidence, assert that the next action and close control are in the viewport; text-presence assertions can pass while a fade is still transparent or the action is clipped.

For MBP fleet source snapshots, initialize a disposable Git worktree (`git init -q`) before the full suite: the file-inventory test executes real Git against cwd, and fleet tar snapshots omit `.git`. Do not weaken that test or label a no-Git snapshot failure as an app regression. Use `bun x` rather than assuming a `bunx` executable exists in the fleet toolchain; resolve frozen root/app/bridge dependencies inside the disposable job and fetch its raw gate logs.

Keep integration tests that import app notification/model code under `app/src`, even when they spawn the real bridge. Importing those helpers into a `bridge/src` test drags React Native ambient globals into the bridge typecheck (conflicting AbortSignal/URL/stream overloads). Preserve the cross-process runtime proof but keep TypeScript compilation domains separate; do not paper over the resulting errors with casts or global type changes.

Run `bun run typecheck`, `bun run lint`, `bun run test`, `bun scripts/mutate.ts --threshold 80 --max 200` serially. Preserve stdout/stderr logs outside the repo. Root test suite includes the real bounded ffmpeg pairing decoder: CI must install ffmpeg rather than skip or mock those tests. Refresh `gh pr checks` at exact head and inspect logs before claiming green. Report local and hosted mutation scores separately when executions differ.

## ACP evidence

Use checked-in `bridge/acp-runtime.ts` with an absolute receipt path. It serially initializes, creates a native session and checks one harmless fixed-word real response for OMP, Hermes, Grok and maintained Claude/Codex adapters, preserving negotiated versions/timing and exact executable. Grok's isolated command is `grok agent --no-leader stdio`; Claude/Codex adapters are pinned under `bridge/acp-adapters/`.

Do not equate fixed-word transport success with permission/edit/cancel/live-adoption parity. Keep compatibility CLI behind its explicit feature flag until that broader parity is proven. Retain terminal failure/no-duplicate-submission behavior and deny unadvertised client capabilities.

## Flow law qualification without devices

- Resume dirty flow work before replacing it. Run the four off/L3/L4/L7 seeded canaries serially and restore source in `finally`; distinguish reproduced canary rejection from historical red-first evidence.
- Exercise a draft's cold-restore/background race explicitly. A background or unmount flush before hydration must not overwrite persisted ink with the empty startup state.
- Use `scripts/mutate.ts --file <module> --all --max 10000 --threshold 85` when complete collected-operator coverage is needed. The default plan samples branches; report the two plans separately and retain raw survivor locations. Neither plan is a complete semantic proof.
- Label `scripts/flow-pen-web.ts` as a helper/DOM proxy. Injected crop/upload adapters and localStorage do not prove the real Composer, Skia crop, Android storage or gesture path. A double-rAF marker is not a native latency baseline.
- Do not emit `chip.paint` when screenshot/upload resolves. Record a real paint/layout boundary with a correlated turn identifier, or leave the metric unavailable. Likewise, an optional native clock reader missing from the APK means calibration is null, not zero-offset success.

## Browser evidence

1. Export debug web with `EXPO_PUBLIC_DEBUG=1 EXPO_PUBLIC_DEBUG_AUTONAV=0 CI=1` to a scratch directory; serve with an owned HTTP child on an unused non-8097 port.
2. Run the app's debug scenario controls to capture Pair, Bots/empty, Chats/empty, Chat/streaming, Orchestra/empty/detail, Settings, Voice/fallback and search/files. Save a manifest containing exact Git SHA, unique scenario count and page errors. Inspect the actual PNGs; expected placeholder mismatches need review, not a fabricated PASS.
3. Export production web separately with debug disabled. Prove `window.__DASH_DEBUG__` is absent. Launch an owned tailnet-bound bridge with temporary credential directory/cwd, never a throwaway HOME that hides provider logins.
4. Allow only that owned web Origin in DASH_ALLOWED_ORIGINS. Enrollment needs an explicit browser preflight/CORS response plus separate bootstrap authentication on actual request. Wrong Origin/Host remains denied; OPTIONS is not execution authorization.
5. Enroll through Pair, seed at most an empty conversation (never a reply), send through the real composer, and assert exact persisted assistant text with terminal done state. Seed persisted data with a sessionStorage-guarded addInitScript before hydration, not by mutating storage underneath the running store (its debounce can overwrite the seed). Never reset that seed on reload. Reload and verify the same reply. Capture live Chat/Bots/Orchestra separately from fixtures.
6. Exercise real nav tab clicks and assert aria-selected and rendered pane text. Debug scenario setters bypass the imperative web pager path and can hide a no-op MainPager.setPage even when every fixture screenshot looks right. Preserve the native callback-shaped onPageSelected contract in the web fallback.
7. Keep temporary bootstrap/execution tokens out of logs/receipts. Close owned browser and HTTP/bridge processes and remove credential directory in finally.

## Approvals / factory-gate qualification

- Resolve project targets and queue locators from the factory clone's `origin/HEAD:factory/projects.json`; a cached queue cohort is evidence, not a second project registry. Reconcile old ready rows with actual publication receipts before seeding. Already-posted, explicit draft/merge holds and legacy/missing routes stay stale or blocked; never manufacture real bulk-ready items to satisfy a demo count.
- Real bulk-ready items come from existing author-owned origin PRs with unanswered review comments that a recent factory repair already fixed (check `gh api repos/<o>/<r>/pulls/<n>/comments` for `in_reply_to_id`, compare the fix commit). File them as `pr_review_reply` with `comment_id` + current `head_sha`; targets whose rules need human text or CLA are never bulk-ready. Policy-check pending items with `FactoryGuard.preflight` from the gate worktree (read-only), since `gate post --dry-run` refuses unapproved items. Do not mark an unchanged item stale just because preflight blocks it: an identical re-proposal dedupes onto the stale record.
- Exercise automated approvals only in an isolated copy of the real outbox, with generated fixture credentials, live posting off and canonical owner-decision recording off. Label synthetic bulk fixtures plainly and report them separately from real pending items. Rehearsal clicks must never create human-approval-shaped coordination receipts.
- Pin the clean source SHA before export and write build metadata from that export job after confirming the head and tracked tree did not change. Require the serving process to read that artifact metadata; deriving build identity from the serving checkout can falsely label a stale export.
- Keep new MainScreen actions below BridgePullOverlay's 24px gesture hit band immediately under the 60px nav. A button centered in that invisible band is visibly present but unclickable. Use real pointer clicks in the regression, never force-click or a debug navigation setter.

## Handing a build to the owner's phone

The owner uses Dash inside Expo Go and pairs the way the app does: sonic pairing or a magic link. Don't send him to a static web preview, because he expects the app he already uses. When he wants to try a branch:

1. Check `ss -ltn` for 4747 (bridge) and 8097 (Metro). If they're free, start both from the branch worktree as owned background processes:
   - bridge: `cd bridge && DASH_HOST=<tailscale-ip> DASH_PORT=4747 DASH_CREDENTIAL_DIR=~/.dash bun index.ts`. For the gate, add `DASH_GATE_ENABLED=1 DASH_GATE_LIVE=0 DASH_GATE_OWNER_DECISIONS=1`.
   - Metro: `cd app && REACT_NATIVE_PACKAGER_HOSTNAME=<tailscale-ip> CI=1 bunx expo start --port 8097 --lan`.

   If a dash-pair is already running, ask before replacing it. When he says "just do the sound pairing" or asks for a link, do exactly that; don't re-explain alternatives.
2. Verify both before sending anything: `curl http://<ip>:8097/status` must return 200. Then make an authorized `GET /pair` with `Authorization: Bearer $(cat ~/.dash/bootstrap-token)`; it returns a 6-character code and `expiresAt`, which is about 3 minutes away. Save the response at mode 600 in scratch. Never print the token or code.
3. `GET /pair` returns the bridge's *current* session when one is open, and that session may have only seconds left. Check `expiresAt - now`. If it's under about 2 minutes, wait for it to expire and request again before sending.
4. Get the device id from `kdeconnect-cli -a --id-name-only`. Open the app with `kdeconnect-cli -d <id> --share 'exp://<ip>:8097'`. For pairing, `GET /pair` now returns `expoGoLink`; sharing it opens Dash with address and code prefilled (bootstrap token still entered privately). Confirm once on the handset; manual pairing below remains the fallback.
5. The pairing route that works is manual: Address `<ip>:4747`, plus Token = the contents of `~/.dash/token` (the execution token, not the bootstrap token). Send the token from a Python subprocess with `kdeconnect-cli -d <id> --share-text <token>` so it never appears in output or chat. The sonic fallback is Settings → Pair nearby (sonic), with computer name = host. Confirm the pairing from the bridge log, and the bundle load from the Metro log line "Android Bundled".
6. Leave the processes running and say so. Posting stays off until the executor is qualified.

## Roster truth (what the phone lists)

- OMP chats come only from `~/.omp/run/daemons/*/broker.{sock,pid}` with a live pid. Threads the phone shows beyond those are its own persisted store from earlier pairings. Reconcile them against each roster refresh and mark them stale/ended; never show them as live.
- Hermes appears as profiles, not sessions, unless the bridge lists sessions. Use the Hermes API server's `GET /api/sessions` and `GET /api/sessions/{id}/messages` (the same server that `hermes-session.ts` already sends `/api/sessions/{id}/chat` to), or read profile `state.db` files read-only as z0live's `work_sources.py` does. Never forward API keys to the phone.
- "Stuck on sending" plus "reply queued until it closes" on an existing Hermes chat is the bridge's live-owner handoff wait: `runtime/active_sessions.json` lists a live CLI/TUI holding that session's lineage. Before calling it a bug, find out what owns that pid. A Hermes CLI/TUI session runs inside the gateway process (`ss -lxp` shows that pid on `gateway.sock` and the API port), and the CLI is just a client of it. The owner treats Dash and the CLI as two surfaces of one backend. So for a gateway-hosted owner, route the message through that gateway, the way a second client would. Wait for the handoff only for a standalone CLI that hosts its own agent.
- When the owner is away from the desk and needs a working phone-to-agent path now, a NEW Dash chat with the Hermes harness on the same profile works immediately. Write a short handoff note file with the state that's in flight and have that chat read it. The session that dispatched them still receives the background-worker results, so say so.
5. Leave the processes running and say so. Posting stays off until the executor is qualified.

## Report and checkpoint

Update the existing draft integration PR and preservation ledger, verify remote readback, preserve closed stale PR branches and keep #8/#9 residual/device criteria open. Report per-page evidence, agent negotiated/CLI versions and elapsed timings, exact-head hosted CI URL and explicit S25 limits: IME, native motion, sonic pairing, lock/reconnect, actual desktop-session controller ownership, permission/tool/cancel/resume parity and z0live/audio lifecycle. Save the final checkpoint in the assigned profile scratch directory.
