---
name: hermes-acp-bridge-clients
description: Use when an app embeds or drives Hermes sessions.
---

# Driving Hermes sessions through `hermes -p <profile> acp`

Reference implementation: kvnloo/z0bridge (`src/hermes/adapter.ts`, `src/hermes/sessiondb.ts`).

## Facts (verified in acp_adapter/gateway_server.py)
- `hermes acp` is a VIEWER of the profile gateway (single execution owner). Prompts from all
  viewers enter one per-session FIFO, so you cannot corrupt a transcript. The connect step
  auto-starts the gateway (idle-exit) if it is not running.
- Probe the installed ACP catalog rather than assuming cross-surface enumeration. Older adapters list only ACP-created sessions; widened gateway-viewer catalogs can list native local/messaging conversations. Until the widened implementation is installed, list other sources from `state.db` read-only (`readonly` + `PRAGMA query_only=ON`).
- ACP-created sessions get ids like `local-<hex>`. Inspect storage provenance rather than assuming a label: current creation can store `source='acp'`, while older canonical sessions can have `source='local'` plus `created_source` and a private policy receipt.
- Gateway `/handoff` is refused, so there is no ownership-handoff verb. A session with
  `ended_at IS NULL` and recent activity is open in another surface. Refuse by default, or
  queue it explicitly.

## Rules
1. On older adapters and ACP-owned conversations, `session/load` cwd MUST equal the policy cwd (`state_meta` key `gateway.local_policy.v1:<id>` → `policy.cwd`): a different cwd can trigger "Move to project". Widened native-session adapters should preserve non-ACP workspace/MCP policy rather than apply import settings; verify that behavior before relying on it. If the installed behavior or policy cwd is unknown, refuse an unsafe import.
2. Leading `/word` text is a Hermes command (`/new`, `/clear`, `/undo` mutate the session).
   Refuse it unless the caller opts in. `/title <t>` is the safe way to name a new session.
3. `session/load` replays history as `session/update` before it responds. Install the protocol update collector before calling load so history is not lost; gate any downstream consumer that wants only new live events until load returns.
4. For read-only protocol probes, answer `session/request_permission` with `{outcome:{outcome:"cancelled"}}` and advertise empty clientCapabilities. When qualifying the actual app client, retain its real negotiated capabilities but deny permissions and writes for the harmless probe; do not confuse this with proof of proposal handling.
5. Cleanup for a throwaway session: close the ACP child (stdin EOF). The owner then ends it
   (`end_reason=acp_disconnect`). Then run `hermes -p P sessions archive --title "<unique title>" --dry-run`
   and check that exactly 1 row lists your id. Only then run `--yes`. Do not rely on an assumed source label for cleanup; inspect the exact row because ACP provenance can be stored as `acp` or canonical `local` across versions.
6. If a turn is interrupted by a child exit or a timeout, its outcome is unknown. Report it and
   never resend it.

## Probing any ACP agent, and external managers (T3 Code)
- Check what a harness exposes before wiring a manager to it. Write a ~30-line stdio JSON-RPC client:
  - send `initialize` `{protocolVersion:1, clientCapabilities:{}}` and read `agentCapabilities.loadSession` / `sessionCapabilities`;
  - then send `session/list {}`, with and without a `cwd`.
  - Run it per profile: `hermes -p <profile> acp` only sees that profile's state.db, and a manager registered with bare `hermes acp` sees the default profile only.
- Automatic Hermes→T3 session sync (scoped token, WS RPC wire format, duplicate-avoiding selection, title-only import limits): see [T3 native session sync](references/t3-native-session-sync.md).
- T3 Code imports "native sessions" from ACP providers (List sessions → Import) and talks to outside agents through its `/mcp` endpoint (read-only, then supervised). On the host, `t3 thread start|send|show|list` drives threads without a sign-in.
- Importing a session that is live in another surface is single-writer only when the harness routes prompts through one owner, as the Hermes gateway does. For a harness that loads the session file in a fresh process (e.g. `omp acp`), test on a throwaway session first. Until then, keep live imports view-only, or fork them. Start new work as manager-owned threads instead of importing.

