## What does this PR do?

Same-turn duplicate elimination drops a tool call when its `(name, arguments)` pair already appeared in the same assistant message. That is the right call for accidental repeats. It is wrong for `computer_use` key input, where the repeat is the request: Tab, Tab moves focus twice. Today the second press is removed before dispatch and before the assistant message is stored. Only one Tab reaches the backend, the model's history shows a single press, and only a log warning records the drop.

This PR keeps calls listed in a small `(tool, action)` table, `_ORDER_SIGNIFICANT_ACTIONS`. The table currently holds one entry, `computer_use` with `action=key`. Every other duplicate is still dropped, including a repeated `computer_use` click on the same element. Argument canonicalization (key order, whitespace) is unchanged.

The check also unwraps the tool-search `tool_call` bridge. `computer_use` is in the default `tools.tool_search.defer` list, so on the default config the model reaches it through `tool_call`. A fix keyed only on the direct tool name would leave that path broken, and an earlier version of this change had that gap.

The helper moves out of the `run_agent.py` facade into `agent/tool_dispatch_helpers.py`, next to the other per-tool dispatch tables and the existing bridge unwrap. `AIAgent._deduplicate_tool_calls` becomes a one-line forwarder, like its neighbours, so the call site in `agent/turn_tool_round.py` and the existing tests stay as they are.

## Related Issue

Refs #112639. Supersedes #124008, which I closed while trimming my open drafts. This version adds the `tool_call` bridge path and moves the logic out of the facade.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `agent/tool_dispatch_helpers.py`: `deduplicate_tool_calls()` (moved from `run_agent.py`) plus `_ORDER_SIGNIFICANT_ACTIONS` and `_is_order_significant()`. The bridge is unwrapped with the existing `_peel_bridge_call()`, and only when a duplicate has already been found, so the common path does no extra work.
- `run_agent.py`: `_deduplicate_tool_calls = _forward_static("agent.tool_dispatch_helpers", "deduplicate_tool_calls")`.
- `tests/agent/test_tool_call_dedup_order_significant.py`: one test, run in two variants: the `tool_call` bridge in its advertised `{"calls": [...]}` shape, and the direct tool. It runs a real `AIAgent` turn against `tests/fakes/fake_llm_provider.FakeLLMServer`, with the in-tree no-op `computer_use` backend as the device. The model sends Tab, Tab and two identical clicks in one message. The test checks:
  - the backend records `key, key, click`;
  - each kept press returns its own `verify_fresh_state` verdict, so a kept repeat never reads as confirmed.

## How to Test

1. `scripts/run_tests.sh tests/agent/test_tool_call_dedup_order_significant.py`
2. On `main` (aea969677c) both variants fail with `assert ['key', 'click'] == ['key', 'key', 'click']`. With this change both pass. I ran each side three times and got the same result every run.
3. Negative controls on this branch:
   - With `_ORDER_SIGNIFICANT_ACTIONS = frozenset()`, both variants fail again.
   - Without the bridge unwrap, only the `tool_call` variant fails.
   - With the old `run_agent.py` method restored, both variants fail.
4. Neighbouring files have the same pass/fail results on `main` and on this branch: `tests/agent/test_agent_guardrails.py` (unchanged), `test_tool_batch_segmentation.py`, `test_tool_call_guardrail_runtime.py`, `test_file_mutation_verifier.py`, `test_run_agent.py`, `tests/tools/test_computer_use.py`, `test_computer_use_delivery_ladder.py`, `test_connector_bridge_wiring.py` and `test_tool_search.py`. That is 559 passed and 0 failed on `main`, and 559 plus the 2 new cases on this branch.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. I ran only the targeted files listed above with `scripts/run_tests.sh`, not the full suite.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (x86_64), Python 3.11

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A (no doc references the moved helper)
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A (pure Python, no platform branch)
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

What I did not test:
- a real cua-driver or desktop session (the test uses the in-tree no-op backend);
- how often real models put the same key press twice in one message;
- macOS or Windows.

AI assistance (Claude) was used to port the change to current `main`, write the test, and run the checks.
