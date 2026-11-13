---
name: garden-room-live-feedback
description: "Use when handling Garden Room owner voice feedback live."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [garden-room, voice, feedback, triage]
    related_skills: [garden-room-voice-realtime, garden-room-replay-watch, garden-room-core-planner]
---
# Garden Room live feedback loop

## When to Use

Applies to the always-on garden_room agent receiving inbox items (complaint/request/bug/praise) from the phone.
Always pass an explicit workdir (`/mnt/zer0models/workspace/zer0/products/garden_room`). Commit only your own files.

## Procedure

1. **`[test]` items**: reply with exactly the requested text. Use no tools and make no edits. Praise alone needs no code change.
2. **Gather evidence** for a real complaint:
   - Read `replay_context.sidecar` and view `snapshot.png` with vision.
   - Read the last ~40 lines of `data/voice/events.jsonl`. The owner's follow-up utterances and `type:action` rows (`reobserve`, `success:false`) usually show the intended command and why voice failed.
   - Run `git status --short` to see which files other builders currently own.
3. **Quantify, don't eyeball**:
   - Load `data/state.json` (gitignored, so it is the live layout) into a routed headless page via `gr_state` localStorage.
   - Count overlaps and hard warnings with `window.__garden.evaluate`.
   - Run `__garden.optimize` with 2–3 seeds to check that a clear plan exists before promising one.
   - Route `/api/state`, `/api/layouts`, `/api/zen/progress`, `/api/replay/batch` and `/api/voice/*` so nothing writes owner data.
   - Optimize is synchronous and takes about 6–10 s per seed under SwiftShader. Keep terminal timeouts at 600 s or less; longer ones become an unwaitable background job.
4. **Misrecognitions**: edit `data/voice/rules.json` (`{aliases: {heard_phrase: action_id}, vocabulary: [...]}`).
   - Read it first, because write_file refuses blind overwrites.
   - Map both the misheard and the intended phrasing to an action id that exists in `buildActionTable`.
   - Alias keys must ignore sentence dots. Otherwise a spoken trailing "." defeats every alias, because `normalize()` keeps '.' for decimals.
5. **Act on the phone**: append `{"id": <next monotonically increasing int>, "action", "params", "say"}` to `data/voice/drive.jsonl`.
   - The phone runs it only while voice is on.
   - Call it *queued* until an `events.jsonl` action row with `source:"hermes_drive"` and `success:true` appears.
   - Write `say` so it stays true even if the phone runs old client code.
6. **Honest acknowledgements**: a success label must reflect the committed result.
   - Some GR calls refuse silently. `GR.suggestApply()` commits only conflict-free plans and otherwise just returns the plan.
   - Check the return value, retry where sensible, and throw "nothing moved" rather than labelling success.
7. **Ownership**: if another builder has app.js (or any file) modified, fix within your module (voice.js, rules, tests). Name any remaining gap in the reply instead of editing their file. Do not change bridge routes, helpers or services unless asked to repair the bridge.
8. **Gate**:
   - Run `node tests/voice_suggest.mjs`. It takes a crowded copy of the owner layout, forces Jev to `reobserve` via routing to prove the alias path, then checks for zero conflicts, mesh sync and undo.
   - Then run `node tests/voice.mjs` and `node tests/phone.mjs`.
   - Commit with `git -c user.name=kvnloo -c user.email=7121943+kvnloo@users.noreply.github.com commit` using only your paths.
9. **Reply** in plain text, briefly: the root cause, what changed (commit), tests, what is queued vs confirmed, and blockers.
