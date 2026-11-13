---
name: hermes-agent
description: "Use, configure, theme, extend, and orchestrate Hermes Agent."
version: 3.2.0
author: Hermes Agent + Teknium
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, bots, bot-mode, features, themes, skins, desktop-plugins, tui-widgets, petdex, development]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [claude-code, codex, opencode]
---

# hermes-agent

Use when using, configuring, theming, extending, or supervising Hermes Agent.

## Rules

1. Resolve the active profile, physical HERMES_HOME, client surface, native session, and gateway owner first. Use get_hermes_home() in code and preserve profile/history ownership.
2. Check installed help, exact source revision, and the documentation index before declaring a feature absent. Verify official mobile distribution separately from public source, enrollment, installation, and authenticated chat.
3. Change settings with hermes config set, keep secrets in the private credential store, and read back only needed nonsecret fields. Use references/configuration.md and references/security-privacy.md for controls.
4. Preserve cached prompt/tool definitions and message-role alternation. Separate hot-reloaded handlers from tools or prompt sections requiring a fresh session; verify behavior in the consuming client.
5. Repair the exact account/model through the shortest supported control, then run a bounded fresh-chat probe. Keep saved identity, credential selection, inference health, and affected-client acceptance separate.
6. Qualify fallback routes and delegation overrides only within authorization. Resolve refresh-grant ownership before account reuse; report requested account identities without exposing tokens or unrelated accounts. See references/providers-and-models.md.
7. Use native goal, loop, or cron semantics for continuation. Reconcile session lineage, admissions, pauses, budgets, and the original mandate before retrying; persist submit intent and reconcile unknown outcomes before resending.
8. Choose delegation versus independent workers by task and lifetime; keep GPT workers in fx/pi under the owner's 2026-11-04 harness rule. Verify parser/gateway options, real tool progress, artifact coverage, and deadlines; hold exhausted or denied lanes without paid fallback.
9. Migrate a live session make-before-break using its exact ID. Verify attachment before closing the old viewer; last-viewer closure can interrupt session-owned children even while the gateway survives.
10. Preflight shared-owner updates and restarts using running revision, live turns/children, recovery checkpoints, credential bootstrap, and an agreed window. Keep a healthy owner running when startup prerequisites are unavailable.
11. Use hermes skin set for a one-color tweak and apply skins yourself. Extend the correct desktop/TUI surface through its native SDK and templates; preserve theme variables and owner focus.
12. Preserve the existing hermes launch interface and independent profile choice when selecting frontends. Verify branch bundle and Python-handler provenance; qualify a Tern channel switch on the same consuming session.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
