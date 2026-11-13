---
name: tern-serve-real-turn-isolation
description: "Use when bug-bashing real turns in isolated Tern serve."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [tern, e2e, isolation, real-turns]
    related_skills: [hermes-tern-parity-orchestration]
---

# Real-turn Tern serve isolation

## When to Use

Use for pixel-rendered exploratory Hermes Tern testing with real provider turns in a disposable home.

- Launch one owned `tern serve` with private `TERN_CONFIG_DIR`, `TERN_DAEMON_SOCKET`, control endpoint and scratch directories. Never connect to the ambient user daemon.
- When the agent itself runs inside a live Tern pane, never qualify on the owner's window. Don't force-reinstall the plugin that pane is running, don't open a `--resume $HERMES_SESSION_ID` preview of the same session, and don't run `tern focus` or `tern ctl key/shot` against the ambient window. Focus moves to a preview that can stall waiting on frame credit, the owner's Ctrl+C goes to that preview, and the working pane looks frozen and can't be stopped. Install into a disposable home and drive an owned `tern serve`, or a specific block with `tern send <block>`.
- On a memory-constrained shared host, wrap the complete heavy batch in the agreed host-wide `flock --close --wait <bounded-seconds> … nice -n 10 timeout …`; check available RAM again after admission. Separate lock-queue time from test execution. `--close` prevents an owned detached daemon from inheriting the lock after its test exits. Never bypass a busy lock or kill a peer's holder.
- Keep a phone-sized pixel viewport (for example 390×844 and 412×915) distinct from measured terminal-column coverage and physical mobile-client acceptance. Assert both the indicator and Stop geometry inside the visible dock, inspect PNGs, and keep the optional image orb independent from the native working-row spinner.
- Treat its interactive shell as untrusted environment setup: shell initialization can replace HOME/HERMES_HOME and source user runtime choices. Launch Hermes through `env -i` with explicit private HOME, HERMES_HOME, PATH, PYTHONPATH, HERMES_PYTHON_SRC_ROOT, HERMES_TERN and owned Tern variables. Verify the resulting private SQLite session/model before the first prompt. Preserve required Tern host identity variables only from the owned shell when qualifying native external editing.
- Copy only the authorized disposable config and symlink .env; never copy auth.json. Use only explicitly authorized free models. Disable delegation or independently pin its model to free to prevent paid incidental work.
- Do not certify Ctrl chords through Tern Linux ctl: the repository adapter documents Ctrl→Meta translation. Use native buttons and supported non-Ctrl keys, or qualify shortcuts in an appropriate native driver.
- `type` containing newlines can submit each line as separate input. For bounded turn tests use a one-line prompt and wait for native draft admission before Enter. Do not mistake the resulting queue for an app defect.
- Measure actual pane cols/rows from `state` after resize. Retain same-request 80×28, 100×30 and 160×44 PNGs and native tree geometry. Inspect pixels, not just emitted node presence.
- Read back model/tool outcomes and message order from the owned SQLite store. A successful control command does not prove prompt admission, approval, turn completion or file mutation.
- Account for lazy session persistence: `session.create` can paint a ready composer before `state.db` or its session row exists. Verify the live model chip before the first prompt, then wait for canonical messages before checking the exact private launch-home database and model. Do not hunt unrelated profile databases or create a row merely to satisfy the harness.
- Check that the authorized dotenv source actually supplies the free provider before a real-turn run. A profile can have Anthropic credentials but no OpenRouter key; never infer provider availability from a model chip. Use the existing authorized free-test source read-only, never copy auth or print secrets.
- Separate unexecuted external-editor, native-window, persistent Always grants, timer expiry and active-child inspector branches from passing headless real-turn observations.
- Qualify native answer Copy through a transparent read-only stdout observer on the real frontend (including a resumed real session if needed). Compare OSC52 with all assistant text blocks in that turn joined by blank lines, including narration but excluding tools/reasoning; distinguish this wire check from unverified headless host clipboard contents.
- Disable `platforms.api_server` in a disposable home whose `.env` links the owner's key file: that file enables the API server, and a second gateway on port 8642 exits as a startup conflict, which the pane shows only as `gateway draining/absent: not ready`.
- Reuse one prepared disposable `HERMES_HOME` across runs: the first `hermes tern` in a new data root installs an isolated runtime and can take minutes before the composer appears.
- Plugin tools sit behind Tool Search: real models reach them through `tool_call`, and a fake-model flow must call them the same way; a direct call returns `Tool '<name>' does not exist`.
- `tern ctl tree` shows classes and text, not `data-role`s: wait on visible text the feature always draws (a hint line, a placeholder), and dump the full tree to a file rather than a truncated log.
- In frontend unit tests, `fakeTern().send()` does not reach node handlers: find the node in the drawn region and call its `handlers.onClick/onActivate` directly.
- Check profile-setting changes against an already-live session as well as their saved readback. A confirmed generic Settings write need not update the session's cached runtime preference; compare the dedicated slash command before attributing continued output to the renderer.
