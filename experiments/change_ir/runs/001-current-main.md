# Run 001 — refresh two stale-change fixtures against current main

Date: 2026-10-06
Target: `kvnloo/hermes-agent@33b8776db688b6926bdd35feb87a841abfc5ccea`

## Method

This run uses direct source inspection at the target SHA. The repository code-search index returned incomplete zero-hit results, so those results were discarded rather than treated as absence evidence.

Anchor matches are evidence only. The classifications below were made after reading the current implementation around each matched/missing anchor.

## E1 — NousResearch/hermes-agent#105624

### OP-observe-sibling-addressed-user

**Current classification: `still_needed`**

Current architecture is present:

- `_telegram_observe_unmentioned_group_messages` at `plugins/platforms/telegram/adapter.py:5762`
- `_telegram_exclusive_bot_mentions` at `:5772`
- `_should_observe_unmentioned_group_message` at `:6148`
- `_should_process_message` at `:6381`

The feature-specific marker `observe_sibling_bot_messages` is absent from current main.

Interpretation: the operation still has a live architectural landing surface, but the concrete sibling-observation realization has not landed.

### OP-mirror-final-response

**Current classification: `still_needed` + `moved` realization surface**

Current main contains the refactored send helper `_send_chunks` at `plugins/platforms/telegram/adapter.py:3707`.

The proposed marker `mirror_final_responses_to_profiles` is absent from both the Telegram adapter and `gateway/config_loader.py`.

Interpretation: the durable operation survives, but a refresh must realize it through the newer send/finalization architecture rather than replaying the original patch shape. This matches the semantic reconciliation recorded on PR #105624.

### OP-preserve-bot-sender-observation

**Current classification: `already_on_main` / invariant to preserve**

`_bot_sender_suppressed` exists at `plugins/platforms/telegram/adapter.py:6138` and participates in both observation and dispatch flow.

Interpretation: this is not code #105624 should own. It is current-main behavior the rematerialized change must preserve.

## E2 — NousResearch/hermes-agent#31157

### OP-mcp-refresh-teardown-guard

Historical baseline (2026-07-13): `still_needed`

**Current classification: `already_on_main` + `moved`**

The old anchor disappeared from `tools/mcp_tool.py` because MCP health behavior was extracted to `tools/mcp_tool_health.py`.

Current main's `_refresh_tools` at `tools/mcp_tool_health.py:132` now:

1. acquires the refresh and RPC locks;
2. snapshots `session = self.session`;
3. returns safely when the session is `None`;
4. explicitly documents the teardown race and #109824.

This was independently implemented after #31157:

- reporter/diagnosis: @patrykkopycinski in #109824;
- fix commit `1c82c22e`: @salch-cred, co-authored by @Tranquil-Flow, @ildunari, @andrexibiza, and @ly6751;
- behavior-contract tests commit `37eb4d0b`: @austinpickett, co-authored by @ly6751 and @salch-cred.

The original #31157 author @sege66 still deserves provenance for identifying/proposing the same guard earlier.

This is the clearest success case for Change IR so far: an old PR-level state of "salvageable fix" should now collapse to "already implemented elsewhere; preserve credit, do not duplicate."

### OP-repo-wide-gitnexus-instruction

Historical baseline (2026-07-13): `invalidated`

**Current classification: `invalidated` / absent**

Neither `GitNexus` nor the rejected contributor-local path `/Users/kihwangkim/dev/hermes-agent` appears in current `AGENTS.md`.

Interpretation: this operation should not be rematerialized.

### OP-gws-generated-credentials

Historical baseline (2026-07-13): `needs_decision`

**Current classification: `needs_decision`**

Current `google_api.py` has `_gws_env()` at line 89 and passes `TOKEN_PATH` directly as `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE`.

Current tests verify persisted `type == "authorized_user"`, but the test file contains no direct `_gws_env` invocation and no permissions/`chmod` assertion.

Interpretation: the implementation shape has changed enough that replaying the old PR change would be unsafe. The durable desired behavior needs to be re-derived against the current credentials path before deciding whether anything remains to implement.

## Experiment findings

1. **A PR is too coarse a lifetime unit.** #31157 contains at least three operations that are now `already_on_main`, `invalidated`, and `needs_decision` respectively.
2. **Missing old symbols are ambiguous.** `_refresh_tools` vanished from `mcp_tool.py`, but the behavior moved and was fixed elsewhere. A grep-only stale detector would misclassify it.
3. **Feature markers and architectural anchors are different things.** For #105624 the landing surfaces are present while the feature-specific markers are absent.
4. **Current state cannot live as mutable truth inside the fixture.** Run 001 immediately made the old #31157 `still_needed` state stale. Fixtures now store timestamped historical baselines; run receipts store new classifications.
5. **Provenance must be a graph.** The MCP operation now has an earlier proposal (#31157), later production diagnosis (#109824), later implementation, and later behavior-contract tests by different contributors. Flattening that to “fixed by commit X” loses useful credit and history.

## Next

- Add E3 from Vox Lockin #78207 and classify the 17 stale-base PRs.
- Add explicit `implementation_markers` separate from architectural anchors.
- Add relation edges so Run 001 can encode `#31157 OP-mcp-refresh-teardown-guard --superseded_by--> 1c82c22e`.
- Measure review compression: old diff/context size vs generated refresh packet size.
