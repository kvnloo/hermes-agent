# Revision-bound plan review

`/plan` (or the registered review shortcut) opens a modal sheet. `/plan <task>`
continues to use the existing backend plan-generation command. An ordinary
heading-structured answer is only a Markdown review candidate: its **Continue
(ordinary prompt)** action does not enable, enforce or approve plan mode.

## Authoritative mode

The sheet reads `plan.status`. **Enable plan mode** sends `plan.mode`; the next
turn is planning-only. Policy is enforced at both agent execution boundaries,
without changing tool schemas or the cached system prompt. Only named read-only
file/search/web/skill-reading tools are allowed. Shell, write, delegation, MCP,
unknown tools and wrapper batches are blocked, rather than heuristically
classifying arbitrary commands as safe. Provider-owned ACP execution and
isolated compute do not support this policy and fail closed.

A completed, nonempty planning turn produces a backend plan ID/revision even
without Markdown headings. A new turn revokes the previous decision target;
interrupted, failed and empty generations do not produce approvable plans.
Review state belongs to the existing live session and expires with that session;
it is not a durable plan archive or an OMP entry DAG. Reopen the sheet to refresh
its snapshot after out-of-band changes; the backend always checks current state.

## Review operations

- The existing section contents/jump and body scrolling remain available.
- **Annotate section** adds, replaces or clears a section note. Each mutation
  creates a new revision. Notes are backend-owned and included in refinement.
- **Edit plan** and **Edit in $EDITOR** create a revision with the exact edited
  bytes and clear annotations, since heading indices may have changed. External
  editing uses a private file and the existing opener, never the hidden composer.
  Closed/replaced/session-stale editor results cannot apply.
- **Refine** sends an explicit `plan.decide` intent carrying the reviewed identity.
  The backend dispatches the reviewed text, section notes and feedback through
  normal prompt admission, retaining planning policy for the new turn.
- **Approve exact revision** records approval and leaves plan mode. It does **not**
  auto-execute or synthesize an `Approved — proceed` prompt. The next turn receives
  the exact reviewed bytes as a user-turn context note, not a system-prompt edit.
- Revision/session/transport changes, a busy generation and repeated decisions
  are rejected. Pointer callbacks also retain the revision they rendered.
- The original composer text, caret and attachments stay untouched. Modal input
  ownership also blocks hidden native edit, paste and send events.

The wire models live in `tui_gateway/contracts/plans.py`; generated artifacts are
produced with `scripts/gen_gateway_contracts.py`, never hand-edited. The Tern
presentation follows OMP's section/annotation/external-editor concepts and role
vocabulary; no OMP implementation code was copied.
