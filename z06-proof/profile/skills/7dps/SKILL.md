---
name: 7dps
description: >
  Generate a designer showcase pack (7DPS) for a 3D web scene: 9 hero stills,
  a full-res preview grid, a 3D photosphere (equirectangular 360°), and a 4D
  photosphere (360° video over time). The skill's main job is to pick the best
  camera locations and photosphere origin; capture uses the host project's
  existing tools; viewing uses Photo Sphere Viewer (not a custom sphere).
  Triggers: "7dps", "preview grid", "photosphere pack", "behance shots",
  "designer preview", "4d photosphere", "/7dps".
metadata:
  short-description: "9 stills + grid + 3D/4D photosphere via existing tools"
---

# 7DPS — designer preview pack skill

**7DPS** = **3D** photosphere + **9** preview stills + **grid** + **4D** photosphere.

You are the **director of photography**, not a graphics engine. Prefer **existing** tools:

| Job | Use this (do not invent) |
|-----|---------------------------|
| Still capture | Host project Playwright/capture harness (`capture.mjs`, `capture-behance.mjs`, CDP screenshots) |
| Photosphere capture | Host `__shopCapturePhotosphere` / `capture-photosphere.mjs` (cube → equirect) |
| 4D photosphere | Sequence of equirect frames → **ffmpeg** equirectangular video |
| View 3D 360 | **@photo-sphere-viewer/core** (equirectangular) |
| View 4D 360 | **@photo-sphere-viewer/equirectangular-video-adapter** + video-plugin |
| Grid | **ImageMagick** `magick montage` |
| Round/ball phone UI look | Photo Sphere Viewer default sphere (user pans) — not a custom little-planet unless asked |

Cross-harness: this SKILL.md is portable (Claude Code, Grok, Cursor, Codex). CLI helpers live in `zer0/products/7dps`.

## Product layout

```
zer0/products/7dps/
  skills/7dps/SKILL.md     ← this file
  bin/7dps.mjs             ← thin CLI: plan | grid | view | run
  adapters/*.json          ← per-project paths & hooks
  viewers/                 ← static PSV HTML (3d + 4d)
```

## Output contract (always produce)

Under `<project>/shots/7dps/<stamp>/` (or adapter `outDir`):

```
01..09-*.png          # nine stills (narrative order)
preview.png           # full-res grid of the nine
photosphere/
  equirect.png        # 3D photosphere (2:1)
  px..nz.png          # cube faces (optional)
  faces-cross.png     # optional designer net
4d/
  equirect.mp4        # 4D photosphere (360 video)
  frames/             # optional frame dump
manifest.json         # paths + camera plan + tools used
README.md             # Behance-oriented shot list
```

## Phase 0 — Load adapter

1. Prefer `7dps/adapters/<name>.json` (e.g. `portfolio-room`).
2. Resolve `projectRoot`, `basePath`, capture APIs, existing scripts.
3. If no adapter: ask for project root + how to set camera / capture photosphere.

## Phase 1 — Camera plan (your main job)

Read the scene (code + latest shots if any). Write a **camera plan** before capturing.

### Nine stills (Behance / S-tier product case study)

Default narrative (adapt names; keep nine):

| # | Intent | Mode | Camera guidance |
|---|--------|------|-----------------|
| 01 | Desktop product hero | chrome UI + 3D | Three-quarter, full kiosk + chrome readable |
| 02 | Menu / IA | chrome | Select second project; panel + list clear |
| 03 | Mobile product | chrome | 9:16; stack usable |
| 04 | Interaction | chrome | Hotspot or menu select; 3D↔panel sync |
| 05 | Cinematic craft | beauty | `threeQuarter` or equivalent; no chrome |
| 06 | Brand | beauty | Exterior neon / sign legible |
| 07 | Materials close | beauty | Counter / food / hero prop |
| 08 | Atmosphere | beauty | Front elevation or plaza-wide |
| 09 | Environment / context | beauty | City square / greenery / skyline (`plazaWide` if present) |

**Rules for choosing positions:**

- Prefer existing `CAMERA_PRESETS` / `__shopSetCamera` keys when they match intent.
- If presets are wrong, pass explicit `{ position, target, fov? }`.
- Hero frames: full subject, no clipped sign underbelly, readable silhouette.
- UI frames: must show **real chrome** (no `beauty=1`).
- Craft frames: `beauty=1` / pure canvas so materials read.
- Avoid mystical mush / blown bloom when judging “best” frame — midtones matter.
- For env showcase, pull back far enough to see plaza + greenery, not only the stall.

