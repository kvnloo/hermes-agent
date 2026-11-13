---
name: kingdom-civ-visual-tdd
description: Use when changing the Kingdom civ game. Test, then look.
---

# Kingdom civ game: test first, then look

Repo: /workspace/civ-gamification-nightly (tools/kingdom/), game: /workspace/kingdom-of-hex. Live server: `node tools/kingdom/serve-live.mjs` on :5177, page `?mode=civ`.

## Loop
1. Add a failing assertion to tools/kingdom/visual/check.py (or fallback.py for WFC failure). Run it, confirm RED.
2. Fix. Pure logic goes in `world-*-model.mjs` with a `node:test` file. Browser code goes in a `world-<name>.js` layer.
3. Re-run check.py until green, then `composite_shot` + vision_analyze a screenshot. Never claim it works from unit tests alone.

## Facts that cost time
- Hermes' own browser tool has no WebGPU. Use Playwright with /usr/bin/google-chrome-stable and `FLAGS` from visual/kh.py (Vulkan/ANGLE, `--disable-gpu-sandbox`). It never touches the user's window.
- Headless GPU init fails ~half the time. Relaunch until `app.city.grids.size > 0` (check.py does 4 attempts).
- The canvas is WebGPU, so page screenshots are blank. `composite_shot` exports the canvas and lays it under the HUD.
- Any file named `world-*.js` in tools/kingdom is injected into the page on every request (world-fx.js loads first). Half-written layers hit the user's tab, so finish quickly or use a non-matching name while drafting.
- serve-live.mjs is read once at start: restart it (`pkill -f "^node tools/kingdom/serve-live"`; never `pgrep -f`, it matches your own shell) after editing it.
- Build All (`city.populateAllGrids`) clears the whole board for 30-100s. Keep the founding cover up until `app.__civLand` and the projection are re-placed. If WFC fails every try: `city.reset()` + `ensureStartingGridPopulated()`. `?expandfail=N` forces N failures, `?expand=0` skips it.
- Fixed realm seed (serve-live injects `seed=101`): 101 built in 33s/2 tries, 7 in 35s/3, 2024 in 43s/4. Seeds 42 and 555 crashed the test page.
- civWorld host API: `cities()`, `cityAnchor(id)`, `hexPos(key)`, `focus(key, dist)`, `setState(mock)`, `celebrate(spec)`, `register(layer)`, `group`.
- Vision models invent game names and misread effects; trust DOM/scene assertions over their prose.
- Kingdom's own `Cannot set properties of null (setting 'onclick')` pageerror predates this work; check.py ignores it.
