# Automatic table charts

The native Tern frontend can append an SVG chart after an eligible table in a **settled assistant answer**. This is a presentation pass after the existing written-artifact projection; it neither reads arbitrary files nor replaces `/visual`'s requested-artifact workflow.

Set **`display.table_charts`** in native Settings (or `hermes config set display.table_charts always`, then reopen the session):

- `off` (default): preserve tables without analysis or model calls.
- `always`: draw a local bar chart, with no model calls.
- `smart`: show the local chart immediately and let Hermes's auxiliary `table_charts` route choose `bar`, `line`, or `none`. **This sends the table to the configured auxiliary provider**. Provider failure or invalid output keeps the local chart.

The original Markdown, answer Copy, stored messages, signed provider sidecars and prompt-cache bytes never change. SVG fences use unresolved terminal semantic palette tokens, so switching theme recolors the chart without sending data to a model again. Native Settings updates apply to the owning live session; other open sessions pick up the saved policy when reopened.

## Conservative eligibility and budgets

Only top-level, pipe-delimited two-column tables outside code fences are supported: a unique nonnumeric category column and a finite decimal numeric column (optionally all percentages), with 2–24 rows. Ambiguous columns, missing cells, duplicate categories, mixed units, grouping commas, exponent notation and zero-only data stay tables. Multi-series, nested, escaped-pipe and numeric-x tables are intentionally not inferred. Source labels are XML-escaped; models return an enum, never SVG or code.

Analysis is capped at 64 KiB per Markdown block, 8 table candidates per block and 8 KiB per table. The per-App derived chart cache has 128 entries. Repeated table source shares a plan. Smart work admits at most **8 requests per runtime session and 1 concurrently**, enforced independently by Hermes. Extra tables use the local fallback. Each admitted provider request has a 5-second deadline and a 64-output-token limit, with no feature retry/fallback chain. An in-flight request is invalidated by session/transport replacement or turning smart policy off; stale completions cannot overwrite a newer frontend policy/session generation. No polling or idle timer is added.

## Verification

`src/__tests__/opt-automatic-table-charts.test.ts` covers the pure analyzer/cache and a connected App's emitted native Markdown nodes, settled-only projection, resume, theme changes, failures, stale results and off-mode model silence. `tests/tui_gateway/test_table_charts.py` exercises real RPC dispatch, profile config, Settings readback, ownership, bounds and backend budgets with an injected planner (no live model calls).
