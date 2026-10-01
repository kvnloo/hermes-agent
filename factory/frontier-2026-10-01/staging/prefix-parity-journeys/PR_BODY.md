## What does this PR do?

The C17 prefix-stability suite (`tests/e2e/core/history/test_prefix_stability.py`) covers two entrypoints: the `tui_gateway` stdio server and the `hermes chat -q --resume` oneshot. Three surfaces had no restart journey: the messaging gateway, the api_server and ACP. Each of them builds a fresh agent per process, and that is where #45499 and #104414 lived.

This PR adds one journey per surface, built on the same runner and invariants:

- **One durable session, four process lives.** Each life is a fresh process of the real entrypoint.
- **A parallel tool batch and one compaction** inside the session.
- **The existing checks**: every request is a byte-identical extension of the previous one, except one sanctioned break at the compaction; every reopening replays exactly what `state.db` persisted; rows are written once; usage equals what the provider billed.

How each surface is driven:

| Journey | Process | Turns | Compaction |
|---|---|---|---|
| `messaging_gateway_restarts` | `gateway.run.main` behind the parity suite's recording Telegram adapter | DMs on one private chat | `/compress` sent as a DM |
| `api_server_runs_restarts` | `python -m gateway.run` with only api_server | `POST /v1/runs` addressed by the client's `session_id` | The provider reports context pressure on one turn, so the next turn auto-compacts. There is no manual compaction over HTTP. |
| `acp_restarts` | `hermes acp` | `session/new`, then `session/load` in each new process | ACP's own `/compress` slash command |

**Results on main at this branch's base (`aea969677c`):**

