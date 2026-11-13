---
name: tern-action-shortcut-receipts
description: "Use when adding Hermes Tern keyboard shortcuts."
---

# Tern action shortcut receipts

- Confirm task refs with `git ls-remote --heads`. A narrow shared fetch refspec plus pruning can delete a valid explicit ref; fetch it with `git -c fetch.prune=false fetch origin refs/heads/<base>:refs/remotes/origin/<base>` rather than modifying shared remote configuration.
- Preserve routing: splash → Ctrl+C special (Settings owns cancellation) → overlay owner → modal guard → completion → app actions → composer. Compute action context after handlers that can mutate the draft.
- Keep composer editing separate. Suppress unbound Alt-letter printable text at the app boundary without disabling Alt+B/F/D word editing.
- Preserve the Ctrl+O guard: empty composer, no overlay/completion. Its legacy handler also accepted Shift; do not silently replace Ctrl+Shift+O with globally hidden active/error/approval state.
- Reasoning show/hide uses the existing local command and canonical config readback when there is no frontend visibility state. Gateway display words are profile settings, not session-only effort. Serialize read→toggle and discard reads from replaced sessions.
- Drive tests through a connected real Tern SDK Session handshake and parsed bytes, not private methods. CSI-u modifier values: Alt 3, Alt+Shift 4, Ctrl 5, Ctrl+Shift 6. Assert gateway calls and emitted native View trees.
- Disable HERMES_TUI_SPLASH in ordinary shortcut fixtures and restore it afterward: the first chord otherwise correctly dismisses the splash instead of firing. Test splash priority separately without assuming its animation ends in one event-loop turn.
- Wait for completion's native omp.autocomplete role, not an unsplit command label: fuzzy highlighting splits labels into spans. Verify Escape and Shift+Tab completion precedence.
- Enumerate all boolean contexts and modifier combinations for collisions, including permissive legacy matching. Inject an overlapping duplicate to prove rejection; allow mutually exclusive predicates.
- Treat OSC52 as a request rather than acknowledged clipboard success; assert exact emitted payload and preserved draft/caret.
- Nonmodal approval prompts still need generation ownership: share the existing overlay identity map with dock roots, queue approvals FIFO, and capture the painted approval in native Send handlers so a stale composer callback cannot deny a successor. Keep empty-draft choice keys in actions.ts; printable text belongs to the composer.
- A response frame's `ServerRequest.respond()` is void and its channel swallows transport failures. For deny-and-steer, preserve ordinary choice responses but await the existing `request.answer` proxy for the exact server-request id before normal unqueued `prompt.submit`; reject expired acknowledgements and retain drafts. Do not mistake the approval-queue request_id for the server-request id or introduce a second approval store.
- Keep Tern-only local command names distinct from existing gateway reports (for example, prompt-history search must not replace `/history`). Check the complete report/command suite, not only the new shortcut fixture.
- Fork into another process with a durable-only, profile-scoped gateway intent: reuse branch persistence without building/adopting a child agent, deep-copy histories before row-id/flush-marker writes, retain tool pairs/reasoning/API sidecars/system prompt, and return the stored id plus owning profile. `get_session().tool_names` is resolved JSON text; decode before `update_session_tool_names` to avoid double encoding. Test exact target prefixes and byte-for-byte parent immutability.
- Keep pane spawning behind a fakeable argv launcher; test both the frontend's literal resume/profile argv and the adapter's `tern split @focused right -- ...` argv with `shell: false`. Module-factory mocks retain call history across `restoreAllMocks`; reset the fake per fixture. Preserve a durable fork id/resume hint if split fails, and never use a real user's daemon to exercise launch tests.
- Run typecheck, complete Vitest suite, ESLint, and bundle. Report baseline warnings separately. Prove a regression test fails with dispatch disabled, restore, and rerun all gates. Absent remote checks are not green CI.
- Check Tern host keymap documentation, keep alternate chords/text commands, and never mutate host bindings merely to make tests pass. Connected SDK coverage does not certify every native-window/preset combination.
- For optional Vim editing, inspect the installed SDK's InputProps: `mode` disables native editing and `anchor` is UTF-16. Emit mode only while opted in, place modal dispatch after overlay/completion but before app Escape, reject stale native edits, and keep IME parsed-Unicode coverage distinct from real OS candidate-window evidence. Use existing profile-owned `display.vim_mode` through `config.get full`, not a new frontend preference store or idle poll.
