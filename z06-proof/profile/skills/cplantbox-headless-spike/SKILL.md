---
name: cplantbox-headless-spike
description: "Use when evaluating CPlantBox headlessly."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cplantbox, fspm, scientific-computing, headless, reproducibility]
    related_skills: [spike, grounded-citations, test-driven-development]
---

# Bounded CPlantBox evaluation

## When to Use

Use for isolated CPlantBox feasibility runs, organ-state adapters, dependency audits or preparation for observation-constrained calibration.

Use `Plant-Root-Soil-Interactions-Modelling/CPlantBox` upstream as the source of truth. Pin commit, model XML hashes, submodule revisions and native binary hashes; the declared version alone does not identify master code.

## Execution

- Audit authorized reusable Python environments read-only before installing. Create a task-local venv with `--system-site-packages` when compatible; never install into the old environment. Disable bytecode and redirect HOME, TMPDIR and caches locally.
- Read current README, wheel guide, pyproject and CMake files. Successful old CI runs may have no downloadable artifacts left; check availability before depending on wheels.
- Build with explicit task-local `Python3_EXECUTABLE`, out-of-tree CMake/Ninja, at most two jobs and a wall deadline. Disable CPU-native tuning and IPO. Keep PiafMunch enabled when evaluating carbon support rather than silently omitting it.
- Record whether native dependencies are bundled, source-built or system. Bundled SuiteSparse/SUNDIALS archive hashes and header versions do not prove archive build provenance; rebuild pinned sources before redistribution.
- Run one scientific process at a time with one numerical-library thread and explicit affinity. If `/usr/bin/time` is absent, use subprocess/resource accounting. On timeout terminate only the owned process group.

## Native forward interface

- Use upstream Plant/MappedPlant and parameter prototypes before initialization, then `simulate(dt)`; never substitute handwritten biology.
- Use a positive constructor seed; native zero is time-derived. Fix the integration grid independently of requested samples. Test fresh-process replay, different-seed response and common-final-state sampling invariance.
- Separate allocated organs from emerged organs. Allocated organs may have negative ages and one node; leaf axes can exist before realized blade area is positive. Do not force early leaf emergence to satisfy a test.
- Export parent/organ/node IDs, creation times, native coordinates, length/radius, active/alive flags and segment ownership. Leaf edge cross-sections and one-sided native leafArea enable headless measurements without VTK.
- Preserve cm/day units and one transform across dates. A canopy bounding box is not a silhouette, projected cover or intercepted light. State JSON/RSML is not automatically a complete physiology/RNG restart checkpoint.
- Label numerical guardrails separately from biological priors. Reject unsupported inputs; execute parameter-effect, finite-output and endpoint tests against the real engine.

## Functional and scientific limits

- Core architecture does not require a GUI, VTK, MPI or DuMuX. Inspect Python helper imports and install only their actual missing dependencies into the task venv.
- Demonstrate functionality with a small existing upstream functional example, removing only plotting and preserving structural/physiological/climate inputs. Record native solver arrays, not merely import success.
- Supplied absorbed PAR is not a radiation solution; prescribed soil potential is not a Richards PDE. DuMuX/dumux-rosi is a separate stack.
- Carbon-limited growth may fall back to exponential growth when its carbon-growth map is empty. Compiling a backend or selecting a growth-function code does not demonstrate active feedback.
- Search the pinned catalogue for common and Latin plant names. A tutorial, pseudostem flag, leaf arrangement or species-named root file does not validate a whole-plant species model.
- Leave unknown identities unknown and let dated-observation quality select calibration targets. Separate engine feasibility, fitting, interpolation and held-out prediction; sparse shoot photos do not identify root or physiological parameters.
- Test named shoot presets by actual attachment groups, not filenames: an opposite-decussate label may contain one leaf per node, a species file under structural/plant may contain roots only, and missing 2-D leaf profiles can fall back to cylinders.
- Verify successor location filters through a native parameter-XML round trip before using XML for replay. Some revisions write `Where` but read only `where`, silently changing topology; retain the raw export and use the prototype recipe as canonical until a separately tracked correction passes graph checks.
- Read phyllotaxy and emergence implementations before adapting prototypes. Rotation fields may be pi-multipliers despite header units; leaf subtype counters may be plant-global, while stem lateral delays count already allocated children per parent and subtype. Keep paired members synchronized with explicit native subtype rules and test their attachment, timing and transverse orientation.
- Separate lifetime flags from abscission and pruning. Native dead organs can retain positive blade area and exported geometry; verify alive-filtered observables instead of treating an unfiltered structural sum as living foliage.
- Retain GPLv3 engine/model notices and component-specific GPL/LGPL/MPL/BSD licenses. Never flatten the dependency stack to MIT.
