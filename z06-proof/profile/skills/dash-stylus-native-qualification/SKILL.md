---
name: dash-stylus-native-qualification
description: Use when implementing Dash S Pen modes or selection.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [dash, stylus, android, annotation, qualification]
---

# Dash stylus mode and selection

## When to Use
Use for Dash S Pen side-button, selection, ink persistence and circle-to-draft changes.

## Procedure

- Load dash-turbo-live-preview and dash-native-dev-build first. Work in an unserved tree; qualify native additions in one APK retaining WebRTC, cutout and sharing. Physical device acceptance remains separate from source/unit/browser evidence.
- Observe BUTTON_STYLUS_PRIMARY from this app's Window.Callback dispatchTouchEvent AND dispatchGenericMotionEvent. Delegate every original event and return its result; observation must not consume normal pen selection or finger navigation. Edge-detect held-button repeats across hover and touch. Release the edge on background and restore owned callbacks on teardown.
- Never make pen contact enter annotation. Toggle only on a button rising edge, preserve unsent ink/words on Normal/Annotate switches, and keep explicit Discard separate. Show mode in the existing pill. Keep the live UI-thread path until the committed stroke renders after lift.
- Add Reply to selection to the selectable TextView's customSelectionActionModeCallback, preserving existing actions. Wrapping only Window.Callback.onWindowStartingActionMode is insufficient: a null return lets the framework continue with its original callback. Read the exact native selected range, not clipboard contents or guessed message text.
- For circle attachments, capture the marked region and its painted text into the original conversation's draft, never send automatically. Reserve capacity out of band before asynchronous capture; do not insert a visible attachment chip until the screenshot finishes, because growing the composer moves the circled text before capture. Save and visually inspect the actual cropped PNG, not just its nonzero byte count or the quoted draft text. Preserve newer typing, reject changed-screen/conversation capture and retain ink on error. Scope native text reads to the foreground native-stack screen and intersect each view's visible clip; retained screens behind a chat window are not visible evidence.
- Keep native adapters optional for older APKs, Expo Go and web. Use a narrow typed event interface when the installed Expo package's NativeModule type does not expose its runtime addListener API; exercise the real typecheck rather than casting the error away.
- Exclude dependency symlinks by name (`--exclude=node_modules`), not only directory pattern (`node_modules/`), when copying a build cache. A workstation symlink can otherwise reach the MBP snapshot as a dangling absolute path. Never mutate the release dependency tree.
- Bind every native artifact to its exact submitted snapshot. Replace only your own queued stale jobs, never peer jobs or thermal admission. Preserve failing JS gate exits while still fetching an assembled APK; a built artifact is not a green gate.
- For isolated browser proofs, route the pinned CanvasKit WASM request to the installed canvaskit-wasm file and disclose this infrastructure substitution. Worker CDN access can leave the real app at Loading canvas. Allow cold admitted-worker bundling to finish before evaluating UI assertions; an HTTP navigation timeout near bundle completion is not proof of an input failure.
- Qualify raw input through Gesture Handler and Skia before reporting visible ink. Browser pen events and synthetic button events do not establish the S25 side button, native ActionMode selection, acoustic voice or physical tip latency. Ask the owner only for the remaining physical script, through the parent report.
