---
name: hermes-dashboard-remote-clients
description: "Use when Hermes phone app/dashboard errors or logs out."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes-mobile, dashboard, tailscale, auth, android]
    related_skills: [phone-harness-android-fast-tree, hermes-acp-bridge-clients, hermes-agent]
---

# Troubleshooting Hermes remote clients (mobile app, tailnet dashboard)

The Hermes mobile app (`ai.nousresearch.hermes.mobile`, ktor-client UA) is a client of a profile's **dashboard** (`hermes dashboard`, systemd `hermes-web.service`). It is not a client of the TUI gateway directly. Find out which hop fails before reasoning about sessions.

## When to Use
Use when the Hermes phone app shows HTTP errors, shows an instance as "Unreachable", fails to open or control sessions, or keeps forcing re-login (session/OIDC expiry). Also use when a tailnet dashboard URL misbehaves.

## Ground rules before answering any auth question
- **Read the live service's config, not `~/.hermes/.env`.** Run `systemctl --user cat hermes-web.service` and read every `EnvironmentFile=` drop-in (e.g. `~/.hermes/dashboard-oidc.env`, generated from `~/.dsh/.credentials.yaml`; the bws runtime env). `.env` is not what the unit loads, so a setting that looks missing there may already be set.
- **Identify the client's auth path first.** The Android app (and Desktop) use the native RFC 8252 broker (`/auth/native/authorize` → `/token` → `/refresh`, bearer tokens held by the app), not browser cookies. Reason about the native refresh path, not cookie Max-Age.
- **Read evidence before theorizing:** `~/.hermes/logs/dashboard-auth.log` (JSONL audit). Count `login_success` vs `refresh_success`/`refresh_failure` and their spacing; `native_authorize_start` from the phone's tailnet IP at ~1h intervals with zero `refresh_success` = no refresh token ever issued.
- **Check upstream before proposing a patch:** `gh issue list/pr list -R NousResearch/hermes-agent --search "<symptom>" --state all`, plus the docs page `user-guide/features/web-dashboard` (Self-hosted OIDC section). Prefer adopting an open upstream PR over a hand patch, and warn that `hermes update` reverts local patches until merge.
- Session expiry with Google as the self-hosted OIDC issuer: see `references/oidc-session-lifetime.md`.

## Procedure
1. **Read the app's own error first, without touching the owner's screen.** He is often using the phone (even typing to you in this app) while you debug. Never `monkey`-launch, `input keyevent`, or tap on display 0: it steals his focus and he will call it out. Read-only first: `dumpsys window | grep mCurrentFocus`, `logcat -d --pid=$(pidof ai.nousresearch.hermes.mobile)`, server logs. If you must drive UI, use a focus-safe virtual display (android-agent-virtual-display) or ask him to tap one thing. Dump the UI tree with `uiautomator dump` instead of taking screenshots. Settings → Instances shows each instance's host and its reachability text, e.g. `Unreachable: HTTP 400`. That text tells you an auth or HTTP failure from a network failure.
2. **Map the chain from the instance host to the dashboard.**
   - `tailscale serve status --json`, and look at the Web handler for the instance's port.
   - `ss -ltnp 'sport = :<port>'` on each hop, then `/proc/<pid>/cmdline` and `systemctl --user status <pid>` to name the owning unit.
   - The typical chain: tailnet `:9119` → aiohttp WS/HTTP proxy `127.0.0.1:9165` (`hermes-drive-web-proxy.service`, chiefstaff `HERMES_HOME`) → dashboard `127.0.0.1:9119`.
   - The hops log nothing: the proxy sets `access_log=None`, and the dashboard runs without an access log.
