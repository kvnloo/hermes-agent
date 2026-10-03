# Continued Hermes downstream correctness and integration evidence

2026-10-03. Seven concrete results from the continuing five-lane program, including two integration gaps identified by independent source mapping. Exact commits, trees, parents and new downstream branches are in publication-map.json. These are separate candidates, not one integrated release. All results below are bounded local evidence, not whole-PR or hosted-CI qualification. No upstream posts, merges, installations, deployments, paid model calls, workflow reruns or auth changes occurred.

## Hosted retirement combined with the existing hosted union

`27d28f08b1be3482cd87f7aaebdbddc6b0c73169` integrates published retirement `b45fe7c21c89a8b46911df7c86afc68023025d2f` onto published hosted union `d87b5611fa7ac87e05cacdc1e7024a72a3a08470`, through cherry-pick `9250d92c123a07d28fa83c3af25590987b7df1e1`. Production files match their published donor blobs. This closes the previously unqualified combination; earlier separate branch results did not establish it. Credits: Teknium, David Dudok de Wit and keeltrace's [retirement review](https://github.com/NousResearch/hermes-agent/pull/106742#discussion_r4123365771). Codex composed and validated existing work.

First single-process eight-file run: **151 PASS, 2 FAIL, 1 deselected**. Collection of runtime-backed profile tests imported gateway.run before the retry fixture selected its temporary home; the config reader retained the earlier startup home, so retry tests never reached their first submission. A minimal test-only correction pins that existing startup-home variable to the fixture home and retains failure diagnostics; production config loading is unchanged. Pre-correction two-file selection: **2 FAIL, 2 PASS**; corrected same pair: **4 PASS**. Final single-process eight-file selection: **153 PASS, 1 deselected**. Independent final single-process four-file selection: **14 PASS, 1 deselected**, no blocker. Earlier canonical 14-pass evidence alone did not resolve the combined-process failure and remains historical.

Exact d87 plus identical retirement tests: **2 FAIL** at missing parked state. Final153 comprises the previous143 (139 inherited plus four previously published cases), eight existing hot-serve cases and two previously published retirement cases. **Zero newly authored cases** in this integration. Real control-socket case excluded. No new native listener, unauthorized routing, provider or full daemon claim.

## Voice evidence union

`bacdc1cfba19bacdc21c2e0ed88b60790df26a78` is the exact test-only cherry-pick of published hook consumer `180f79282bd6bafe62f9654c85b68dd1522b0b84` onto published production/conversation composition `00df1a838c40badf77cfb6b6ed11f2e9682bcfd8`. The sole added test file exactly matches the donor; relevant production/test blob compatibility independently verified. Previously these test branches were separate.

Seven-file selection: **56 PASS** (previous54 plus two previously published cases), canonical Desktop typecheck PASS; independent actual-hook/conversation selection **3 PASS**. **Zero new cases or production changes.** Reused matching installed dependencies; no install. Prior component negative controls retain their original scope; this union adds compatibility evidence rather than new defect controls. Finite audio/IPC/fetch seams, not native hardware/network or an integrated Desktop release. Credits: Detail app, Julien Talbot, Teknium and Kevin Rajan; Codex's previously authored tests retain their history.

## Chronos existing-fix integration

