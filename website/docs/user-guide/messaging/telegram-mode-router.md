# Single-token Telegram mode router: local setup

Status: disabled candidate. It does not read/change the BotFather token, create a bot, create a group/topic, invite anyone, restart the gateway, or write production config.

## Human-only setup

1. Captain creates private forum supergroups named `zer0 Company`, `zer0 Products`, and `zer0 Feeds` in the system Telegram client.
2. Captain adds the existing Hermes bot. Do not create another bot/token.
3. Captain enables forum topics and manually creates the topics listed below. Base groups cannot be created by the Bot API.
4. Keep groups private. Captain must be an administrator. Do not enroll other members yet.
5. After independent review, configure this router disabled, bind the existing Captain DM, and enable it only for a synthetic no-tools canary.
6. For each slot, Captain starts a one-time nonce in the Captain DM. The operator observes the exact group/topic ID and verifies `supergroup`, private membership, forum status, and Captain admin status using Telegram. Captain then approves that observed tuple from the DM. A nonce pasted in a group is insufficient.
7. Enroll `chiefstaff` first, then `starwars`. `mbp` remains inactive until a canonical speaking profile plus signed Mesh identity/health/trust receipt exists.

## Dry-run tree (no API calls)

- zer0 Company: Bridge; Company Council; Overnight Operations; Decisions Required; Reviews; Incidents; Receipts
- zer0 Products: Hermes3D; Hermes OSS; Keel+Mesh; Infrastructure; Content+Creative; Products+Experiments
- zer0 Feeds: YouTube Chat; GitHub/CI; Stream Health; System Health; Releases

Telegram supports `createForumTopic`, but this candidate intentionally contains no topic-creation call. A future apply step must show a dry-run mapping, require a separate Captain confirmation bound to the exact chat, generation, and topic names, and then independently verify the returned topic IDs.

## Controls and safety

Owner-only controls are `/status`, `/chat`, `/work`, `/updates`, `/feed`, `/authority`, `/freeze`, `/resume`, and `/mute`. Group/topic mutations require confirmation. Unknown chats/topics are silent. `frozen` lowers authority to `observe`; it is reversible and is not Keel activation. `autonomous` fails closed while the governance receipt is `RECORDED_NOT_ACTIVE`. Critical incident delivery may bypass a cadence preference, never the authority ceiling.

Visible output uses one bot and attribution like `[First Mate · chiefstaff]`. Local receipts carry only profile, lane, request ID, and verified-node marker. Audit records exclude message bodies, token values, raw nonces, chat titles, and private paths.

## Rollback

1. Disable the router; this restores the existing Telegram adapter path without changing the Captain DM/session.
2. Freeze enrolled routes, then remove their exact bindings from the router state through an reviewed migration (do not hand-edit a live state file).
3. Set feed routes to `off`; preserve relay cursors to prevent replay.
4. Remove the existing bot from newly created groups if isolation is required.
5. Keep audit receipts. Revoke the existing BotFather token only for a confirmed compromise.
