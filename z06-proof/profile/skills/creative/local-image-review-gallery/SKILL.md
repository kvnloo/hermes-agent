---
name: local-image-review-gallery
description: Use when building a local viewer for a batch of images.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [images, gallery, inspo, viewer, review]
    related_skills: [local-gltf-review, company-os-visual-language]
---

# Local image review gallery

## When to Use

- The user asks for an artifact viewer / gallery of inspo, designs or generations they made.
- A batch of images must be triaged (keep/drop/notes) before choosing a design direction.

Build a self-contained static viewer for a batch of images the user created (design inspo, generations, screenshots) so they can browse and triage them.

## 1. Find the images (cheap places first)

When the user says they made or sent images, check these BEFORE broad disk scans or long history searches:
- KDE Connect inbox: `grep -h incoming_path ~/.config/kdeconnect/*/kdeconnect_share/config` (here `/mnt/zer0models/Recvd`); sort by mtime, newest archives first.
- `~/Downloads`, the project's repo/worktrees, `project-artifacts/<project>/`.
If those miss, ask the user where they generated/sent them (ChatGPT, Grok, phone) instead of burning many `ctx search`/`fd` passes: whole-filesystem `fd` runs take minutes, and short regex like `dsp`/`amp-` match unrelated names (`dSphere`, `lamp-`).

## 2. Store canonically

Unpack into `/mnt/zer0models/project-artifacts/<project>/<kind>/` (e.g. `aural/inspo/`), never a filesystem root or the app repo (large binaries stay out of Git). If a MANIFEST with sha256 ships with the archive, verify every file and report count/mismatches.

## 3. Build the viewer

- Thumbnails: `vips thumbnail <src> viewer/thumbs/<id>.webp[Q=82] 720` (openslide module warnings are harmless).
- Write `viewer/data.js` (`window.GALLERY={sections,items}`, the global the template reads) from the manifest/folder layout: group by the archive's folders (design waves), one-line blurb per section from viewing the contact sheet, per item title/date/role/dims/sha/relative original path. Use a `data.js` script, not `fetch()` of JSON, so it works over `file://`.
- Copy `templates/viewer.html` to `viewer/index.html` and set title/subtitle/localStorage key. It provides: sticky glass header, role and keep/drop/unrated filter chips, size slider, lazy thumbnail grid per section, lightbox with arrows / Z zoom 1:1 / L keep / X drop / notes, localStorage persistence and an "Export notes" JSON download.

## 4. Verify, then open

- Headless check: `chromium --headless=new --disable-gpu --allow-file-access-from-files --window-size=1600,1100 --virtual-time-budget=4000 --screenshot=$TMPDIR/v.png file://.../index.html`, then view the screenshot (thumbnails loaded, no broken images). `--dump-dom | grep -c 'class="card'` counts cards (+1 for the template string in the script).
- Open it for the user in Zen (they want visual artifacts opened, not just paths): run `zen-browser "file://..."` via `terminal(background=true)`; `setsid`/`nohup` wrappers are refused. A fast exit 0 means the running Zen instance took the URL.
- Reply with the path, section counts, controls, and an offer to turn exported keep/drop notes into a design direction.
