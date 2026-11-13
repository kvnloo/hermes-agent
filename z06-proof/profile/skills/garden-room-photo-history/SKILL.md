---
name: garden-room-photo-history
description: Use when indexing Garden Room photos or testing history.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [garden-room, photos, dng, gpu, threejs, history]
---
# Garden Room photo history

## When to Use
Use for Garden Room photo ingestion, individual plant matching, the history/timelapse module, or its read-only browser evidence.

Work in the explicitly provided garden_room repository. Keep source photos, observations, indexes, model caches and rendered review sheets private/local. Commit only assigned modules, routes, tools and tests; never shared app/server files during parallel work unless authorized.

## Shared-host resource safety
- On the 23 GB Garden Room host, check `free -g` for >=4 GB available, then wrap indexing, model/judge jobs, suites and browser tests with `flock /home/kvn/.hermes/profiles/clean/cache/scratch/heavy.lock nice -n 10 ...`. Keep host-wide ML and browser/build work serial; parallel runs previously triggered systemd-oomd despite swap.
- Poll the exact process and lock holder before assuming a silent log is a stalled model: another project's build may own the global lock. Kill only exact owned PIDs, never process-name patterns.
- Use project `.venv` for `history_judge.py`: a ComfyUI OpenCV build can import successfully while lacking `CascadeClassifier`; privacy screening must fail closed rather than bypassing it.
- Report assigned-photo coverage, confidently assigned coverage and unresolved plant presence separately. An unsure proposal is not a verified identity.
- Deduplicate derivative hashes in a precision-review cohort, while preserving every path-based ID in the production index. Cross-source copies otherwise inflate independent visual evidence; still disclose near-duplicates and pot-only similarity.
- Persist a seeded 30-photo sample manifest before independent visual review; count outcomes programmatically and do not extrapolate small, privacy-gated samples to archive precision. If exact historical identities cannot be established, report mismatches/pot-only/indeterminate rather than inventing a precision percentage.

## Bounded decoding
- Prefer `vips thumbnail` to <=1600px before Python image processing. For Samsung compressed DNGs unsupported by system libraw, instantiate `rawpy.RawPy()`, call `open_file`, then `extract_thumb`; **do not use `rawpy.imread()`**, which unpacks raw pixels. Write the embedded JPEG to the project's work directory and shrink with vips. Do not touch `raw_image`, `postprocess` or full-resolution Python arrays.
- Some HEIC sources exceed libheif's item-count guard. For explicitly selected local source files only, vips input option `[unlimited=true]` permits decoding; do not disable limits on untrusted web uploads.
- Read capture DateTimeOriginal first, then filename timestamp, then mtime, and retain date provenance. The garden-intake manifest lives beside `raw/`, not necessarily inside it.
- Recursively inventory Telegram exports; direct children alone miss most images. Preserve path-derived IDs even for duplicate image bytes, because the user's ID contract is source-path based.
- Cache thumbnail fingerprints and object/whole embeddings separately. A changed source must invalidate both feature and detector caches. Test a repeated final run with actual index checksums.

## Identity calibration
- Compare object crops as well as whole/multiscale crops to individual reference crops; matching whole room images labels every plant in the scene incorrectly.
- COCO FasterRCNN's potted-plant label is 64. Detection gives normalized boxes, not individual identity. Pot-bottom similarity can help but cannot establish which of several peppers/curry trees an image shows.
- Treat cosine scores as similarity, not probabilities. Review <=768px contact sheets. Keep uncertain individual identities explicitly unsure even when plant family is obvious. Distinguish same-day alternate-angle precision from historical identity precision; never extrapolate a tiny current-state sample to the archive.
- Persist agent visual rejects separately from owner overrides. Owner corrections must win and be verified by an exact timeline read-back.

## Module integration
- Animate a nested preview group inside `userData.holder`, not the holder scale: Zen also writes holder scale each frame. Scale only the model, never the pot; restore children on sheet close/replacement. Adopt late-arriving model children into the preview group.
- Precompute deterministic logistic scale stages and interpolate; use elapsed wall time for playback, not a capped frame dt that slows playback on low-FPS phones.
- The route dispatcher passes a query-stripped path. Parse pagination from `h.path`, not only the supplied path argument.
- Never return source paths or manifest descriptions from timeline/library APIs. Independently inspect static `/history/` exposure: an existing broad static mapping may expose the raw index even when APIs are authenticated. Escalate server changes if outside scope.

## Evidence
- API tests use a disposable directory under project `work/`. Browser tests intercept GET state to `{}` and all state/layout writes; real-data tests must never POST owner assignments.
- Wait for the asynchronously imported history module before opening an item sheet. Use observable wait conditions for animation and loaded images, not fixed short sleeps in software-WebGL tests. For a crossfade screenshot, wait for the selected image's computed opacity to approach 1 as well as its naturalWidth; a loaded image can still be fully transparent at transition start.
- Run fixture touch/swipe/correction tests, a real indexed-photo journey at narrow/phone/wide widths, and the original phone smoke suite. Inspect downscaled actual renders, not only fixtures.
- Measure each current plant's full thumbnail timeline plus one largest viewer derivative against the transfer budget. Keep the grid/library paged and filmstrip virtualized.