## Diagnosing misleading ongoing-work status
1. Inspect the affected session before assigning ownership. Use T3 `t3_thread_list` / `t3_thread_read` and join the exact thread to the Hermes transcript, using `state.db` read-only with `PRAGMA query_only=ON` when needed. Distinguish native `delegate_task`, T3 MCP `delegate_task`, and `terminal(background=true)` from their actual calls/results, not the user's shorthand or an assistant's prose. Follow returned `parentThreadId`; do not derive it from an opaque task ID.
2. Verify what is still running. T3-owned children have app-owned task/run records; Hermes-native children have their own lifecycle. For background commands, inspect the recorded process handle/PID and fresh progress receipts. A completed parent turn can coexist with an active renderer, while its subagents really are finished. Do not leave this retrievable distinction as a caveat for the user to resolve.
3. Resolve the consumer's actual provider driver, running revision, and checkout before tracing code. Compare `git worktree list` and candidate HEADs; an older root checkout may predate the adapter used by the app. Source inspection does not identify the loaded runtime, and the current directory is not automatically the repair target.
4. Search existing issues, PRs, and discussions in both projects before recommending a new transport or fix. Use focused title searches to avoid model/harness footers contaminating results, then read relevant bodies and human comments. Follow replacement/landed-as links and verify the successor PR's merge state; closed does not mean merged. Check whether an existing generic background-work model is implemented only for selected providers. Discussions are not in the REST issue search; find them with a `site:github.com/<owner>/<repo>/discussions` web search and read them with web extract. If `gh` stalls, unauthenticated `curl https://api.github.com/search/issues?q=repo:...` works for read-only triage.
5. Compare the working frontend's backend contract with the failing adapter. Inspect `@hermes/shared`'s OpenRPC/generated contract and `tui_gateway` handlers, including session-owned `process.list`, subagent lifecycle, and terminal output/close events where present. Trace those producers into `acp_adapter/gateway_server.py`, consumer ACP normalization, persisted task state, and UI selectors. Missing ACP projection is not a missing backend capability or proof that T3 cannot support it; identify the first boundary that loses already-available state.
6. Trace one stable child/job ID across that boundary, including tool updates and out-of-turn events. A completed delegation call may mean dispatch succeeded rather than children finished. Compare provider-specific extraction hooks, but do not assume another agent's wire shape applies to Hermes. Separate standard negotiated ACP subagent events from custom raw-output formats, and separate progress visibility, terminal-result delivery, and autonomous parent resumption; proposals can solve only one of these.
7. Reuse the consumer's established activity model. Distinguish an active parent, a yielded parent with awaited work, fully settled work, and ambient processes deliberately left running. A dev server should not pin a finished task forever, while a render whose result is still owed should remain visible. Preserve active-child counts and failed/interrupted outcomes; do not mask missing lifecycle data with an indefinite spinner or force synchronous delegation merely to keep a prompt open. In T3 the seam is the provider runtime's optional `awaitBackgroundTasks` plus its pending-background-task projection (`ThreadManagementService` returns `unsupported` when a runtime lacks it; the `t3_background_wait` tool description names the supported providers). Scope a Hermes fix as: Hermes ACP reports background-job start/exit on the launching tool call (opt-in), and T3's Hermes runtime implements `awaitBackgroundTasks` from it. Reject designs that hold the ACP prompt open until children finish; they make dev servers look like unfinished turns.
8. Before claiming a fix, exercise a deterministic lifecycle test: work starts, dispatch returns, parent reply finishes, work remains active, then completes/fails/is cancelled. Verify reconnect restores authoritative state and terminal delivery does not cross sessions, duplicate a wake, or resurrect cancelled work. Treat this as an acceptance recipe until actually executed.
9. Report the observed incident, the first losing boundary, existing upstream coverage, and remaining integration scope separately. Label PR test results as author-reported unless independently run; merged code, installed code, and verified behavior are distinct claims.

## T3 features keyed on its own MCP tools (html_render, MCP apps) under Hermes
- Hermes registers editor-supplied MCP servers as `editor_<sanitized name>_<8-hex session tag>` (gateway/session_local_mcp.py) and, unless patched, reports tool calls under that name (`mcp__editor_t3_code_<tag>__html_render`). T3 resolves its own tools by server alias (`t3-code`/`t3_code`/`t3code`), so it treats the call as foreign. The ACP adapter then skips the `takeHtmlRender` recovery, and the inline page row never appears on web, desktop or mobile.
- Diagnose from the persisted item before blaming a client: read `orchestration_v2_projection_turn_items` (read-only) and check `toolName`. `editor_t3_code_<tag>.html_render` means the server-identity bug; `t3-code.html_render` with no `{htmlRender}` in its output means a different problem.
- Prove it on a frozen replay copy (never live state): rewrite only `toolName` to `t3-code.html_render` with the output as one `{type:"text",text:JSON({htmlRender})}` block, restart the replay server, then clear the client's cache. Mobile keeps a client cache, so a force-stop serves the stale item; use `pm clear <test package>` and re-pair.
- Fix at the Hermes boundary: `build_tool_title` in acp_adapter/tools.py maps `mcp__editor_<name>_<8hex>__<tool>` to `mcp__<name>__<tool>`. T3's `T3_MCP_TITLE_CALL` already accepts `mcp__t3_code__<tool>[: preview]`. Leave legacy `editor_<20hex>_<i>` names and the user's own servers unchanged.

