# Hermes shortcuts in Tern

App-level bindings live in `src/actions.ts`. The same registry supplies grouped
`/help` rows and the compact `f1 help` composer hint; editor keys remain in
`composer.ts`, and sheets keep their own local keys.

| Chord | Action |
| --- | --- |
| Alt+M | Model picker |
| Alt+P | Session-only model picker (no profile-default control) |
| Alt+, / Ctrl+, | Hermes settings (`/settings` still works) |
| Alt+C | Context window (`/context`) |
| Alt+U | Usage (`/usage`) |
| Alt+A | Agents (`/agents`) |
| Alt+S | Session picker |
| Ctrl+T | Toggle `/reasoning show` / `/reasoning hide` using backend readback |
| Alt+Shift+C | Copy the literal composer text via OSC 52, with a notice |
| F1 / Alt+/ | Commands and grouped shortcut help |
| Shift+Tab | Cycle session reasoning effort (unchanged) |
| Ctrl+O / Ctrl+Shift+O | Toggle the newest foldable tool's detail, only with an empty composer and no overlay/completion (unchanged, including Shift alias) |
| Alt+Up | Recall the oldest queued prompt (unchanged) |
| Escape | Close completion first; otherwise interrupt if busy (unchanged) |
| Ctrl+D | Quit on an empty prompt; otherwise composer forward-delete (unchanged) |
| Ctrl+C | Clear draft / interrupt / double-press exit; Settings owns cancellation (unchanged) |

Routing remains splash → Ctrl+C special handling → top overlay → modal guard →
completion → action registry → composer. New chords require exact modifiers.
Legacy app chords retain their permissive modifier behavior. Unbound Alt letters
cannot type into the composer; Alt+B/F/D still perform readline word editing.

## Terminal ownership

Checked `tern help`, `tern help dev`, and Tern's
[commands/keymap guide](https://docs.stencil.so/tern/guides/commands.html) and
[built-in actions](https://docs.stencil.so/tern/reference/actions.html).
Tern's defaults, selected preset, plugins, and user keybind layer can take keys
before a program sees them; the user layer wins. This frontend does not install
host bindings or override Tern's preferences, pane navigation, or other commands.
Prefer Alt+, for Hermes settings when the host takes Ctrl+,; use Alt+/ if F1 is
owned by the host/OS. `/settings` and `/help` are always available as text.
Bindings are tested using a connected real SDK peer and parsed terminal key
bytes, not a complete native-window/preset matrix.

## Deliberate limits

- Ctrl+T uses the existing Hermes command because there is no app-level thinking
  visibility preference. `show`/`hide` updates the **profile display setting** in
  the gateway (not session-only effort); it does not cycle the reasoning level or
  rewrite existing transcript blocks. Rapid toggles are serialized and stale
  session reads are discarded.
- No global hide-tool-activity shortcut: active, failed, and approval state must
  remain visible. Ctrl+Shift+O keeps its pre-existing detail-fold alias instead.
- Model cycling (Ctrl+P / Ctrl+Shift+P), external editor (Ctrl+G), history search
  (Ctrl+R), and OMP plan-mode toggling (Alt+Shift+P) are not implemented here.
- User-configurable bindings remain a single TODO at the registry boundary.
- OSC 52 has no acknowledgement; the notice reports the clipboard request, not
  guaranteed terminal acceptance.

Shortcut vocabulary and defaults are adapted from
[oh-my-pi at eb74cf84](https://github.com/can1357/oh-my-pi/blob/eb74cf84d8e16ac9b8c4fa5d7c43037023d016ac/packages/tui/src/app-keybindings.ts),
by Can Bölük / Stencil, MIT licensed.
