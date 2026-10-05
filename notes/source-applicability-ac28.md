# Source-only applicability: 803091 → ac28abc

Compared exact upstream objects `80309111b480937264881f29f66fa87a3af72356` → `ac28abc96ce83f22f6b831f80d9007e2aba81f21`. Fifteen files changed. No tests, rebase, production edits, or installed dependencies. Historical qualification bases remain unchanged.

## Actual changes

- Auxiliary Codex parsing now preserves completion status/phase and issuer-sensitive normalization; parser moves to `agent/auxiliary_codex_response.py` and returns finish_reason. `_CodexCompletionsAdapter` now passes issuer metadata into that parser. Shared `agent/codex_responses_adapter.py` also changes. New completion-status tests are upstream evidence, not executed here.
- CLI bare-model mapping/list assignments gain refusal/coercion handling and an extracted `config_section_guard.py`. Config defaults/examples are edited.
- Gateway `_drain_active_agents` moves api_server work from the chat deadline to the cron deadline. Stop logging includes API runs. Restart/config-loader/CLI docstrings and defaults documentation describe the new floor. Existing cron-drain test file gains API coverage.

## Delivered-artifact implications

`f6792ca7` directly overlaps `agent/auxiliary_client.py`; whole-file equivalence no longer holds. Nine upstream functions involved in its direct same-provider retry/progress path remain AST-identical: preparation, sync/async retry, sync/async progress wrappers, stream requirement, sync/async relay and response validation. Its own patch concerns those retry functions, while new upstream edits concern the Codex adapter. This is disjoint function-level drift, not a verified current-head composition: Codex adapter result semantics and bindings are shared inputs. Preserve the historical715 two-test/11-check qualification; a current composition, if selected, must retain the new parser contract and independently qualify actual affected behavior. No conflict or regression was reproduced here.

Gateway `run.py`, `run_turn_runner.py`, the entire `platforms` tree, `gateway/config.py`, cron tree, `hermes_state.py`, pyproject and uv.lock retain exact object identities. This supports only scoped direct-source continuity for turn/platform/cron artifacts; shutdown/restart/config-loading behavior changed, so no blanket gateway/core readiness claim follows. The held systemd artifact also overlaps `hermes_cli/gateway.py` (this delta is a docstring there); its existing decision gate is unchanged.

The machine-readable overlap map checks each available artifact history against the delta. Besides f679 and systemd-HOLD, no direct changed-path overlap was found in comparable histories. Owner-only histories without an available common ancestor are explicitly unassessed; absence of direct overlap does not prove dependency closure. All object IDs and function comparison results are in `identities.json`; exact source patch is `delta.patch`.

## Next choices

1. If current integration readiness is wanted for f679, preserve owner ancestry and reconcile the new Codex parser/issuer contract before any narrowly selected test; do not call the old artifact source-equivalent wholesale.
2. For gateway changes, select only a concrete shutdown/API drain consumer gap if one exists; upstream already supplied API drain tests. No reason to repeat unchanged platform/turn tests.
3. Retain systemd and other policy holds. No new implementation follows from this audit alone.
