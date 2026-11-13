---
name: chatgpt-image-generation
description: "Use when generating images via the ChatGPT subscription."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [image-generation, chatgpt, gpt-image-2, comfyui, codex, textures, materials]
    related_skills: [blender-reference-match-loop, comfy-da3-producer-gate]
---

# ChatGPT image generation (subscription route)

## When to Use

Use for smoke tests and mass runs of "ChatGPT image generation" / gpt-image-2, in ComfyUI or scripted, including material/texture asset pipelines.

## Procedure

1. **Choose the requested billing route before testing.** For ordinary "ChatGPT image gen", use the user's ChatGPT Pro OAuth, not an API key. For an explicit API-credit, named API-model, or native-resolution comparison, use the OpenAI API and the linked organization's project key; the subscription route is not a substitute for testing API-only controls. The working route already exists: ComfyUI custom node `/mnt/zer0models/comfyui/custom_nodes/comfyui-codex-image` (node `CodexChatGPTImage`). It reads `~/.codex/auth.json` per call and POSTs to `chatgpt.com/backend-api/codex/responses` with the `image_generation` tool. Do not ask for a Comfy.org or OpenAI key first. Those are metered alternatives, and asking makes the user repeat setup that is already done.
2. **Check limits from the live account, not from marketing pages.** GET `https://chatgpt.com/backend-api/wham/usage` with `Authorization: Bearer <access_token>`, `ChatGPT-Account-ID`, `originator: codex_cli_rs` and `User-Agent: codex_cli_rs/<ver>`. Report `plan_type`, `rate_limit.primary_window.used_percent` / `reset_after_seconds` (weekly window), and `credits.balance`. Read the token in Python and never print it. Docs say Pro has no 5-hour cap, image turns burn the allowance 3–5x faster, and overage draws credits. Measure the before/after delta around a batch.
3. **Probe the size you actually get before promising a resolution.** Run this skill's `scripts/probe_size.py <WxH> <tag> '<tool-extra-json>' [instr]` from the artifact dir. The probe prints the returned pixel size and the backend's `quality`/`size`/`revised_prompt` metadata. To run several sizes, parallelize with `xargs -P`; the terminal tool refuses `&` backgrounding in a foreground command.
4. **Save outputs in the canonical artifact store,** `/mnt/zer0models/project-artifacts/<project>/<run>/`, with the script and a FINDINGS note. Do not leave them in scratch or the repo.
   - Before generating anything, look for the user's existing generations in sibling folders such as `<product>-import/` (an asset-import bundle with `assets.manifest.json`), the artifact store and `/mnt/zer0models/Recvd/` (where files the user sent from their phone via KDE Connect land, not `~/Downloads`). A repo note saying images are "pending upload" means they exist locally somewhere. Search by folder and manifest, not by the catalog's expected filenames, before telling the user an asset is missing. Once found, use the user's originals (verify the manifest's checksums, commit them as delivered; plain Git is fine at tens of MB) in preference to regenerated stand-ins.
   - Batch runs: one script with a `TARGETS` dict (id → traits), a thread pool of 3, and an incremental `manifest.json` (file, size, sha256, prompt, seconds). Re-running fills only the missing ids, so a `server_is_overloaded` failure is fixed by running it again. Expect 23–41 s per image. Check a contact sheet with vision before using any of them.
   - Run scripts with the ComfyUI venv under `env -u PYTHONPATH -u PYTHONHOME` (or `env -i`). The Hermes environment leaks a PYTHONPATH that makes PIL fail to import `_imaging`.
   - Pass id lists inside the script, not as `$ids` on the command line: the terminal runs zsh, which does not word-split variables, so the script receives all ids as one argument.
5. Compare against the user's existing references at the same zoom (vision tool), then report the resolution, quality and cost receipts.

## ChatGPT-linked API credit experiments

1. Read the current first-party benefit guide at `https://developers.openai.com/api/docs/guides/chatgpt-api-credits` and the current model/prompting docs. Distinguish documented eligibility from the user's verified grant, balance and expiry.
2. Keep credit activation, browser authentication, project-key availability and image-model organization verification separate. A linked subscription does not supply an API key or sign the automation browser in. Do not report the subscription route's `wham/usage` credit balance as an API organization balance.
3. Locate the project's existing prompts, API runner and original images before building another harness. For ElementalUI, consult `docs/pipeline/image-generation.md` and the canonical artifact store. Treat an old credential failure as historical evidence, not proof of the current key's validity.
4. Verify the receiving organization and available grant before spending; free-credit exhaustion may fall through to purchased credits. Do not enable auto-recharge as part of an experiment.
5. Compare identical material prompts at a fixed model and size while varying quality; test resolution separately. Save requested settings, returned dimensions, elapsed time, response usage, hashes and native-detail crops. Describe a single-sample comparison as exploratory, not proof that the highest setting is consistently better.
6. If access blocks execution, name the exact missing prerequisite and state that no generations ran. Do not replace the requested API test with subscription generations or present a proposed comparison as measured results.

## Size and quality behaviour (subscription route)

