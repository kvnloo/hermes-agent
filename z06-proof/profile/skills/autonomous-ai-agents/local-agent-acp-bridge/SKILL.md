---
name: local-agent-acp-bridge
description: Use when a web app must use local agents via ACP.
---

# Local agents in a web app over ACP

Lets a browser app use the coding agents already logged in on the user's machine (Claude Code,
Codex/ChatGPT, Gemini CLI, Hermes, OpenCode) through the Agent Client Protocol, so the user's
existing subscription does the work and no API key enters the app. The app is the ACP client; a
small local bridge spawns the agent on stdio and relays JSON-RPC over a WebSocket.

## Procedure

1. Inventory agents and logins: `command -v claude codex gemini hermes opencode`,
   `codex login status`, `claude auth status`, `hermes acp --help`, `gemini --help | grep acp`.
2. Reuse before writing: recover the owner's earlier feature requests and inspect related app checkouts for existing client/bridge code and real-agent acceptance records before proposing a new bridge. Separate transport reuse from private app copy/data; agree ownership and public disclosure scope before extraction. Historical local acceptance proves neither current deployment nor hosted-origin compatibility. The official TypeScript SDK `@agentclientprotocol/sdk` (`ClientSideConnection`, `PROTOCOL_VERSION`) does the protocol; the bridge only moves frames. Check the ACP client list for a maintained stdio-to-WebSocket bridge too.
3. Launch commands (pin versions, take them from the `@agentclientprotocol` npm scope):
   - Claude Code: `npx -y @agentclientprotocol/claude-agent-acp@<ver>`
   - Codex: `npx -y @agentclientprotocol/codex-acp@<ver>` (accepts `-c key=value` overrides)
   - Hermes: `hermes acp`; Gemini: `gemini --acp`; OpenCode: `opencode acp`
   Allow per-agent overrides in a user config file (`args`, `append`, `env`, custom `cmd`). Label API-key providers separately from an already-authenticated local agent/subscription. Make connection and model probes explicit user actions; do not trigger inference on page load or model selection. Distinguish list-price estimates, reported usage and subscription billing rather than presenting an estimate as actual spend.
4. Bridge security, all required:
   - listen on 127.0.0.1 only; random token per launch written to a 0600 config file
   - WebSocket auth via subprotocol `app.<token>` (browsers cannot set headers on WS); HTTP via
     bearer; for the app's own pages a `/open?token=` link that sets an HttpOnly SameSite=Strict
     cookie and redirects, so the token never sits in page JS
   - reject non-loopback `Host` (DNS rebinding) and Origins outside an allowlist
   - spawn agents with cwd = project root; file endpoints resolve paths and refuse escapes;
     serve absolute media paths only if a project file references them; support HTTP Range for video
   - treat cwd and prompt restrictions as context, not a sandbox: the agent's native tools may retain broader filesystem/shell access; disclose that boundary and use real isolation when required
   - Bound incomplete stdout lines, inbound socket buffers and aggregate fragmented WebSocket messages separately; an individual frame limit does not bound accumulated memory. Apply matching backpressure or close the connection on overflow.
   - Give connection setup and each JSON-RPC request a deadline. Clear request timers on success, error and disconnect; reject calls before connection without retaining pending state. Cancel owned prompt work on timeout rather than merely hiding its response.
   - Terminate the owned agent process group on disconnect or bridge shutdown, using bounded graceful termination then force; do not release the busy slot until cleanup completes, because killing only the direct child can leave tools running. Remove only bridge-created session directories, never an operator-supplied cwd. Verify descendant shutdown with a real spawned-child fixture.
   - Sanitize stderr and JSON-RPC errors before forwarding them; side-channel separation alone does not remove credentials. Default to withholding arbitrary diagnostics, with phase-specific safe messages and an explicit allowlist for useful details.
5. Client: wrap the WebSocket as the SDK stream (one JSON message per frame), advertise
   only capabilities the app actually implements (disable filesystem and terminal capabilities for read-only clients), implement `requestPermission` as a visible choice in the UI with offered-option validation and exactly one reply; clear pending permission UI on disconnect,
   stream `agent_message_chunk`, `tool_call`, `tool_call_update` into the chat, and reload the
   document when the agent writes the open project file.
6. Make agent edits reviewable: instruct the agent to write a proposal (list of app commands)
   rather than rewriting the document, and apply it through the app's undo system.
7. Verify with a real end-to-end script, not mocks: bridge refuses no token, wrong token, foreign
   Origin, rebinding Host (send a raw `Host` header with `http.get`; `fetch` cannot override it),
   path escape and token-less WS; then for each agent initialize + new session + a one-word prompt,
   and, for editor clients, one real file edit checked on disk. For read-only clients, verify denied write capabilities instead. Exercise attended permission allow/deny and cancellation/disconnect cleanup. Test pairing from the actual HTTPS app origin, not only localhost: mixed-content and local-network policy can differ. Do not claim hosted support from a local-only run or bypass browser security to obtain a pass. Record exact app revision, agent version, selected advertised model, origin and timings.

## Pitfalls

- Adapters moved from `@zed-industries/*` to `@agentclientprotocol/*`; the old packages stopped
  updating and fail on current models with "requires a newer version" or "model not supported".
  Check `npm view <pkg> time` and use the maintained scope.
- An adapter reads the CLI's own config (e.g. `~/.codex/config.toml` model). If that model is
  rejected for the login type, override it in the bridge config instead of editing the user's CLI config.
- First connect through `npx` can take 20-30 s (package fetch); show a "starting" state.
- A parent directory's `package.json` with `"type":"module"` turns `.js` into ESM; write the
  bridge and any functions as ESM so they run the same everywhere.
- `command -v` is not availability: an npm-installed CLI can exist but be broken (skipped
  postinstall). Mark an agent available only if an optional `probe` command (e.g. `--version`)
  exits 0, and cache the result per bridge launch.
- Never auto-answer `session/request_permission` (with `cancelled` or a deny) for an attended chat. Agents ask for permission before every file edit (Hermes in ACP mode does this even when its own approvals are off), so a silent auto-cancel makes every edit fail with "approval denied by ACP client" while the user never sees a prompt. Surface the request in the UI with allow-once / allow-session / deny, or make an explicit per-session auto-allow the user turned on; auto-deny only for unattended jobs, and say so in the turn.
- Never echo arbitrary agent error text to a remote client (it can contain credentials), but do not collapse all JSON-RPC errors into one generic message either. Map an allowlist of known-safe `error.data.details` patterns (e.g. `Could not restore model <id>`) to specific messages, and include the protocol phase (initialize, session/load, session/prompt), so the user can tell a lost login from a crash.
- Keep safe diagnostics outside protocol traffic; never forward raw stderr simply because it uses a side channel. If raw output is withheld, do not tell users it was saved in local logs unless the implementation actually persists it.
- Add deterministic regressions for timeout/pending-map cleanup, disconnected requests and sentinel-secret non-disclosure before broader acceptance. Exercise buffer overflow, fragmented-message accumulation and stderr withholding against the real bridge process; client unit tests and syntax checks do not prove bridge hardening or real-agent acceptance.
