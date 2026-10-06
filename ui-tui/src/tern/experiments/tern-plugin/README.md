# Hermes UX Lab — Tern development harness

Development-only Tern plugin for issue #436. It creates the same three-pane
workspace for every A/B/C experiment branch:

```text
┌─────────────────────────────┬────────────────────────┐
│ Hermes --tui --native       │ TSP tests              │
│                             ├────────────────────────┤
│                             │ scratch shell          │
└─────────────────────────────┴────────────────────────┘
```

The plugin does not implement Hermes behavior, intercept TSP, or become a runtime
dependency. It only arranges panes using Tern's documented window layout API.

## Install for development

From a Tern shell:

```bash
tern plugin link /absolute/path/to/hermes-agent/ui-tui/src/tern/experiments/tern-plugin
tern plugin reload
```

Optional type definitions for editing the Luau file:

```bash
tern plugin types /absolute/path/to/hermes-agent/ui-tui/src/tern/experiments/tern-plugin
```

Then focus any pane inside the Hermes checkout and run **Open Hermes UX lab** from
Tern's command palette, or press `Ctrl+Alt+Shift+H`.

The focused pane is only used to discover the checkout root. The lab opens in a
new tab and does not mutate the current layout.

## Why this exists

Every variant must be dogfooded in the same geometry. Without a repeatable
workspace, screenshots and glance-test timings are too easy to bias by pane
placement.

The canonical layout API reference is:
https://docs.stencil.so/tern/guides/layout.html

Credit: Tern/TSP and the layout/plugin APIs are by Stencil Labs.
