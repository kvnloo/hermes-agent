# Push-to-talk safety and current host limitation

**Current build: hold-to-talk is unavailable.** Mic / Alt+V remains the working
review-only start/finish toggle; Escape discards. The availability control and
named `app.stt.hold.info` action (default Alt+Shift+Space) explain this rather
than silently arming a microphone. There is no enabled hold preference that
could mislead the user or survive a session change.

## Verified prerequisite

The installed `@stencil-hq/tern` **0.1.0** package:

- Defines `Key` as a press with name, text and modifiers, with no event phase.
- Its running `KeyDecoder` maps CSI-u `Space;1:1` (press), `Space;1:2`
  (repeat) and `Space;1:3` (release) to **identical Space keys**. The acceptance
  suite runs this probe against the real installed SDK, not a source regex.
- The Session requests kitty flag 1 only; it does not negotiate event types.
- TSP `focus` means a click requesting a field's keys, **not window blur**.
  `visible` reports pane visibility. Neither is a physical key release.
- The documented pointer actions are click, double-click and menu, not a
  down/up gesture contract. No invented `keydown`, `keyup`, `onBlur`,
  `hold-start` or capability name is used.

Sources: [TSP Input and Events](https://docs.stencil.so/tern/protocol/input.html),
[Handshake](https://docs.stencil.so/tern/protocol/handshake.html), and the installed
SDK's `src/{keys,session,wire}.ts`. The relevant OMP insert-only constraints are
in pinned `custom-editor.ts:1481–1492`; its gesture cannot be transplanted onto
an input stream which erases release identity.

## Behavior on this host

Space taps and repeats remain ordinary text. Vim motion/jump characters,
completion and IME committed text are not claimed by a hold handler. No spaces
are removed because no gesture owns any. No microphone can become stuck due
to a missing release because a hold never acquires it. No timer infers release,
and no idle timer/poll or provider is started by the availability controls.

Mic / Alt+V continues to use the exact capture/session and existing gateway
recorder/STT, showing hypotheses and committing only a final at the caret in
one undo step. It never submits. Startup cancellation is serialized behind
start acknowledgement, late finals are suppressed and disconnect retires the
capture (gateway teardown releases the device).

## Required before actual hold support can be enabled

A host/SDK contract must deliver distinguishable press/repeat/release, plus
reliable cancellation on input-owner/window loss. Only then implement an
opt-in insert-mode gesture pinned to capture/session and editor revision,
remove only its owned Space, preserve taps and completion/Vim/IME ownership,
and serialize release/cancel behind capture startup. There is deliberately no
dead hypothetical hold state machine or timer-based release fallback here.

Automated tests use a connected SDK Session and fake gateway; they do not
open audio devices or a real OS IME candidate window. Physical hold/release
acceptance is **blocked**, not claimed green.
