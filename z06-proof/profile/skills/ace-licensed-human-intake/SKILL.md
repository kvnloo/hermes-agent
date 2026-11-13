---
name: ace-licensed-human-intake
description: "Use when sourcing licensed humans for ACE Blender."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [ace, blender, assets, licensing, characters]
    related_skills: [ace-campus-twin, browser-3d-asset-pipelines]
---

# ACE licensed human intake

## When to Use

Use for human-source selection, licensed clothing/motion intake, or triage before replacing ACE mannequins. This is intake guidance, not a rendered-character approval.

## Rules

- Prefer an anatomical, already-weighted human source over generating a static mesh and treating it as a rig. MPFB/MakeHuman bundles are candidates, not approved ACE characters until rendered.
- Separate software and output licenses: MPFB program code is GPLv3; its bundled mesh/targets/rigs/weights/assets and combinations of those assets are CC0. A separately licensed garment changes the composite's obligations. Never label every MPFB output CC0 automatically.
- Retain first-party pack ZIP hashes and per-item MHCLO/MHMAT headers, pack metadata, creator/source URLs, and hashes for actual OBJ/texture dependencies before use. File names and pack titles are not license proof.
- Inspect clothing/hair source thumbnails before building a roster. Denim hotpants retain fly/pocket/hem construction after recoloring: select a sports-cut garment instead. Shaggy/card-like hair can fail near-field review despite a valid license.
- Fail unclear license intake closed. A Sketchfab CC0 title may conflict with its platform license field; a garment header saying only CC-by does not establish its exact version. Prefer an explicitly versioned alternative.
- Exclude Bandai Namco Research datasets from unrestricted commercial content: datasets 1/2 are CC BY-NC 4.0 even though their visualization code is MIT. CMU permits commercial inclusion but prohibits direct resale of data, including converted forms.
- Distinguish Hunyuan shape/paint stage files from a complete runnable stack. Scan directory paths as well as filenames: generic model.safetensors and UNet filenames hide inside versioned Hugging Face cache directories. Record checkpoint revisions and bytes; never infer VRAM from file size.
- Keep character binaries external with LICENSES.md and SHA256 manifests, loaded by config path. Do not commit .blend files or large packs.
- Queue one neutral clothed coupon before full-campus renders. Every Blender/generation invocation must share the approved host render flock. A long queue does not authorize stealing the lock or claiming a pass; explicitly hand a still-running job to the coordinator when closing a lane.
- Blender 5.2 reports `Addons.new(): takes at most 0 arguments` for `addons.new(module=...)`. Do not reuse that unsupported call. A corrected registration path still needs a real Blender retry before it is a proven recipe.
- Separate rights/intake tests from runtime and visual gates. Config, dependency, bone-map and source-weight tests do not prove generation, deformation, hair/cloth, grounded poses or a 128-spp hero.

## Verified intake / unqualified pipeline

- External assets: `/mnt/zer0models/ace-artifacts/people-assets/`.
- MPFB intake revision: `b1a2dc98776da9d1eea751b159d42cf61778fe2e`.
- Worktree: `/workspace/wt/ace-campus-people`, branch `ace/lane-people`.
- Executed intake interfaces: `gfx/blender/scripts/inventory_ace_people_assets.py` and `test_ace_people_intake.py`; six tests passed.
- Source decisions and current status: `/mnt/zer0models/project-artifacts/ace/campus-buildout-20261019/wave3/people/{SOURCE-SELECTION,REPORT,STATUS}.md`.
- This does **not** establish an approved ACE near-field pipeline. Recover the current report and actual images before reuse.

## Sources

https://raw.githubusercontent.com/makehumancommunity/mpfb2/master/LICENSE.md
https://static.makehumancommunity.org/assets/assetpacks.html
https://static.makehumancommunity.org/mpfb/docs/getting_started.html
https://github.com/BandaiNamcoResearchInc/Bandai-Namco-Research-Motiondataset
https://mocap.cs.cmu.edu/
