# stats-dashboard

`/stats` opens a trace dashboard for this profile's Hermes sessions. The dashboard is
[oh-my-pi](https://github.com/can1357/oh-my-pi)'s own `omp stats` (MIT); this plugin
exports Hermes sessions into the session format omp reads and runs one `omp stats` server
for them. omp users get the same pages they know: Overview, Models, Providers, Costs,
Requests, Errors, Traces, Tools, Projects.

## Commands

| Command | What it does |
|---|---|
| `/stats` | Export sessions that changed, start or reuse the dashboard, open this session's trace. On the CLI, TUI and desktop app it opens a browser; elsewhere (ACP editors, messaging) it replies with the URL. |
| `/stats status` | Show the dashboard URL if it is running. |
| `/stats export` | Export only; no server. `--all-profiles` exports every profile's `state.db`. |
| `/stats stop` | Stop the dashboard this plugin started (by its recorded pid). |

Enable it with `hermes plugins enable stats-dashboard`. It needs `omp` on `PATH`
(`bun install -g @oh-my-pi/pi-coding-agent`); without it `/stats` replies with that hint.

Settings (`plugins.entries.stats-dashboard.settings`): `port` (default `3858`; omp's own
dashboard uses 3847), `host` (default `127.0.0.1`), `omp` (executable path),
`all_profiles` (bool), `max_chars` (per text block, default 20000), `open_browser` (bool).

## Where things live

Everything is under `$HERMES_HOME/omp-stats/`: the exported sessions
(`agent/sessions/<project>/<time>_<session id>.jsonl`, subagents one level deeper inside
their parent's directory), the export watermark (`agent/hermes-export-state.json`),
omp's `stats.db`, `server.json`/`server.log` and omp's native addon cache. The omp child
gets `PI_CONFIG_DIR`, `PI_CODING_AGENT_DIR` and `PI_NATIVES_DIR` pointing there and no
`XDG_*_HOME`/`OMP_PROFILE`, so it never reads or writes `~/.omp`. `state.db` is opened
read-only.

The first `/stats` exports this session's tree right away and the rest of the history on
a background thread (about 40 s for 5,800 sessions / 340,000 messages). Later runs only
rewrite sessions whose fingerprint changed (about 1–3 s).

## What maps to what

| Hermes (`state.db`) | omp session entry |
|---|---|
| `sessions` row | `session` header (cwd, title); `session_exit` marker at `ended_at` |
| `messages` user / assistant / tool | `message` user / assistant (`toolCall` blocks) / `toolResult`, every timestamp from the row |
| subagent (`source='subagent'` or `model_config._delegate_from`) | nested transcript + `session_init`, shown as a subagent lane |
| `session_model_usage` row | `model_usage` entry (tokens, Hermes's cost) |
| `_compressed_summary` row | `compaction` marker |

Limits, all because Hermes does not record the data:

- Usage is per session and model, not per API call. Requests, tokens and cost on the
  Overview/Models/Costs pages count one request per usage row. Each trace shows that total
  as a zero-width model span at the row's `last_seen`.
- A model span runs from the previous row's timestamp to the assistant row's; there is
  no time-to-first-token or per-call latency.
- Where Hermes recorded a subscription request as $0, omp shows its API-equivalent
  estimate, as it does for its own subscription usage.
- A subagent lane is placed from the child's own activity. Hermes does not link a
  `delegate_task` call to the child session it started.

## Asking the agent about a trace

The plugin also gives the agent two tools and a skill (`stats-dashboard:trace-query`):

- `trace_query` takes the user's question (or a `trace-query.v0` plan), session (`current`,
  `latest`, `last 2`, an id), layers and focus ids. It runs against the same `omp stats` server
  and returns a bounded analysis (a few KB: summary, tools with p50/p95, longest spans, failures,
  idle gaps, per-track cost, every row with its span id) plus `render.handle`.
- Passing that handle as `html` to an `html_render`/`html_preview` tool shows an interactive
  board of trace cards over the same data slice; a `pre_tool_call` hook swaps the handle for
  the document, so the model never carries the HTML.
- On the board the user clicks spans, tool rows or error groups, brushes the timeline, pins,
  and presses **Copy for chat**. The reference (`@trace:v0;s=<session>;k=…;ids=…;r=<ms>-<ms>`)
  pasted into the next message is expanded before the model reads it; `trace_resolve`
  expands one on request.

The board is built from a template at `$HERMES_HOME/omp-stats/stats-inline.html` (setting
`inline_template` overrides the path). Without it `trace_query` still answers and says how to
build the template.
