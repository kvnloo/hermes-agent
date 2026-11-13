---
name: hermes-messaging-gateway-routing
description: Use when routing a Hermes Telegram bot to a profile.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, gateway, telegram, discord, profiles, multiplex]
    related_skills: [hermes-agent, hermes-api-only-worker]
---
# Route a messaging bot to the right Hermes profile

The host runs one multiplexed gateway, `hermes-gateway.service` (HERMES_HOME=/workspace/hermes-home), which serves every non-standalone profile. A bot token can serve only one profile, and whichever profile claims a shared token first wins.

## When to Use

Use when the user asks to turn the Telegram or Discord gateway (back) on, wants to reach a specific profile or agent through a bot, or a bot answers from the wrong model.

## Procedure

1. Inventory the token before starting anything. Compare `grep '^TELEGRAM_BOT_TOKEN=' profiles/*/.env | sha1sum` across profiles. Also check every profile whose config has `secrets.bitwarden.enabled: true`, because bws injects tokens at startup and an `.env` without the token can still claim the bot. Resolve the bot name with Telegram `getMe`, and never print the token.
2. Choose the target profile. When the user wants to talk to "you", that is the current profile (its model), not whichever profile historically owned the bot. Run `hermes -p <p> gateway status` for health and duplicate-credential warnings.
3. Start or restart the gateway: `systemctl --user start hermes-gateway`. Then grep `logs/gateway.log` for `telegram connected (profile: X)`. If X isn't the target (for example a bench profile on a cheap model), fix the routing:
   - Back up each config you edit to `config.yaml.bak-tg-<epoch>`.
   - Set `platforms.telegram.enabled: false` and `platforms.discord.enabled: false` in every non-target profile that holds the token.
   - Set `platforms.telegram.enabled: true` in the target.
   - Copy `TELEGRAM_ALLOWED_USERS` (and `TELEGRAM_HOME_CHANNEL`) from the old owner's .env into the target's .env. Without the allowlist, the bot is open or unauthorized.
   - Validate the YAML with the Hermes venv python (system python3 has no yaml), restart the gateway, and re-check the connected-profile line.
4. Prove it: send one message through the bot to the allowed chat ID and confirm `sendMessage ok`.

## Pitfalls

- A profile marked `gateway.standalone` is skipped by the multiplexer for adapters, but the multiplexer's cron still ticks it. A separate API-only host for that profile can coexist on the same state.db.
- A gateway chat is a new session. It is not the user's live CLI conversation, so say so rather than implying continuity.
- If `getUpdates` returns 409, another poller owns the token. Find it before starting a second one.
- When the owner reports Telegram spam or a burst of late messages, check for duplicate sends before blaming lag. The gateway chat is itself a session (`sessions.source='telegram'`), so group its assistant messages by `substr(content,1,80)` and timestamp. N identical rows at the same second means each reply was delivered N times; the same text again minutes later means the batch was replayed. Also look for another profile (e.g. a chief-of-staff bot) relaying into that chat, and for a looping flow that re-mints device codes. Report the source; don't guess.
- Report every config change (files and backups) to the user, since you edited profiles other than the current one.
