---
name: artifact-stage-browser-proof
description: Use when running artifact-stage proofs or its demo.
---

# artifact-stage browser proof

Repo: `/mnt/zer0models/workspace/zer0/products/artifact-stage` (kvnloo/artifact-stage). Bun: `/mnt/zer0models/home-offload/kvn/bun/bin/bun`.

## Run
```
AS_THREADS=8 AS_POOL_SIZE=1 flock -w 2400 $TMPDIR/heavy.lock nice -n 10 \
  timeout 1700 python3 tests/browser/proof.py --session /home/kvn/.cache/artifact-stage/sessions/<id> --out <dir> [--only desktop|phone]
```
- Run it with terminal background=true and notify. A full run takes about 12 minutes on a loaded host.
- Pass absolute paths. The persistent shell's `$HOME` can drift to a scratch home, so `~` may point at the wrong place.
- For one-off Playwright scripts in `$TMPDIR`, run `python3 -P`. A stray `inspect.py` in scratch shadows the stdlib.

## Rules (each one learned from a failed run)
- **Use one rehearsal session per run.** proof.py stamps the session id with `-proof-<date>-<HHMMSS>`. A reused id keeps notes and intents from earlier runs, which hid a broken recolour step for three runs.
- **Check what the render shows, not only that a frame arrived.** The recolour check counts warm pixels in the refined image. Glowing materials take their colour from a ColorRamp into Emission Color, so a `default_value` change does nothing. The worker retints the ramps instead.
- **Report three latencies per frame:**
  - `server_ms`: settle → frame ready;
  - `recv_ms`: the message reached the page;
  - `client_ms`: the image is on screen.
  
  Headless Chromium uses software GL. On a host at load ~20, its rAF and screenshots stall for seconds, so `client_ms` there is a test-host number, not a product number. The Dash 390x844 shot with a warm pool gave EEVEE 284/448/869 ms.
- **Lower Blender threads during proofs** (`AS_THREADS=8` on 20 cores). Otherwise Chromium's GPU process starves and screenshots time out.
- **Cancel refinement on camera input, not on the next drawn frame.** `SettleDetector.touch()` runs from keys, drags and the wheel. On a starved renderer, frame-driven detection left a stale refined frame up for 3 s or more.
- **Every viewer shares one refine lane.** `src/refine/lane.ts` maps each socket's generations onto the server sequence. Without it, a second viewer (phone after desktop) is stale forever.
- **Demo server:** `AS_POOL_SIZE=1 bun server/serve.ts --session ... --host 100.113.138.100 --port <free> --keep-frames` with background=true and persist_on_release.
  - Check `ss -ltn` first.
  - Avoid ports 5188, 4747, 8097 and 8791.
  - The URL and token are in `<session>/.url` and `.token`.
- **Stop servers by pid** from `ss -ltnp`, never with `pkill -f`. A pool worker can outlive a killed server for a few seconds.
