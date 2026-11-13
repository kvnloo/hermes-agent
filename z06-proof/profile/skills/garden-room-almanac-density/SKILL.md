---
name: garden-room-almanac-density
description: Use when changing Garden Room Almanac density.
---

# Garden Room Almanac density

- Keep browsing an identity index: three-column real-photo plates on phone, or 58px alphabetical rows. Care, dimensions, models, source attribution, history and editing belong in the full-screen entry.
- Design from the owner's intent, not from available data: browsing answers "which plant is this", the entry answers "how is it doing and what should I do" (age, height, produce count when relevant, health, a top focus with a few actions, photo timeline). Hide coordinates, ids, quaternions and model internals; never fake a value, show 'not known yet' with its source.
- Split a trailing parenthetical qualifier (pot) onto its own tile line; ellipsizing it erases the only thing that tells look-alike plants apart. Let calm status glyphs recede and only exceptions draw the eye.
- Reuse zerOS Living Night tokens and the public GR seams. Do not change app.js merely to register an Almanac feature.
- Run `nice -n 10 node tests/almanac_density.mjs http://127.0.0.1:8790` and `nice -n 10 node tests/almanac.mjs http://127.0.0.1:8790` in `/mnt/zer0models/workspace/zer0/products/garden_room`. Both intercept every mutating API request and GET state/Zen progress; never run an unguarded screenshot harness against the owner's saved layout.
- Gate at 412x915 DPR2: expanded header <=112px, >=12 fully visible grid tiles, >=15 after condensation, >=12 index rows, no horizontal overflow, 25 entries reachable, filtered sort page flips, exact scroll return. Count whole tile/row bounds, not partial plates.
- Test Photos as the first entry point before care references are loaded. A photo-to-plant link must await the reference. Clear stale plant detail state before opening Photos so Escape navigates the photo viewer correctly.
- Keep the model renderer dormant during browsing, shared and bounded in entries, and gated by an explicit Live 3D toggle. Visit/render all 25 models in the retained integration suite.
- Use an IntersectionObserver sentinel to collapse the header without a per-frame scroll handler. Animate shared heroes using only transform/opacity, with a reduced-motion path.
- Namespace root state (`data-order`) separately from control attributes (`data-sort`); generic selectors otherwise match the dialog instead of the select.
- Native select arrows reserve extra width. Inspect the actual labels, including Location and active filter values, rather than trusting CSS width arithmetic.
- Frame-budget assertions (transition/scroll p95) fail under host load from parallel builders or GPU jobs; when only those checks fail, rerun on a quiet host before treating it as a regression, and say so in the report.
- Feature-detect `/api/plants/<id>/profile` by validating its id and photos array; fall back to `/api/history/plant/<id>` without substituting model dimensions or Zen scores for observations. Photo boxes can arrive without image dimensions: derive crop aspect from decoded naturalWidth/naturalHeight, not a square assumption. Prefer thumb1600 for the hero and viewer, thumb512 for the strip.
- Share the exact checklist action resolver between rendering and logging. Supplement a short/pending provider plan with observation checks to keep 2–4 steps; disable placeholder actions until profile resolution so a late response cannot silently log a different action. Persist locally with explicit on-device copy unless a supported journal endpoint is advertised and verified by GET.
- Re-read source and target assignments after a photo correction before reporting success; a generic `{ok:true}` is not proof. Prefer atomic `/api/history/correct` when profile-specific correction routes are unavailable, preserving the selected plant box.
- Serialize browser suites with `flock /home/kvn/.hermes/profiles/clean/cache/scratch/heavy.lock nice -n 10 ...` and check `free -g` for at least 4 GB available first. A lock-wait timeout is not a failed test; record the distinction and never bypass the lock.
- Inspect the DPR2 PNGs under `/mnt/zer0models/project-artifacts/garden-room/almanac-v2/`. For before captures, route the committed legacy JS/CSS only inside Playwright; do not revert a shared working tree. Never drive the owner's phone for this qualification.
