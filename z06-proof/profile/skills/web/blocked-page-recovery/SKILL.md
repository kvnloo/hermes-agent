---
name: blocked-page-recovery
description: "Use when a fetch fails: 403/429, paywall, WAF, bot wall."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Archives, Wayback, Paywall, WAF, Fallback]
    related_skills: [grounded-citations]
---

# Blocked-Page Recovery

When a page won't fetch — 403/429, Cloudflare "Just a moment...", a paywall,
or a bot-detection interstitial — don't give up and don't loop on the same
URL. Third-party services often hold a **copy** of the page. Work down this
ladder, cheapest first.

## The ladder

```
1. Wayback Machine  — archive.org "available" API  (snapshot + timestamp)
2. archive.today    — domain rotation: archive.ph → .md → .li → .is
3. Jina Reader      — only if JINA_API_KEY is set  (live server-side render)
4. API-first pivot  — look for /api/, /graphql, .json, or RSS on the same host
5. Real browser     — browser tool as the last, most expensive resort
```

Run it in one shot with the bundled script:

```bash
python3 scripts/recover_page.py "https://example.com/blocked-article" --json
```

The script tries each route in order, validates every body (see "Fake
successes" below), and prints the first genuine hit with its provenance.

## Provenance discipline (non-negotiable)

Every recovered copy carries a provenance you MUST preserve when citing:

| Route | Provenance | How to cite |
|-------|-----------|-------------|
| Wayback / archive.today | `snapshot` | Cite WITH the snapshot date: "as archived 2026-08-06". Never present a snapshot as the live page — it may be stale. |
| Jina Reader | `live` | Server-side re-render of the live page; cite normally. |
| Live fetch / browser | `live` | Cite normally. |

If the user needs *current* data (prices, availability, breaking news), a
snapshot is context, not an answer — say so explicitly and note its age.

## Manual routes

### 1. Wayback Machine (best provenance, try first)

```bash
# Discovery: returns closest snapshot URL + timestamp as JSON
curl -sL "https://archive.org/wayback/available?url={URL}"
# Then fetch archived_snapshots.closest.url
```

For enumerating many snapshots (or recovering deleted pages), the CDX index:

```bash
curl -sL "https://web.archive.org/cdx/search/cdx?url={URL}&output=json&limit=10"
```

CDX intermittently returns 503 under load — if it does, fall back to the
`available` API; don't retry-hammer it.

Works for: any publicly crawled URL. Fails for: robots-blocked sites,
never-crawled URLs, JS-only SPAs (snapshots don't render).

### 2. archive.today (paywalls, deleted content)

User-submitted archives — often has paywalled news articles Wayback lacks.
Rate-limits aggressively (429) and rotates domains, so iterate:

```bash
for d in archive.ph archive.md archive.li archive.is; do
  curl -sL --max-time 20 "https://$d/newest/{URL}" -o ~/.hermes/cache/scratch/page.html \
    -w "%{http_code}" && break
done
```

**Validate the body, not the status code** — a 429 still ships several KB of
rate-limit HTML that looks like a success to a size check alone.

### 3. Jina Reader (access varies)

`r.jina.ai` re-renders pages server-side and returns markdown. Anonymous
access can work for public pages, but availability varies by route and time;
do not declare it universally dead. Try a public unauthenticated request when
appropriate, validate the returned page, and use a configured key if needed:

```bash
curl -s -H "Authorization: Bearer $JINA_API_KEY" "https://r.jina.ai/{URL}"
```

Handles some JS SPAs that archives can't. A 200 reader response can still
contain an upstream 403/404 warning or a no-results stub: retain that warning
and do not present it as a successful authoritative retrieval. Never relay
private cookies or credentials through the reader.

### 4. API-first pivot

WAFs protect the HTML surface far more aggressively than the data endpoints
behind it. After 2-3 blocked attempts on a site, stop fighting the HTML and
look for:

- `/api/...`, `/graphql`, or `.json` variants of the page URL
- An RSS/Atom feed (`/feed`, `/rss`, `<link rel="alternate">` in any copy
  you did recover)
- A sitemap (`/sitemap.xml`) revealing canonical URLs that may not be gated
- X/Twitter posts: `curl -s https://api.fxtwitter.com/<user>/status/<id>` returns JSON with the text, author, date, quoted post and `media.photos[].url` (pbs.twimg.com originals). Load the photos with vision; screenshots of the owner's product usually carry the actual bug report. Videos are under `media.videos[].url` (direct mp4); download, then transcribe and make a contact sheet.
- Instagram public profiles: `www.instagram.com/api/v1/users/web_profile_info/?username=<u>` answers `require_login` to a desktop UA, but the mobile host works without login: `curl -s -A 'Instagram 309.1.0.41.113 Android (34/14; 480dpi; 1080x2340; samsung; SM-S931U; pa1q; qcom; en_US; 541635890)' -H 'X-IG-App-ID: 567067343352427' 'https://i.instagram.com/api/v1/users/web_profile_info/?username=<u>'`. It returns bio, counts and the newest 12 posts with captions, view/like/comment counts and a direct `video_url` per reel. Pagination (feed, graphql cursor, clips) needs a logged-in session; say how many posts you covered and ask for a logged-in route rather than claiming the whole account. `web_search "site:instagram.com <handle>"` surfaces some older reel captions. yt-dlp's Instagram extractor is unreliable without cookies.
- Transcribe downloaded clips locally with faster-whisper (`WhisperModel('small.en', device='cpu', compute_type='int8')`, `vad_filter=True`) and pair each transcript with an ffmpeg contact sheet (`-vf fps=1/3,scale=360:-1,tile=6x4`) viewed with vision: captions and speech miss most of the process a shop reel shows.

## Fake successes — routes that LIE

These return HTTP 200 with a plausible body that is NOT the page. The script
rejects them automatically; reject them manually too:

- **Google Cache is dead** (since mid-2024). `webcache.googleusercontent.com`
  returns 200 + tens of KB, but it's a Google Search interstitial with a JS
  redirect, not a cache. Never use it.
- **AMP caches** (`*.cdn.ampproject.org`) mostly return a ~300-byte
  `<title>Redirecting</title>` meta-refresh stub pointing back at the
  original (blocked) URL. Treating that as success creates a fetch loop.
- **Rate-limit bodies**: archive.today 429 pages are multi-KB HTML. Check for
  the target's actual content (title words, expected strings), not just size.

Detection heuristics the script applies: body under a per-route byte floor;
meta-refresh/JS-redirect stubs whose target is the original host; interstitial
titles ("Just a moment", "Redirecting", "Google Search", "Attention Required").

## Proxy relays: don't

Generic "web proxy" relays are man-in-the-middle by construction. Never send
cookies or Authorization headers through one, and don't use them for anything
the user will rely on — provenance is unverifiable. Prefer archives, which at
least timestamp their copies.
