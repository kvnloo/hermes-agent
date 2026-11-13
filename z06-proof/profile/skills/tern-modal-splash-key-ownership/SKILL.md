---
name: tern-modal-splash-key-ownership
description: "Use when Tern modals lose keys during launch splash."
---

# Tern modal / splash input regressions

- Reproduce through the real Session byte parser and App input loop before changing Settings parsing or consent logic. Several unrelated failures (lost paste, uncancelled confirmation, missing actions) can share an earlier key consumer.
- Run the identical focused suite with `HERMES_TUI_SPLASH=0` as a diagnostic ablation only. If it becomes green, inspect `App.#onKey`, `App.open`, and `LaunchSplash` ownership. Do not disable splash globally in tests to conceal the regression.
- Opening a modal must relinquish both the splash surface and input ownership immediately. Merely routing keys around the splash leaves a hidden interactive modal; animated `skip()` may continue consuming keys until the dissolve completes.
- Exercise modal handoff with a deterministic clock: assert immediate screen-surface closure, delivery of the first key to the modal, no composer mutation, and no additional splash frames after advancing beyond its lifetime. Keep the ordinary key-to-skip animation tests intact and verify nonmodal overlays do not dismiss the splash.
- Preserve Settings behavioral tests unchanged when the defect is in shared App ownership. Run the full ui-tsp Vitest suite, TypeScript check and ESLint afterward.
- Route screen-splash lifecycle events before the inline-surface address filter. Scope visibility to the owning pane/splash, stop frame intervals while hidden or reduced-motion, and retain only a one-shot boot/readiness deadline so a hidden slow startup still hands off without waiting for show. Keep pure frame elapsed time on the original clock and leave native theme tokens to recolor static cells.
- When fake-timer tests use the real Tern Session, let App teardown reach Session.close, then advance its 50 ms input-drain timeout before awaiting the run promise. Otherwise teardown timeouts mask the actual behavioral regression. Assert no timers after draining, and distinguish the SDK drain timeout from splash-owned timers.
- Use the canonical Python test runner. If bootstrap provisioning fails, inspect its supported `HERMES_PYTHON` override and use an existing pytest-capable interpreter without altering shared environments. Give settings contract tests enough time to finish; their parameterized executed count may exceed the runner's static discovery estimate. Report the executed summary, not the estimate.
