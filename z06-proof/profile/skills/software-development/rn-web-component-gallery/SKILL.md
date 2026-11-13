---
name: rn-web-component-gallery
description: "Use when one RN component set must run in Expo and web."
---

# React Native + web component library with an Expo web gallery

One TypeScript source tree (react-native-svg + Reanimated) rendered in Expo Go and on the web through react-native-web. The gallery is itself an Expo app, so `expo export --platform web` is the web render proof and `expo export --platform android` proves the native bundle compiles.

## Setup rules
- Use bun with `bunfig.toml` `[install] linker = "hoisted"`. The isolated linker gives Metro duplicate-looking React paths.
- Put the gallery in `gallery/` (own `package.json` with `main: index.ts`, root `workspaces: ["gallery"]`), `metro.config.js` with `watchFolders=[repoRoot]`, `nodeModulesPaths=[root/node_modules]`, `disableHierarchicalLookup=true`.
- Pin peer versions to the host app's Expo SDK `bundledNativeModules.json` (svg, skia, reanimated, worklets are all in Expo Go).
- Platform splits: `foo.tsx` (native) + `foo.web.tsx`; a `.web.tsx` may mount a plain DOM component (e.g. a canvas library).
- Fonts: `Platform.select` web CSS stacks vs single native face names; never comma lists on native.
- Custom `gallery/public/index.html` is the Expo web template; self-host fonts in `public/fonts` (copy from `@fontsource/*` at build).

## Pitfalls
- On web, RN `ScrollView` is the scroll container, so full-page/element screenshots below the fold come out black. Use a plain `View` on web and let the document scroll (`#root{min-height:100vh}`, no `height:100%` + `overflow` on body).
- Reanimated `useAnimatedProps` on react-native-svg elements works on web (cx, d, opacity, strokeDashoffset). Mark helpers used inside with `'worklet'`. Hooks must be unconditional per node component.
- A settle curve is front-loaded: a screenshot 90 ms after a tap already looks finished (screenshot latency). Prove a morph by sampling DOM attributes per rAF inside `page.evaluate`.
- `npx tsc` can stall under load and the gateway guard blocks direct `node_modules/.bin/tsc`; run `npm run -s typecheck`.
- YAML step names containing `: ` break the whole workflow (0 jobs, "workflow file issue"); quote them.
- Playwright's bundled browser may be missing; launch with `executable_path='/usr/bin/chromium'`.
- Never rely on a dev server with file watching on this host: inotify watches run out (vite dies with `ENOSPC ... syscall: 'watch'`). Add the page as a build input, `vite build` / `expo export`, and serve the output statically.
- Start builds with terminal `background=true` + notify: the gateway guard rejects foreground `vite`/`vite build` as a long-lived server and rejects `nohup`/`&` wrappers.
- For screenshots of heavy or continuously animated pages, use `chromium --headless=new --hide-scrollbars --window-size=W,H --virtual-time-budget=8000 --screenshot=out.png URL`; the browser_exec CDP capture can time out on them.

- A DOM-only library (e.g. tldraw) in one prototype: install it into a sibling deps dir (`<proto>/canvas-deps`, `npm install --legacy-peer-deps` so react/react-dom come from the root), prepend that `node_modules` to Metro `nodeModulesPaths`, add a tsconfig `paths` entry, and keep it in one module with no react-native imports (mountable later via Expo `'use dom'`).
- Metro with a symlinked `node_modules` (worktree sharing a checkout's install): add `fs.realpathSync` of it to `watchFolders`.
- `chromium --headless --virtual-time-budget` does not finish Reanimated or tldraw camera animations: render static props once settled, and take truth frames with Playwright in real time (click the row, then sample).

## Evidence loop
1. `scripts/shoot.py URL OUT --widths 390,1100 --full` element-captures every `testID=section-*`; view each with vision, zoom regions at 390.
2. `scripts/probe.py`: tap-to-open morph frames, two frames of a running animation must differ, a paused one must not, `reduced_motion='reduce'` must hold still.
3. Typical fixes found by looking: label halos (stroke text in canvas colour under fill), greedy collision-free labels, fold quiet nodes into count aggregates without edges, keep only top-k edges per node, reserve fixed slots so grid cells align.

## tldraw canvas inside an RN-web app
- Install tldraw only in the consuming folder (`npm install tldraw --legacy-peer-deps`) and put that `node_modules` first in Metro `nodeModulesPaths`: react resolves from the root, so no second React. Metro bundles tldraw + `tldraw/tldraw.css` as is.
- Keep `<Tldraw cameraOptions>` (and themes, shapeUtils) referentially stable: a new object per render rebuilds the whole editor, cancelling camera animations and remounting shapes.
- In readonly mode, flip `isReadonly` off around programmatic `editor.run(..., {ignoreShapeLock: true})` syncs, then back on.
- Do not track owner drags with `store.listen({source:'user'})`: programmatic edits are `user` too. Compare the shape's position to where the layout last put it.
- Glyph to canvas: `setCamera` immediately on the glyph's box, then `zoomToBounds(..., {animation})` on a timer. Do not clear that timer in an effect cleanup that model refreshes re-run. Snap to fit after the animation, because a scrollbar appearing mid-flight resizes the viewport.
- Sample animation frames with `page.screenshot(clip=bounding_box)`. Element screenshots wait for stability and miss the timing.
- License: any `http:` or localhost origin counts as development (no watermark). An `https:` origin with no key is `unlicensed-production` and the editor hides. Note this for the owner; never bypass it.
- Keep the canvas module free of react-native imports, with plain props. Mirror tokens in a plain palette file so the module can later mount as an Expo DOM component.

## Serving
Serve the static build with `python3 -m http.server --directory <abs dir>` (survives rebuilds). From a subagent, start it with `persist_on_release=true` and `process_manage handoff` so it outlives you. Before replacing a server, confirm the exact PID with `ss -ltnp` and `/proc/<pid>/cwd`, then `kill <pid>`.

Reference implementation: kvnloo/aodl-views (`scripts/shoot.py`, `scripts/probe.py`).