3. **Check that the dashboard is running current code.** `hermes update --plan` lists running services due a restart. Compare the unit's start time with the checkout's update time. A dashboard started before an update serves stale routes, so restart it with `systemctl --user restart hermes-web.service` when it is idle. Verify the restart with `curl -w %{http_code}` on loopback, the proxy and the tailnet URL; 302 → `/login` is healthy.
4. **Capture the app's real requests when the logs are blind.**
   - Copy the proxy script to scratch and change its port (e.g. 9166). Enable `access_log`, and log the status, request JSON keys and response body for any status ≥400, redacting long tokens.
   - **Never** start it with terminal `background=true` + a manual `tailscale serve` repoint: the background process dies with the agent turn and leaves :9119 pointing at a dead port. The app then shows `Unreachable: HTTP 502` until someone notices (this was the 2026-11-02 "app keeps disconnecting" outage). Use `hermes-mobile-serve capture --minutes 10 -- <python> -u <copy>.py`: it runs the copy as transient unit `hermes-mobile-capture`, repoints :9119, and restores :9119 → 127.0.0.1:9165 on exit/crash/kill/timeout. Read it with `journalctl --user -u hermes-mobile-capture`; stop early with `systemctl --user stop hermes-mobile-capture`. `hermes-mobile-serve status` checks the mapping; the proxy unit also re-asserts it on every start (drop-in `80-tailnet-serve.conf`, source in `.files`). Events: `~/.local/state/hermes-mobile-serve/events.jsonl`.
   - To see the app's own status without touching the owner, launch it on a focus-safe display (android-agent-virtual-display, `FocusSafeDisplay`, own FIFO/log copy). The single app task moves to that display; flag 0x1ddc9 includes DESTROY_CONTENT_ON_REMOVAL, so on quit the task is destroyed rather than dropped onto his screen. Settings → Instances shows stale status until you toggle the instance off/on.
   - Ask the owner to reproduce once (one tap) and read the log; don't force-stop or relaunch the app yourself while he's using it. Mic/WebRTC features (Live Voice) can't be reproduced on a hidden display: the app is one process and the call grabs the real mic/speaker.
   - **Restore the serve mapping to the original target immediately afterwards**, and verify it with `tailscale serve status --json`. Then stop the copy.
5. **Interpret the dashboard's auth endpoints.**
   - `POST /auth/native/refresh` with an empty `refresh_token` returns **400 `refresh_token required`**. The app shows this as "HTTP 400" or "Unreachable" on every screen. It means the app holds no refresh token, and the fix is for the owner to sign in again in the app (tap the instance, or remove it and add it back).
   - The same endpoint returns 401 `session_expired` when the token is rejected by every provider, and 503 when a provider is unreachable. `GET /api/auth/providers` lists the sign-in methods.
   - Never enter his password or OIDC login yourself. Tell him which screen to use.
6. **Separate session-control errors from auth errors.** After auth works, `session.control.read ... not in memory (detached/reaped runtime; client should resume the stored session)` in `<profile>/logs/gui.log` means the client is controlling a live runtime that was detached. Pane relaunches and Tern channel switches detach runtimes. The client has to resume the stored session.
7. **Report** the failing hop, the evidence (status and body), what you changed and reverted, the owner action needed, and the upstream bug if any (e.g. the server could answer an empty token with 401 so the app shows its sign-in prompt).

