# Batch2 H3 — source recheck and independent review

Base remains24b9f0f8c5df5ec6d3d5c10ad9b27c3346bbc925. Prior H3 probe and receipts preserved; no unchanged suite repeated.

##132410 evidence parked

Public issue unchanged2026-10-03T19:36:44Z, no comments, no sanitized error status/body and no effective retry budget. Its CLI `--max-turns1` does not establish `agent.api_max_retries1`. Current agent_init.py1463 clamps explicit api_max_retries to>=1, defaults3; config_defaults.py135 also defaults3. Prior owned restart-cap proof remains valid but cannot establish this report's cause. Required missing evidence: actual provider exception shape and effective retry budget; no solicitation sent.

## Fresh lead check

Maintainer-filed121294 Bedrock already owned121558/121318;121317 Gemini owned121479/121322;121295 Vertex owned121311/123119;121323 Nous owned121331/121339;121299 Codex owned121314;121301 compaction owned121625/121310;121254 OAuth poll owned121260/121262.
Recent132271 pin warning owned132287;132259 plugin registry race owned132367;132214 DeepSeek normalization resolved on current source (known retired aliases only, unknown/current slugs preserved; issue triage cites merged107236/107295).

132284 MoA aggregator rotation has no exact issue-linked PR in current search, but is a larger cross-owner integration gap, not a safe tiny pool rebinding change. auxiliary_client.py8190 explicitly returns the streaming path before the non-streaming recovery ladder; agent_runtime_helpers.py1014 reads the agent pool and1029 rejects mismatch by design. Simply attaching aggregator's pool while agent.provider remainsmoa hits that guard, and relaxing it would violate cross-provider attribution. Existing123413 deliberately leaves streaming consumer retry untouched while changing MoA slot cache resolution;112629 changes virtual MoA fallback identity. A useful future proof needs a real MoA facade, synthetic failed credential identity, underlying-provider pool, and pre/post-first-chunk behavior. No new implementation or tests started on this crowded seam.

Parent redirected this lane to independent review of H1's gateway attachment→pool rotation composition consumer. Review follows below when artifact is ready.

## Independent composition review completed

Reviewed `/workspace/lanes/h1/tests/gateway/test_override_pool_rotation_composition.py` on branch `evidence/batch2-pool-composition`, HEADa39e56cfdc7616da0dcdfd759efcfd4ba3f8e021. No blocking finding for its declared narrow consumer contract.

- Real gateway `_resolve_session_agent_runtime` and `_apply_session_model_override` consume a synthetic on-disk profile configuration and two synthetic pool rows. Both configured-model rows are cooled down; the session override selects a different effective model. No credential/network mock substitutes the attachment or rotation code.
- The attachment-only red log shows both paths obtained a pool and failed at `replacement is not None`, precisely the remaining rotation gap.
- The composed green log shows2passed in0.93s for the same consumer on gateway40b59b2144 plus original-author PR132231 patch cherry-picked as a39e56cfdc. Owner patch author banozz and source2a91d03d81a4962ca6f159fdb06b3feaf5c4223a are retained. Verified composed patch-id5b55d8699c939efa57bdc80ea3c8086978c44983 matches reported original patch identity.
- The consumer asserts final second-seat selection and that the unrelated configured-model cooldown remains effective. This meaningfully composes the two changes rather than restating implementation structure.
- Main `recover_with_credential_pool` already forwards nonblank `agent.model` at agent_runtime_helpers.py1059-1064, consistent with the direct pool call in this test.

Scope limits: direct attached-pool rotation only. It does not execute main-loop credential swap/retry, request transport, fallback ordering, or multi-profile A→B→A transitions. No such claims should accompany delivery. Existing owner tests are not newly reviewed by this narrow signoff. No duplicate test run performed by reviewer; inspected exact supplied red/green logs and source. Test remained untracked at inspection; finalize/commit/exact-head verification belongs to H1/parent.