### 3D photosphere origin

Pick **one eye** in world space:

- Slightly above human eye (~1.6–1.9 m).
- In the open plaza **in front of** the hero building (not inside geometry).
- Clear sightlines to hero + neighbors + sky; not buried in foliage.
- Default for portfolio-room: near `[0.15, 1.75, 3.2]` or better after reading `CitySquareEnv`.

### 4D photosphere (time)

Use **existing** video path — do not write a custom 4D engine:

1. Capture **N equirect frames** (default 24–36) while either:
   - rotating capture yaw around the same origin (turntable eye), or
   - orbiting the origin around the hero (circle radius ~6–10 m, height constant), or
   - advancing an in-scene clock/animation if the host exposes it.
2. Encode with **ffmpeg** as H.264 mp4 (equirectangular layout, 2:1).
3. View with **Photo Sphere Viewer equirectangular-video-adapter**.

Prefer orbit of the eye around the shop so the 4D path sells the environment.

## Phase 2 — Capture (host tools)

1. Build host project if needed (`adapter.build`).
2. Stills: use host `capture-behance` **or** Playwright + `__shopSetCamera` + CDP/`Page.captureScreenshot` (same patterns as portfolio `tools/capture*.mjs`). Prefer CDP over Playwright screenshot on WebGL.
3. Photosphere: call `__shopCapturePhotosphere({ size, mode: 'equirect' })` with `?capture=1&beauty=1`, or run adapter photosphere script.
4. 4D: loop capture equirect (or cube→equirect) per frame → `ffmpeg`.
5. Grid:  
   `magick montage 01.png … 09.png -tile 3x3 -geometry <WxH>+48+48 -background '#050308' preview.png`  
   Pad non-landscape stills with `-extent` so the grid is uniform.

If 8K OOMs on software GL, capture 1080p/1440p and optional `--upscale 2` via magick Lanczos — say so in manifest.

## Phase 3 — View (Photo Sphere Viewer only)

From `7dps` package root:

```bash
node bin/7dps.mjs view 3d path/to/equirect.png
node bin/7dps.mjs view 4d path/to/equirect.mp4
```

These serve `viewers/psv-3d.html` / `viewers/psv-4d.html` using **@photo-sphere-viewer/*** from node_modules (or CDN fallback). Do not implement a custom ball shader unless the user insists; PSV’s sphere is the product look (drag to look around — same family as phone “360° / Round” viewers).

## Phase 4 — Manifest + honesty

Write `manifest.json` with:

- adapter id, stamp, tool versions (psv, ffmpeg, magick)
- camera plan (positions/targets/presets used)
- photosphere origin
- 4D method (orbit | yaw | scene-clock) + frame count
- any fallbacks (upscale, skipped shots)

Never claim ship-quality craft just because 7dps ran — 7dps is **documentation/marketing capture**, not the visual quality gate (that remains `ramen-boba-loop` / VISUAL-BAR).

## CLI quick reference

```bash
# From zer0/products/7dps
node bin/7dps.mjs plan --adapter portfolio-room     # print plan checklist
node bin/7dps.mjs grid --dir /path/to/stills        # magick montage → preview.png
node bin/7dps.mjs view 3d /path/to/equirect.png
node bin/7dps.mjs view 4d /path/to/equirect.mp4
node bin/7dps.mjs run --adapter portfolio-room      # agent-oriented: print ordered steps + invoke known scripts when safe
```

## Portfolio-room one-liner (agent)

When the user says “run 7dps” in the portfolio room:

1. Load this skill + `adapters/portfolio-room.json`.
2. Plan 9 cameras + photosphere origin + 4D orbit (write into `shots/7dps/<stamp>/README.md` first).
3. Capture stills (host scripts or Playwright).
4. Capture 3D photosphere (host `__shopCapturePhotosphere` or script).
5. Capture 4D frame set → ffmpeg mp4.
6. `7dps grid` for `preview.png`.
7. Optionally `7dps view 3d` / `view 4d` for local QA.
8. Report artifact paths.

## Anti-patterns

- Reimplementing a sphere renderer when PSV exists.
- Hand-rolling a video player when PSV video adapter exists.
- Hardcoding only one camera forever — always re-plan from current scene.
- Beauty-only packs when the user wants UI skill showcase (include chrome stills).
- Soft-stopping the quality loop because 7dps marketing assets exist.
