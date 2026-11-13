---
name: device-credential-handoff
description: "Use when sending tokens or CLI sign-in links to the phone."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [pairing, tokens, android, tailscale, qr, telegram]
    related_skills: [phone-adb-tailnet-qualification, lawnchair-z0live-delivery, secrets-manager-bws]
---

# Device credential handoff

## When to Use

Use this to deliver a device token, pairing deeplink or other bearer credential from the desktop to one of the owner's own devices: z0live, app pairing or `myapp://pair?token=` links. Also use it when a CLI on the host needs the owner to sign in again (`gh`, `vercel`, any OAuth device flow).

## CLI sign-ins (device flow)
When a CLI reports it is logged out or its token is unreadable, don't stop and ask the owner to run `<tool> login`. He expects you to start the sign-in and send the link to his phone so he can approve it there.
0. **Rule out a broken shell first.** "Not logged in" is often a readable keyring behind a stale `DBUS_SESSION_BUS_ADDRESS` (`/tmp/dbus-*`). Retry the status check with `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus`, and for gh with `/usr/bin/gh` (see the github skill's auth troubleshooting table). Start a device flow only if that also fails: each unneeded code costs the owner a sign-in, and unapproved codes expire.
1. Start the device flow as a **background** process and poll its output for the URL and user code. For `gh`: `BROWSER=true GH_PROMPT_DISABLED=1 gh auth login --hostname github.com --web --git-protocol ssh --skip-ssh-key --scopes <needed>`. Add `--insecure-storage` when the keyring can't be read (file stored 0600 in `~/.config/gh/hosts.yml`), and tell the owner you did.
2. Open the approval page for him instead of making him type the code. Load `https://github.com/login/device?user_code=<CODE>` (other providers: their verification URI with the code) in a new tab of the Bot Screen browser (`browser_exec`). GitHub keeps the code through its login redirect (`return_to`). Raise that window on :20 (`xdotool search --onlyvisible --name '<title>' windowactivate`), then send him the Bot Screen noVNC tailnet link (skill secure-provider-onboarding, Standing permissions) plus the code and its expiry time. He signs in once, the profile keeps the session, and later approvals are one click.
   - A bare code in chat goes stale if he isn't watching. Device codes last about 15 minutes. When the login process exits with `context deadline exceeded`, mint a new code and re-open the page; don't just repost a code.
   - Taildrop (`timeout 60 tailscale file cp page.html <phone-node>:`, node from `tailscale status`) is an extra channel, not the primary one. It fails when the phone's peer API doesn't answer.
   - A device user code is not a bearer token. It works only inside his signed-in browser session, so it may appear in chat.
3. Keep working on everything that doesn't need the credential while he approves (build, push over SSH). Afterward, confirm `<tool> auth status` before using it.

## Localhost-callback OAuth (`omp login anthropic`, any PKCE flow with `redirect_uri=http://localhost:<port>/callback`)
The browser must reach the CLI's listener, so a phone sign-in normally ends on a dead page and a code to paste. Tunnel the port instead, so nothing secret passes through you:
1. Start the login as a background pty: `timeout 1200 script -qfc "omp login anthropic" /dev/null < /dev/null > login.txt`. Read the port from `redirect_uri` in its output and confirm the listener with `ss -ltnp | rg <port>`.
2. `adb -s <phone> reverse tcp:<port> tcp:<port>` (check with `adb reverse --list`). The phone's `localhost:<port>` now hits groot.
3. Send him `http://localhost:<port>/launch` (omp's shortcut that redirects to the authorize URL). He signs in on the phone and the callback lands in the CLI by itself.
4. One account per run: the port is fixed, so logins are sequential. For a second account, tell him to sign out of claude.ai first, then start a new run.
   - The CLI's own callback wait is about 5 minutes (`OAuth callback cancelled: TimeoutError`), far shorter than the outer `timeout`. Start each run only after he says "ready", and send the link in that same reply.
5. Verify by identity, not exit code: list the stored credentials' email/expiry fields (never tokens), then a real request per account. For omp, `sqlite3 -readonly ~/.omp/agent/agent.db "select json_extract(data,'$.email') from auth_credentials where provider='anthropic'"`, then `omp dry-balance --count 10` shows which account requests go to.
6. Give each harness its own login rather than copying another harness's Anthropic OAuth tokens: refresh tokens rotate, so two harnesses sharing one grant sign each other out, including the session the owner is in.
7. **omp account order** ("use the sub with usage left, ultra first"): set `omp config set auth.accountPolicies '[{"provider":"anthropic","account":{"email":"<first>"},"priority":30,"reservePct":5}, ...]'` (higher priority is tried first; `reservePct` moves off an account before its quota runs out) and `omp config set retry.usageAwareFallback true` (switches same-provider accounts before configured fallback models). Back up `~/.omp/agent/config.yml` first. Policies that match no stored account are ignored, so they can be set before the logins finish.

## Paste-back OAuth codes (`claude auth login`, any `code#state` flow)
The code is short-lived but becomes a long-lived token, so it goes through T3 `request_secret` (`delivery: "file"`), never chat.
- **Send the sign-in link as plain chat text first and end the turn**; open the card only after he says "ready". Links inside a card's `reason` are not clickable, and a card opened before he has the code just times out.
- The MCP call itself dies at 300 s: pass `timeoutMs` <= 280000. A timed-out or interrupted card is gone for good (no re-open button yet), so open a new one with a new `clientRequestId`.
- A pty owned by the Hermes `terminal` tool can only be fed through `process_manage submit`, which puts the code in your tool args. Run the CLI under a small `pty.fork()` wrapper that waits for a pointer file, reads the secret file and writes it to the pty itself. Give it a wait of hours, not one hour: a code that arrives after the wrapper stops is wasted, and each restart mints a new link he must re-approve. `ptrace_scope=1` and `legacy_tiocsti=0` on groot rule out injecting into a running pty.
- Never `pkill -f '<cmd string>'` from the terminal tool: it matches its own shell and kills the call. Kill by PID.

## Rules
- **The owner finishes the handoff himself.** He prefers to tap a link or scan a QR. Do not invent a flow that only the agent can complete. When he asks for "a QR" or "just send me the link", deliver exactly that.
- **Bearer tokens never go into chat** (Telegram history is stored in the cloud), command-line arguments that show up in logs, or tool output. Mint the token in-process, redact it from subprocess output with `.replace(token, '<redacted>')`, and print only lengths or ids.
- **Hermes' own `hermes pairing` is a different feature.** It approves which users may message the bot on a messaging platform and issues no app or device tokens. Say so instead of offering it.
- **Revoke every token a failed attempt left unused, right away,** and confirm the device list shows none left over.
- **Prove success outside the app.** Check the server's auth/request log, or the mtime of the app's credential store (`run-as <pkg> ls -la shared_prefs/`). Secure screens come out blank in screenshots, and "activity started" is not proof.

## Prefer z0bridge for new pairings
z0bridge (kvnloo/z0bridge, `docs/PAIRING.md`) is the single pairing layer. Use `z0bridge pair --app APP --name DEVICE --bind-node DEVICE [--kind resource] --scheme <app scheme> --link|--qr|--deeplink-file NEW_FILE`. Codes are single use, bound to the device's tailnet node (checked with `tailscale whois`), and never printed. An unused code expires on its own, so there is nothing to revoke. `z0bridge devices` / `revoke` / `audit` give the one paired-devices view.

## Delivery options, best first
1. **QR scanned inside the app.** The desktop CLI prints a QR (`qrencode -t ANSIUTF8`, or a 0600 PNG). The app scans it with a scanner that needs no camera permission (GMS code scanner) and sends the result through the same parse, confirm and store path as the deeplink.
2. **Chat-safe one-shot https link.** Use this when the owner wants a link in chat. Telegram will not make a custom scheme like `z0live://` clickable, and the token must stay out of chat. See `references/one-shot-tailnet-link.md`.
3. **ADB `am start -d <deeplink>`.** Use this only when the owner is watching the unlocked phone and has just said he's ready.
   - Resolve the handling package first with `cmd package query-activities -a android.intent.action.VIEW -d '<uri>'`. Several debug flavors can be installed at once.
   - A deeplink pushed while another app is in front launches behind it (`LaunchState UNKNOWN`, top activity unchanged). A confirm screen with a short timeout then expires unseen.
   - If the target activity isn't exported, it can't be brought forward with `am start -n`.