## Qualifying native-session catalog changes
- Keep the standalone `SessionManager` ACP-only: it constructs an execution owner. Expand only the gateway viewer catalog, and keep gateway authorization and legacy active-writer refusal authoritative for attach.
- Preserve compression/reset logical IDs, canonical cwd and freshness from the read-only rich catalog. Exclude internal worker/API, hidden, archived and empty transcripts. Tern/Dash are clients, not necessarily storage source labels.
- A non-ACP import must not become a workspace move or an editor-MCP rebind. Existing ACP sessions may retain those editor behaviors; native sessions keep their own policy and receive another gateway subscription.
- For live acceptance, use explicit `HERMES_HOME` and worktree `PYTHONPATH` with `python -m acp_adapter.entry`; the module entry does not accept CLI `-p`. Collect initialize, every session/list page and history updates during an idle session/load, send no prompt, then close stdin. Compare metadata/message count/generation and keep private IDs/titles/transcripts out of public PR bodies.
- Distinguish real multi-viewer idle mounts, authority tests with a started durable admission and an actual live mid-turn test. Do not claim the last from the first two.
- In real-authority tests, derive the adapter catalog home from `Path(authority.db.db_path).parent`; module-bound home helpers can remain pinned to pytest's hermetic home despite a later environment monkeypatch. Flush buffered message counts before opening a separate read-only catalog connection.
- T3 Code lists ACP sessions per project: `session/list` carries `cwd` = the project workspace root, and Hermes matches it exactly. A native session appears only under a T3 project rooted at its stored cwd. Tern sessions usually carry the Tern launch dir. Hermes desktop/mobile (`gui`) sessions carry the profile home (`~/.hermes/profiles/<p>`). Without a project at that path, they stay invisible even when the catalog is correct.
- Before claiming the widened catalog is live, check that the commit is an ancestor of the live checkout's HEAD (`git merge-base --is-ancestor`). Probe with T3's exact provider command from `settings.json` (read-only). A draft PR being pushed does not mean it is installed.
- To test a Hermes candidate locally, build a scratch venv from the launcher's 3.14 Python (`hermes --print-runtime-command`), `uv pip install pytest==9.1.1 pytest-asyncio==1.3.0`, and add a `.pth` that points at the live install's selected `installs/<id>/environments/<gen>/venv/.../site-packages`. Run it from a clone outside `~/.hermes`. `tests/home_io_guard.py` refuses a `git worktree` whose `.git` lives in the real home, and `hermes_bootstrap` refuses a foreign root.
- Keep tests and busy-state simulations off live-service hosts through the owner's fleet runner. Prove new tests fail with exact base modules in a disposable remote snapshot, then pass on the candidate; never replace the running checkout's files for baseline comparisons.

## Choosing the Hermes embedding surface
- Python in-process: `from run_agent import AIAgent` (`AIAgent(model=...).chat(...)`); Python hosts only.
- TypeScript client of a warm Hermes: `@hermes/shared` (`apps/shared`, typed JSON-RPC to `tui_gateway`, OpenRPC contract in `gateway-contract.openrpc.json`, reconnect/replay). Desktop, the Ink TUI and the Tern frontend use it; it carries tool calls, thinking, approvals, subagents and todos, so use it when an app must render a rich transcript (SessionDB text rows drop agent work).
- `hermes acp` (this skill) for harness-neutral session control; API server `/v1/runs` for simple run/poll.
- There is no native Hermes engine library; Hermes core is Python. A libfx-style API (agent/session/turn, prompt stored before accept, messageId idempotency, steer, NDJSON stream with cursor resume) belongs in the bridge as an interface over these surfaces, with per-harness adapters.

