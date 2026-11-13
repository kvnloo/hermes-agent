---
name: app-card-design-resources
description: Use when designing app cards, generative UI or motion.
---

# App card design resources

The owner wants app cards that look like the real apps ("literally copy the official style guide")
and motion at the level of @pitus_'s Generative UI series. Start from the indexed list, not a fresh search:

- `/mnt/zer0models/workspace/zer0/products/launch-videos/resources/RESOURCES.md`: official design
  systems with verified token values (Primer, Base Web, Material 3 / Gmail / Maps measured live),
  fonts and their licences, Dribbble/Behance/Mobbin/X references, ephemeral-UI essays, music.
- `resources/motion-techniques.md` (+ `.json`): all 923 oneshotprompts.com techniques with
  definitions and example-loop URLs. Name techniques by id when planning motion.
- `resources/refs/pitus/`: the Generative UI #1–#6 videos and contact sheets (local only).
- The public kit is **ephemeral-ui**: `pretotypes/ephemeral-ui/`, live at https://ephemeralui.vercel.app
  (Vercel project `ephemeral-ui`; `ephemeral-ui.vercel.app` is someone else's). The old gallery
  `pretotypes/app-cards/` is its `/classic`; https://t3-app-cards.vercel.app redirects there. Deploy with
  `tools/deploy.sh`; check with `tools/shot.mjs` (playwright on a local `http.server`; the agent browser
  can't reach loopback).
- ephemeral-ui themes come from host source, not screenshots: `tools/themes.py` resolves T3 Code's
  `index.css` and Hermes desktop's `presets.ts` (via `tools/vendor/dump-hermes.sh`). Hermes radius-scalar is
  0.2, so its cards are near-square. App colours come from simple-icons; no entry means a neutral tile.
- In the site's `h()` helper, custom properties need `style.setProperty`; `Object.assign(el.style, {"--x": …})`
  silently drops them (every brand colour went missing until this was fixed).
- Prefix every component and state class (`.us-win`, `.gl-big`, not `.win`, `.big`, `.cur`): the base
  stylesheet already styles generic names (`.win` is the host window, `.big` a 26px number, `li.cur` a step),
  and a collision silently restyles or pulls rows out of flow. Grep `styles.css` for the name before using it.
- Extending the kit (new apps, card kinds, 3D, combos, Hermes plugin cards): follow
  `references/ephemeral-ui-architecture.md` for where each piece lives and the check-every-card loop.
- Ship gallery changes by copying `dist/index.html` to `pretotypes/ephemeral-ui/src/classic/index.html`
  and deploying `ephemeral-ui/src` to Vercel project `ephemeral-ui`; never deploy the old
  `t3-app-cards` project, which now only redirects there.
- Maps must be real: OSM basemaps and OSRM routes via `pretotypes/app-cards/tools/geo.py`; never
  hand-drawn route curves (the owner called them slop).

## Previewing cards in other harnesses (harness kits)

The owner wants to preview cards as they would sit in T3 Code, Hermes desktop, hermes-tern, ChatGPT/Codex,
Claude, o8 and other harnesses. `pretotypes/harness-kits/` holds one kit per harness (canvas, surface, text,
muted, border, accent, user bubble, code background, fonts, radii) in `kits.json`, built by `finalize.py`
with per-field provenance. `apps/web/test/harnessKits.renders.tsx` in the t3code fork maps each kit onto
T3's semantic variables (`--background`, `--card`, `--foreground`, `--primary`, `--message-surface`, `--font-sans`, ...)
around the real board, so the board frame takes the harness look while each card keeps its app's design system.

1. Open-source harness: run `extract.py` (free model via semantic-router, falling back to Hermes `-m kilo-ultra`)
   on its own stylesheet, or on CSS strings pulled from a binary (`strings <bin> | grep -E '^\s*--'`). Values that
   do not occur verbatim in the source are dropped.
2. Variables that are `var()` chains (T3, Hermes desktop): resolve them with the parser in `finalize.py`, not a model.
3. Closed site (ChatGPT, Codex, Claude): measure roles from real elements with `sample-roles.mjs` (computed styles,
   light and dark). Signed out, only canvas, text, font and a button colour are observable; leave the rest null so
   the preview falls back to T3's token, and label it.
4. Render every kit x light/dark x 412/760 px with the renders test (heavy: run it where memory allows) and look at
   the images before reporting.

Rules:
- A grounded value proves the colour exists in the source, not its role. Accept model-mapped roles only where the
  variable names carry meaning; hashed StyleX names (`--x1w9ml1o`) led a model to call a blue tint the user
  bubble. Measure those roles instead, or leave them unknown. Even a meaningful name can be the wrong role
  (Tern's `--ink-pen` is the annotation pen, not message text): look at every render, and list each drop in
  `finalize.py`'s `DROP` set. A dropped role must stay null; it must not be refilled by the source fallback.
- Run the kit renders off groot (the MBP checkout works). vitest needs the exact `chromium_headless_shell-<rev>`
  that its playwright-core asks for, and an older build already in the cache is not it: rsync that revision's
  folder from `~/.cache/ms-playwright/` on groot instead of reinstalling.
- Measure the chat surface, not a landing page: a marketing CTA is not the harness accent. Drop it.
- Signed-in chat surfaces need the owner to sign in on the isolated Chrome himself; never use his credentials.

## Data cards that mirror a dashboard (traces, stats, analytics)

When the owner wants cards that "look like direct results from" an existing dashboard (e.g. omp's `/stats` trace pages):
1. Copy the dashboard's own client components (layout, density, chart styles) from its source, and render them inside the kit's host theme. Put a fidelity screenshot of each card next to the real dashboard view.
2. Cards take exactly the JSON shapes the dashboard's server API returns. That way an agent can fetch `/api/...` and pass the response straight into a card, with no adapter. Record real API samples first, then extend `src/schema/card.v0.json`.
3. For a natural-language query surface, have the answer be a composed set of cards with the data layers (spans, tokens, cost, errors, subagents) toggled by context or by the user. Drive it with a typed, documented query plan (intent → API calls → card kinds + layers + filters), stored as a schema next to `card.v0.json`. A live agent follows that same contract. On the static site, map phrases to plans deterministically; never fake an LLM.
4. The site is public. Build fixtures from real structure (timings, counts, tool and model names), but strip message text, paths, hosts, repo names and emails with a sanitizer script in `tools/`. Grep the output for leaks before every deploy.

## Rules learned

- Before you or a worker edits the kit, run `git status` and check file mtimes in `pretotypes/ephemeral-ui`. Another session may have left uncommitted edits there, and the brief must say whether to keep them or leave them out of the commit.

- Every card must be validated by eye before it ships: screenshot each new or changed card at 1440 and
  390 px (`tools/studio-shot.mjs`, `tools/journey.mjs`), open the PNGs, fix, re-shoot. The owner does not
  trust design from cheaper or free models; delegate only mechanical work (catalog rows, doc lookups) and
  review any delegated visual output the same way.
- Studio cards copy the app's own editor chrome and its real vocabulary from its docs (Blender brush names
  and shortcuts, Unreal PCG node names, ComfyUI starter graph and link colours, Anki buttons and default
  steps, a plugin's real tool names and credit costs). Content must match the task it claims: a Meshy
  'treasure chest' card that shows a torus knot reads as fake.
- 3D assets: prefer real generated models (Hermes `meshy` plugin in the clean profile; needs
  `MESHY_API_KEY` via `hermes config set` and cost confirmation before every credit-spending call; list
  existing tasks first, free). Procedural three.js stand-ins are the fallback and should be labelled as such.

- Copy tokens from the open-source packages (`@primer/primitives`, `baseui`, `@material/web`) and
  sample live pages with `getComputedStyle` or screenshot pixels; never guess brand hexes.
- Fonts: Google Sans, Google Sans Text, Mona Sans and Material Symbols are on Google Fonts. Uber
  Move is proprietary: use Inter or Inter Tight and say it is a stand-in.
- T3 Code ships monogram tiles, not brand logos (docs/user/openui-reports.md). Exploration may show
  official marks behind a toggle; flag them before anything ships.
- Positioned elements that also animate need the `translate:` property, not `transform:`, or the
  keyframes (which set `transform`) wipe the offset.
- X: `x_search` may be out of credits and x.com returns 403 to the agent browser. Use
  `web_search "site:x.com …"` for discovery and `https://api.fxtwitter.com/2/profile/<user>/statuses`
  (retry on 404) for posts and video URLs.
- ChatGPT image generation: do not import the ComfyUI node module (it pulls torch, about 2 GB, and
  the memory guard SIGTERMs the runner). Load only its `generate()` source; see
  `/mnt/zer0models/project-artifacts/t3-app-cards/gen-20261103/gen.py`. Check `wham/usage` first; once the
  weekly window is at 100 % the calls draw credits (10 images cost about 18 credits), so report the delta.
- Show the gallery with screenshots and the hosted URL; the full page (~1 MB with images) exceeds
  html_render's 512 KB input limit.
