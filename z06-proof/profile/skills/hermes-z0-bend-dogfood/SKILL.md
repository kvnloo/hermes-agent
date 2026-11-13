---
name: hermes-z0-bend-dogfood
description: Use when running, planning or debugging Hermes+z0 stack.
---

# Hermes + Jev + Bend + z0intelligence dogfood stack

## Daily surface
- `dogfood doctor [--full] [--json]` (script at `~/.hermes/profiles/clean/bin/dogfood`): Jev, Bend, Bend GPU, z0, AODL, Hermes<->z0, receipts. `--full` runs a real PASS, deliberate FAIL, replay and stale replay (about 70 s). SKIP is never shown as GREEN.
- `dogfood up` restarts the user unit `z0intelligence.service` then runs doctor.
- Evidence lives in `/tmp/hermes-z0-bend-dogfood` (symlink to `/mnt/zer0models/dogfood/hermes-z0-bend`; root disk is too small).

## Wiring
- bend-native installed from `kvnloo/bend-native --ref <SHA>` into the clean profile. Settings: executable `/home/kvn/.bend/bin/bend`, `stack_mode: shadow`, `stack_opportunities: true`, `stack_service_port: 11501`.
- z0 service: port 11501, loopback. Drop-in `~/.config/systemd/user/z0intelligence.service.d/dogfood.conf` points it at `/mnt/zer0models/z0-wt/z0intelligence` with venv `/mnt/zer0models/z0-wt/venv-claude-code` (has `aodl_contract` aodl-canon-1). `/readyz` must show `aodl_admission_ready: true`. Remove the drop-in to revert.
- Jev routing lives in `~/.hermes/profiles/clean/jev/state.json` (`routing: on`). Preserve it; never duplicate Jev calls through z0.
- `hermes chat -t ...,bend` is needed for the `bend_verify` tool; without the toolset the model falls back to the CLI.

## Shared harness integration diagnosis

Trace installation → runtime source/interpreter → transport inventory → native registration → actual dispatched call separately for every requested harness. A working backend import or service readiness response does not prove that a model can discover or invoke the feature. Inspect the configured shared stack before asking the user to reinstall or concluding from PATH alone that a dependency is absent.

Reproduce the user's missing capability at the consumer boundary first: inspect MCP `tools/list`, native plugin registration and the actual endpoint status in the same runtime/profile the harness uses. Check restricted/shared-only inventories, cached transport shims and package import visibility before changing backend code. Verify real native retrieval rather than an exact-path shortcut or mocked binding, because those controls can pass without exercising the index. Keep installed, exposed, dispatched and behaviorally consumed as separate report states.

Verify native tools against the effective platform tool selection, not merely the plugin registry or an unrestricted catalog. Enable the toolset in the requested profile, read back its effective CLI configuration, and dispatch the registered handler against the live shared service; registration alone can pass while platform filtering hides the tool. After transport or plugin changes, state which existing sessions must restart to reload their inventories. Distinguish capability availability from whether a model actually chooses it.

Use references/harness-capability-diagnostics.md for the diagnostic sequence and evidence table. Do not present an unverified implementation or deployment plan as a working repair.