`a83b87d635459c5c850115e2ff5c4f3ce259f66e` preserves Finn763's [#126977](https://github.com/NousResearch/hermes-agent/pull/126977) implementation, donor `daf0d026d5cf8d79fcc003784344cda345bceea6`, via author-preserving cherry-pick `d2e2e5576c9ad1683b96292b310ad5ea02b7cc0a` onto pinned main `bd0affe5e5f723579df8902852f5d0c47795f355`. Keeps main's deferred external startup and existing ownership predicate while passing the optional live dispatch gate into compatible providers/Chronos fallback. Credits also unsupportedpastels (Mark S.) for [#126907](https://github.com/NousResearch/hermes-agent/issues/126907) and deferred startup, and vanscodex for the issue work claim.

Real scheduler entry, Chronos and built-in fallback, with finite fake liveness/NAS outcome/jobs/tick body: defer while gateway owns scheduling, start after it stops, stand down after it returns, resume after it stops again. Final cycle-based evidence observes three actual owned probes; ungated control produces three wrong ticks, not merely a timeout. **66 PASS (one new parameter case,65 inherited)**, independent **5 PASS**. Exact whole pinned main plus identical final test overlay: **2 FAIL** (zero gate probes/three wrong ticks). No live NAS, gateway process or auth validation. Alternate snapshot `b12e672e23ce70b33ed9293da1286ada92760bd9` has identical seven relevant blobs; neither whole alternate-main nor latest-main qualification is inferred.

## Discord exact-head repair

`7d5643c1254d3167ed94372cc5d69440360f71ce` repairs exactly two misindented statements on [fork #45](https://github.com/kvnloo/hermes-agent/pull/45), parent `0efdd2946f7e3abe334d8e507e2d9c5243d411e3`. Exact original head fails collection with IndentationError: **zero tests executed**, despite historical PR-body passing claims. No explanation for that discrepancy is inferred. The implementation and tests belong to Detail app; original ledger/offload work is Teknium's. Codex changed indentation only.

Repaired three-file selection: **37 PASS** (9 ledger,8 overflow,20 backfill), independent ledger selection **9 PASS**. Whole original parent `3cf08656a340e3be6ce4117c535eef7a5de12c6a` with unchanged authored nine tests: **5 FAIL,4 PASS**, separately confirming ledger semantics. No tests added. Actual SQLite/adapter/backfill methods with mocked Discord transport; inherited timing-based offload observation is narrow, not a responsiveness guarantee. No live reconnect or whole-main qualification.

## Checkpoint public restore consumer

Test-only `2334804827c21a2bbea714a5f05984e4f10af703`, direct child of [fork #111](https://github.com/kvnloo/hermes-agent/pull/111) `2194c9fb75988e25225496e799f98c3ffa29e533`. Credits Detail app for the reparent/rollback correction and Teknium for checkpoint identity migration.

Actual temporary profile rename interrupted at wrapper cleanup, two post-rename checkpoints, migration, public safe restore of pre-rename and both post-rename file bytes, human-edit preservation, stable retry. **62 PASS (one new,61 existing)**; independent new consumer **1 PASS**. Exact pinned-main migration module substitution: **1 FAIL** at migration prerequisite; later restore assertions are positive evidence only. No production changes, all-fault/concurrency/cross-platform or process-CLI claim.

## Sidebar Show-all consumer

Test-only `6db79c9212cd04ee4f819e81408a8e283135fcdc` preserves wangtaotaotao95's current [#123468](https://github.com/NousResearch/hermes-agent/pull/123468) head `c9c5d0da7635a3d0f623a22afd3f94fde578b1eb`; [fork #170](https://github.com/kvnloo/hermes-agent/pull/170) is stale. The author already fixed hydration: Codex adds one actual ChatSidebar/store/Show-all consumer instead of reimplementing it. Existing owner tests manually supplied the correct filter and did not exercise that wiring.

Three files **98 PASS (one new,97 existing)**, canonical typecheck/lint/format PASS; independent final committed consumer **1 PASS**. Exact old-carrier index.tsx under current unchanged helpers/test: **1 FAIL**, deleted row reappears after hydration. Restored **1 PASS**. Fetch boundary mocked; no native backend. Existing installed resolved-package entries match, but one workspace dependency declaration differs; compatible reuse is disclosed, not an exact-lock-install claim. A source-ambiguous overlapping review run was discarded; final independent run used frozen restored commit.

## Execution completion after uncertain recovery

Test-only `effd8c19730b8c4672a596988935d94685e8e38d` on Detail app's [fork #60](https://github.com/kvnloo/hermes-agent/pull/60) `736d43cec1f21d291d6c579c8d47a662d9be0f4e`. Real temporary SQLite APIs plus finite identity instrumentation: recorded-NULL uncertainty preserves execution, independently fences delivery, original owner completes durably, delivery drain emits nothing, terminal overwrite rejected.

**6 PASS (one new,five existing), one deselected** to avoid a real-process probe; independent consumer **1 PASS**. Pinned-main execution/delivery module control **1 FAIL** at premature execution fencing. Main already preserves unreadable current fingerprints and includes newer drift/stale-claim behavior: this is exact-candidate evidence, not current-main integration or a newly fixed unreadable branch. No production changes or real procfs/process/network test.

## Meta-check and remaining boundaries

Read-only owner/source checks prevented redundant work on forks182/190/232/268/194/218: corresponding mechanisms were adopted upstream. Fork216 has an open successor, not proof of a main fix. Current hosted #121813 already implements the requested Bot receipt-task retirement and real recovery-created task tests; no duplicate patch was made. Fork107 already implements its old QA gate; fork29 has substantial existing consumer evidence. Fork65's remaining native older-backend acceptance gate lacks a qualified environment; no installs or synthetic substitute claimed. PluginDoctor54 admits no current repeating production consumer and was not promoted as a high-consequence gap.

#123578 remains **owner-contract HOLD**. Its [cited comment](https://github.com/NousResearch/hermes-agent/pull/123578#issuecomment-5861217260) explicitly identifies itself as **automated review, not maintainer direction or rejection**. The conflicting reconnect contract needs owner disposition; no probe/policy change was performed. #417 remains acceptance HOLD (NOT_MET_AS_WORDED); Library authorization remains blocked. #131689 remains needs-decision, and separate Bend/z0 career/integration work stays with its other owner. Current picker261a2b qualifies reviewed e03ca28 against pinnedbd0, not oldfork400 or unspecified current main.

Independent reviews and exact workflow audits found no blocking publication issue or reviewed-prefix push/create trigger. New refs only, no tags or existing-ref replacement. Separate post-publication ref/tree/Actions/check/status verification treats empty CI as **NOT_RUN**, never PASS. Raw logs and complete bindings remain local; this receipt contains sanitized public provenance and bounded outcomes. The queue review is not a claim that every repository task is exhausted.
