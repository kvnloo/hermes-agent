# Execution checkpoint v2 — 2026-10-05

This metadata-only packet preserves the downstream delivery ledger across workspace replacement. It is a dated checkpoint, not a claim that the standing six lanes stopped.

- [Hermes deliveries](manifests/hermes.json) and [OMP deliveries](manifests/omp.json): exact published commit URLs, classification, local validation and limits, remote verification, and separate hosted-CI status.
- [Non-fix evidence](manifests/nonfix-evidence.json), [hold index](manifests/holds.json), and [CUA next choices](manifests/cua-next-choices.json): unresolved contracts, resource gates and non-reproductions remain explicit.
- [Overlap map](notes/overlap-map.md): combined review heads and overlapping histories; branches are not unique fixes.
- [Hermes cap decision](notes/hermes-cap-decision.md): read-only inventory reports 17 open entries, including four drafts; the standing three-PR constraint remains. No states were changed.
- [Agent/consumer shortlist](notes/consumer-review-shortlist.md), [Desktop/CLI shortlist](notes/desktop-cli-shortlist.md), and [OMP owner follow-ups](notes/omp-owner-followups.md): review choices, not authorization to contact anyone or publish upstream.
- [Roster](manifests/roster.json) and [snapshot metadata](snapshot.json) are explicitly point-in-time.

Receipt paths retained inside records refer to the original /workspace/receipts directory and are provenance locators, not bundled files. Exact downstream GitHub commit URLs remain independently accessible. The packet preserves summarized results; it does not pretend to bundle every raw log.

All author-owned integrations retain original author histories or explicit cherry-pick provenance. Owner-branch follow-ups marked current_main_ready=false must not be described as current-main-qualified. Historical runtime results remain historical when later source-equivalence audits show unchanged relevant inputs. The specifically requested ACP c6641dab exact-final runtime rerun passed one selected test; its earlier receipt was retained.

No secrets, runtime configuration, dependency caches, live-provider output or test environments are included. Recorded CI_NOT_RUN remains distinct from local test/check success. CUA e37d is the explicit exception: one unrelated Image API workflow/check was in progress at remote verification (HOSTED_PENDING), not a hosted Python consumer pass.

## Snapshot changes

This 13-file snapshot contains 33 Hermes and 15 OMP branch records, plus one separately recorded CUA test-only consumer delivery; these are not unique-fix counts. The previous approved packet a952aee remains untouched. New Hermes records cover Slack metadata integration, temporary-root doctor tests, owner-only real-shell workdir proof, and overlapping Slack composition.

Main e473 changes only plugin-status entry-point handling. The three recent Slack/doctor records have scoped 19-input source equivalence from715, with historical runtime/check bases unchanged. Terminal 918def remains an older-owner child (current_main_ready=false); unchanged715-to-e473 terminal files do not prove owner-to-main compatibility.

CUA 25f63 has selected consumer dependencies now available in supported scoped Python 3.12; e37d is reviewed and remotely verified. Its real adapter/inert-client proof and approved packaged Fleet ABI initialization are recorded separately from native Driver or service behavior. This resolves only that consumer dependency gate, not griffe/TypeDoc/SDK documentation generation holds. Standing 123578/417/131689 holds remain unchanged. Latest bounded agent intake found ownership/contract gates rather than another justified implementation.