- The messaging gateway and api_server journeys pass.
- The ACP journey fails, and it fails for a real reason. After `/compress`, the first request of a session reloaded in a fresh `hermes acp` misses the whole cached prefix. There are two causes, and each is enough on its own:
  1. **The compacted transcript is never persisted.** `session/load` replays the pre-compaction rows. This is #76215. Two open PRs fix it: #76224 and #88364, which builds on #76224 and also covers #49226.
  2. **The prompt rebuilt at the compaction nests the cached prompt.** `acp_adapter/commands.py` passes `system_message=agent._cached_system_prompt` to `compress_now`. The `compress_now` docstring warns against exactly that call (the #15281 shape). In the recorded run, the system prompt goes from 6,242 to 12,486 chars after `/compress`: the stable tiers, then the whole old prompt, then the volatile tier again. Because this nested prompt is never persisted either, the reload falls back to the stored copy. Neither open PR changes this argument.

**One new invariant, checked on every surface:** the prompt rebuilt at a compaction must never contain the previous prompt. Without it, fixing cause 1 alone would make the ACP journey pass, because the nested prompt would then be persisted and restored byte-for-byte.

**The ACP journey is gated with `known_gate`.** The gate matches only this failure's own message, so the journey stays merge-order safe:

| What has landed | Journey result |
|---|---|
| Neither fix (main today) | XFAIL: the reload request breaks at `messages[0]` |
| Only the cause-2 fix | XFAIL: the reload request breaks at a message (stale transcript; `messages[4]` in the recorded run) |
| Only the cause-1 fix (the in-place compaction of #76224 and #88364, hand-ported) | XFAIL: the nesting assertion fails |
| Both fixes | PASS. Delete the `KNOWN` entry then. |

The last three rows were measured with scratch patches (How to Test, step 3). Both PR heads currently conflict with main, so the cause-1 row uses a hand-port of the in-place compaction they share, not either head. Any other failure fails loudly. The test file explains the mechanism in a comment, so the gate doubles as a repro note.

**How this relates to the #76224 reviews.** The sweeper review on #76224 asked for "a real-SessionDB ACP regression that compacts a seeded session, restores the same session ID, and verifies the compacted live history plus retained inactive/compacted original rows". dosenr wrote such a test. It is posted on #76224 as `tests/acp/test_76215_regression.py`, and #88364 carries `test_compact_survives_process_restart`, which checks both the compacted active transcript and the archived original rows. This journey does not replace either. It never checks that the original rows are kept as inactive/compacted. What it adds is the same reload done through real `hermes acp` processes and checked on the request bytes the provider receives. That is where cause 2 shows up.

## Related Issue

Refs #76215
Refs #76224 and #88364 (open fixes for cause 1; the journey was run against a hand-port of their in-place compaction, not against either head)
Motivated by #104414, #45499 and #120116 (all closed; this guards the class)

## Type of Change

- [x] ✅ Tests (adding or improving test coverage)

## Changes Made

- `tests/e2e/core/history/test_prefix_stability.py`:
  - three new `JOURNEYS`, dispatched by surface;
  - a `PRESSURE:` turn marker for provider-reported context pressure;
  - the compaction is located by the summary it leaves in the next request;
  - the nesting assertion;
  - a `KNOWN` table with `known_gate` around the message-prefix block;
  - usage and integrity are now asserted before the gated block, so a gate cannot mask them.
- `tests/e2e/core/history/_helpers.py`:
  - `SurfaceHome`, which runs the parity drivers with this suite's allowlisted child env;
  - `run_messaging_gateway`, `ApiServerRuns`, `AcpStdio`, `root_session` and `first_summary_request`;
  - `model_payload` now skips `session_meta` rows. The gateway writes one per fresh session, and every production reader filters it out.
- `tests/e2e/core/parity/_drive_gateway.py`: `run_gateway` (one gateway life, several DMs) and `spawn_api_server` are extracted from the existing drivers so the journeys reuse them. A later life's `API_SERVER_*` lines replace the previous life's lines instead of shadowing them. The parity drivers keep their behaviour.
- `tests/e2e/core/parity/_drive_acp.py`: `spawn_acp` (start and `initialize` `hermes acp`) and `close_acp` (stdin EOF, then terminate if it overstays) are extracted from `drive_acp`, which now uses them. `AcpStdio` uses them too.
- `tests/e2e/core/parity/_gateway_child.py`: the recording adapter delivers each DM of `PARITY_GATEWAY_PROMPTS` in order, after the previous one completes. Message ids stay unique across gateway lives.

No production code changes.

## How to Test

1. `scripts/run_tests.sh --include-integration tests/e2e/core/history/test_prefix_stability.py -rxX`
   - Local result: 5 passed and 1 xfailed (`acp_restarts`), 213 s for the file. Main's version of the file (the three existing journeys) took 87 s in a separate run in the same session. The machine was shared and busy (1-minute load average 15.3 and 12.4 at the end of those two runs, on 10 cores), so these times run long.
   - The new journeys took 36 s (messaging gateway), 32 s (api_server) and 31 s (ACP).
2. Negative controls. Each one was applied as a scratch patch that is not part of this PR:
   - Add a per-request timestamp to the system message in `agent/turn_context.py`: 6 of 6 journeys fail, including the three new ones.
   - Force a prompt rebuild on every resume, plus a per-build nonce (the #104414 shape): 6 of 6 journeys fail. In 5 of the 6 the first break is the first request of the second process. For api_server it is the second request of the first process, because api_server re-runs the stored-prompt restore on every turn, not once per process.
3. ACP arms, each applied as a scratch patch to `acp_adapter/commands.py`:
   - stop passing `system_message`;
   - hand-port the in-place compaction of #76224 and #88364 (`compression_in_place = True` instead of detaching `_session_db`);
   - both together.

   The outcomes match the gate table above. Only both together make the journey pass.
4. The neighbouring suites that share the changed helpers have the same pass/fail set on main and on this branch:
   - `tests/e2e/core/parity/test_entrypoint_parity.py` (it uses the refactored `drive_acp`)
   - `tests/e2e/core/history/test_transcript_ledger.py`

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Only the targeted files listed above were run, not the whole suite.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS, kernel 7.2), Python 3.11

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A (module docstring updated)
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A. These are Linux e2e process tests, like the rest of C17.
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

ACP after `/compress`, from the fake provider's recorded requests:

| Requests | System prompt | Compaction summary |
|---|---|---|
| 0–6 | 6,242 chars | no |
| 7–8 (after `/compress`) | 12,486 chars | yes |
| 9–10 (after `session/load` in a fresh process) | 6,242 chars | no (the pre-compaction transcript again) |

**Not tested here:**

- Real provider caches. The fake provider records bytes; it does not bill cache reads.
- Relay `plugins.toml` exporters. The local test venv's nemo-relay is older than this tree, so Relay initialization failed with a warning and these journeys ran with Relay off.
- The serve WebSocket, A2A, the relay connector and `/goal` continuation surfaces.
- Changing the cwd between lives. For these surfaces cwd is an explicit input (`terminal.cwd`, the `session/load` cwd), and `_stored_prompt_matches_runtime` rebuilds the prompt on a cwd change by design.
- That the original rows survive as inactive/compacted after an ACP `/compress`. dosenr's real-SessionDB test in #88364 covers that.

AI assistance: Claude Code (Claude Opus 5.5) wrote the test code in this PR and this description, and ran the tests and scratch-patch experiments described above.
