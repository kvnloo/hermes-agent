---
name: blender-cpu-locked-hero-audit
description: Use when auditing a byte-locked Blender hero CPU-only.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [blender, cpu, provenance, visual-audit]
    related_skills: [blender-material-identity-audit]
---

# CPU-only locked-hero critique

## When to Use

Use for reference-versus-shipped Blender audits where hero bytes are locked, GPU rendering is prohibited, and candidate recipes need preparation without publishing.

1. Extract the exact shipped blob with read-only `git show`, record commit/hash, and compare supplied screenshots separately. Never assume a file named final is the shipped recipe; read prior experiment logs and probe base versus held edits independently.
2. Run only background Blender probes with two threads, no render or save operators. If embedded Python cannot import stdlib modules, use explicit system PATH and matching PYTHONHOME/BLENDER_SYSTEM_PYTHON, with CUDA_VISIBLE_DEVICES empty. Use `--python-exit-code 1`: Blender may otherwise exit zero after a Python failure.
3. Dump actual socket links and ordered inputs with identifiers. Math/Map Range/Mix duplicate names make name-keyed dictionaries lossy. On newer Blender inspect `compositing_node_group` as well as legacy scene.node_tree; an empty legacy property does not prove an absent compositor.
4. Reuse the validated structure gate unchanged, with a tight theme-specific UI stroke mask and protected robot silhouette. Include self-control and ambiguous-overlay sensitivity. A failed composition gate permits diagnostic observations, not a total match score. Do not move a locked robot to game edge statistics.
5. Rank localized corrections by impact and edit breadth; separate colour direction approval, render acceptance, and permission to break hero byte identity. State current and proposed numeric values, and distinguish old multi-edit experiments from evidence for an unrendered subset.
6. Preserve native recipe compatibility. If the native loader lacks ColorRamp-element edits, supply an explicit companion using an established extension plus a local adapter; do not hide unsupported keys or claim native application alone is complete.
7. Apply prepared candidates only in fresh in-memory scenes; read back exact sockets and compare camera, transforms, stored geometry, UV/mapping, links and untouched graph channels. Do not treat loader success as validation.
8. Quantify pyramid cost from shipped levels: master pixel count, tile count, level pixels and raw buffer sizes. Separate measured same-theme timing from historical other-theme estimates. New hero, tiles and pose sequence need a consistent source family; an old pyramid is not made valid by a new hero hash.
9. Save scripts, sheets, masks, Lab definitions, source hashes, failed and successful probe logs, and final verification receipts only under the authorized output directory. No generated 2D illustration is a renderer result.
