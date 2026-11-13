---
name: harness-speed-ab
description: "Use when benchmarking agent harnesses on one model."
---

# Harness speed A/B (same model)

Use for Hermes, fx, pi or omp (or similar) speed and quality comparisons: interleaved arms, verified tasks, one variable per contrast. Reference implementation: kvnloo/z0evals `studies/harness-speed-v1` (PR #110). Copy `harness/` and `tasks/` to `~/.cache/harness-speed-v1/` on the target host. Install `libfx@0.0.14` in `fx/` next to `fx_run.ts`, then run the session script under `harness/env.sh`. env.sh sets PATH for that process only, never globally.

## Procedure

1. Write and commit `protocol.md` before any counted run. Store smoke runs under `data/smoke`, and log any amendment in the protocol before the session it affects.
2. Keep the model, provider and effort fixed on every arm. Each harness runs at a minimal baseline (plugins, skills, rules and MCP off; file and shell tools only). Change one config per contrast.
3. Latency: run 1 warm-up block, then at least 32 blocks. Shuffle the arms inside each block with a fixed seed. The parent process times from spawn to the first text event, and to exit. Use a verifiable prompt (`17 * 23` -> `391`).
4. Warm: one long-lived process per arm. pi and omp use `--mode rpc`, sending `new_session` and then `prompt`, and the request ends at `agent_end`. fx uses `fx_run.ts --serve`.
5. Tasks: copy each task repo fresh and run `git init`. The verifier restores the visible tests and adds the hidden ones. Before running, check that every original repo fails and every reference solution passes.
6. Analysis: report the median with a bootstrap CI, a CI on the difference in medians, and paired CIs (pairing by block or by task and rep). Use Wilson intervals for pass rates. Compare arms only within the same session.

## Pitfalls

- pi extension boolean flags (`--rlm`) swallow the next argv. Put `--` before the prompt, or pi exits silently with no turn.
- pi `-p` exits about 3.1 s after its answer, and `--offline` does not fix it. Report TTFT and total separately.
- omp cold startup costs about 2.3 s before the request. omp json `message_end` carries `usage.cost` (list price) and the provider's `ttft`. Its `input` excludes `cacheRead`.
- On rpc streams, omp emits `extension_ui_request` events every few seconds. A per-event timeout never fires, so use an overall deadline.
- Hermes `invalid_params` on `chat -q` without `-t` means a configured MCP server's toolset (e.g. an expired-OAuth `linear`) was forwarded into `session.create`, and the gateway rejects unknown toolsets. Bisect with `-t file,<toolset>`. Fix with `hermes config set mcp_servers.<name>.enabled false`. `--format stream-json` gives `text`, `tool_use` and `result.tokens` events, where input includes cached tokens.
- Hermes on gpt models runs a shell for arithmetic because `agent.execution_guidance: auto` injects `<mandatory_tool_use>` ("Arithmetic -> use terminal"). Set it to `false` (and `agent.tool_use_enforcement: false`) to remove that tool round trip.
- Never benchmark Hermes with `--safe-mode`. It spawns a cold managed worker, adding about 8 s per request before the first model call. Use a minimal profile instead.
- To build a minimal Hermes profile, run `hermes profile create <name> --no-skills --no-alias`; OAuth comes from root `auth.json`, so copy nothing. Then apply Blank Slate (`hermes_cli/setup_quick.py`) with `HERMES_HOME` set for that process only. See `harness/hermes_speed_profile.py`. Also set `terminal.cwd: .`, or the terminal runs in `$HOME`. And set `approvals.single_query_mode: approve`, because `--yolo` does not reach a multiplexed secondary profile and `python3 -c` gets blocked.
- Hermes warm path: `hermes -p <profile> acp` (ACP over stdio). Send `initialize` once, then `session/new` and `session/prompt` per request. `inputTokens` excludes `cachedReadTokens`.
- Stage-time Hermes from `~/.hermes/[profiles/<p>/]logs/agent.log`, which has ms stamps (`ws accepted`, `inbound message`, `codex_stream_request`, `API call #N ... latency`). `-v` is refused with `--format stream-json`.
- fx CLI sign-in: the file is `~/.fx/chatgpt-auth.json` `{version:1, access_token, refresh_token, expires_at_ms, account_id}` (0600, dir 0700). Then run `fx provider codex` and set effort in `~/.fx/settings.json` `effort`. `--context-limit skill_catalog_bytes=0` is a global flag and goes before `ask`; it cuts input from 15k to 4.3k. `fx ask --json` emits one final object (no streaming, no cache split), so read TTFT from raw-text mode.
- The libfx native backend has no built-in tools, so the fx arm's tools and prompt are host-authored. Say so. The turn `usage` equals the sum of per-call `model.end` hook usage. Audit it with `--audit-usage`.
- Check sign-ins with `fx status --json` and the keys in `~/.pi/agent/auth.json`. Compare token hashes, never values, across `~/.codex/auth.json`, `~/.hermes/auth.json` and pi. Copied OAuth shares one refresh-token family, and the first client that refreshes rotates it for the others. A separate `fx login codex` or `pi /login` per harness avoids that.
- The terminal tool caps a call at about 420 s, sleep included. Poll long background runs (started with `setsid nohup` on the host) with sleeps of 300 s or less.
- Hermes sends `reasoning_effort: none` to free nemotron lanes (NIM, Kilo). The model then answers tool tasks without calling the tool and invents the result. That makes a large capability gap against fx that is config, not harness. Before calling a quality difference, diff the wire request between arms with a loopback logging proxy (system chars, message roles, tool count and schema bytes, reasoning_effort, max_tokens). Drop the field and rerun.
- Use a loopback proxy as each arm's `base_url` to log wire TTFT and decode tok/s apart from harness overhead. Hermes treats a loopback URL as possibly Ollama and sends one `/api/show` probe first, so subtract it. Also set `fallback_providers: []` on the Hermes arm, so a 429 shows as a failure instead of a silent model switch.
- Shared free-tier orgs (Groq TPD, Kilo promo caps) are often already drained by other consumers. Check remaining quota before the run, and stop a lane on its first daily/promo 429 instead of retrying.
- For frontier comparisons, cite the public Hermes Index (portal.nousresearch.com/bench). It covers Hermes Bench, TerminalBench 4, TerminalBench Science and SkillsBench, run inside Hermes with per-task cost. Don't present it as our own measurement; say plainly when paid models haven't been run on our eval set.
- Check `burn-pace --json` before running Claude arms. Keep second-model arms small, at 1 rep.
