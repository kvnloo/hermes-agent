---
name: hermes-engine-extension
description: "Use when extending Hermes Agent engines (e.g., tern)."
version: 0.1.0
author: Hermes Agent
license: MIT
category: software-development
metadata:
  hermes:
    tags: [engine, extension, typescript, testing]
    related_skills: [hermes-agent]
---

# Hermes Engine Extension

## When to Use
Use this skill when you need to extend Hermes Agent with a new engine (e.g., for a new tool) or modify an existing engine (like ternEngine) to add features such as including the program name in snapshots.

## Procedure

1. **Locate the engine definition**
   - Find the function that returns an `EngineHandle` via `defineEngine` (typically in `src/index.ts`).

2. **Add state for program name (if the engine launches a process)**
   - Add a variable to track the program name (e.g., `let program: string | undefined;`).
   - Set this variable when launching a new pane (in `session.restart()` when `!options.pane`).

3. **Update the observe() root node name**
   - In the `observe()` function, set the root node's `name` to include the program name when available.
   - Use a fallback chain: `program ?? pane ?? "default-name"`.

4. **Write a test**
   - Create a test file in `tests/` (e.g., `ternEngine.test.ts`).
   - Mock the underlying tool commands (e.g., `tern` CLI) using a mocking library (vi.mock if using Vitest).
   - Test that the snapshot root name reflects the program name when a custom command is provided.
   - Ensure the test passes after your changes.

## Pitfalls

- **Forgetting to set the program variable for new panes**: Only setting the variable when `options.pane` is provided misses the case where a new pane is launched. Always set it in the `session.restart()` path when creating a new pane.
- **Incorrect fallback order**: The root name should prefer the program name, then the pane ID, then a default. Reversing this order can cause the snapshot to show the pane ID even when the program name is known.
- **Not mocking all necessary commands in tests**: When mocking the tool CLI, ensure you mock all commands used in the engine (e.g., `new tab`, `capture`, `close`). Missing a mock can cause tests to hang or fail.

## Example: ternEngine

See the changes made to satisfy the BENCHMARK.md requirement: a snapshot must name the program that owns the pane, not only the pane id.

- Added `let program: string | undefined;` after `let owned = false;`.
- In `session.restart()`, set `program = command[0];` after determining the command.
- Updated `observe()` root name to `name: program ?? pane ?? "tern"`.
- Test: `tests/ternEngine.test.ts` verifies that with `command: ["myprog", "arg"]`, the root name is `"myprog"`.
