---
name: project-docs-site
description: Use when documenting a repo as a VitePress site.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [docs, vitepress, vue, playwright]
    related_skills: [dogfood, vercel-cli-deploy, threejs-real-gpu-receipts]
---

# Project documentation site (VitePress)

## When to Use

Use when the user asks to "make docs", "document the repo" or "show me X" for structured project data such as a catalog, taxonomy or schema. The deliverable is a site that builds in CI and has been looked at in a real browser, not a list of markdown files.

## Procedure

1. **Inventory first.** Read the README, the existing docs/*.md, CLI argparse definitions, workflow `on:` triggers, schemas and data files. Every option, default, range and number in the docs must come from the code. Grep for `add_argument`, range checks and recipe values before writing, and never write "see recipe" placeholders.
2. **Install into the existing workspace:** `npm install -D vitepress vue`. Add `docs:dev`, `docs:build` and `docs:preview` scripts. Add a `docs:prepare` script only if the site needs build artifacts copied into `docs/public/`.
3. **Keep existing docs in place.** Put `docs/.vitepress/config.mts` next to them so they become pages. Fix markdown that VitePress mis-renders, such as escaped backticks and `../LICENSE` links that point outside the tree. Absolute GitHub URLs are fine for out-of-tree files.
4. **Information architecture:** Guide (getting started, ethos/principles, repository tour with a table of generated vs tracked paths), domain section(s), Runtime/API, Reference (CLI, testing & CI with "proves / does not prove" columns), Project (roadmap, contributing via `<!--@include: ../../CONTRIBUTING.md{2,}-->`).
5. **Data-driven pages:** load the source JSON with a build-time data loader (`docs/<name>.data.ts` with `watch` and `load()`) and render it with a Vue component registered in `theme/index.ts`. The page then updates when the JSON changes. Join it with other repo state, such as which entries have implementations.
6. **Interactive explorers:** add search, filter chips (`aria-pressed`), a radiogroup, counts and a sticky control bar. If the project has its own web component, embed it for live previews, loaded from `public/` at runtime and degrading to a placeholder when absent.
7. **Gates:** run `npm run docs:build`; VitePress fails on dead links, so keep that. Add a CI step that builds the docs. Re-run the repo's unit tests.
8. **Look at it.** Serve the build, drive it with Playwright using the system Chromium, and record:
   - entity counts
   - filter results for several combinations
   - console errors and responses with status 400 or above
   - light and dark screenshots saved to `reports/generated/docs/`

   Then view the screenshots. Finally, open the page in the user's browser with `setsid -f xdg-open URL`, so they don't receive an unclickable path.
9. **Commit separately** from feature work: "docs: ...".

## Pitfalls

- **Raw tags render as HTML.** A raw `<custom-tag>` in a sidebar `text`, a frontmatter `features.details` string or YAML prose is rendered as a real element: the text disappears and a stray element is mounted. Use plain words in nav labels and `&lt;tag&gt;` in frontmatter. Backticks only protect markdown body text.
- **Vue custom elements:** set `vue.template.compilerOptions.isCustomElement` for the tag. Bind with `:attr.attr=`. Vue sets a DOM property whenever `key in el`, and a getter-only property such as `tier` silently drops the value.
- **Passing refs to helpers:** do not pass a `ref` from the template into a helper that reads `.value`. Templates auto-unwrap refs, so the helper receives the raw value and the update is lost. Write one dedicated setter per ref instead.
- **Static asset paths:** never put copied assets in `docs/public/<x>/` when `<x>` is also a page section, such as `/runtime/`, because the two merge in `dist`. Use a distinct path such as `public/live/`, gitignore it, and add it to `srcExclude`.
- **Preview server is stale after a rebuild:** `vitepress preview` keeps serving the old asset hashes (404s on the hashed app/theme bundles). Restart it after every `docs:build`, on a fresh port if the old process lingers.
- **Killing servers:** stop them by PID or session id. `pkill -f <pattern>` matches the invoking shell's own command line and kills the tool call.
- **Headless WebGPU:** canvases may not present in headless Chromium, which leaves white boxes. Give live previews a `?tier=` (or similar) override and screenshot through WebGL2 with `--use-angle=vulkan --enable-features=Vulkan --ignore-gpu-blocklist`. Say in the report that the auto path still needs a real-browser check.
- **Favicon:** add `head: [["link", {rel:"icon", href:"/favicon.svg"}]]` so the console has no favicon 404 to explain away.

## Report shape

Give the URL (opened), what each section covers, the bugs found and fixed while verifying, measured browser results, what is not verified, and the screenshot directory. Offer deployment (GitHub Pages or Vercel) rather than doing it unasked.
