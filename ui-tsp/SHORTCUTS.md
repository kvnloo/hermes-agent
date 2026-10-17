# Hermes shortcuts in Tern

App-level bindings live in `src/actions.ts`. The same registry supplies grouped
`/help` rows and the compact `f1 help` composer hint; editor keys remain in
`composer.ts`, and sheets keep their own local keys.

| Chord | Action |
| --- | --- |
| Alt+M | Model picker |
| Alt+P | Session-only model picker (no profile-default control) |
| Ctrl+P / Ctrl+Shift+P | Next / previous session-recent model (`/model-next`, `/model-prev`) |
| Ctrl+R | Search prompt history; Enter fills, never sends (`/history-search`) |
| Ctrl+G | Round-trip the draft through an external editor (`/editor`) |
| Alt+, / Ctrl+, | Hermes settings (`/settings` still works) |
| Alt+C | Context window (`/context`) |
| Alt+U | Usage (`/usage`) |
| Alt+A | Agents (`/agents`) |
| Alt+S | Session picker |
| Alt+Shift+F | `/fork`: copy the conversation into a new Tern pane (idle session) |
| Ctrl+T | Toggle `/reasoning show` / `/reasoning hide` using backend readback |
| Alt+Shift+C | Copy the literal composer text via OSC 52, with a notice |
| F1 / Alt+/ | Commands and grouped shortcut help |
| Shift+Tab | Cycle session reasoning effort (unchanged) |
| Ctrl+O | Expand / collapse every tool's detail, only with an empty composer and no overlay/completion |
| Ctrl+Shift+O | Show / hide successful settled tool activity (same input ownership guards) |
| Alt+Up | Recall the oldest queued prompt (unchanged) |
| Escape | Close completion first; otherwise interrupt if busy (unchanged) |
| Ctrl+D | Quit on an empty prompt; otherwise composer forward-delete (unchanged) |
| Ctrl+C | Clear draft / interrupt / double-press exit; Settings owns cancellation (unchanged) |
| Ctrl+Shift+X | Explicit agent interrupt: preserve the draft, even under a modal |

Routing remains splash → explicit owned interrupt → Ctrl+C special handling → top overlay → modal guard →
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

## Forking

`/fork` creates a durable child through `session.fork` and opens a pane with
literal argv `hermes --resume <new-id> -p <owning-profile>`. `/fork <message-id>`
copies through that durable user/assistant message (inclusive). The gateway owns
all transcript copying and profile resolution; the original pane/session stays
unchanged. Outside Tern, or if pane launch fails, a notice retains the new id and
resume command. No shell interpolation or automatic model request is involved.
Busy, hydrating, and compute-host-owned histories are refused rather than copied
partially. Tests use fake pane launchers, never a real user's Tern daemon.

## Carly and host lifecycle

The frontend emits edge-triggered OSC 9;4 progress from confirmed Hermes activity:
indeterminate working, paused while a server request waits, cleared on settlement,
backend loss or exit. OSC 777 emits one host notification when input is required
and one at final confirmed settlement (finished/failed/interrupted), not on idle
repaints or duplicate completion events. App dispatch notices are independent;
there is no synthetic percent, keepalive timer or extra bell. Resumed
running/waiting state is projected too. Host transcript reads retain `omp.*` roles
and original tool names.

Native `sendable` and the submit transaction share the session/switch,
modal/approval-owner, rewind, attachment and dictation gate.
Carly's `agents:ask` retains a prompt at the host until that gate opens. Admission
while busy still uses the configured queue/steer behavior, not a second turn store.

**Interrupt limitation:** Tern's generated `AgentsCx.interrupt` sends plain Ctrl+C;
there is no origin bit distinguishing Carly from a person. With a nonempty human
draft that clears the draft, not the running turn. Use the explicit owned path
`tern send <exact-owned-block-id> keys ctrl+shift+x` for a draft-preserving stop,
or click Stop. Never send a second Ctrl+C blindly (an idle pane can exit). The
owned chord reaches Hermes even under a modal, but host/OS bindings can still own
it before it reaches the program. Stop is confirmed only by Hermes settlement.

## Deliberate limits

- Ctrl+T uses the existing Hermes command because there is no app-level thinking
  visibility preference. `show`/`hide` updates the **profile display setting** in
  the gateway (not session-only effort); it does not cycle the reasoning level or
  rewrite existing transcript blocks. Rapid toggles are serialized and stale
  session reads are discarded.
- Tool visibility and expansion are pane-local presentation preferences, not
  gateway settings. Hiding retains tool nodes and all context. Running, failed,
  cancelled, unknown, background and unfinished/failed child-agent activity stay
  visible, outside host work groups; pending approval temporarily shows all tools.
  Resume keeps pane preferences and clears per-call overrides.
- Tern's **Fold tool calls** preference is separate: consecutive settled tools
  are top-level main siblings so Reader, Spine and Console can group them.
  Ctrl+O changes individual detail, not the host's group disclosure. Pointer
  folds feed the same per-call state; a mixed set expands together, then
  collapses together. Answers and usage stay after work, thought chains stay
  together. Host folding is never enabled or changed by Hermes.
- Cycling shares the picker's session-scoped recent selections and the existing
  `switchModel` / expensive-model confirmation path. With no recent selections,
  it uses the configured picker inventory (including provider fallback catalogs).
- External editing prefers `tern open --wait` inside Tern; otherwise `$VISUAL` /
  `$EDITOR` (or `vi`). A private temporary file is deleted after readback.
  A changed draft/session is never overwritten; its editor result is shown separately.
- OMP plan-mode toggling (Alt+Shift+P) is not implemented here.
- User-configurable bindings remain a single TODO at the registry boundary.
- OSC 52 has no acknowledgement; the notice reports the clipboard request, not
  guaranteed terminal acceptance.

Shortcut vocabulary and defaults are adapted from
[oh-my-pi at eb74cf84](https://github.com/can1357/oh-my-pi/blob/eb74cf84d8e16ac9b8c4fa5d7c43037023d016ac/packages/tui/src/app-keybindings.ts),
by Can Bölük / Stencil, MIT licensed.
