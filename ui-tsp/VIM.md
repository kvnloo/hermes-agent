# Optional Vim composer

Vim editing is **off by default**. It uses the existing Hermes profile setting:

```sh
hermes config set display.vim_mode true
```

Start Tern after changing this config-only setting. The frontend reads the owning
profile through `config.get full` when adopting a session and after closing Settings;
it does not poll or write a second preference store. Disable it with
`hermes config set display.vim_mode false`. No new gateway RPC is required.

## Editing contract

- Starts in Insert. Text/IME composition, readline editing, multiline insertion,
  prompt history and Enter submission retain ordinary composer behavior.
- Escape leaves Insert or Visual, or cancels a pending operator/count, **without
  interrupting**. Escape in quiet Normal mode retains the app's interrupt policy.
  Overlays and completion own their keys before Vim. Ctrl+C and the dedicated
  interrupt action retain their existing priority.
- Normal/Visual: `h j k l` and arrows, `0 ^ $`, `w b e`, `gg G`, counts;
  `i a I A o O`; `v V`; `d c y` with motions or doubled linewise operators;
  `x D C`, `r`, `p P`, `u` and Ctrl+R. Vertical motion remembers grapheme column
  across short lines and never browses prompt history from Normal/Visual mode.
- Visual selections are inclusive and grapheme-safe. `r` replaces each selected
  grapheme, preserving newlines. `y` stores a composer-local Vim register; `p/P`
  paste from it (no claim of system clipboard synchronization).
- A paste event is literal text, never commands, and one undo step, in every mode.
  Insert typing retains the ordinary composer's typing-burst undo policy; mode
  boundaries, operators, replacement and paste are explicit undo boundaries.
- Only enabled Vim emits Tern's native editor `mode` and Visual `anchor`. The mode
  disables competing native editing/selection ownership. Stale native edit,
  send and undo callbacks are rejected while enabled; normal editor callbacks
  remain unchanged when disabled. The dock shows the mode and pending command.

This is a bounded Vim subset, not a full Vim emulator. Search, text objects,
macros, repeat-dot, named registers, indentation operators and continuous Replace
mode are not implemented. Overlay-local editors do not inherit Vim mode.

## Evidence and remaining native gate

`src/__tests__/vim-composer-state-machine.test.ts` connects a real Tern SDK
Session to a fake gateway and exercises parsed key/paste bytes plus native
callbacks, emitted editor props, settings readbacks and binding collisions.

The isolated `tern-serve` smoke exercises the real gateway and ordinary composer.
Native-window acceptance is blocked by the isolated Tern account being signed
out. Real OS IME candidate-window behavior and native pointer/selection behavior
with Vim enabled still require an authenticated isolated native-window check;
parsed Unicode input coverage is not a claim that OS IME integration was tested.

Reference: OMP `packages/tui/src/vim.ts` and
`packages/tui/src/prompt/custom-editor.ts`, pinned
`eb74cf84d8e16ac9b8c4fa5d7c43037023d016ac` (Can Bölük / Stencil, MIT).
