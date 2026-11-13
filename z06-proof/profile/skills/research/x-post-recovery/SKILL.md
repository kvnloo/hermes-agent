---
name: x-post-recovery
description: "Use when finding a half-remembered X post or video."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [twitter, x, search, video, recall]
    related_skills: [agent-reach, session-recovery, phone-adb-tailnet-qualification]
---

# Recover a half-remembered X post

## When to Use

Use when the owner asks you to find an X/Twitter post or video he saw, liked or bookmarked but can't name, or wants a list of candidate posts to scroll through.

## Approach

The owner describes a post by what the VIDEO showed ("an app where you make a shirt and stretch it"). The caption often contains none of those words, so keyword filtering alone fails. The final check is always visual.

## Procedure

1. **Check the prior session first.** Use session-recovery. Reuse its dumps (`$TMPDIR/likes_huge.json` etc.) and its ruled-out candidates. Never re-propose a candidate the owner already rejected.
   - **If he says he sent it to you ("check convo history"), grep every user message, not session titles.** He often forwards links from another client (T3 Code, phone) into a Hermes session about a different project, so topic keywords miss it. In each profile's `state.db` (read-only `file:state.db?mode=ro`), select `role='user'` messages from the last ~10 days, regex out every `x.com|twitter.com/<user>/status/<id>` URL, dedupe, and print each with ~300 chars of surrounding text plus date/session. Scan that context for his description words ("dash", "realtime", "prompting"). Do this before any X scraping; it is seconds versus hours.
   - Cover every source in one pass: all profile `state.db` files plus `~/.hermes/state.db`, T3's `statev2.sqlite` (`orchestration_v2_projection_messages`, role=user, `creationSource` mobile/web), and user-typed text in Claude Code / Codex / OMP / Grok jsonl (`scripts/collect_sent_links.py`). Then batch-fetch every hit through fxtwitter and grep the post text, not only the chat context. Grepping raw jsonl without filtering to user-typed turns returns over 1,000 ids from tool output and bookmark audits, which is noise.
   - "Links I sent you" is often wrong: the post may only be **bookmarked**. When sent links miss, check `twitter bookmarks --max 300 --json` next (minutes, not hours) and keyword-filter text plus quoted tweets. A sent link by the same author is a strong hint: pull `twitter user-posts <handle> --max 120 --json` and look for a numbered series ("Generative UI #2").
   - Only after those come up empty, try X search.
2. **Pull the owner's own surfaces with the `twitter` CLI** (signed in with his cookies; read-only, never like/bookmark/post):
   - Likes: a full dump via the pipx venv python: `c=_get_client(load_config(),quiet=True); c._max_count=12000; c.fetch_user_likes(c.resolve_user_id(HANDLE), count=12000)`. Run it in the background; it takes minutes.
   - Bookmarks: `twitter bookmarks --max 200 --json` plus every folder (`twitter bookmarks folders --json`, then `folders ID -n 400 --json`). The owner's bookmark taps can silently fail, so missing from bookmarks is weak evidence.
   - Feed: `twitter feed -n 200 --json` and `-t following`.
3. **Search X** with `scripts/xsearch.py` (see the pitfall below for why plain `twitter search` may 404). Batch about 15 queries per run, then pause, because X rate-limits search (429). Vary the vocabulary (object, action, medium, tool names, other languages) and combine `since:`, `min_faves:` and `filter:videos` in the query, plus the `Videos` and `Latest` products.
4. **Read a known post or a creator's recent posts without an account.**
   - **Exact text, quote and media:** `https://api.fxtwitter.com/<user>/status/<id>` returns JSON. `tweet.text`, `tweet.quote`, `tweet.media.all[].url` and `tweet.article.content.blocks` hold the full text of an X long-form article; the main `x.com/i/article/...` link is not fetchable.
   - **Recent posts by one person:** open the profile on a nitter-style mirror (nitter.cf, xitter.cf) with the browser tool and read `document.body.innerText`; it shows the full post text, dates and quoted posts without login. To go further back, follow the `Load more` anchor (`?cursor=...` href; select it by `innerText=='Load more'`, the `.show-more` selector misses it) page by page, collect `.timeline-item` innerText per page into a workspace file, and stop once `.tweet-date a` reaches the period you need. ~20 posts per page, so 6 pages covers ~3 months for an active poster. Mirror search pages sit behind a checkbox captcha, so page the profile rather than searching. If one mirror shows a suspension notice, try the next host. Fetch specific status IDs through fxtwitter for media and quotes.
   - **Summarise a creator's claims by what is verifiable.** Posts announcing results are mostly hype; anchor the summary on artifacts they link (HF manifests, repos) and say which claims you could check.
   - **Images:** load the media URL with vision. Benchmark tables often appear only in the image.
   - Use this route whenever the cookie CLI is unavailable, and for any read-only lookup where it is unnecessary. Never route X lookups through the xAI `x_search` tool: the owner made agent-reach the default for X and disabled `x_search` in the clean profile.
