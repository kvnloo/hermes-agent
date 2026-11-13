---
name: dash-stage-html-prototypes
description: Use when publishing HTML prototypes to Dash's stage.
---

# Publish HTML prototypes into Dash's artifact viewer

Dash opens any tailnet/https URL with a `#t=<16-64 hex>` review token as a stage (pill under a chat reply, or `dash://stage?url=<encoded>`). Use kvnloo/artifact-stage as the host so the owner can step between prototypes and leave notes/decisions.

## Build
- One self-contained HTML per prototype: inline fonts (base64 woff2 from `@fontsource/*`; when no checkout has them, `npm pack @fontsource/<family>` in scratch and extract the `latin-<weight>-normal.woff2` files), shared CSS/JS and data. The stage frames artifacts in a cross-site iframe; sub-resources would not carry the review token.
- Keep sources in the product repo (`docs/design/<topic>/{src,data,fonts,tools,out,captures}`); `dist/` is gitignored in Dash, so write to `out/`.
- Public repos: export data through a script that emits counts, durations, tool names and synthetic labels only; grep the export for paths/ids before committing.
- Private owner data (asks ledgers, lane status) is fine on a tailnet-only page; keep the build script, template and fonts in an `operations/<topic>-<date>/` folder rather than a repo.
- For roadmaps or rollout views of the owner's asks/lanes/repos, follow `references/owner-roadmap-views.md` (data source, view grammar, ranking, live-rebuild server).
- CSS pitfalls seen in these pages: a shared `.glass` class beats an element selector, so scope overlays as `aside.glass{...}` and give drawers/sheets an opaque fill (translucent sheets let the board text bleed through). Density strips with one tick per item need `min-width:0` and a 1 px gap on phone, or 100+ ticks overflow 412 px. If the view lives in the URL hash, add a `hashchange` listener: same-page hash navigation does not reload.
- Cormorant Garamond has old-style figures (1 looks like I): set `font-variant-numeric: lining-nums` or use mono for numbers.

## Design rules (owner's standing preferences for data/trace views)
- Design rounds go to Opus (the Claude lane, or the Nous reserve `--provider nous -m anthropic/claude-opus-5.5` when Claude is throttled). Sol may implement against a concrete Opus spec, but a Sol-led redesign turns the views into generic prose cards and loses the diagrams.
- Start every new round from the round the owner approved, and keep earlier rounds as `<name>-r<N>.html` for comparison. Never rebuild from scratch on a feedback list.
- The visuals are the product: the summary number strip, timeline, lanes and charts stay visible by default. Nothing important hides behind an expander, and there are no nested accordions, because "tap to expand everything" reads as silly.
- Actionable over exhaustive. Lead each view with what happened, why it matters and what to do next, while keeping the detail he likes on screen. Aggregate dense ticks into density bars instead of hiding them.
- Colour carries meaning only: at most 3 semantic colours (blocked/failing, needs-you, healthy), everything else neutral. Never colour by phase or category.
- Phone-first. At 412 px nothing may be crushed horizontally. Use a vertical timeline, or a swipeable zoomed lane with a minimap. Touch targets are at least 44 px.
- Human labels: name runs by product and goal ("Dash · trace prototypes", "NOOP · ring double-tap", "Phone · S25 supervisor"), never "Run 01". Derive the names in the exporter from goal text and repo paths.
- Ephemeral: live and just-finished items stand out; stale items fade and collapse.
- Separate deterministic facts (one-line header) from LLM interpretation, and use interpretation sparingly.
  - Each view gets one 2–3 line read with real numbers, plus at most 3 action chips, each tagged with the product outcome it serves.
  - Add inline one-line notes only where something matters: a stall, a cluster of failures, a handoff. No essay cards, no generic prose.
  - Mark interpretation subtly, e.g. a small "read" tag.
  - Generate it from the real data at build time and cache it. Make the build fail if a read cites a number the data doesn't support. Never hand-write insights.
- "Analyze together", kept light: each action chip has Do / Not now / ?, and ? opens one inline text field. Persist responses (localStorage plus an exportable JSON, and a POST endpoint contract) so the agent can pick them up.

