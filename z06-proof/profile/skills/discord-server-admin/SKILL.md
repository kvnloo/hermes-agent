---
name: discord-server-admin
description: "Use when administering or adding bots to a Discord server."
version: 1.0.0
metadata:
  hermes:
    tags: [discord, community, permissions, connectors]
---
# Discord server admin (audit, plan, restructure)

## 0. Resume an existing plan
- When the user asks for "the plans we made", read `/mnt/zer0models/project-artifacts/<server-slug>/PLAN.md` first (find it with `search_files pattern='*discord*' target=files path=/mnt/zer0models/project-artifacts`, then pick the non-source directory). That file is the source of truth; do not reconnect or rescan just to recall it.
- Summarize it as: nothing changed yet (or what has been), risks, target layout, role ladder, who-does-what, owner checklist, open decisions. End by naming what unblocks the build (decisions + owner checklist).

## 1. Connect
- The owner wants the agent to do the whole build itself, not hand back long click-through checklists. Plan for full API control from the start.
- Full control means raw Discord REST through a Hermes gateway bot that is already in the server. Find it with `grep -oHE '^DISCORD_BOT_TOKEN' ~/.hermes/profiles/*/.env` (for 🅱ater it is "groot" in the chiefstaff profile). Read the token inside a script, never print it, and confirm with `GET /users/@me/guilds`. The Composio `discordbot` connector cannot edit roles, member roles, guild settings, AutoMod or Onboarding, and it cannot see role-gated channels, so it is only a fallback for additive builds.
- Let the owner choose the bot's power with `clarify`: Administrator on its role dragged to the top, or scoped Manage* permissions plus the gating roles. Administrator is the only way to see channels whose @everyone overwrite denies View. Even Administrator cannot set the mod 2FA requirement; that is owner-only.
- Keep the admin bot private. Never make an admin-capable bot answer other members. Public AI or voice bots get their own Discord app and Hermes profile (`references/hermes-discord-bot.md`).
- When a bot holds Administrator, route every call through a guarded helper, which for 🅱ater is `/mnt/zer0models/project-artifacts/bater-discord/dapi.py`:
  - It refuses DELETE, bans, prune, guild PATCH, dangerous role permissions and member changes unless confirm="METHOD path" is passed.
  - It snapshots the server before each such call, caps destructive calls at 3 per run, supports BATER_DRY_RUN=1 and logs to actions.log.
  - Pass confirm only after the owner approves that exact action in chat.
  - Copy this helper for other servers.
  - Tell the owner the guard binds only the agent: the real control is removing Administrator when idle.
- Connector fallback: `manage_connections action=connect connectors=["discordbot"]`. One connection covers the one server it was installed in. Find tools with `tool_search` (`discordbot list guild channels`, `discordbot create role`); `GET_CONNECTED_GUILD` and `UPDATE_CHANNEL` exist even when search misses them.

## 1b. Servers the owner does not admin (e.g. Nous Research)
- A bot reads a server only after someone with Manage Server invites it; the owner's consent alone is not enough. Offer: mods invite a private read-only bot (`permissions=66560` = View Channel + Read Message History), or a user-installed app with a message context-menu command (owner forwards chosen messages; no mod approval). Never automate the owner's user account (self-bot, user-token exporters): ToS ban risk. Plan + mod draft: `/mnt/zer0models/project-artifacts/hermes-agent/community/README.md`.

