---
name: blender-headless-addon-qualification
description: Use when vetting Blender skills or headless add-ons.
version: 0.1.0
author: Kevin (kvnloo), Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [blender, extensions, audit, headless]
    related_skills: [blender-lighting, oss-checkout-install]
---

# Vetted headless Blender add-ons

## When to Use
- Evaluate third-party Blender skills/extensions before adding them to this agent's workflow.
- Generate terrain or rock coupons through the installed, bounded operator paths below.
- Do not use to install a live-scene bridge or modify a production scene without approval.

## Procedure
1. Use `terminal` for `hermes skills search <query> --limit 8 --json` and `hermes skills inspect <id>`. Preserve results; do not treat popularity or a SAFE scan as API compatibility.
2. Read candidate source through `read_file`; pin GitHub downloads to commit SHAs. Check real scripts, references, network/credential requirements and dangerous Python. Reject interface/keybinding checklists that add nothing beyond existing skills.
3. Read the Blender extensions index at `https://extensions.blender.org/api/v1/extensions/`. For archive requests use a Blender-version User-Agent and the package website Referer if a plain request fails. Check the registry SHA-256, reject absolute/parent ZIP paths and symlinks, then extract for review. A content hash proves integrity against the registry, not absence of malicious logic.
4. Audit import/registration/operator paths before enabling. Do not execute unreviewed remote scripts, use `--force` to bypass a skill audit, or enter credentials to qualify an optional package.
5. Install with `hermes skills install <id> --category creative --yes`, then audit. Extensions use `env -i HOME="$HOME" PATH=/usr/bin:/bin TMPDIR="$TMPDIR" blender -b --factory-startup --command extension install-file --repo user_default --no-prefs <audited.zip>` through `terminal`. Verify installed source against audited files. No system-wide install or persistent preference enabling is needed.
6. Test under `env -i HOME="$HOME" PATH=/usr/bin:/bin TMPDIR="$TMPDIR" blender -b --factory-startup --python-exit-code 1 --python <coupon.py>`. Use Cycles CPU, four threads, 384px, fixed seed, 24 samples, AgX and exposure zero; or acquire the project's shared GPU lock. Keep all test outputs separate from production.
7. Require a real operator/node assertion, evaluated geometry, a saved render, JSON receipt and visual inspection via `vision_analyze`. Count node-probe successes/failures programmatically. A node constructor test does not validate sockets or an entire graph.
8. Uninstall failed skills using `hermes skills uninstall <name> --yes`; preserve rejected source and failure logs as evidence. Record exactly which recipes/operators passed, not blanket add-on certification.

## Qualified operator paths
Enable only in the ephemeral process:

```python
import addon_utils, bpy
assert addon_utils.enable('bl_ext.user_default.antlandscape', default_set=False)
assert bpy.ops.mesh.landscape_add(refresh=True, subdivision_x=64, subdivision_y=64,
    mesh_size_x=4, mesh_size_y=4, noise_type='ridged_multi_fractal',
    random_seed=41, height=0.8, at_cursor=False) == {'FINISHED'}
assert len(bpy.context.object.data.vertices) == 4096
```

A.N.T. Landscape 0.2.0: tested terrain generation, not erosion/file import/export. Extra Mesh Objects 0.4.1: tested `bpy.ops.mesh.add_mesh_rock(num_of_rocks=3, use_random_seed=False, user_seed=41, detail=2, display_detail=2, scale_X=(0.65,0.85), scale_Y=(0.65,0.85), scale_Z=(0.65,0.85))` after enabling `bl_ext.user_default.extra_mesh_objects`. Evaluate modifiers before measuring geometry. Its unrelated equation-surface tools use eval; never feed untrusted expressions. Rock settings can create local user-configuration XML. Neither tested operator needs networking or credentials.

## Pitfalls
- The ra100 Geometry Nodes Python reference contains nonexistent `GeometryNodeCurvePrimitiveArc`, `GeometryNodeCurvePrimitiveSpiral`, `GeometryNodeCurvePrimitiveStar`, and removed `ShaderNodeTexMusgrave` on Blender 5.2.2. Query actual node RNA instead of trusting names.
- Skills referring to desktop bridges are not prerequisites for `blender --background --python`; a persistent live scene is a different requirement.
- Do not inherit arbitrary Python environment paths into Blender. Preserve HOME for user-level extensions and TMPDIR for the approved scratch directory.
- `World.use_nodes`/`Material.use_nodes` work in Blender 5.2.2 but warn about removal in 6.0; requalify rather than suppress compatibility failures.
- No beauty improvement is implied by successful coupon renders. Reference-match visual gates still own production acceptance.

## Verification
Evidence and reproducible scripts live at `/mnt/zer0models/project-artifacts/quackles/process/blender-mastery/tools/`: `REPORT.md`, `smoke_coupons.py`, `api-probe.json`, source manifests, extension audits, render receipts, and `smoke/contact-sheet-v1.png`. Verify this location exists before using it; it is specific to this local profile. Blender 5.2.2 LTS build d13f752e3b9c is the qualified runtime.