- The route ignores the tool's `size`, `quality` and `model` fields. That includes newer API model names (`gpt-image-2.5-*`) and API-only qualities (`xhigh`, `max`), so a model upgrade cannot be switched on from here. When asked which model the subscription uses, cite the Codex image-generation doc: it says the built-in tool is `gpt-image-2`. Then contrast that with the API guide's current model list, and read both docs live because model names change. It returns about 1.6 MP buckets: 1536x1024 by default, 1254x1254 square when the instructions demand the exact size, and 1448x1086 is also seen. With a wide input image and a "wide landscape" prompt it follows the input's aspect instead (e.g. ~1860x845), so crop afterwards rather than relying on the size field. Metadata usually reports `quality: low|medium`, but the output still matches ChatGPT-web references.
- The ComfyUI node's size combo (1024x1024, …) does not reflect what the route returns. Fix the options or label them before a mass run.
- True max resolution needs the metered API: built-in `OpenAIGPTImageNodeV2`, or the OpenAI Images API. Limits are a 3840 px long edge, 655,360–8,294,400 total pixels, multiples of 16 and at most 3:1, so the square max is 2880x2880. Above 2560x1440 the API docs label the size experimental. The route needs a Comfy.org or OpenAI key, and the OpenAI org may need API Organization Verification. ComfyUI's built-in node can lag behind the newest API models, so check its model enum in `comfy_api_nodes/nodes_openai.py`. Offer this route as an option for approved heroes only; do not make it the default.
- Local 4x restoration: RealESRGAN_x4plus (`/mnt/zer0models/comfyui/models/upscale_models/`), loaded with `spandrel` in the ComfyUI venv, fp16 on CUDA, 512 px tiles with 32 px overlap. Takes about 8 s per 1536x1024 image on the 3080 Ti. It is crisp at 1:1 on stone, bark, frost, scales and nacre; water comes out slightly smooth. Label the output as model-inferred detail.
- Before using a key from bws for the metered API, check it is a real `sk-` API key. An expired session token stored under `OPENAI_API_KEY` returns "Provided authentication token is expired". Tell the user and ask for a valid key; do not retry.
- Before reaching for tiling or a paid max-resolution route, decide whether more pixels are needed at all. See `references/texture-resolution-and-delivery.md`.

## Image-conditioned regeneration (scripted)

- For "regenerate this crop in higher resolution", call the node module's `generate(prompt, [base64_png], size, quality)` directly from a script run with the ComfyUI venv (`env -i HOME=$HOME PATH=/usr/bin:/bin /mnt/zer0models/comfyui/.venv/bin/python`); no ComfyUI server or graph needed. Rectify/straighten the source crop first (it is the composition reference), name the medium and palette explicitly, ask for a flat straight-on scan with no frame/text, and run 2 variants in parallel with `xargs -P 2`. Prefer this over local diffusion img2img when the user asks for ChatGPT.
- Cleaning up a soft/low-res whole image (e.g. a reference/inspo photo): send the original as the only input with "re-render this exact photo; keep composition, objects, text, colours and lighting identical; only remove blur/compression artifacts and add natural fine detail; do not add, remove or move anything", requesting the input's aspect (portrait 1024x1536 is honoured for a portrait input). Then Real-ESRGAN x4 in ComfyUI and scale to the target size. This beat SDXL+ControlNet-tile img2img clearly on crispness while staying faithful; still compare native crops of subject, text and props against the original before adopting, and keep the original untouched.
- Extending an image (outpainting) without stretching: the route has no mask input, so place the image's edge strip on a canvas, fill the area to generate with flat magenta, and say "fill the magenta area so the artwork continues seamlessly; keep the given part exactly", plus the style reference as a second input. Then scale back, keep only the new pixels, and feather the seam inside the overlap. Returns in ~40 s per call.

## Material/texture prompting

- Request one raw, full-frame, top-down orthographic surface: neutral diffuse light, sharp edge to edge, with no text, labels, panels, borders, props, horizon or vignette.
- Never ask the model for 4-panel PBR atlases. Generated "normal/roughness/height" panels are hallucinated and not aligned. Derive all maps from one source (Blender bake), and label AI images `valid_pbr_map: false` / visual target.
- Showcase and taxonomy posters are references for the catalog, not per-pixel inputs.
- Keep provenance with every image: model and route, prompt, the revised_prompt from the metadata, size, and sha256.
- A mass run needs an approved material list first, sized for mass generation. The user's atlas posters and roadmap are the seed, not the scope: transcribing them gives a few dozen entries, and this user rejects that as far too small (one family alone, such as stone, should cover the real rock types, minerals and lapidary stones, so expect hundreds of materials in total). Build family > class > material from real geology, botany, zoology and weather. Keep every seeded id and atlas code, tag each entry's `origin` (atlas / roadmap / expansion), and give it a kind. Put finishes and seeds below the material level, and state the count they multiply to. Generate the list with a script that refuses to drop an existing id, check coverage with a test, then have the user validate it before generating.

## Pitfalls

- To regenerate a reference detail at higher resolution, pass the native reference crop (upscaled 3x) plus a rectified copy, and say both images show the SAME artwork and the output must keep the SAME print style (describe the texture explicitly). With only a small strip and a generic style prompt, the model drifts to its own clean style and the user rejects it.
- Each image call burns subscription allowance; cap delegated workers at a stated number of real generations.
