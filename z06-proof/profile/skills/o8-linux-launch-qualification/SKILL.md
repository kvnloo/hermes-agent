---
name: o8-linux-launch-qualification
description: Use when launching or recording o8 on Linux.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [o8, linux, tauri, recording]
    related_skills: [isolated-gui-interaction-trials, fframes-workflow-evidence]
---
# o8 Linux launch qualification

## When to Use

Use to diagnose installed o8 startup, qualify a native Linux launch, or prepare a truthful wallpaper-backed app demo.

- Read the actual desktop entry and stat its executable before attributing launch behavior to the current checkout. Installed release binaries can predate current source by weeks. Preserve dirty worktrees.
- Separate historical failed launches from a fresh observed launch. A mapped Tauri window can still contain a blocking native dialog or splash; inspect its pixels and private compositor window tree.
- Check the native Node-version dialog before rebuilding. The installed Linux binary can reject system Node 26 while existing Node 22 works. Qualify a process-local PATH pointing to the installed Node 22 binary; never change global Node or assume the running source build shares the same ABI requirements.
- Use a private headless Sway, private HOME/XDG directories and private DBus for smoke tests. The local Sway may require its own LD_LIBRARY_PATH. Keep software-rendered onboarding acceptance distinct from native GPU/Hyprland, populated-project and wallpaper/glass acceptance. Do not borrow the owner's display as an unverified fallback.
- Keep a baseline screenshot and a separately named supported-Node attempt. Verify owned processes have exited after teardown; retain receipts outside Git.
- Treat live wallpaper as desktop context unless actual o8 integration is found and exercised. Never composite wallpaper through opaque panels and claim native glass. Show wallpaper around the app if transparency is not verified.
- For a demo, record a short disposable-repository mission through review and its actual persisted outcome. Adapter names, multiple tiles and opened dialogs are not evidence of working runtimes, concurrency or successful approval. Billable execution and production merges require their respective authority.
- Reuse editorial ideas from existing fframes projects with explicit source/truth boundaries. A storyboard timer is not recorded app footage or a native performance measurement.
