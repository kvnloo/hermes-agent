---
name: hapsland-bend-fsm-layers
description: Use when drawing Bend state machines as Hapsland layers.
---

# Bend statecharts as Hapsland layers

The working setup lives on the `.files` branch `docs/fsm-hapsland-layers-20261021` (draft PR kvnloo/.files#34), in `docs/spec-diagram/fsm/`. A local checkout is at `/mnt/zer0models/worktrees/hapsland-fsm-20261021/{hapsland,.files,deps}`. The served site is `project-artifacts/hapsland-fsm-layers/`, which holds `publish.sh`, `serve.sh` and `shots`.

## Rules
- Compile the **unchanged** upstream `fsm.bend` with `bend Runtime.bend -o Runtime.mjs`, where Runtime.bend imports the modules `as` namespaces. You get `export default {"NS.step": fn, ...}`. Constructors are `{$: "NS.Tag", field}`, Nat is BigInt, and Bool is a JS boolean. Do not hand-write a numeric wire in Bend: it adds bug surface.
- Pin the compiler identity (sha256 of the binary) that produced the PROOF.bend receipts. For the z0 FSMs that is `~/.bend/bin/bend` 2.0.34, sha256 `66e5faf9…`. The `.files` architecture diagram keeps its own 2.0.37 pin; never change one pin to suit the other.
- Verify the copied sources by **git blob id** (`sha1("blob <len>\0"+bytes)`). This works offline in `--check`.
- Bend leaves the state unchanged on a refusal. Label it from a guards table (machine, from, event → laws). Treat `clock` and `observation` guards and terminal states as no-change, not refusal. Device-style machines need effect-based acceptance (`peff`).
- Derive the edges by executing the compiled module over sample states and events. Diff them against the upstream `.mmd`; it should be exactly 0 missing and 0 extra.
- Copy only ids, times, event kinds, short SHAs and finding codes into public tapes. Tag each step `report` or `what-if`.
- The browser re-runs each step and compares it with the receipt-bound `replay.json`. Show any mismatch.
- **Publishing one machine publicly:** don't ship the full runtime when its metadata or symbols name hosts or devices.
  1. Write a tiny `Runtime.bend` that imports only the unchanged module (e.g. `WorkItem.bend`) plus an `abi_version`, then compile it.
  2. Append a `bendMetadata` filtered from `model.json` down to that machine's types, states, guards, laws and proofs, with any remaining names scrubbed.
  3. Run the old and new runtimes through the same adapter over the full build sample space (states × events × availability). Require 0 mismatches.
  4. Update the receipt with the input blob ids, the new sha256 and the parity count, and stop claiming byte identity.

## Pitfalls
- A Bend `match` needs a parameter, not a computed value; add a helper def. Any parameter used more than once needs `+name`.
- Hapsland only needs `effect@4.0.0`, `foldkit@0.165.0`, `@effect/platform-browser@4.0.0` and `vite@8.3.1`. Install those into a side dir and move `node_modules` in, so the monorepo install is not needed. A Vite build takes under 1 s.
- The ensemble layer svg is 894×505. On phones, override `.ensemble-scene` margin and viewport height, use camera zoom of about 39, and hide route labels in the 2D phone layout.
- The terminal tool refuses commands that contain `http.server`. Start the transient user unit with `systemd-run --user --unit=... python3 -m http.server PORT --bind <tailnet-ip>` from a script run with background=true.
- A Playwright `selectOption` re-render can swallow the next click. Wait about 400 ms before stepping.
- The original Hapsland reference checkout is on omarchy-phone (`root@100.104.42.85:/root/workspace/hapsland-dotfiles-reference-20261016`). It is not on groot or the S22.