## Google OIDC sign-in expiring hourly
- Google ID tokens last 1h. The app (native `/auth/native/*` broker) only renews if Google issued a refresh token, which needs `access_type=offline&prompt=consent` on /authorize (upstream issue #100147, PR #100157).
- Live config is `~/.hermes/dashboard-oidc.env` (systemd drop-in on hermes-web.service, mirrored from `~/.dsh/.credentials.yaml` refs), not `~/.hermes/.env`. The client secret is already set there.
- The checkout carries a local patch to `plugins/dashboard_auth/self_hosted/__init__.py` adding `HERMES_DASHBOARD_OIDC_EXTRA_AUTHORIZE_PARAMS` and `HERMES_DASHBOARD_OIDC_ALLOWED_EMAILS` (verified-email allowlist on login, refresh and verify), with tests in `tests/plugins/dashboard_auth/test_self_hosted_google_offline_allowlist.py`. `hermes update` autostashes it; reapply after updates.
- Verify: `curl -s -o /dev/null -w '%{redirect_url}' 'http://127.0.0.1:9119/auth/login?provider=self-hosted'` must show `access_type=offline`. In `logs/dashboard-auth.log`, look for `refresh_success` instead of an hourly `login_success`.
- **Sign-in loops after adding `prompt=consent` (server logs `native_code_issued` but never `native_token_*`):** the app's loopback listener gets the code, but its `/auth/native/token` POST fails with `Unable to resolve host` (a red banner that shows for about 3s). Android blocks network for backgrounded apps (`dumpsys netpolicy` → `blocked=APP_BACKGROUND`) once the app has sat behind the Custom Tab past its grace window. The consent screen makes that wait long; plain auto-redirect logins took about 3s and got through. Fix: exempt the app from battery restriction, which is the same as setting Battery → Unrestricted: `adb shell dumpsys deviceidle whitelist +ai.nousresearch.hermes.mobile`. Then sign in again; the capture should show `refresh_token":"1//…`.
- Hermes had no email allowlist before this patch. Only publish the GCP app to production (long-lived refresh tokens) while the allowlist is set.

## Voice in the mobile app
- The app's Live Voice ("GPT-Live") is already routed to the subscription adapter `hermes-mobile-subscription-voice.service` (127.0.0.1:9168, `gpt-live-1-codex`, voice `sol`) through the proxy drop-in `HERMES_MOBILE_VOICE_UPSTREAM`. Read `/mnt/zer0models/project-artifacts/hermes-mobile/subscription-voice/README.md` before changing anything.
- Check it on the phone: App Settings → Voice. It should show Speech engine GPT-Live, Live Mode Ready, MODEL gpt-live-1-codex, VOICE sol. The adapter journal logs `mobile voice readiness available=True` each time the app checks.
- The "Voice → Gpt Live → Voice" field (e.g. `marin`) is the profile's core `voice.gpt_live` config. The adapter ignores it and hardcodes `sol` and its own persona.
- **Debugging "Live Voice doesn't start":** the adapter logs only `readiness available=…` (status, which runs the same `/api/auth/me` bearer check as session), `subscription voice negotiated`, `signaling rejected status=…`, and `closed … reason=`. A 401/400/429 on `POST /session` is returned silently. So readiness lines with no `closed` line after a tap = the session request failed before a call was created; capture at the proxy (step 4) to get the status/body. App-side, `logcat --pid` does show `org.webrtc.Logging` (peer created → `stopRecordingIfNeeded` within ~0.2s = client gave up on the session response). Compare against the last `negotiated` timestamp vs dashboard/proxy restarts (`systemctl --user show -p ActiveEnterTimestamp`) to bound the regression.
- "Syntax error in regexp pattern near index 3 (?U)\s+" / Live mode stopped right after the voice agent delegates is an app bug: Android 1.0.0 (vc21) compiles `(?U)\s+` (ICU rejects it) when it formats the transcript for `session.delegation.created`. The adapter now runs delegations on the host (`hermes chat -q --oneshot -Q`) and never sends that event; see the README "Host delegation" section. Find such client bugs by pulling the APK and searching dex strings with androguard (`uvx --from androguard`).
- The same `(?U)\s+` crash also fires client-side at Live start, before any signaling (adapter logs no `negotiated`; mic opens and closes within ~12 ms in logcat): the app seeds Live with the open chat's last 24 user/assistant messages (each ≤1200, total ≤6000 code points) and normalizes them with that regex. No server fix is possible; start Live from an empty new chat. Restarting the adapter does nothing for this path.
- `hermes chat ... --source voice` fails with invalid_params; omit --source.
- Do not set `voice.voice_chat_mode: gpt-live` on the profile to "enable" it: core gpt-live needs a paid OPENAI_API_KEY and would break the desktop's chained voice. The adapter answers the mode for the app on its own.

## Pitfalls
- App error "gateway is running code from <sha> but the checkout on disk is now <sha>" (model/effort switch refused) = the DEFAULT multiplexed gateway predates `hermes update`. Bare `hermes` follows `HERMES_HOME` first and `~/.hermes/active_profile` second, and `HERMES_HOME` is exported from `.files` (`~/.config/environment.d/hermes-home.conf`, `~/.zshenv`), so `hermes profile use` alone doesn't redirect it: always pass `-p default` for gateway lifecycle commands. A plain `hermes gateway restart` restarts only the sticky profile's slot and leaves the default gateway's PID unchanged; check `systemctl --user show -p MainPID hermes-gateway.service` before and after. The agent terminal guard blocks gateway restarts even from ACP sessions; run `systemd-run --user --collect hermes -p default update --yes` and follow `journalctl --user -u <unit>`. It drains active turns first (up to agent.restart_after_turn_timeout, 30 min). Then restart `hermes-web.service` if `hermes update --plan` still lists the dashboard.
- `pkill -f <pattern>` run from the agent's terminal also matches the terminal's own shell command line, so the tool call dies with SIGTERM. Kill by PID from `ss -ltnp 'sport = :<port>'`, then confirm the port has no listener.
- The app doesn't log HTTP to logcat (WebRTC lifecycle only). Capture at the proxy for statuses and bodies.
- A profile list that still renders in the app does not prove the API works; it can be cached. Trust the proxy capture.