## Salvage and cross-check lane (z0intelligence)
- Master's ruleset "main" enforces `required_linear_history` with no bypass, so `gh pr merge --merge` is refused and merges land as squash. A verified head SHA is then not reachable from master; prove the merged content by tree comparison (`git diff --name-only <verified-head> origin/master` equals exactly the other merged PR's files) instead of ancestry.
- Claude Code sessions on this host live under `CLAUDE_CONFIG_DIR=~/.claude-home/projects`, not `~/.claude/projects`; most lines carry `gitBranch: HEAD`, so attribute by the line's `cwd`. Codex rollouts: first line `session_meta` (cwd, git), last `token_count` line holds cumulative `total_token_usage`.
- The OMP bridge spawns `python3` unless `Z0INT_PYTHON` is set; system python3 has no `fff`, so `z0_file_search` silently returns `fff_status: absent`. `~/.z0int/bin/python` wraps the venv that has it.
- Verdict harness pattern that caught #141 and cleared #151: run the unchanged entry points (`route_worker`, `dispatch_worker`, `free_fanout.run`) through the real `OpenAICompatTransport` with `urllib.request.urlopen` redirected to a loopback stub and a non-loopback `socket.connect` guard; compare head, prior head and master on one grid. For spawn claims, load the real `.ts` extension in bun with a logging `python3` shim first on PATH.
- `test_agentweb_bridge_overload.py::test_host_overload_is_503_before_handler_execution` is flaky on master (BrokenPipe, a few % of runs); interleave runs on both trees before blaming a PR. Setting `TMPDIR` under the scratch symlink makes `test_hermes_adapter` and `test_z0int_onboard::test_ensure_layout` fail on master too.
- Receipt check reads `github.event.pull_request.body` from the event payload, so the `synchronize` run after a push always sees the old `head_revision` and fails; the `edited` run after the body update can be skipped or race. After push + body edit, confirm the latest receipt run is green; if not, re-save the body (append a newline) to fire a fresh `edited` run.
- Re-verdict after a master merge: `git diff <accepted-head> <new-head>` byte-equal to `git diff <old-merge-base> origin/master` proves the new head adds nothing but master.
- `core-unit.yml` path-filters `pull_request`; docs-only PRs (#125, #148) never start core-unit/offline-suite, so those checks can't be required until the filter is dropped (#160).
- `hermes curator archive` refuses bundled skills unless `curator.prune_builtins` is on; only agent-created skills archive.

## Pitfalls
- Bend GPU needs `CUDA_HOME=/opt/cuda` (default `/usr/local/cuda` does not exist, so it silently builds CPU-only with no `.gpu` file). Always run with `--gpu 1GB` (an explicit size fails loudly with no usable GPU; the default reserves the whole shared card). Check free VRAM first (skip under 2 GiB).
- Lean's bundled `clang` lacks `stdbool.h`. Put the Lean bin dir LAST on PATH so the system clang builds Bend native/GPU binaries.
- `z0int onboard --auto` needs `pip` in the z0 venv for its editable evolution-lab install.
- The z0 venv imports `z0int` from `PYTHONPATH=<checkout>/src`; set it explicitly.
- Jev failure test: set a fake `TYPESAFE_API_KEY` in a child env only, never in the profile.
- Shadow evidence: `~/.hermes/profiles/clean/plugin-data/bend/z0/events.jsonl` (bend receipt id and hashes labelled `scoped_proof_evidence_not_task_success`). A Bend PASS never mints verified_success or AODL admission.

## Status asks: report what runs locally
The owner judges z0intelligence by what works on this host and what THIS agent can use, not by GitHub state (GitHub is issue tracking only). Lead every status report with local evidence:
1. `dogfood doctor` (and `--full` when time allows) plus `/readyz` on the z0 service.
2. Clusters: check `kubectl config get-contexts` first. The default context can be an older kind cluster while k3s runs separately; reach k3s with `KUBECONFIG=~/.kube/k3s.yaml kubectl ...` (the root kubeconfig needs sudo). Report pods, readiness-probe failures and restart counts per cluster, and say which cluster actually hosts z0 services.
3. Intended setup lives in the dotfiles checkout the symlinks point to (`readlink -f ~/.zshrc`), often on an unmerged remote branch: search `git for-each-ref refs/remotes` trees for k3s/sandbox files and compare to the running version before calling it managed.
4. Self-check: list which z0 tools are loaded in this session (tool_search) and make real calls with timings. A plugin installed elsewhere that this session cannot call counts as not working for the owner.
5. Only then cite GitHub PRs/issues as pointers for what is missing.

## Strategy asks: pick the smallest compounding change
When Kevin asks for direction, a goal, "what next" or "10x" on z0intelligence, he wants results, not a plan of plans. He has said repeatedly that earlier agents over-engineered and never pushed to an outcome.
1. Anchor on the north star: fewer frontier tokens/time per *verified* task at equal quality. Name ONE scoreboard number and say whether real data computes it today. If nothing does, the first change is the smallest join over existing data (Hermes `state.db` sessions + GitHub merged PRs) that produces it. Don't build a new pipeline for it.
2. Gather evidence before you recommend anything. Do a cheap baseline pass yourself: ROADMAP, the open issue and PR lists, recent `origin/master` history, the dirty or ahead/behind state of the live checkout, `/readyz`, and token totals from `state.db`. Then fan out read-only lanes as described in references/project-recon-fanout.md (it covers lane topics, cheap-model delegation override and restore, and DB privacy rules).
3. Rank candidates by leverage per line changed. Good candidates are: merge or close green stale PRs; wire an existing library into a live consumer; prune per-turn prompt overhead; close a learning loop with Hermes built-ins (skills, curator, memory). Treat RFCs, receipts, docs-only PRs, new daemons, new memory stores and new frameworks as cut candidates unless a measured bottleneck requires them.
4. Deliver one goal plus 3–5 concrete changes. For each change give the file or command, the expected before/after on the scoreboard, and the first action you can take now. Stop there. Don't append research agendas, and don't put shadow or canary ceremony on changes that are cheap to revert.

## Integration planning and risk-tiered rollout

Before implementing an integration gap, recover the existing plan from the relevant repositories: paginate open and closed issues/PRs, read candidate bodies and comments, follow dependency links, and compare merged/head SHAs with the actual executing checkout. Check candidate CI and deployment state separately; a missing live feature may need an existing PR or deployment, not duplicate implementation. Preserve dirty runtime work and follow the owning repository's promotion rules.

Classify the optimization before choosing its gate. For deterministic retrieval, prioritize exact-source correctness, scope isolation, index freshness, no-hit completeness, bounded-result coverage and fallback parity; do not require learned-model quality trials merely to expose a lookup tool. Still test truncation and ranking against representative discovery tasks, because deterministic search can omit relevant evidence. For learned selection, compression or model substitution, require matched task-level quality/non-inferiority evaluations, abstention/escalation controls and end-to-end cost/latency before promotion. Use shadow mode where it can compare real competing decisions without affecting execution, not as a ceremonial gate for every tool.

Report the rollout as existing dependency → verified merge candidate → deployment → native consumer canary → promotion/rollback gate. Keep availability, automatic selection and measured workflow benefit separate; neither a green unit suite nor a search receipt establishes all three. Compare a candidate's exact head with corrective branches mentioned in reviews before proposing a merge; green checks on the original head do not include fixes elsewhere. Reconcile source lineage and receipt integrity before rebuilding missing live bindings, and retain behavioral FAIL/DISCARD even when native model-input delivery succeeded. Verify merged target ancestry and actual installed source separately, because promotion branches and default branches can carry different implementations.

## FFF, shadow and memory tracing

Follow references/fff-shadow-memory-traces.md when proving repository retrieval through shadow or unified-memory surfaces. Verify the exact executing checkout and separate observation persistence, semantic admission, decision selection, dispatch and model consumption; a flag or receipt cannot prove the next layer.

## Native decision capture boundaries
- Hydrate exact persisted Hermes user rows with SQLite `mode=ro`; never instantiate a native state manager merely to read, because initialization may migrate or mutate the source.
- Bind an explicit dedicated home, session and complete user/project/repo/task scope in the trusted host. Match row ID, message UID and the SHA-256 of exact submitted text; never infer authority from a pre-LLM text envelope or the latest matching row.
- Reject compressed, inactive, internal/display-tagged, assistant and tool rows even when their content resembles a declaration. Normalize only an explicit bounded whole-object grammar and pass typed native attestations to existing canonical claim admission.
- Preserve synthetic controller attribution in the bounded normalized value and pass an explicit correction target; never mint historical human statements from synthetic inputs.
- Prove corrections, scoped projection and restart idempotence through the real EventLog rather than mocked writers. Resolve TMPDIR to its physical path when baseline tests compare canonical paths.
- For a stale-cache control over real admitted events, byte-copy the canonical event prefix into an owned fixture and use `EventLog.rebuild_index()` for derived metadata. Prime the existing recipe cache before appending the byte-preserved correction; assert the corrected claim and changed snapshot even when the recipe reports a hit. Never alter the live canonical ledger.
- Separate persisted native input, serialized model request, actual completion and executed artifact. Literal unavailable-tool markup in a completion is response-level evidence, not a dispatched action or verified implementation.
- Distinguish outcome completeness from positive task acceptance and externally supplied tier metadata from the actual owner publisher. After demonstrating inconsistent gold-label acceptance with public synthetic inputs, run the unchanged append/join producer in an explicitly owned receipt home and feed its persisted rows to the unchanged consumer. If owner normalization emits negative tiers correctly, report a trusted-input/consumer boundary rather than claiming live canonical corruption; keep cross-revision UNIT checks separate from manifest-qualified canaries.

## Existing-trace latency attribution
- Freeze a bounded cohort and deduplicate by native provider response identities before counting; keep request witnesses, aborted responses and no-usage attempts distinct. Join receipt revisions by trace/native identity rather than treating each update as a call.
- Reconcile uncached input, cache read/write and output categories using the producer's schema. Reasoning is often a subset of output. Treat planner receipt latency as planner latency unless an exact model-call join establishes otherwise.
- Sum model-call duration only within a named observed window; union overlapping tool intervals. A dispatch-to-result tool span can include human approval. `duration - ttft` is a post-first-token remainder, not independently measured reasoning or decode time.
- Trace requested effort through compatibility, fallback and final-payload seams on pinned source bytes. Without a captured final request, record effective effort as unknown; neither low configuration nor large reasoning output establishes provider compliance or an adapter defect.
- Require matched model/provider, wire effort, stable prompt-prefix/tool-schema hashes and cache warmness before diagnosing regression. Historical cache percentages from different workloads are descriptive only.
- Preserve latency success conditioning and missing-outcome coverage. Including fast 429/other failures can lower a median without a code or provider improvement; report attempted and successful denominators separately. A historical verified flag derived from HTTP status or tool-call presence is not task gold: exercise the unchanged producer with clearly labelled invalid-argument and empty-response UNIT controls, network blocked, before interpreting it as efficacy. Keep corrected grading revisions separate from stale nested scores and never rerun protected graders merely to reconcile a report.
- Use existing decision/shadow interfaces for no-model eligibility replay on pre-call evidence. Preserve exact observed action arguments, abstain on planning/mutations/unknown scope, and count dangerous false ACT controls. Historical time attached to eligible cases is an addressable upper bound, never measured savings.

## Read-only effectiveness and no-hint continuity
- Freeze append-only source prefixes with exact byte lengths and SHA-256, then preserve raw prefixes as private research artifacts. Later appends must not silently change the reporting cohort; archive snapshots are not a replacement memory backend.
- Join an outcome to an unambiguous trusted user/project/repo/task execution trace. Preserve distinct artifact failures instead of treating the latest outcome as implicit supersession, and attach existing claim projection with original synthetic attribution.
- Render next legal actions through the existing opportunity/compiler policy. For required fact families outside its request vocabulary, use an explicit bounded packet with repo-scoped gating so unscoped matching cannot silently discard required unknowns. Read-only ACT must not become write or execution permission.
- Prove a no-hint consumer from an empty home and native input, first serialized request, actual returned tool evidence and real completion. Generic evaluation policy is not an outcome recap; keep answer digests and source receipt-directory hints out of the first request. Label temporary opt-in registration separately from stock installation.
- Inspect Hermes lazy tool discovery and inner tool_call dispatches. Seeing only tool_search/tool_describe/tool_call schemas does not mean the owned tool was absent or that mutation tools ran.
- Grade outage prose separately from fail-closed data. An exception class covering missing sources does not establish corruption; a recap suggestion can fail the response control even when outcome and permission correctly remain unknown/false.
- Select optimization work from recurring receipt-backed task families before benchmarking a provider. First test the strongest deterministic and existing Jev controls; discard a model arm when structured metadata or exact-source lookup already resolves the task. Preserve a deterministic competing arm and independently freeze the selection oracle for nontrivial menus; observed parent actions are not gold and historical addressable time is not measured paired savings.
- Verify current account-bound entitlement and governed no-paid-spill admission before live offload calls; historical zero-cost fields, successful calls and public rate tables do not establish present authorization. If admission remains unknown, use a decisive offline falsification or a minimal unowned admission repair rather than consuming quota. Report matched correctness and verified outcomes alongside total parent, worker and verifier usage, cost coverage, end-to-end latency and fallback rate; an isolated worker token reduction is not full-workflow savings.
