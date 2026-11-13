---
name: noop-hermes-agent-access
description: Use when testing Hermes control of NOOP via tailnet.
---

# NOOP × Hermes agent access (fork-only, kvnloo/noop)

Code: branch `feat/android-hermes-agent-api` (PR kvnloo/noop#95), Android `com.noop.agent.*`, Hermes side `Tools/hermes-agent/`, doc `docs/HERMES_AGENT_ACCESS.md`. Study: kvnloo/z0evals `studies/noop-hermes-agent-api` (#108).

## Shape (why)
- MCP, not ACP: Hermes calls tools ON the phone. NOOP serves JSON-RPC `POST /mcp` on its Tailscale IPv4 :8765 only while a time-boxed grant runs (memory-only; reinstall/restart = OFF).
- Identity = an ordinary z0live broker device pairing. Phone keeps only SHA-256(token) and re-checks `/v1/devices/self` every 5 min, so `noop-agent-pair revoke` cuts access within 5 min (measured 4m57s).
- Hermes uses stdio MCP `~/.local/bin/noop-agent-mcp` (registered as `noop` in the clean profile config). It runs in venv `/mnt/zer0models/venvs/noop-agent-pii` (Presidio + spaCy sm + `mcp<2`; mcp 2.x removed FastMCP). The wrapper must `env -u PYTHONPATH` because Hermes leaks its own PYTHONPATH.

## z0bridge pairing (v2, current since 2026-10-21; kvnloo/noop#96, kvnloo/z0bridge#2)
- Identity now comes from z0bridge, not z0live. NOOP is a z0bridge *resource* (`noop@dev_…705071`) that pins z0bridge's ES256 key. Hermes holds `~/.config/noop-agent/z0bridge-credential.json`, a 0600 `hermes/noop-agent` client credential. `credentials.json` has a `z0bridge` section and no token. Tokens last 120 s and are verified offline on the phone. A tool needs its scope in BOTH the on-phone grant and the token (`token_scope_required`).
- Revoke with `z0bridge revoke cred_… [--scope noop:health.read]`, re-grant with `z0bridge grant`, and replace with `z0bridge enroll-local … --force`. None of these need a phone action. Measured: the phone refuses a held token 61 s after the revoke (ttl 60).
- The daemon is the transient unit `z0bridge-identity` (identity-only, loopback :4789, tailnet :4788). Do not move it to :4787: Dash switches its Hermes transport when :4787 is healthy.
- Re-pair with `noop-agent-pair pair-z0bridge kevins-s25-ultra [--deeplink-file F]`. It revokes the replaced legacy z0live `noop-agent:` device, and nothing else: the gesture broker (`noop-oura-ring`) and Lawnchair keep their own z0live devices.
- Hermes's gateway keeps a long-lived `noop` MCP subprocess. After changing the credential kind or the code, that process still sends the old credential (`refused_bad_token` on the phone) until Hermes's MCP is reloaded.
- **Hands off the S25 UI when the owner is holding it.** He objects to visible scrolling and taps. For any phone step, send him a one-line notification or link and let him tap. `cmd notification post` from the shell cannot carry an activity content-intent (Permission Denial), so send text only. Installing restarts NOOP and loses an armed ring capture, so install only builds from `integrate/s25-20261020` that include the gesture worker's commits, under the install lock.

## Run it (legacy z0live pairing)
1. `noop-agent-pair pair kevins-s25-ultra` prints a one-shot `https://0.taila30dc.ts.net/z0pair/<nonce>` URL. Open it on the phone, tap Open NOOP & pair, then Confirm pairing from link. Pairing survives `install -r`.
2. In NOOP > Settings > Advanced > Hermes agent access (or `am start -n com.noop.whoop.debug/com.noop.agent.AgentAccessActivity`), tick scopes and tap Allow.
3. `Tools/hermes-agent/e2e_phone.py OUT.json --action=open_screen:sleep` runs 12 checks with no adb and writes structure and latency only.
4. Hermes turn: `hermes -p clean chat --oneshot -Q -q "...use the noop tools..."`. Write its output to a private 0600 file, because it contains health values.
5. Verify with adb (read-only): `run-as com.noop.whoop.debug cat no_backup/agent-audit.jsonl`. It holds counts/outcomes, not values.

## Pitfalls
- Simplest full read for analysis on groot: `limitless-sync` (kvnloo/.files#140) copies NOOP's DB via `run-as` every 15 min into `/mnt/zer0models/sft-svlm/data/limitless/state/noop/noop_whoop.db` (WAL folded, 0600). Query that copy read-only rather than arming a grant. Journal answers live in `journal(day, question, answeredYes, numericValue)`. This only works for the debug package: `com.noop.whoop.staging` is a release build (`run-as: package not debuggable`), so its data reaches groot only through Health Connect writeback or by pairing the strap with the debug app.
- Custom journal items are added on the phone: Today > Quick actions > Log journal, then the field "Add a custom item..." at the bottom of the journal card. fsd `key` takes integers only (`key 4`, not `key BACK`), and the field moves down after every add, so re-screenshot before each tap. A wrong add is removed via Edit > Delete.
- Health Connect auto-sync is on-open only upstream; background import is kvnloo/noop#104 (needs READ_HEALTH_DATA_IN_BACKGROUND).
- The installed APK must be built from the OTHER workers' current stack tip plus these commits (local branch `local/s25-hermes-agent-integration`, worktree `/mnt/zer0models/noop-hermes-agent-s25`). Re-check `git rev-parse feat/android-breath-camera` and the phone's `lastUpdateTime` right before `install -r`. Their branches move every ~10 min.
- Gradle on groot: do not queue behind heavy.lock (owner rule). Use `--max-workers=2 -Dorg.gradle.jvmargs=-Xmx3g -Pkotlin.compiler.execution.strategy=in-process`, or build on mbp once `scripts/fleet run --node mbp --no-src -- sh -c 'command -v java'` works. Run Python tests with `scripts/fleet run --node mbp --src ...`.
- MBP build lane: `fleet-build --android --jdk 17 --class build --wait -1 --out <dir> --fetch app/build/outputs/apk/full/debug -- bash -lc 'mkdir -p app/build/roomSchemaOracle; ./gradlew --no-daemon :app:assembleFullDebug'` from `android/`. A bounded `--wait` that expires leaves its Kueue workload pending (exit 75). Delete your own job (`kubectl -n fleet-mbp delete job <name from the log>`) before resubmitting, or two copies queue.
- `testFullDebugUnitTest` can fail its configuration when `app/build/roomSchemaOracle` is missing. Run `mkdir -p` on it and run the test task on its own, after assemble.
- The flavor is required: `assembleFullDebug` / `testFullDebugUnitTest` (package com.noop.whoop.debug, fork-debug.keystore digest 4511d903…).
- spaCy sm tags brand names (oura/whoop) as PERSON. Keep closed-vocabulary fields in SAFE_KEYS.
- Each surface holds its own AgentAudit instance, so the lock must be process-wide or entries are lost.
- Background activity starts are blocked. `open_screen` uses in-app navigation only when NOOP's process is foreground; otherwise it posts a tap-to-open notification (`landed:false`). The owner's foreground app is never stolen.
- The phone is the owner's daily phone. Check `topResumedActivity` before every tap and return them to their app afterwards. FLAG_SECURE: use `uiautomator dump` text and bounds, not screenshots.