5. **Exa web search** (`mcporter call 'exa.web_search_exa(...)'`) is the only account-free search route. It finds product and company names to feed back into X search, and for "what has <creator> said about <topic>" it often returns nitter status pages and video-transcript summaries (usetranscribe, ainotes) for the creator's posts and talks. For a cheap read of a profile without the browser tool, `curl -s https://r.jina.ai/https://<mirror>/<handle>` returns the timeline as markdown. Exa rarely indexes posts only a few days old, so don't treat an Exa miss as absence.
6. **Verify visually.** Text filters only shortlist; the owner's description is of the video. Grab frames straight from the media URL: `ffmpeg -user_agent 'Mozilla/5.0 ...' -ss 3 -t 20 -i URL -vf fps=1/5,scale=240:-2,tile=4x1 -frames:v 1 ID.jpg`, run in parallel with `xargs -P 16`. Stitch 16 per labelled grid with PIL and inspect each grid with vision. Download only finalists (`-c copy` into the project's `refs/` dir) and build a fuller contact sheet.
7. **Present candidates** as post URL, author, date, likes and local mp4 path. When the find is part of a series, download the whole series and give a table; describe the video's states step by step (from a cropped `fps=1.2,crop=...,tile=4x3` sheet of the key segment) so the owner can confirm without opening it. Save a `FOUND.md` beside the videos. If two rounds miss, stop guessing and either ask 1–2 discriminating questions (app vs web vs desktop, 2D vs 3D, creator size) or hand him a scrollable list.
8. **Scrollable list for the owner:** rank about 100 video posts (relevance terms + tech terms + log likes + a boost for his own likes/feed), strip ad and AI-video-prompt spam with a regex, write a markdown list of `https://x.com/USER/status/ID` links, publish it as a secret gist and open it on his phone (phone-adb-tailnet-qualification). Keep a copy and the JSON in the project artifact store.

## Pitfalls

- **`twitter search` 404 + `Failed to init ClientTransaction`**: the logged-out x.com homepage no longer ships the JS bundles needed for the x-client-transaction-id. Build the ClientTransaction from `https://x.com/home` fetched with the owner's Cookie header instead. `scripts/xsearch.py` does this in-process without patching the install. A pipx upgrade doesn't help when already on the latest version.
- **`twitter` hangs with no output (or `agent-reach doctor` reports a twitter health-check timeout):** run `twitter -v user <handle>` under `timeout 25`. If it stops at `Attempting browser cookie extraction`, the CLI is waiting on the GNOME keyring to decrypt Chrome cookies. Check `busctl --user status org.freedesktop.secrets` and `pgrep -a gnome-keyring-daemon`: no bus owner, or two daemons racing after boot, means the keyring never came up and bws bootstrap lookups hang too. Restarting the keyring may need the owner's unlock prompt, so ask before doing it; meanwhile read posts via the nitter mirror. `scripts/xsearch.py` hangs on the same keyring wait.
- **agent-reach does not make X searches account-free.** Its Twitter backend is this same cookie-backed CLI, and the browser tool gets a 403 on x.com. Say so plainly when the owner asks.
- **Plain-urllib media downloads 403**: video.twimg.com needs a browser User-Agent. ffmpeg's `-user_agent` works.
- **Searches for clothes/shirt/dress terms return mostly AI-video prompt spam and NSFW.** Exclude `seedance|prompt|kling|grok imagine|nsfw…` before ranking, or the shortlist drowns.
- **A candidate is not a reference.** Posts you proposed (and he didn't explicitly confirm) must not be carried into downstream artifacts such as inspo boards, briefs or design docs as if he chose them. When he asks to pull posts from a delivered list into an artifact, filter the list's JSON by the asked term (e.g. regex `clo ?3d|marvelous`) and add only those, labelling near-misses (sister products) so he can drop them.
- Don't conclude "not in bookmarks" from the first 200 alone. Check the folders too, and remember that his bookmark taps may not have saved.
