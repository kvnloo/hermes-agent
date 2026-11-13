---
name: threejs-procedural-asset-builds
description: Use when bulk-building three.js models from photos.
---

# Photo → procedural three.js models (img2threejs style, in bulk)

For apps that need many small models of real objects (plants, props) built as code, fast. The full img2threejs skill (`/mnt/zer0models/workspace/zer0/oss/img2threejs`, ~80-180k tokens per object) is too slow for 10+ objects; run its idea as a parallel swarm of cheap code models plus a vision judge.

## Procedure
1. **Group objects into families** (e.g. 25 plants → ~12 families) and parameterize the rest (height, spread, pot size, seed). Map instances to families in a JSON file the app reads, with an `approved` flag per family.
2. **Separate what the app supplies** (pots, bases) into its own module so builders only write the varying part. Tell the judge about it, or it keeps scoring the supplied part.
3. **Build the harness before dispatching:** a `preview.html?m=<module>&view=front|three|side|top&<params>` page that frames the model, sets `window.__ready` and reports triangle count/size; a Playwright capture script on the real GPU (`--use-angle=vulkan --enable-features=Vulkan --ignore-gpu-blocklist`; SwiftShader cannot render splats/heavy scenes); a vision judge script (reference + renders → JSON `{score, matches, fixes}`, e.g. via the ChatGPT subscription route used by chatgpt-image-generation). Smoke-test all three with a stub model first.
4. **References:** give builders padded crops of the original photo, not background-removed cutouts; cutouts of cluttered plant clusters are fragments that mislead the judge.
5. **Brief once, point to it:** output contract (`createX({...}) -> THREE.Group`, origin, units, seeded PRNG, triangle budget, InstancedMesh, real leaf silhouettes, no external assets, edit only your file), library pages to read first (`grimoire/build/geometry_patterns.md`, showcase foliage such as `img2threejs-showcase/src/demos/coffee-house/foliage.ts` and `tropical-island/shrubs.ts`), the render→judge loop with a round cap (4), every judge JSON saved to `rN/judge.json`, and a short final reply. After round 1, name the best family file as the exemplar to read.
6. **Dispatch in parallel** from a launcher script: `hermes -p clean chat --oneshot --provider <p> --model <m> -t terminal,file -q "<pointer to brief + family params>"`, each `( ... ) &` with its own log, then `wait`; run the script as a background terminal with notify. Without `-t` the run has no shell/file tools. The provider must be defined under `providers:` in that profile (`hermes -p clean config set providers.cerebras.base_url ...`, `.key_env`, `.api_mode chat_completions`, `.default_model`). Export keys only inside the launcher subshell.
7. **Use models for what they can do:** the code models have no vision, so they never look at images; only the judge script does. DeepSeek V4 Pro handled multi-round organic geometry; Cerebras gpt-oss-120b often stopped early or produced broken shapes, so keep it for simple families or short verifiable tasks.
8. **Gate yourself:** re-render every family, build one reference-vs-render contact sheet, view it, approve per family. Read scores only from the saved judge files: cheap workers report scores no judge produced. Unapproved families keep a fallback (photo billboard) in the app; rebuild only the broken ones with a sharper description including what it must never look like (bare stick, black star, cones).

## Strict retention and botanical preflight

- Freeze a native contextual crop and a source snapshot per family before rewriting. Record neighbor exclusions and visible fruit/flower presence from a native image; a generic family label or code model cannot correct a mistaken coordinator observation.
- Prefer a pinned permissively licensed mature generator such as EZ-Tree for branching structure, but do not confuse reuse/connectivity with botanical fidelity. Its default terminal leaf sites can under-fill crowns. Preserve an accepted parent architecture unless a measured defect warrants replacement.
- Require a real rendered leaf+petiole coupon and short two-node shoot, vision-approved by the coordinator, before whole-family bulk generation. Check local leaf-frame orientation, base/tip attachment and actual dimensions. A code-model checklist claim does not pass this gate.
- Capture parent and child with a fixed camera/lighting/seed, plant-only triangle counts and a repeat-control geometry fingerprint; auto-fit cameras and pot-inclusive counts hide regressions. Test 15%-height juveniles with both reduced and unchanged spread/pot diameter. Measure actual above-soil maximum, not a nominal-height claim.
- Keep a child only when its same-fixture saved absolute judge score strictly exceeds the parent AND two fresh side-swapped dream-loop A/B trials prefer it without protected regressions. Audit native image loads/model/session IDs. Equal scores, tie votes, missing receipts and juvenile/unit failures retain the parent. A single-view win is not multiview or owner acceptance.
- Inspect current exemplar sources before recommending them: Coffee House foliage in the current showcase is a PixiJS contextual-image grid, not reusable Three.js plant geometry. Use tropical-island shrubs as a craft reference, not an implied licence grant.
- Resolve a bws secret environment once before worker fan-out; concurrent secret-list/get calls can rate-limit. Preserve interrupted worker/critic artifacts, distinguish exit from completed evidence, and make orchestration errors return nonzero.

## Pitfalls
- Judge scores of 4-5/10 can still be acceptable stand-ins; the contact sheet decides, not the number.
- Load family modules dynamically with a fallback so one broken builder file never breaks the app.
- Camera-facing billboards look wrong from a top view; real models fix this. In eye-level views hide meshes within ~0.35 m of the lens so one plant cannot fill the screen.
- After any edit to a long one-line JS statement, run `node --input-type=module --check < app.js` and a boot test: a `//` comment inserted mid-line silently comments out the rest and the whole app fails to load.
