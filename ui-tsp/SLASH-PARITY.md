# Classic slash parity

The offline completion catalog is generated from
`hermes_cli.commands.COMMAND_REGISTRY`. Regenerate it with:

```sh
python scripts/dump_tern_slash_registry.py
```

`classic-slash-parity.test.ts` checks the generated catalog against the live
Python registry, checks every canonical name and alias, renders every CLI
completion, and exercises gateway dispatch for commands without a native owner.
Use a Python interpreter with the Hermes dependencies, through `HERMES_PYTHON`,
when running Vitest.

## Dispatch audit

All registry entries were checked against Tern's local command table and
`App.slash` routing. This is dispatch/completion coverage, not a live exercise of
every command's external service or destructive action.

| Route | Classic commands | Contract |
| --- | --- | --- |
| Local session lifecycle | new/reset, clear, quit/exit, resume, sessions, branch/fork | Real session RPCs, not transcript-only changes. `/new` accepts a title; `/quit --delete` deletes the stored session; `/sessions list`, `ls`, and `browse` open the picker. |
| Local native controls | model, reasoning, help | Native picker/settings/help; argument forms retain the existing RPC or backend usage path. |
| Native agent/plan views | agents, plan | Bare commands open native views; argument forms go to the canonical backend. |
| Read-only operational views | mcp, ssh | Native reports use literal text, never Markdown escaping or math. These are existing native commands outside the classic registry. |
| Side question | btw | Existing live side-question API. |
| Messaging gateway only | start, topic, pause, approve, deny, sethome, commands, restart, platform | Not advertised as CLI commands. Their registry metadata remains in the generated catalog. |
| Backend dispatch | Every remaining registry command and alias | `slash.exec` resolves the canonical name before built-in dispatch or the classic CLI worker. Backend output uses literal monospace rows. |

Additional divergences corrected during this audit:

- `/fork` now has classic `/branch` semantics and adopts the child in this pane.
  The existing message-targeted new-pane operation is `/fork-message [message-id]`.
  Its Alt+Shift+F action is unchanged.
- `/q` always resolves to `/queue`, including uppercase input. Queue management
  reads and changes the gateway's accepted-prompt envelopes. Prompt forms request
  queued submission rather than an ordinary send.
- `/resume` no longer depends on a separate frontend alias table.
- Exact `/model`, `/jobs`, and `/editor` completions outrank fuzzy matches.

## Rendered regression captures

```sh
env TMPDIR=<owned-scratch> python ui-tsp/e2e/slash_parity.py "$PWD" \
  --receipts <after-directory>
env TMPDIR=<owned-scratch> python ui-tsp/e2e/slash_parity.py "$PWD" \
  --baseline --receipts <before-directory>
```

The baseline build loads the affected renderers and dispatch verbatim from
`724b2aaec5`, without changing the checkout. The same deterministic gateway
fixture runs in isolated `tern serve` at measured 80x28, 100x30, and 160x44.
Each size starts with a populated fixture conversation, then checks that
`/clear` creates an empty session. The runner retains PNGs, native text trees,
RPC calls, geometry, and exact-owned process cleanup records. It makes no model
calls. It does not certify signed-in native-window behavior.

The capture runner must finish before it can report success. A baseline run is
expected red only when at least one assertion actually fails.
