---
name: ripple-visual-review
description: "Use when the owner reviews renders by pick, draw and talk."
---

# Ripple visual review (HITL pick + ink + voice + object tracking)

Successor to the Quackles HITL-NOW page: kvnloo/ripple `feat/visual-review-intent-surface` (draft PR #3, issue #2). Ideas credited to Kit Langton's Scrawl (read via agent-reach; evidence in `/mnt/zer0models/project-artifacts/ace/ripple-review-20261020/SOURCE-EVIDENCE.md`).

## Run a session
1. Masks: render object-ID passes for the exact commit that produced each candidate image with the ACE twin's `gfx/blender/scripts/run_idmask.sh <worktree> <out>/<variant> CAM_A,CAM_B <variant> 50` (host flock + clean env; ~17 min per variant for the full campus). Never in the lane's own worktree: add a worktree at the lane's commit and cherry-pick the idmask commits.
2. `bin/ripple-review <session-dir>` (private paths from `<session>/../ripple.env`: RIPPLE_ACE_RUN, RIPPLE_IDMASK, RIPPLE_LABELS). It rebuilds the manifest from disk (newest file per camera, sha256/mtime/round) and serves 127.0.0.1:43251+.
2b. The server is not a durable service: it dies with the session that started it. Before pointing the owner at the URL, `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:43251/` and relaunch as a background process if it isn't 200. Relaunch after every new batch of finals too; the manifest is rebuilt only at launch, so check its printed candidate table (stamp, hash, mask object count, `align`) to confirm the new frames were picked up.
3. Owner notes land in `<session>/agent-queue.jsonl`; all events in `<session>/data/events.jsonl` + SQLite. Read the queue, act, report per note.

## Agent cards (ephemeral-ui inside Ripple)
kvnloo/ripple `feat/ephemeral-ui-host` (draft PR #7, stacked on #3). Show cards: `RIPPLE_EUI=<kit checkout> bin/ripple-cards <session> <name> --cards app:kind,...` (needs `ESBUILD` if esbuild isn't on PATH, e.g. hermes-agent's node_modules/.bin/esbuild); the open page picks it up in ~3 s. Owner actions land in `agent-queue.jsonl` with `source: "ephemeral-ui"` and a `card_intent` payload (authority always none: a card's Approve is context, never approval). The inline "Agent: …" ack under a card is the kit's scripted ack, not you; answer from the queue. Proof: `tests/browser/cards.py --session <copy src> --shots OUT`. Default theme hermes-slate: hermes-nous-dark is bright blue and pulls Google Fonts (blocked by the frame CSP).

## Open it in Dash
All Ripple branches are on kvnloo/ripple `main` (#3 #4 #5 #7 #8 merged 2026-11-03). Dash needs no change: its artifact-stage screen opens any `http://100.x:port/#t=<hex>` link. Run `bin/ripple-review <session> --host $(tailscale ip -4)` and hand over line 1 of `<session>/DASH-LINK.txt` in a chat reply (Dash shows "Open in stage") or send the `dash://stage?url=` deep link from line 2. Device proof without touching the S25: on the S22, use `flock /tmp/s22-ui.lock scrcpy --new-display=1080x2340/420 ...`, open `exp+dash://expo-development-client/?url=http%3A%2F%2F100.113.138.100%3A8213` there with `am start --display N -f 0x18000000`, then send the deep link with `--display N` and screenshot with `screencap -d <SF id>`. Kill the scrcpy child PID, not the flock wrapper. The mic doesn't work inside Dash over plain-http tailnet (not a secure context); voice there needs https.

## Approval gating
The Hermes `/v1/responses` bridge stays off until the owner wires approvals through the Ripple/Dash turbo-mode flow; until then notes go through the file queue. While formal approval is pending, keep unblocked work moving: merge reviewed lanes locally (not pushed), keep the review session current, and don't idle waiting for picks.

## Verify before calling it done
- `bun test src`, then `RIPPLE_CHROMIUM=~/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome python3 tests/browser/smoke.py --session S --shots OUT --wav speech.wav` on a COPY of the session (the script copies). `--use-file-for-fake-audio-capture` feeds real speech through MediaRecorder, so the mic path is tested without playing audio aloud.
- Check mask quality, not just test passes: blend a random-colour id map over the beauty frame and look; edge agreement (builder prints `align`) should be well above 1.5.

## Pitfalls
- Blender `Object.pass_index` clamps at 32767; the campus has ~58k objects, so ids above that collide (the whole plaza read as an L3 lab rack). Use an object custom property read by an Attribute node (OBJECT) and encode 8-bit digits R+256G+65536B in an EXR.
- Blender 5.2 has no 'Raw' view transform; never put ids through an 8-bit PNG with a view transform.
- The campus build rewrites `gfx/blender/export/unreal/ace_sockets.json`; never `git commit -a` in an idmask worktree.
- faster-whisper 1.2.1 breaks with PyAV 19 (`metadata_errors`); the STT venv pins `av==18.1.0` at `~/.local/share/ripple/stt-venv`. Hermes' faster-whisper only imports with Hermes' PYTHONPATH.
- Transcribe with VAD + greedy decode: without VAD a silent hold loops through temperature fallbacks for 10-60 s while Blender loads the CPU.
- Label parts from the object NAME first, materials/collections second (a glass-clad roof is still a roof; a water court in the Biosphere collection is not the dome).
- Single-letter building names (A, I) are ordinary words; only bind them next to "building/hall".
- Public repo: keep private paths and ACE data out of git; the ACE adapter reads paths from env.