## Publish
1. Session dir `~/.cache/artifact-stage/sessions/<id>/` with the HTML files and `manifest.json` (`schema: artifact-stage/v1`, artifacts `{id, src, type: "html_preview", title, sha256}`). Put the first VISUAL prototype first and the brief last. The stage opens on artifact 1, and a text-only brief there reads to the owner as "I just see text".
2. `AS_POOL_SIZE=1 bun server/serve.ts --session <dir> --host 100.113.138.100 --port <free>` (background, persist). No Blender starts without a scene artifact.
3. The URL+token is in `<dir>/.url`; never print it in logs. Write a 0600 `review-link.txt` with the URL and the `dash://stage?url=` form for the parent to relay. Restarting the server mints a new token.
4. Open it IN DASH on the S25 yourself, without printing the token. The owner wants to see the prototypes, not a link to paste. Before you point him at the stage's tools, check that they do something on flat HTML. Ink, pin and select were built for 3D panes, and on HTML artifacts they only switch the mode label. That reads as "looks like vim, nothing works". If the stage can't show the visuals right away, serve `out/` on the tailnet IP (`systemd-run --user --unit <name> -p WorkingDirectory=<out> python3 -m http.server <port> --bind 100.113.138.100`) and open a prototype page (not the brief) in Chrome: `am start -a android.intent.action.VIEW -p com.android.chrome -d <url>`. Put that `systemd-run` line in a small script file and run the script: the terminal tool refuses a foreground command that looks like it starts a server. Then `curl` the page for a 200 before you open it. When the owner says "show me on my phone", that is the permission to take over the screen. Serving the folder directly means later in-place rebuilds go live on a reload.
   - Playback storyboards (panels plus music): on phone, a sticky player with the active panel, a scrubber marked at each panel and 44 px controls, above a scroll-snap filmstrip that auto-centres the active panel. On desktop, a stage plus a grid that keeps the active panel in view. Manual scrolling pauses auto-follow until play or a follow button. Edit the generator, not the built HTML.
   - Read the link inside the command, URL-encode it (`urllib.parse.quote(link, safe='')`), and run `env -u ADB_SERVER_SOCKET adb -s <s25> shell am start -a android.intent.action.VIEW -p host.exp.exponent -d "'exp://100.113.138.100:8097/--/stage?url=<encoded>'"`. Dash runs in Expo Go from Metro on :8097, and App.tsx maps the `stage` path to the ArtifactStage screen.
   - Check `topResumedActivity` first. If the owner is in another app, ask before taking over the screen.
   - Wait 10–30 s for the bundle to load, then `screencap` and look at it. A red screen is a native-module or JS error; read its text.
   - Don't rely on `kdeconnect-cli --share-text`: on Android it only fills the clipboard silently, so the owner sees nothing.
   - The stage component must use react-native-webview on native. Expo Go has no `ExpoDomWebViewModule`, so an Expo DOM (`"use dom"`) stage crashes with a red ViewManager error. Keep the DOM path opt-in (`EXPO_PUBLIC_STAGE_DOM=1`).
   - After editing Dash source, check that Metro is actually serving the edit: `curl -s 'http://100.113.138.100:8097/index.bundle?platform=android&dev=true&minify=false' | grep -o '<changed line>'`. A long-running `dash-metro-8097` can keep serving the old module even after a `touch`. Restart it with `--clear` from the unit's WorkingDirectory and EnvironmentFile (`~/.config/dash-services/`), reload the app with `exp://100.113.138.100:8097`, then send the stage deep link.
5. Serve the review from a process that outlives the worker (`systemd-run --user` or a persistent background process). Processes a subagent started are killed when it finishes, and a restart changes the token.
- HTML-only reviews crashed on boot (`stage.focused` undefined) until kvnloo/artifact-stage#1; serve from a checkout that has it.

## Verify (not on the owner's desktop)
- Isolated headless Sway (`WLR_BACKENDS=headless`, pixman, private HOME/XDG_RUNTIME_DIR via `env -i`) + Playwright Chromium on a CDP port; drive with CDP only. The stage needs WebGL: launch that Chromium with `--use-angle=swiftshader --enable-unsafe-swiftshader`, not `--disable-gpu`.
- Use a fresh browser context after rebuilding the stage client (old `main.js` is cached).
- Read the stage's on-page error overlay text, not just `pageerror`: boot errors show there.
- Capture each prototype at 412x915 and 1440x900, check `scrollWidth == clientWidth`, look at every PNG. Open a detail drawer/sheet in one capture too. For plain tailnet pages, a local Playwright script works: `p.chromium.launch(executable_path=<~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome>)` (the hosted browser tool refuses private IPs). Load each view in a fresh `goto` per view, and check that the screenshot actually shows the requested view.

## fleet-build pitfall
fleet-build ships untracked-but-not-ignored files: a `node_modules` symlink in the worktree breaks `bun install` on the worker. Remove it before the job, restore after.
