---
name: ace-racquet-net-receivers
description: Use when refining ACE racquet nets and hall equipment.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [blender, ace, racquet, geometry]
---

# ACE racquet receiver discipline

## When to Use

Use for ACE G tennis, L1 badminton/squash/table-tennis and L2 pickleball equipment lookdev, particularly overlapping opaque net receivers or OS court-grid drift.

## Procedure

1. Read `build_ace_campus.py` and each space detail module before replacing equipment. The builder creates opaque primary Net_i/PNet_i receivers; adding a cord overlay cannot make those boards transparent. Replace the actual board object from the owned detail module.
2. Align L2 details with the primary eight-pad/ace_apply_os grid: x=-36+18*col, y=-24+28*row. Legacy detail pads at a different grid sit below Field_L2 while their nets remain visible, producing ghost courts. Preserve the eight primary courts plus existing heritage; do not duplicate a second grid.
3. Measure net heights above actual playing surfaces: G z=.42, L1 z=10.22, L2 z=20.22 in the recovered model. ITF tennis post=1.07m, center=.914m, span=doubles width+2*.914m. BWF post=1.55m, center=1.524m and net depth=.76m, not a floor-height wall. Pickleball post=.9144m and center=.8636m; preserve service centerline gaps through the NVZ.
4. Build actual open cord geometry with sag-following headband tape, nonmetallic dark nylon and physical posts. Inspect a native crop as well as the wide frame; subpixel cord geometry may be correct but invisible at delivery size.
5. Inspect all overlapping objects at windscreens. Legacy FenceN/S steel boxes occlude the separate GEO-WindN/S material receiver. Remove duplicate boards or update both; use a thin fabric surface and supports rather than glass/steel.
6. Treat L1 floor gaps as a shared envelope problem. Adding a full deck without coordinated lightwells blocks G ceiling skylights directly below. Request shared changes with a patch and require G/L1/L2 A/B rather than hiding the issue in a detail module.
7. Preserve L2 camera/world/skylight daylight unless specifically authorized. A successful net replacement is not permission to globally relight the approved floor.
8. Open the actual supplied reference before judging against its name. A roof-obstructed reference cannot support claims of matching an interior quality bar.
9. Use unique timestamped render paths for vision review. Reusing an overwritten path can hit image-load limits and muddle lineage.
10. Serialize every Blender render through the project's supplied lock wrapper. A transport timeout is not proof the job stopped: inspect exact PID/cwd and log, wait for that owned job before editing or retrying. Never launch a second racquet render while the previous queue/job survives.

11. Verify actual receiver material slots after save/reopen, not original material names. `apply_os` copies TennisHard/Pickle for soil; their zero-user originals can disappear on reload. Inspect the copied Principled shader and linked roughness mix range, not its unlinked default value: soil writes to the roughness default do not override an already linked procedural range.

## Completion

Require 128spp picked views, exact sport/equipment inventory, net height/tape verification, camera wall/slab probes, unchanged OS soil/occupant/socket wiring, per-pass keep/reject log and before/after contact sheet. Rank unresolved floor continuity, glazing, people proxies and TT duplicate blockers honestly; a wide hall still does not certify squash or TT interiors.
