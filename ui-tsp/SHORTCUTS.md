# Hermes shortcuts in Tern

App-level bindings live in `src/actions.ts`. The same registry supplies grouped
`/help` rows and the compact `f1 help` composer hint; editor keys remain in
`composer.ts`, and sheets keep their own local keys.

<!-- generated-bindings:start -->
| Context | Action id | Chords | Intent |
| --- | --- | --- | --- |
| app | app.clear | ctrl+c | Clear the draft / interrupt / exit (twice) |
| app | app.interrupt | escape | Close completion / interrupt the agent |
| app | app.interrupt.owned | ctrl+shift+x | Interrupt the agent (preserve draft, including under a modal) |
| app | app.exit | ctrl+d | Exit (empty prompt; otherwise delete forward) |
| app | app.thinking.cycle | shift+tab | Cycle the reasoning effort |
| app | app.thinking.toggle | ctrl+t | Toggle reasoning display (profile setting) |
| app | app.tools.expand | ctrl+o | Expand / collapse all tool detail (empty prompt) |
| app | app.tools.toggleVisibility | ctrl+shift+o | Show / hide settled tool activity (empty prompt) |
| app | app.message.alternate | alt+enter | Steer while busy (queue instead when busy mode is steer) |
| app | app.message.dequeue | alt+up | Edit the oldest queued prompt |
| app | app.clarify.toggle | alt+h | Hide / show the waiting clarification (preserve answers) |
| app | app.stt.toggle | alt+v | Toggle microphone dictation (review before sending) |
| app | app.live.toggle | alt+shift+v | Live voice (explicit consent; automatic spoken turns) |
| app | app.stt.hold.info | alt+shift+space | Push-to-talk availability (Mic / Alt+V fallback) |
| app | app.model.select | alt+m | Select model |
| app | app.model.manage | alt+shift+o | Manage profile auxiliary roles, fallbacks and providers |
| app | app.model.selectTemporary | alt+p | Select model for this session only |
| app | app.model.cycleForward | ctrl+p | Cycle to the next recent model |
| app | app.model.cycleBackward | ctrl+shift+p | Cycle to the previous recent model |
| app | app.history.search | ctrl+r | Search prompt history (fill draft, never send) |
| app | app.editor.external | ctrl+g | Edit the draft in an external editor |
| app | app.settings | alt+, / ctrl+, | Open Hermes settings |
| app | app.context | alt+c | Show context window |
| app | app.usage | alt+u | Show usage |
| app | app.plan.review | alt+shift+p | Review the latest plan |
| app | app.jobs | alt+j | Show background jobs |
| app | app.browser.blocks | alt+shift+b | Show / hand over Tern browser blocks |
| app | app.agents.hub | alt+a | Show agents |
| app | app.session.resume | alt+s | Open session picker |
| app | app.tree | alt+t | Browse the copied-session branch tree |
| app | app.tree.search | alt+shift+s | Search saved sessions and branch paths |
| app | app.session.fork | alt+shift+f | /fork-message [message-id]: fork into a new Tern pane |
| app | app.history.older | ctrl+home | Load and scroll to older retained history |
| app | app.clipboard.copyPrompt | alt+shift+c | Copy composer text |
| app | app.retry | f5 / alt+r | Retry the latest retryable text-only failure (idle, empty prompt) |
| approval | app.approval.approve | ctrl+enter / ctrl+q | Allow a pending tool once (empty prompt, approval owns input) |
| app | app.clipboard.copyLine | alt+shift+l | Copy the current composer line |
| app | app.help | f1 / alt+/ | Commands and shortcuts |
<!-- generated-bindings:end -->

Routing remains splash → explicit owned interrupt → Ctrl+C special handling → top overlay → modal guard →
completion → action registry → composer. New chords require exact modifiers.
Legacy app chords retain their permissive modifier behavior. Unbound Alt letters
cannot type into the composer; Alt+B/F/D still perform readline word editing.

## Profile configuration

In the owning Hermes profile's `config.yaml` (or native Settings → Display):

```yaml
display:
  tern_keybindings:
    app.help: [alt+h]
    app.retry: []  # disable; null resets one action, {} resets all
  tern_profile_identity: true  # default false
```

Use `hermes config set display.tern_profile_identity true` for the optional tag.
Bindings load through session-scoped `settings.get` on adoption and confirmed Settings
readback, not a new environment variable or a cwd-derived profile. Reopen Settings to
load external edits; there is no idle polling. Native Settings validates before saving.
An invalid manually edited map leaves the last valid bindings (defaults on a new
session) and shows a warning. Use the field's default action to reset it.
Chord aliases/order are normalized. Duplicate and overlapping legacy-modifier chords,
host-reserved Meta/Cmd/Super, Ctrl+Shift+C/V, Alt+F4/Tab, and composer-owned editing
keys are rejected. Approval has its own context; its allow-once chord requires the
approval to own input and an empty composer. It cannot approve behind a modal.
The profile tag comes only from the owning gateway response and disappears immediately
on session replacement until that profile's preference is confirmed.

The table above is generated by `npm run shortcuts:generate`; check with
`npm run shortcuts:check`. Runtime help and dock hints use the effective registry,
including disabled/rebound actions; this document records the defaults.

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

`/fork` is the classic alias for `/branch` and switches this pane to the child.
`/fork-message` creates a durable child through `session.fork` and opens a pane with
literal argv `hermes --resume <new-id> -p <owning-profile>`. `/fork-message <message-id>`
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

## Session / branch tree

`/tree` projects Hermes copied-session lineage, **not** OMP’s in-file entry DAG.
The active ancestry is first. Filtered branch traversal uses raw ancestry and
the first visible descendant; missing parents and cyclic legacy links remain
browseable. Selecting or moving the highlight never changes a session. Resume,
delete and the current-session fork action use a confirmation sheet (Enter
cancels by default); there is no tree-triggered undo. Forking another branch
requires resuming it first.

Both `/sessions` and `/tree` support F2 rename with durable readback, Ctrl+S
sort (recent/title/path), Ctrl+L workspace paths, Ctrl+F search, and explicit
Ctrl+Down load-more beyond the first 200 results. Ctrl+Left/Right traverse
previous/next visible branches. Selection stays pinned across sorting and page
loads. Search runs against stored metadata, not just the loaded page. No idle
polling is installed. These sheet-local bindings also live in `actions.ts`.

New forks persist the parent’s durable message row and copied-message count.
Legacy or unstored boundaries are shown as unknown, never inferred from the
child’s newer row IDs. Compression continuation links are labelled separately.

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
- Bindings override app actions only; native composer editing and sheet-local navigation remain owned locally.
- OSC 52 has no acknowledgement; the notice reports the clipboard request, not
  guaranteed terminal acceptance.

Shortcut vocabulary and defaults are adapted from
[oh-my-pi at eb74cf84](https://github.com/can1357/oh-my-pi/blob/eb74cf84d8e16ac9b8c4fa5d7c43037023d016ac/packages/tui/src/app-keybindings.ts),
by Can Bölük / Stencil, MIT licensed.