## One-shot `hermes chat` dispatch from an app server
For fire-and-forget jobs (e.g. an app review that should produce a reply plus files), shelling out is simpler than ACP:
1. Command: `hermes -p <profile> chat --query-file <prompt.md> [--image <file>] --in <app root> -Q`. Always pass `-p`; the default profile may have a broken provider. Always pass `--in`: Hermes restores its own cwd, so the subprocess `cwd=` is ignored and relative paths in the prompt (`reviews/<id>/m2.png`) fail in the agent's file and vision tools, sending it on filesystem-wide searches. Also state the absolute root in the prompt. Keep the argv template in app config with `{prompt}`/`{image}`/`{root}` placeholders and drop the `--image` pair when there is no image.
2. Spawn with `start_new_session=True`, `stdin=DEVNULL`, a timeout, from a worker thread; Hermes' process-group cleanup otherwise kills the server that spawned it.
3. Parse output: `-Q` still echoes tool diffs as lines starting with `│` — drop them so only the answer is stored. The `session_id: <id>` trailer can arrive on stderr, so search stdout+stderr for it and save it for resume links.
4. Persist job state (`queued/working/done/failed`, cmd, started/finished, exit, reply, session) in a per-job JSON written atomically (tmp + replace), and collect produced files by naming convention (e.g. `v*.png`).
5. Run the server and any long dispatch as `systemd-run --user --unit <name> --working-directory=... --setenv=PATH="$PATH" ...`, not as terminal background jobs; agent-session restarts kill their children and orphan jobs mid-run.
6. Guard each job with an `O_CREAT|O_EXCL` lock file before spawning, so one job never gets two agent runs. On Python 3.14 `http.server.ThreadingHTTPServer` can bind with SO_REUSEPORT, so a leftover second server silently shares the port, requests alternate between processes and both dispatch. Set `ThreadingHTTPServer.allow_reuse_port = False` so a duplicate fails to bind, and `pgrep -af serve.py` before relaunching.
7. After a restart, a job stuck at `working` with no live process is orphaned: confirm with `pgrep`, then re-dispatch it once by importing the server module in a fresh unit (`python3 -c "import serve; serve.dispatch('<id>')"`) rather than resubmitting through the UI (which creates a new version).
8. If chat fails with `invalid_params`, bisect the flags with a trivial prompt (bare query, then `+--image`, then each extra flag); an unaccepted flag value (a custom `--source` was one) produces this error, not the image or prompt.

## Subscription-backed app bridge qualification
- Keep provider OAuth on its existing owner host; expose the app transport through an owned loopback bridge/SSH forward rather than copying provider credentials to the client machine. Keep app bridge tokens distinct from provider authentication.
- Qualify the actual app ACP path, not an adjacent live helper or native provider CLI. Verify initialize, new session, one bounded prompt, final text and canonical billing/model receipt before claiming subscription execution works.
- Collect `agent_message_chunk` updates before submitting the prompt and return their accumulated text to the app caller; ACP `prompt()` completion carries stop metadata, not the final answer text. Keep commentary separate from speech and preserve indeterminate outcomes without automatic resend.
- Preserve the production bridge/proxy and public mounts during candidate qualification; stage a separately named service and disposable library, and leave promotion to the designated owner.

For the ordered deployment and verification recipe, see [remote subscription bridges](references/remote-subscription-bridges.md).

## Fast worker surfaces under a Hermes-owned session
When a faster harness (e.g. libfx/fx) drives a realtime surface (canvas, quick chat, generated UI), Hermes stays the session of record: give the worker a tool that asks/delegates to the owning Hermes session through the bridge (commentary silent, final speakable), and write a compact receipt (summary, artifacts, decisions) back as a child/worker record. Never interleave worker turns into a session that is live in another surface; queue or attach as a child.

## Pitfalls
- In a T3 ACP session, `Edit approval denied by ACP client` comes from T3's per-thread edit gate, not a filesystem fault. Stop, report what is done, and ask the user to approve edits; do not route writes through the terminal. Delegated children run under the same gate, so delegating does not get around it. It can clear on a later run, so probe with one harmless write before resuming.
- When a test server runs in the same Bun process, `Bun.spawnSync` blocks it. Use async `Bun.spawn`.
- Bun.serve's default idleTimeout kills SSE. Set `idleTimeout` and send heartbeats.
- Startup is about 4-5 s (initialize). A first reply takes about 1.5-12 s on clean.
