# Parked downstream readiness: two Hermes candidates and existing CUA stack

Tested Hermes upstream main: `24b9f0f8c5df5ec6d3d5c10ad9b27c3346bbc925`. Fork main at recovery: `be3fd671d7069f7a1515a21fb1c7cd6ffb08a849`. Both candidates are direct children of the tested upstream pin. They remain downstream-only parked work under the restored three-open-PR limit; no upstream posting, review solicitation or merge authority is implied.

## Backup scan completeness

`downstream/20261004-backup-scan-completeness` at `719c812144dc3d6c82626d0704ac67966d8a997f`.

A real directory walk silently ignored an included-subtree scandir I/O error, so manual and pre-update backup consumers reported incomplete archives as complete. The manual negative also logged pruning an older backup; its assertion stopped at false success before an independent retention assertion. The fix propagates scan errors; manual backup returns False and pre-update uses its existing None failure handling, before publication/pruning. Healthy retry still includes the data and performs normal retention.

Two new synthetic filesystem consumer cases fail on exact main before the production edit. Candidate:21 selected PASS (2 new,19 existing). Independent reviewer:the same 2 new consumer cases PASS; overlapping subset, not additional unique coverage. Tests call real walk, ZIP and backup consumers with finite injected scandir EIO. Source/test hashes bind the before/after evidence; negative hash receipt was generated afterward, not a claimed contemporaneous capture. No live filesystem denial or security reproduction.

Codex authored this narrow correction under Kevin's direction. Preserve human backup writer/retention work by kshitijk4poor and JoaoMarcos44. This does not replace ciaomrgrey #124710 or liuhao1024 #127751, select critical-file policy, or qualify external-memory scanning/quick-backup paths.

## External memory provider initialization

`downstream/20261004-memory-provider-init` at `363a1b151eb8eb67f78421f04aee60495392af34`.

Preserves Detail app's (commit author `detail-app[bot]`) existing isolated `d9a22446a31083b406c92b92e096b8bd4b82382a` correction from fork #30, with original authorship and identical patch ID. Its unrelated parent was not imported. Bind memory config before optional built-in import, so import failure does not silently disable the separately configured external provider; retain the original once-per-process diagnostic.

No new code behavior or test cases invented. Candidate:9 existing tests PASS; identical3-test overlay on exact whole main:3 assertion failures; independent reviewer:the same3 PASS. Real AIAgent and MemoryManager run with synthetic import/config/plugin/SDK seams. No actual external service, model turn, retrieval/prefetch, multiplex-warning or installed-broken-environment qualification. Spill-policy choice remains held; dskwe/liuhao1024's competing contracts are untouched.

## Existing CUA stack: already green, not another candidate

Kevin Rajan / kvnloo's observation `8db4b94b555c84bc4b6a8eb37cb59501ca35e8ff` is included in completion `f74a4d5e1ae804249c0d37f576702890949d76f8`. Preserve Cua AI, Inc. MIT notice. Existing draft [kvnloo/cua#111](https://github.com/kvnloo/cua/pull/111) has exact f74 head and targets guarded carrier `b2ae7cb934403f2585c7d3ed23a188b44264f293`, the open [trycua/cua#4316](https://github.com/trycua/cua/pull/4316) head. Neither ordinary main includes the prerequisite architecture. No main port or duplicate refresh is justified.

Fresh exact-f74 focused consumer suite:21 PASS using synthetic MCP and owned loopback HTTP fixtures. Identical6 outcome cases on current stack target:3 consumer errors/3 PASS; the errors are unhandled observation DriverToolError and post-completion HTTPError, not collection failures. Clean no-commit composition produced the same relevant Python source/tests as f74; no repeated merged matrix or commit. These are bounded consumer results, not live Driver/native GUI acceptance.

Exact f74 hosted CI:14 successful checks,1 skipped installer matrix;4 successful workflow runs. [CI: jev-use](https://github.com/kvnloo/cua/actions/runs/37156367659) and [release metadata](https://github.com/kvnloo/cua/actions/runs/37156367720) are direct receipts. This supersedes historical CI_NOT_RUN for that CUA head only. Remaining gate is owner/reviewer decision and the guarded prerequisite, not a demonstrated code defect.

## Gates and continued work

New Hermes heads require remote verification and CI observation after publication; until then CI is NOT_RUN, not green. Local tests are not whole-PR qualification. Independent reviewers found no blocking issue within the stated scopes. No unapproved installs, paid calls, credentials, upstream posts/bumps, third-party messages, deployments, merges, force pushes or canceled-workflow reruns.

Checkpoint immediate cleanup still lacks an ownership contract. Timeout candidates retain existing evidence; the IMAP port must preserve newer authorization handling and its tail deadline remains an owner policy. Cancellation source was unchanged, so no duplicate122-case matrix was run. Those workers instead independently reviewed the real backup/memory/CUA work.

Preserve123578 HOLD,417 NOT_MET,131689 needs-decision, TUI after-landing and other policy/native/install holds. Do not overlap seven-phase/o8/Ripple/archive/agentcontact owners. Upstream promotion stays parked under the restored THREE-open-PR rule and actual reviewer interest. This packet authorizes neither promotion nor a new numeric task quota.