## 2. Scan read-only first
- `GET_CONNECTED_GUILD` (settings, roles with permission bitfields, features, verification, mfa, system/rules/safety channel ids), `LIST_GUILD_CHANNELS` (categories, overwrites, last_message_id), and `LIST_MESSAGES` on rules/welcome/general (limit 5-15) to see whether they hold real content or just chat.
- Decode every role's permission integer with `scripts/decode_perms.py <int> ...`. Flag MENTION_EVERYONE on ordinary roles, ADMINISTRATOR/MANAGE_* outside a mod role, and @everyone CREATE_INSTANT_INVITE/TTS.
- Decode the connector bot's own role too: it shows what you can actually change. Private channels the bot cannot see return a provider error; report them as not scanned.
- Before calling a bot role dead, check that bot's recent messages in any channel. Shut-down bots sometimes relaunch (Rythm did), and deleting a live bot's role breaks it.
- Decode the connector role before planning any build. A freshly installed connector often has only send/read, so every create call would fail. Ask the owner for the grants first instead of probing with failing calls. After the owner says "done", re-run `GET_CONNECTED_GUILD` and decode again; owners often miss one grant, and the new set can drop perms the role had before. The bot still inherits @everyone perms, so check those too.
- When the owner wants existing channels kept, sample each public channel (`LIST_MESSAGES` limit 5-6; 25 only for #general) and write a short "what the server was for" section into the plan. Message payloads are huge, so keep limits small and batch them into one `tool_call`.
- Flag: dead bot roles (shut-down music bots), duplicate roles, duplicate channel names across text/voice, channels idle for years (snowflake -> ms: `(id >> 22) + 1420070400000`), unset system/safety channels, Low verification, mod 2FA off, no moderator role.

## 3. Plan before changing
- Write the plan to the project artifact store (one directory per server): current state, risks before inviting people, target category/channel layout, role ladder, a "who does what" split, the owner's settings checklist, and numbered decisions.
- Split by capability: list which operations the connector exposes (create channel/role/webhook/thread, post/pin, welcome screen) versus settings only the owner changes in the UI (verification, 2FA, AutoMod, Onboarding, system channels, editing or deleting existing roles/channels). Give the owner a short click-path checklist for the second group.
- Ask the owner to grant the connector's role only Manage Server (welcome screen), Manage Roles, Manage Channels, Manage Webhooks (GitHub feeds) and Manage Messages (pins). Never Administrator.

## 4. Change safely
- `UPDATE_CHANNEL` (parent_id/position/name) can move and rename existing channels once the bot has Manage Channels. It fails with a provider error on any role-gated channel whose @everyone overwrite denies View Channel, because the bot cannot see it. Predict those from the overwrites and hand them to the owner as a drag list. Do not fire calls you know will fail.
- Save the original parent/position of every channel to a JSON file in the plan directory before a re-org, for rollback.
- `tool_call` takes at most 10 calls per batch.
- Unattended (owner asleep): only additive or easily undone changes (new channels/categories/roles, welcome text, webhooks). Deleting, archiving, or editing existing permissions waits for an explicit OK.
- Repurposing a friends/gaming server (e.g. OSS + gaming): keep existing members' spaces, add START HERE / COMMUNITY / topic / STAFF / ARCHIVE categories, opt-in topic roles via Onboarding, mentionable game-ping roles without @everyone, forums for showcase/help, a read-only GitHub feed via webhooks.

## 4b. Build (connector)
Follow `references/build-recipe.md`: roles first (created bare, lowest first), then categories, then channels with explicit overwrites, then posts and the welcome screen. Append a build log with every new ID to PLAN.md.

## 4c. Full build (REST via the admin bot)
Follow `references/rest-admin.md` for the order:
1. Dump the roles to JSON.
2. Move channels.
3. Strip @everyone pings and TTS from roles.
4. Set Mod's permissions and its position.
5. Delete roles only after a member scan shows nobody holds them.
6. Change guild settings.
7. Add AutoMod.
8. Set up Onboarding.
9. Add the roles-claim channel.

Then verify by printing the category tree, the role order, and the AutoMod and Onboarding state.
- Keep access roles and ping roles separate. Old game roles often gate private voice rooms, so offering them in Onboarding would let strangers into friends' rooms. Create permission-less `<Game> 🔔` ping roles for self-assign instead.
- When the owner says to keep existing channels, keep them all (no archive or rename of channels) and group them: game chats into GAMING, role-gated friend rooms into SQUADS, general hangout voice into HANGOUT. Renaming the default categories is fine.

## 5. Report
Lead with whether anything was changed. Then risks, the plan path, the owner's checklist, and the open decisions.
