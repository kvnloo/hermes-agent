---
name: tern-keyboard-bugbash
description: Use when testing Tern keyboard and Ink fallback UX.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [tern, keyboard, accessibility, ink, testing]
    related_skills: [tern-source-parity-audit, isolated-gui-interaction-trials]
---

# Pixel-backed keyboard bug bashes

## When to Use

Use for isolated Tern keyboard-only exploratory testing, AX audits, real model-turn qualification and same-session Ink fallback comparisons.

## Procedure

- Isolate Tern control endpoint, daemon socket, config/XDG directories and Hermes home under the current profile scratch directory. Never control an ambient user pane.
- Set launch environment explicitly in the command run inside Tern. Do not assume the shell spawned by the daemon inherits the serve process environment. Avoid persistent terminal exports during parallel tester runs; use an explicit subprocess env.
- Distinguish native-window, tern-serve, fixture notifications and real model turns. A signed-out window remains blocked, not bypassed by serve.
- Wait for actual process-driven state and committed pixels. A scenario `wait` is not a reliable wall-clock wait for external PTY output; semantic snapshots and accepted shots can depict different surfaces. Compare screenshots with paired AX/tree data before accepting evidence.
- Read actual pane columns/rows after resizing. Adjust width and height independently and leave an axis unchanged when its cell delta is zero; an accidental decrement creates oscillating geometry.
- Test ordinary Tab/keyboard traversal before using accessibility focus. AX focusability plus a successful forced focus/Space test does not establish keyboard-only reachability. Preserve a trace of focused AX identity after each key.
- Audit all input/list/navigation names, not only Button names. Numeric badge-only category names and unnamed clarification lists pass a nonempty-button-name gate.
- Exercise pending approvals with an exact owned empty scratch target, not user data. Inspect command/title visibility at narrow heights before allowing once, and verify target removal or preservation after allow/deny.
- Reuse the canonical session in real Ink PTY with HERMES_TERN=0 and --tui --resume. Respect Ink-specific bindings. Space slash typing and submission so completion acceptance is not confused with command execution.
- Test live host light/dark switching in both frontends and wait again before capture. Pixel-sample persistent foreground/background colors and compute contrast instead of asserting readability from a theme name.
- Report coverage blocks honestly: do not credit a pointer/AX workaround as keyboard action, a source capability as a rendered feature, or a fixture as a model turn. Quit the owned serve and clean only exact socket-owned processes.
