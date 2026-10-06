# Experiment: OMP TUI as a Hermes frontend

Companion branch: `kvnloo/oh-my-pi:exp/hermes-backend`.

## Finding

The first dogfood slice requires **no Hermes backend changes**.

Hermes main already exposes the required boundary through `tui_gateway.entry`:

- newline-delimited JSON-RPC transport
- `session.create`
- `prompt.submit`
- `session.interrupt`
- `message.start/delta/complete`
- `tool.start/complete`
- `subagent.*`
- `session.info`

The OMP experiment therefore consumes this existing contract directly. This
branch stays isolated so any gateway gaps discovered by dogfooding can be fixed
here without contaminating the existing Hermes-first Tern experiment
(`feat/tern-tsp-surface`, PR #431 / RFC #432).

## Boundary

```text
OMP frontend + TSP/Tern
        ↓
Hermes tui_gateway
        ↓
Hermes runtime
```

OMP owns presentation only. Hermes remains authoritative for session state,
model execution, tools, subagents, and safety decisions.

Unsupported consequential server requests are never auto-approved by the OMP
spike.

## Provenance

- OMP TUI/TSP: Can Bölük / Stencil Labs.
- Existing Hermes-first Tern integration and conformance work: PR #431 / RFC #432.
- Inverted frontend/backend experiment proposed by Kevin Rajan.
