---
name: agent-reach
description: >
  Use for X/Reddit/YouTube/social URLs and web research.
  MUST USE when user wants to research/search/look up/find anything on the
  internet — e.g. "research this topic", "do a deep dive on X", "search the
  web for X", "see what people say about X", "look this up".

  Also MUST USE when user mentions any platform or shares any URL/link:
  Twitter/X, Reddit, Facebook, Instagram, YouTube, GitHub, Bilibili, XiaoHongShu,
  Xiaoyuzhou Podcast, LinkedIn/jobs/recruiting, V2EX, Xueqiu (stocks), RSS.

  15 platforms, multi-backend routing (OpenCLI / per-platform CLIs / APIs).
  Zero config for 6 channels. Run `agent-reach doctor --json` to see which
  backend serves each platform right now.

  NOT for: writing reports/analysis/translation (this skill only FETCHES
  internet content); posting/commenting/liking (write operations); platforms
  that already have a dedicated skill installed (prefer that skill).
metadata:
  openclaw:
    homepage: https://github.com/Panniantong/Agent-Reach
---

# Agent Reach — internet capability router

15 platforms, multiple backends each. **When this skill exists, use it for
these platforms — do not invent your own approach.**

## Standing rules (apply for the whole session)

1. **Health-check before acting**: for multi-backend/login-backed platforms (XiaoHongShu /
   Reddit / Bilibili / Twitter / Facebook / Instagram), run `agent-reach doctor --json` first and
   pick the command group matching each platform's `active_backend`.
2. **Announce what you use**: say "using agent-reach, platform X via backend Y"
   before starting.
3. **On failure, follow the retry chains in references/** — never guess
   commands.
4. **For broad research tasks**: combine platforms (Exa for web search +
   Twitter/Reddit for discussions + XiaoHongShu/Bilibili for Chinese
   perspectives), collect in parallel, then synthesize.
5. **Watch versions for the user**: after finishing a substantial
   multi-platform task, run `agent-reach check-update` (fast, one API call).
   If a new version exists, append one line to your wrap-up: "Agent Reach
   vX.Y.Z is available — paste this to me to update: 帮我更新 Agent Reach：
   https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/update.md".
   Never interrupt the current task to update; never nag about the same version twice.

## Host notes (groot, Kevin's machine)

- **X/Twitter: this skill is the default, not xAI `x_search`** (owner rule; `x_search` is disabled in the Hermes `clean` profile). Order: `agent-reach doctor --json` → `twitter user-posts/tweet/search` → nitter mirror (`https://nitter.cf/<handle>`, xitter.cf) read via the browser tool, paging with the `Load more` link → `api.fxtwitter.com/<user>/status/<id>` for one post.
- **twitter-cli auth comes from Chrome cookies decrypted through the GNOME keyring.** If `twitter -v ...` stops at "Attempting browser cookie extraction", the keyring (org.freedesktop.secrets) is down or locked. Don't retry; use the nitter route and tell Kevin. Never print cookie values.
  - Agent shells sit on the bot screen's private D-Bus (`/tmp/dbus-*`), which has no keyring. `~/.local/bin/twitter` is a wrapper that pins `/run/user/1000/bus` (a pipx upgrade turns it back into a symlink; re-create it).
  - After a reboot with no desktop login, the login keyring stays locked and gcr-prompter has no display. Check: `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/login org.freedesktop.Secret.Collection Locked`. If `b true`, ask Kevin to run `keyring-unlock` in his own terminal (or log in at the desktop). Never run it for him or handle the password. Don't restart gnome-keyring-daemon: that doesn't help and re-locks it.
- **Web search:** prefer Exa (`mcporter call 'exa.web_search_exa(...)'`) over the generic `web_search` tool, which returns off-topic results for niche ML queries.
- **Hugging Face models:** `curl https://huggingface.co/api/models/<repo>` and `/raw/main/<file>` (README, config.json, run_manifest.json) work when `web_extract` does not.

## Routing table

| User intent | Category | Details |
|---------|------|---------|
| Web / code search | search | [references/search.md](references/search.md) |
| XiaoHongShu / Twitter / Bilibili / V2EX / Reddit / Facebook / Instagram | social | [references/social.md](references/social.md) |
| Jobs / LinkedIn | career | [references/career.md](references/career.md) |
| GitHub / code | dev | [references/dev.md](references/dev.md) |
| Web pages / articles / RSS | web | [references/web.md](references/web.md) |
| YouTube / Bilibili / podcast transcripts | video | [references/video.md](references/video.md) |

## Zero-config quick commands

```bash
# Exa web search
mcporter call 'exa.web_search_exa(query: "query", numResults: 5)'

# Read any web page
curl -s "https://r.jina.ai/URL"

# GitHub search
gh search repos "query" --sort stars --limit 10

# YouTube subtitles (NOTE: never use yt-dlp for Bilibili — see video.md)
yt-dlp --write-sub --skip-download -o "/tmp/%(id)s" "URL"

# V2EX hot topics
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"

# Bilibili search (bili-cli, no login needed)
bili search "query" --type video -n 5
```

## Login-backed platforms (pick by doctor's active_backend)

```bash
# Twitter search (twitter-cli preferred; retry chain in social.md)
twitter search "query" -n 10

# Reddit (NO zero-config path — OpenCLI or rdt-cli, login required)
opencli reddit search "query" -f yaml   # desktop
rdt search "query" --limit 10            # legacy/server

# XiaoHongShu (desktop prefers OpenCLI)
opencli xiaohongshu search "query" -f yaml

# Facebook / Instagram (desktop OpenCLI, browser session)
opencli facebook search "query" -f yaml
opencli facebook groups -f yaml
opencli instagram search "query" -f yaml       # user search
opencli instagram user USERNAME -f yaml        # recent posts from one user
```

## Environment check

```bash
# Channel availability + which backend serves each platform
agent-reach doctor --json
```

## Workspace rules

**Never create files in the agent workspace.** Use `/tmp/` for temporary
output and `~/.agent-reach/` for persistent data.

## Detailed references

Read the matching file when you need specifics (commands above cover the
common cases; references hold per-backend command groups, caveats, retry
chains — note: reference docs are written in Chinese, commands are universal):

- [Search](references/search.md) — Exa AI search
- [Social](references/social.md) — XiaoHongShu, Twitter, Bilibili, V2EX, Reddit, Facebook, Instagram (multi-backend/login-backed groups)
- [Career](references/career.md) — LinkedIn
- [Dev](references/dev.md) — GitHub CLI
- [Web](references/web.md) — Jina Reader, RSS
- [Video](references/video.md) — YouTube, Bilibili, Xiaoyuzhou

## Configure a channel

If a channel needs setup, fetch the install guide:
https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md

The user only provides cookies / one extension click; the agent does the rest.
