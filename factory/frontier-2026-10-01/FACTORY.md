# Hermes Experiment Factory: FACTORY.md

Blueprint v1, 2026-10-01. This merges three independent designs (mvp-first, scale-first, evidence-first) and applies the selected staging set of 14 branches. The architecture comes from mvp-first. scale-first adds throughput and reuse; evidence-first adds the evidence chain and the promotion gates. The selected staging set and the binding constraints settle every conflict between them.

Base for everything below: upstream main `e496ccc7d7` (2026-10-01 02:55 -0500). The designs used `ffc74885c5` and `aeff051a18`. "(UNVERIFIED)" marks a claim nobody checked.

---

## 0. What was checked for this synthesis (read-only)

Nothing was written to any repo, branch, issue, Linear item or provider. The checks were: `gh` reads, `git ls-remote`, the scratch bare mirror, and one no-op sandbox probe.

**Blocker found**

- `refs/heads/staging` exists on kvnloo/hermes-agent.
  - Tip: `28790e597c`, "Merge pull request #9 from kvnloo/fix/per-1271-…", 2026-09-10.
  - It has diverged from upstream main: 8 ahead, 19,840 behind.
  - Git cannot create `refs/heads/staging/<id>` while `refs/heads/staging` exists (directory/file ref conflict). So no selected branch can be pushed under its selected name. See OD-0. The factory never deletes or renames that branch.

**Ledger and namespaces**

- `claude/ledger` is at `1b823a659f` ("factory: v2 rebuilds of 12 staged branches; drop fork-34 (external owner)"). That is past both `c139c7762c` and `713333c155`, which the designs cite.
- `factory/` on the ledger holds only `frontier-2026-10-01/`, `promotion-readiness-2026-10-01/` and `salvage-wave-2026-10-01/`. `factory/xf/` is free.
- The fork has no refs under `frontier/` or `factory/`. `exp/` has only `exp/bend-hermes-verify`.
- These exist: `ready/fork-47-ratelimit-missing-remaining-v2` (`1d31fe5193`), `ready/fork-112-kill-race-notify-attribution` (`83190e3859`), `ready/fork-50-honor-save-over-limit` (`4d0e03c8a1`).

**Workflow push triggers at e496ccc7d7**

| Trigger | Workflows |
|---|---|
| `main` | archive-inputs, ci, deploy-site, docker, js-autofix, nix, skills-index, termux-verify |
| `wine2e/**` | 1 workflow |
| `wine2e-install/**` | 1 workflow |
| tags `v*` | live-providers |

A `staging/*` push fires 0 push workflows on this tree. `--no-follow-tags` is mandatory because of the `v*` tag trigger.

**Carrier heads (gh read-only, all OPEN)**

| PR | Author | Head | Note |
|---|---|---|---|
| #54575 | MaxFreedomPollard | `e28d7c772d` | Includes an upstream-merge commit. Touches `tools/fuzzy_match.py` and `tests/tools/test_file_tools_live.py`, a real-shell LocalEnvironment test with no LLM call. |
| #125376 | Finn763 | `5f3f5896a4` | **Bundles unrelated commits**: a `bot_relay` gateway fix "Closes #95741" (`tools/bot_relay.py` +138, `tui_gateway/methods_bot_relay.py`) and an email-mapping chore, on top of the fail-loud commit `5f3f5896a4`. See F01. |
| #111127 | KoNit-K | `5444b1a2a8` | |
| #107731 | lorencato23 | `069adfb67e` | |
| #122522 | Nagisa-3000 | `f596584b01` | |
| #117895 | fangliquanflq | `54dd30e7d5` | |
| #53806 | ledfoot631 | `6067388d0c` | |

**Hook-carrier candidates (gh search)**

- Candidates: #53806 ledfoot631 `6067388d0c`, #93391 clomp42 `9da3734b8e`, #118847 Baophan00 `222e3e26c3`, #4123 GratefulDave `16c60cd623`, #7150 Tauriqbarron `f823aebeb2`.
- #125881 (pstarkgit, fail-closed policy hooks) is a control point, a different invariant. It is recorded, not an arm.
- The demand report also cites #93389, #125384 and #8643. None of them resolves as a PR.
- The branch's STAGING.md is the authority for F05's five carriers. This list is a candidate resolution (UNVERIFIED against the selection).

**Code facts re-verified on e496ccc7d7**

- `evals/postmortem/forensics/logcalls.py` `_LINE` requires `cache=(\d+)/(\d+)`. `agent/turn_usage.py` emits `cache=` only when `cache_read_tokens` is truthy.
- `MINIMUM_CONTEXT_LENGTH = 64_000` (`agent/model_metadata.py:272`).
- `evals/postmortem/run.py:47` uses `env.setdefault("HERMES_HOME", …)`.
- `scripts/run_tests.sh` uses `HERMES_PYTHON` only when `__HERMES_ACTIVATED` is unset and that interpreter imports pytest (lines 47-56). If `$HOME/.hermes/pytest_live_guard.py` exists, it adds `$HOME/.hermes` to `EXTRA_PYTHONPATH` (lines 86-87).
- `agent/anthropic_adapter.py` contains no `clear_tool_uses` or `context_management`, so Anthropic context editing is absent. NousResearch#526 (teknium1, "Anthropic Context Editing API Integration") is open.
- `website/docs/developer-guide/observer-hooks.md` contains 0 occurrences of `first_chunk_at`, `context_length` or `moa_references`. `agent/chat_completion_helpers.py` sets `first_chunk_at`.

**Harness facts that change the plan**

- `evals/readtool` drives the full AIAgent against a real model (its README). It is not a $0 guard as shipped. Only its deterministic fixtures, driven by direct `read_file` calls, are $0.
- `tests/computer_use/driver_fixture.py` records a fake cua-driver install for package-manager selection. It is not a turn-level backend stub, so F07 has to write one (test-only).
- `tests/computer_use/live_cua_0_9_smoke.py` is live and denylisted.
- These exist on main: `tests/fakes/fake_llm_provider.py`, `tests/fakes/providers/anthropic_messages.py`, `openai_responses.py`, and others.

**Sandbox re-probe**

- bubblewrap 0.12.0.
- The read-only root returns EROFS under `/home/kvn/zer0`.
- The masked `/workspace/hermes-home` lists 0 entries.
- `connect(1.1.1.1:443)` under `--unshare-net` fails with OSError.
- PID 1 is `bwrap`.
- Correction to mvp-first: `/sys/class/net` still lists host interfaces, because sysfs is the host bind. Network isolation has to be asserted by a connect probe, not by listing interfaces.

**Local substrates**

- llama.cpp router `100.113.138.100:11530` serves qwen3-{0.6b, 1.7b, 4b, 8b (q4km, q6k), 14b} and nemotron-orchestrator-8b. All presets are 8K (L3).
- ollama `localhost:11434` serves qwen2.5:3b, qwen2.5-coder:7b, qwen2.5vl:3b and nomic-embed-text.
- GPU: RTX 3080 Ti, 12 GB.

**Reuse targets located**

| Target | Location | Notes |
|---|---|---|
| evolution-lab | `/home/kvn/tmp/evolution-lab` @`4cf52bb` | Dirty: `slice_informativeness.py` and its test are untracked, `l2_benchmark.py` is modified. Has `capacity_queue.py`. |
| Older evolution-lab clone | `/workspace/evolution-lab` @`2c95b59` | |
| evolver gates | fork `feat/evolver-phase0-gate-calibration` @`20eb166106` | |
| hermes-stack receipt schema | fork `lab/evals/hermes-stack-receipts-v0` @`22b0c745d5` | |
| Tokenomics | `/mnt/zer0models/workspace/tokenomics` @`cb83d42` | `spec/schemas/{event,experiment,outcome}.schema.json` |
| z0evals | `/home/kvn/tmp/z0evals` @`0326c14` | `schemas/study-manifest.schema.json` |
| z0int | `/tmp/z0intelligence` @`c4a4554` | `receipt.py` separates `execution_completed` from `verified_success`; `routines.py` `promote_credited` promotes only already-credited candidates and computes nothing |
| hermes-k8s-lab | `/home/kvn/zer0/oss/hermes-k8s-lab` @`91caa78`, no remote | `bin/run-experiment`, `experiments/000-003` |
| verified-oss-loop SPEC | @`8e6368a` | |
| oss-factory | @`820c9f5` | |
| kvnloo#322 | open | "[lab:S4] Build the common Hermes integration receipt + failure-injection runner" |

**Live-install hazard.** `/workspace/hermes-home/hermes-agent` is the live install's checkout, and `/home/kvn/.hermes` resolves to `/workspace/hermes-home`. Neither is ever a source tree. All trees come from the bare mirror.

---

## 1. Synthesis decisions

### 1.1 Spine: mvp-first

mvp-first is the architecture. It is the only design whose enforcement is verified on this host (a kernel sandbox). It has the shortest path to promotion-grade evidence. Its main output, a carrier adjudication in WAVE.md row format, is the method that already produced the 9-row salvage wave and the 73-item readiness reproof. The constraints make it the right shape: 0 free slots (A3), support rather than compete (E3), and salvage_cherry needs no slot (F1).

### 1.2 Grafts

| Idea | From | Lands in |
|---|---|---|
| Content-addressed `cell_key` plus a write-once frozen store: identical cells never re-run, and base-arm cells are shared by every candidate on the same base | scale-first | §3 executor, §9 cell receipt |
| Path-scoped invalidation (`invalidate_on`) plus a drift watch that demotes on main movement | scale-first | §7 spec, §8 step 13 |
| Load- and memory-adaptive CPU admission, plus a `cpu-quiet` lane for timing | scale-first | §5 |
| Per-hunk sabotage, a coverage-checked production seam, a static "mock of the seam" rejection, and all four proof columns asserted (fixes run.py's "last column only") | scale-first | §8 step 9 |
| Campaign-level threads and GitHub write caps | scale-first | §3 queue, §12 |
| ABBA ordering; pre-registered n=3 with a single escalation to n=6 | scale-first | §7, §8 |
| Defence-in-depth `sitecustomize` audit hook inside the kernel sandbox | scale-first | §6 |
| Calibration on maintainer fixes (FX-01 idea), folded into F14 and F11 | scale-first | §13 |
| Evidence chain: frontier-kb prior → Evolution Lab execution → Tokenomics receipts → z0evals freeze → promotion record under z0int rules | evidence-first | §4 |
| Labels `PRIOR` and `NOT_MEASURED` beside OBSERVED and MODELED | evidence-first | §9 |
| Slice-informativeness gate (UNINFORMATIVE outranks PASS and FAIL) | evidence-first | §8 step 10 |
| Wave 0 kill switch (E30), plus a global precondition before any PROMOTION-READY | evidence-first | §11 |
| Paid decisions accepted only from the owner's GitHub comment author, never from a self-asserted envelope `from` | evidence-first | §8 step 3 |
| Claim race rule: the earliest unexpired lease wins | evidence-first | §8 step 4 |
| `promotion_freeze` set by the A5 sweep | evidence-first | §8 step 1 |
| Staging cap of 5 PROMOTION-READY rows | evidence-first | §11 |
| `evidence_class` (mechanism vs product), `route_scope`, `observer_effect`, harness and editor ABI (C4) | evidence-first | §7 |
| In-tree harness adapters on a fork branch, now `staging/factory-replay-gate` | evidence-first | §3 |
| Freeze to z0evals only results a STAGING.md cites | evidence-first | §4 |
| Promotion never computes metrics; cited evidence sha256 must still match; `execution_completed` never becomes verified | z0int (via evidence-first) | §11 |

### 1.3 Conflict resolutions

| # | Conflict | Resolution | Why |
|---|---|---|---|
| R1 | Runner home: ledger (mvp), hermes-k8s-lab (scale), evolution-lab (evidence) | **The executor and gates go in kvnloo/evolution-lab** as `evolution_lab/hermes_factory/`, CLI alias `xf`. The package is Python stdlib only, so it runs with `python3 -m` from a worktree without evolution-lab's dependencies. It is built in a **fresh worktree off origin**, never in the dirty `/home/kvn/tmp/evolution-lab` checkout. In-tree Hermes adapters live on `staging/factory-replay-gate`. Public specs, receipts and STAGING.md live on `claude/ledger:factory/xf/`. hermes-k8s-lab supplies the 7-question lab contract, `stats.percentile` and the kind lane. | C1: one executor. Evolution Lab is the execution component (evidence-first cites the z0 registry; not re-verified). The ledger holds evidence, not code. Uncommitted work is never overwritten. Pending OD-5. |
| R2 | Branch names: `frontier/<slug>-vN` in all three designs vs the selected `staging/<id>` | **The selected names bind.** A rebuild takes a suffix (`staging/<id>-v2`, `-v3`). Never force-push. | The selection is binding. B1: earlier evidence is never mutated. Blocked by OD-0. |
| R3 | Queue granularity: per experiment (mvp), per campaign (scale), comments (evidence) | **One campaign per staging branch** (14), posted as a `work_order` on the existing feature thread, or else on one `[frontier] <id>` thread with `dedupe_key frontier:<id>`. Each experiment is a child `work_order` comment with its own SPEC §2 lease. | C1, spray norm, write caps |
| R4 | Spec format: TOML vs YAML | **TOML** for specs and STAGING.md front matter (stdlib `tomllib`). **JSON** for receipts. | No dependency to install in the sandbox |
| R5 | Three verdict vocabularies | Per gate: `PASS / FAIL / N_A / UNINFORMATIVE / INFRA`. A/B: `CREDIT / NO_CREDIT / REGRESSION`. Experiment: SPEC §7 `KEEP / DISCARD / PARTIAL`, or a non-result `FLAKY / UNINFORMATIVE / INFRA / BLOCKED`. | SPEC §7 stays canonical |
| R6 | Sandbox approach | **Three layers.** bwrap is the boundary. A `sitecustomize` audit hook blocks and logs exec and non-loopback connects inside it. Spec preflight refuses before anything is materialized. | Kernel enforcement plus attribution |
| R7 | CPU workers: a fixed 6 vs adaptive | `clamp(⌊10 − load1 − 2⌋, 1, 6)` flock slots, re-checked at each cell start. A cell starts only if `MemAvailable ≥ need + 4 GB`. | Load measured 3.7–18.7 on 10 cores (H7) |
| R8 | The selected set includes branches the designs excluded (cu-\*, plugin-catalog-entries, prefix-parity-journeys, eval-only branches) | **The selection decides what is staged and queued. Holds and D5 decide what can reach PROMOTION-READY.** cu-\* stay HOLD until OD-6. prefix-parity-journeys and factory-replay-gate are never promoted alone. postmortem-logcalls-zero-hit needs consumer evidence. | Selection vs E1, E2, D5 |
| R9 | E01 harness head: catalog `602e596389b` vs live | `5444b1a2a8`, matching the selected set and gh | D8. A head that drifts after claim invalidates the run. |
| R10 | Salvage branch form: fold-in pushed on the carrier head vs a ledger patch | Both are supported. Pushing needs OD-4. The default is a ledger patch plus a local ref. | E3, K1 |
| R11 | When to freeze to z0evals | Only when a STAGING.md cites the receipt | Avoids spamming studies |
| R12 | #125376 is a 3-commit bundle | F01 runs two arms. `c125376` is the full PR head, which is what a maintainer would merge. `c125376-leaf` is `5f3f5896a4` cherry-picked alone, which isolates the edit fix. The carrier choice records the unrelated surface (D9). | Arms differ in one variable |

---

## 2. Binding constraints as mechanisms

These are constraint IDs as the source designs cite them. Each row says how the factory enforces it.

| ID | Mechanism |
|---|---|
| A1, A2, A3 | Zero writes to origin or Linear. PROMOTION-READY means "ready to ask a maintainer". It is never a merge, never a slot. |
| A4 | Body tone gate (7 items) and a jargon lint before STAGING.md can say ready |
| A5, C3, T2 | Each loop starts with a read-only sweep of the open upstream PRs. Its result sets `promotion_freeze`. Experiments continue regardless. |
| B1 | Write-once receipts. A rerun creates a new receipt with `supersedes`. |
| B4, B5 | Namespace allowlist `staging/*` only. Never `promote/*`, `ready/*`, `wine2e/**` or `wine2e-install/**`. Always `--no-follow-tags`. |
| B8 | Only a different worker sets the QA class |
| C1 | Envelope status is the only queue state. No daemon, no cron, no Actions. `xf status` is a read-only projection. The capacity_queue only mirrors cells that are already claimed. |
| C2 | Order comes only from the owner-set `queue_rank`. Traction is never read. |
| C4 | Every spec names the harness and editor ABI |
| D1–D3, D9 | 12-step gate. RED/GREEN/NEG/ADJ. Real call path with the seam coverage-checked. One invariant. Blind verifier. |
| D5 | Test infra and evals never go upstream alone (factory-replay-gate, prefix-parity-journeys, logcalls without a consumer) |
| D6, D7, D8 | LANDED means a merge SHA with the content present. Local, CI, simulation and runtime evidence stay in separate fields. A freshness re-check within 24 h. |
| E1, E2 | Admission checks the Hermes-lane PLAN items, the claimant lanes (#127373, #127374, #127375, #127332, #127228), the hard hold (#69, #70) and the design holds (CU/Jev, realtime voice, agents overlay, row budget, glyph) |
| E3, E4 | An external owner forces the salvage or support route, with our part as a `Co-authored-by` fold-in |
| E6 | A hook row must name a fire site and a consumer. Plugins go through the plugin-catalog route. |
| F1, F3 | salvage_cherry is preferred. Spray is avoided. Cost per KEEP is rolled up, including failed runs. |
| G1, G2 | No fork Actions or schedules, no fork PRs. Push triggers are parsed before every push. |
| H1, H2, H3, T3, H5, H7 | Denylist. A→B→A two-home E2E for profile or scope changes. Disposable venv only. No worktrees on `/tmp` tmpfs. Adaptive CPU admission. |
| I1, I2, I3, I5, I6 | A/A before any delta. Credit only on human-curated batteries. A falsified hypothesis is recorded as a win. Informativeness gate. Pre-registration (spec committed before run 1). Cache-read ratio for caching-adjacent changes. |
| K1, K2, K3, K4 | Private data stays local and only aggregates publish. Security repros stay off the fork. No credentials in workers. Paid runs need an owner decision and the owner launches them. |
| L3, L5, L7 | 64K floor vs 8K presets. The live cluster is off limits. GPU flock. |
| T6 | New rows queue behind the 40 rows already in #404 |

---

## 3. Components and where they live

| Component | Location | Reuses | Role and authority |
|---|---|---|---|
| **Queue / bus** | kvnloo/hermes-agent issues with `oss-factory:v1` envelopes, label `claude bot` | oss-factory CONTROL_PLANE; SPEC §2 leases; the `hermes-agent` entry in projects.json | One campaign per staging branch on its existing feature thread. The factory thread for xf and E48 is **kvnloo#322**. Each experiment is a child `work_order`. A claim is a `receipt` with a lease. A verdict is one `result`. The only queue authority. |
| **Roadmap ranks** | `queue_rank` in the work order, owner-set | none | The factory may propose rank as cost × demand × readiness. Only the owner sets it. |
| **Hypothesis source** | frontier-kb vault `/home/kvn/tmp/frontier-kb` @`8562d50`, `catalog.json`, demand report | KB permanent notes | Read-only. Results carry a `kb_candidate` text for the human curator. |
| **Spec registry** | `claude/ledger:factory/xf/specs/<id>.toml` | catalog E-ids | Public-safe. The commit that adds a spec is its pre-registration timestamp. A spec is immutable after first claim; edits create a new `rev`. |
| **Executor `xf`** | kvnloo/evolution-lab `evolution_lab/hermes_factory/`, branch `exp/hermes-factory-v0` (collision-checked; push only after OD-5) | evolver `gates.py` and `calibrate.py`, pinned and vendored with the source SHA recorded; `slice_informativeness.py` (owner must commit it first); evolution-lab `run_pair` interleave idea; postmortem fresh-interpreter-per-probe pattern | Subcommands: `xf base`, `xf next`, `xf run <spec>`, `xf validate <receipt>`, `xf status`, `xf stage`. One claimed work order per invocation. About 500–800 LOC, stdlib only. |
| **Capacity placement** | evolution-lab `capacity_queue.py` (`flyforge.capacity_queue_item.v1`) | Kerdoios constraints | Mirrors only GPU cells that are already claimed, with `provenance: <work_order id>`. Never assigns work. |
| **Lab contract and stats** | hermes-k8s-lab @`91caa78` (local) | the 7 experiment questions, `stats.percentile`, `bin/run-experiment` patterns | Imported as a library. The kind lane (`kind-hermes-lab`, namespace `hermes-lab`, never Secrets) is reserved for contention cells. It runs on the same host, so it adds no capacity. |
| **In-tree harness adapters** | `staging/factory-replay-gate` on fresh main, holding `evals/_factory/` | FakeLLMServer wrapper (`tests/fakes/fake_llm_provider.py`, `tests/fakes/providers/*`); loopback guard lifted from `evals/provider_fallback/probe_104260.py:11-39`; a postmortem-style probe runner with asserted red-on-base and forced HERMES_HOME; an arm materializer | Never upstreamed alone (D5). A feature's staging commit copies only the eval files it needs. |
| **Upstream evals (guards and batteries)** | Run in-tree from the pinned arm worktree, unmodified | See F14 for the list | Standing regression set on base and on every arm |
| **Postmortem forensics** | `evals/postmortem/forensics/{logcalls,tokens,tools,delegation,rework}.py`, `common.Run` | as shipped | T0 replay on **copies** of state.db and `agent.log*`. The private store keeps results; only aggregates publish. |
| **Compaction replay** | `evals/compaction/scripts/{reconstruct_lineage,replay_lineage}.py`, `policies.py`, `fixtures.py`, `test_region_scoping.py` | as shipped | E03, F02, E37-offline |
| **Object store and arms** | `/mnt/zer0models/project-artifacts/hermes-agent/factory/xf/{h.git,wt,venvs,cells,journal,frozen,private,locks}` | PROTOCOL.md worktree discipline; btrfs reflink | Blobless bare mirror. PR heads are fetched to `refs/xf/pr/<n>`. Arms are built with `git merge-tree --write-tree` plus `git apply`, keyed by tree SHA, and cloned by reflink. Never `git stash`. GC is reference-counted. |
| **Disposable venv** | `.../factory/xf/venvs/<uv.lock sha256[:12]>/` | `python -m pm.build_env --source . --out <dir> --group dev --group test` on host python 3.14.7, which satisfies the nemo-relay marker | Built in bwrap with network on and a read-only root except the venv directory. Always passed as `HERMES_PYTHON`. Preflight checks it imports pytest and fails closed. The last 3 are kept. |
| **Receipts** | Private: `factory/xf/{journal,cells,private}`. Public: `claude/ledger:factory/xf/receipts/` | SPEC §4 and §7; Tokenomics `event/experiment/outcome.v0` (`cb83d42`); `z0eval.hermes_stack_experiment.v0` (fork `22b0c745d5`) for z0 factorial work | Two levels, cell and experiment (§9) |
| **Gate engine** | `evolution_lab/hermes_factory/gates.py` | evolver `validity_gate`, `activation_gate`, `paired_bootstrap_ci`, `credit_gate` (CREDIT_MIN_PAIRS); `slice_informativeness`; PROTOCOL READY definition | Computes RED, GREEN, NEG, ADJ, GUARDS, FLAKY, NOISE, CREDIT, INFORMATIVE, ROUTE_SCOPE and CACHE |
| **Freeze** | kvnloo/z0evals branch `study/hermes-<exp>` (`study-manifest.schema.json`) | z0evals validate | Only for receipts a STAGING.md cites. Branch push only; humans merge. Private artifacts appear as sha256 only. |
| **Promotion record** | `claude/ledger:factory/xf/staging/<id>/STAGING.md` plus `body.md` and `*.patch` | PROTOCOL packaging; WAVE.md rows; the #404 table; z0int eligibility rules | §10 |
| **Promotion boards** | fork #402 (salvage wave) and #404 (staged PRs) | existing boards | A `state` comment proposes a row behind the existing ones. The owner decides. |
| **Blind verifier** | A second worker (another Claude session, or the grok/codex lane), addressed by envelope | SPEC §5 reviewer verdicts | Gets only the branch or patch, the repo and the spec's oracle block. Returns `APPROVE_EXACT_HEAD / CHANGES_REQUIRED / DISCARD_DUPLICATE / DISCARD_WRONG_DIRECTION / BLOCKED_EXTERNAL` and a QA class `CLEAN / CHECK / HOLD / FAIL_GAP`. |
| **Local models** | llama.cpp router `100.113.138.100:11530`; ollama `localhost:11434` | GPU flock `/tmp/claude-1000/gpu.lock` | L2 lane. Hermes arms are blocked by the 64K floor until OD-1. |
| **HITL** | Linear, owner only | HITL.md | The factory writes 0 |

**Not used:** hermes-agent-cluster (live, L5), fork CI (G2), any second queue or store.

---

## 4. Evidence chain and data flow

```
frontier-kb + catalog.json + demand map        (hypothesis, PRIOR only)
      | hypothesis_refs (read-only)
      v
spec.toml committed to claude/ledger            (pre-registration)
      | owner sets queue_rank; campaign work_order on feature thread
      v
xf next: sweep -> select -> claim (SPEC §2 lease) -> admission (need, ownership, holds, lint)
      v
xf run: arms (merge-tree, reflink) -> cells in bwrap lanes -> cell receipts (Tokenomics fields)
      v
gates: validity, red-on-base, green x3, per-hunk sabotage, adjacent, guards, A/A noise,
       credit (paired bootstrap), informativeness, route scope, cache-read
      v
receipt.public.json -> claude/ledger      receipt.full + raw -> private store (K1)
      | result envelope + SPEC §7 learning record (falsified = win)
      v  (KEEP and route allows)
xf stage: staging/<id> commit (or carrier + fold-in / ledger patch) + STAGING.md + body
      v
blind verifier (different worker, exact head) -> QA class
      v
freshness re-check (<=24 h) -> z0evals freeze of cited receipts -> PROMOTION-READY
      v
state comment on #402/#404 behind existing rows -> [owner] Linear Todo -> [owner] origin action
```

The z0int rules apply at the last two arrows:
- Promotion recomputes nothing.
- Every cited receipt's sha256 must still match.
- An `execution_completed` cell never counts as `verified_success`.
- A shadow or advisory result never promotes.

---

## 5. Lanes and cost classes

| Lane | Cost class | Tier / substrate | Concurrency | Today |
|---|---|---|---|---|
| `cpu` | $0 | T0 replay or static; T1 FakeLLMServer or scripted fake through the real AIAgent and tool paths | adaptive, 1–6 | Runnable |
| `cpu-quiet` | $0 | T1 timing cells (E09) | Exclusive, takes all slots; runs only when load1 < 4; ABBA order | Runnable when the host is quiet |
| `docker` | local | sandbox-desktop image (E23) | 1 | Gated by OD-6 and image availability |
| `gpu` | local | T2: llama.cpp router or ollama, flock, one model resident, cold load discarded but recorded, nvidia-smi before and after, power.draw integrated | 1, strictly serial, never preempts Quackles | Non-Hermes cells only. Hermes arms blocked by OD-1. |
| `k8s` | $0 | kind-hermes-lab, FakeLLMServer pods | shares host CPU | Reserved; none of the first 30 |
| `paid` | paid | T3 real providers | n/a | OFF. Needs OD-3 and the owner launches. |
| `free-quota` | $0 external | Groq or Cerebras via Kerdoios | n/a | OFF. Needs credentials in the worker (K3) and fixtures off-box. Owner decision only. |

**Budgets.**
- A spec budget is a hard cap. The executor projects the cost of the remaining cells and posts a `blocker` before it would exceed the cap.
- Global caps are in the owner-edited `~/.config/hermes-factory/caps.toml`, which the factory only reads: daily CPU core-hours, GPU window, `usd = 0`.
- A paid cell requires all three:
  1. `paid.enabled = true` in caps;
  2. an owner-authored `decision` comment naming the spec, a $ cap and a Linear issue;
  3. `budget.usd > 0` in the spec.
- When all three hold, the egress allowlist admits only the budgeted provider host.

---

## 6. Sandbox contract

Preflight refuses the cell if any item fails.

1. **Kernel layer** (bwrap, profile `none`, the default):
   ```
   bwrap --ro-bind / / --dev /dev --proc /proc
     --bind $RUN $RUN --bind $RUN/tmp /tmp
     --tmpfs /workspace/hermes-home --tmpfs $HOME/.ssh --tmpfs $HOME/.config/gh
     --tmpfs $HOME/.config/nemo-relay --tmpfs /etc/nemo-relay
     --unshare-net --unshare-pid --die-with-parent --clearenv
     --setenv HOME $RUN/home --setenv HERMES_HOME $RUN/home/.hermes
     --setenv HERMES_PYTHON $VENV/bin/python --setenv PATH $VENV/bin:/usr/bin:/bin
   ```
   `$RUN` is on `/mnt/zer0models`, never on `/tmp` tmpfs.
   - `--clearenv` unsets `__HERMES_ACTIVATED`.
   - The fresh HOME has no `pytest_live_guard.py`, so `run_tests.sh:86-87` stays inert.
   - The explicit HERMES_HOME neutralizes `run.py:47`'s setdefault.
   - No credentials are reachable, which also blocks `tool_search_livetest` copying `.env` and `auth.json`.
2. **Profile `router`** (only with OD-1): shares the network namespace. An in-process allowlist permits only `127.0.0.1` and `100.113.138.100:11530` (or `localhost:11434`), plus the GPU flock.
3. **In-process layer** (`sitecustomize.py` on PYTHONPATH):
   - A loopback-only `socket.connect` guard. Every attempt goes to `egress.log`.
   - A `sys.addaudithook` that raises on `os.exec*` and `os.posix_spawn`, and on `subprocess.Popen` of `hermes`, `hermes_cli.main`, `update`, or any interpreter under a live install. Exceptions require `safety.allow_exec` plus an owner decision.
   - Any blocked attempt fails the cell as `INFRA`, never silently.
4. **Selection layer (H1 denylist)**, applied at collection time:
   - `tests/e2e/core/upgrade/**`, `tests/e2e/core/windows_update/**`, `evals/update_*`.
   - Any selected file that `git grep` at base finds referencing `os.execv`, `execvp` or `_reexec`.
   - `tests/computer_use/live_*`.
   - Pytest always gets `-m 'not live and not integration'` appended.
   - Harnesses that exec the CLI (`toolperf_abeval`, `codebase_navigability/runtime_bench`, `hermes plugins validate`) need OD-2.
   - `cache_prefix_wire` defaults to `~/.hermes` and has an empty pass marker. It runs only after a patched copy is used.
   - `tool_search_livetest*` never runs.
5. **Path layer.** The runner refuses any realpath under `~/.hermes`, `/workspace/hermes-home` or the live venv. Scratch homes are created with `exist_ok=False`.
6. **Relay.** If Relay is present, both arms get an identical `plugins.toml`, one process per arm, and `resolve_plugin_sources().config_paths` is recorded per cell.
7. **Canary.** F15 proves layers 1–5 each block, and that each escapes when its guard is removed. F15 re-runs whenever bwrap, the kernel or the profile changes.

---

## 7. Experiment spec format (`xf_spec = 1`, TOML)

Path: `claude/ledger:factory/xf/specs/<id>.toml`. The work-order envelope carries `{spec, spec_sha256, queue_rank, staging}`.

### 7.1 Gate (carrier A/B) example: F01

```toml
xf_spec = 1
id = "F01"
rev = 1
staging = "edit-fuzzy-wrong-region"
catalog_refs = ["E01", "E02"]
feature = "edit-tool-fail-loud-and-meter"
kind = "carrier-ab"   # redgreen | carrier-ab | ab | aa | forensic | sizing | static | calibration
queue_rank = 7        # owner-set (C2)
hypothesis_refs = ["NousResearch#111116", "NousResearch#54572", "catalog:E01"]
priors = []           # PRIOR-labelled numbers only; never a claim

[contract]            # hermes-k8s-lab 7 questions (I5); locked at first claim
question = "Which open carrier makes a single-line wrong-region fuzzy edit fail loud on main without regressing exact or legitimate fuzzy edits?"
hypothesis = "main applies the edit to the wrong region; #54575 and/or #125376 refuse it"
varied = "tree"       # exactly one of: tree | config | plugins | provider | model
fixed = ["contract test", "inject patches", "venv lock", "fixtures"]
falsifier = "main already refuses (no live need -> DISCARD), or no carrier is GREEN 3/3 with NEG RED (-> HOLD)"
kill = "falsifier met on two consecutive base-of-day pins"
observer_effect = "none: direct tool calls, no hooks loaded"

[class]
cost = "$0"
tier = "T1"
lane = "cpu"
evidence_class = "mechanism"   # mechanism | product | sizing | regression | calibration
route_if_keep = "salvage-row"  # core-leaf | salvage-row | support-note | decision-request | plugin-catalog | docs-leaf | eval-fix | internal | ride-along
route_scope = "n/a"            # compaction specs: local-compressor | native | all
harness = { name = "hermes", editor_abi = "patch + fuzzy_match", surface = "tool-direct" }

[safety]
net = "none"
data_class = "public"          # public | private-local
cli_entrypoint = false
allow_exec = []
owner_decisions = []           # e.g. ["OD-1"], ["OD-3:<decision comment url>"]

[base]
repo = "NousResearch/hermes-agent"
pin = "e496ccc7d7"             # base-of-day, recorded at claim

[[arms]]
id = "base"
tree = "@base"

[[arms]]
id = "c54575"
pr = 54575
head = "e28d7c772d"
merge_onto = "@base"

[[arms]]
id = "c125376"
pr = 125376
head = "5f3f5896a4"
merge_onto = "@base"           # full PR: includes bot_relay #95741 + email chore

[[arms]]
id = "c125376-leaf"
cherry_pick = ["5f3f5896a4"]
onto = "@base"                 # fail-loud commit alone (R12)

[[arms]]
id = "both"
prs = [54575, 125376]
merge_onto = "@base"           # merge-tree in PR order; a conflict marks the arm CONFLICTING, never silently resolved

[inject]                       # test-only hunks applied to every arm so base can be RED
patches = ["factory/xf/staging/edit-fuzzy-wrong-region/contract-test.patch"]
carrier_tests = [54575, 125376]   # each carrier's own tests cross-applied to every arm

[probe]
kind = "pytest"
cmd = "scripts/run_tests.sh {files} -q -j {jobs} -m 'not live and not integration'"
files = ["tests/tools/test_fuzzy_match.py", "<contract test path, fixed at authoring>"]
reps = 3
escalate_to = 6
order = "ABBA"
timeout_s = 900

[oracle]
type = "gate"
red_on = "base"
red_marker = "<assertion text the contract test raises on main>"
green_on = ["c54575", "c125376", "c125376-leaf", "both"]
production_seam = { file = "tools/fuzzy_match.py", symbols = ["<resolved at claim>"] }
sabotage = "auto_per_hunk"     # each non-test fix hunk reverted alone; >=1 must re-RED; unpinned hunks reported
adjacent = { files = ["tests/tools/test_file_operations*.py", "tests/tools/test_patch_parser.py", "tests/tools/test_file_tools_live.py"], rule = "identical pass/fail set to base" }

guards = ["F14"]
invalidate_on = ["tools/fuzzy_match.py", "tools/file_operations.py", "tools/patch_parser.py"]

[outputs]
public = ["per-arm counts", "assertion text", "shas", "sizes"]
private = []
not_tested = ["model behaviour after a refusal (E02, deferred)"]

[budget]
usd = 0
wall_s = 3600
cpu_core_s = 7200
max_cells = 120
lease_hours = 24
```

### 7.2 Metric variant example: E09

```toml
[oracle]
type = "metric"
metrics = [
  { name = "submit_to_first_delta_ms", label = "OBSERVED", direction = "report", primary = true },
  { name = "create_agent_share", label = "OBSERVED", direction = "report" },
]
aa_required = true             # A/A on the same tree first; MDE from A/A
statistic = ["median", "p95"]
test = "paired_bootstrap"
pairs_min = 5
ci = 0.95
reps = 30
escalate_to = 0                # no optional stopping
baselines = ["aa"]
denominator = "errored reps score 0 and stay in; infra crashes are INFRA, excluded and counted; >10% infra -> INFRA verdict"
```

### 7.3 Lint

The lint refuses to mint a work order when any of these fail:

- Exactly one varied variable, checked mechanically by diffing tree SHA, overlay and plugin set.
- Every arm is pinned to a SHA at claim. PR-head drift after claim invalidates the run.
- Every input carries a sha256.
- Every measurement carries a label from `OBSERVED / MODELED / PRIOR / NOT_MEASURED`.
- Falsifier, kill criterion and `observer_effect` are present.
- Cost class matches the lane. Every `owner_decisions` entry resolves to a recorded owner comment.
- A red/green kind has a `red_marker`, a `production_seam` and a sabotage mode.
- Compaction specs set `route_scope`. Native compaction is declared uninspectable.
- A caching-adjacent spec lists a `cache_read_ratio` measurement or declares it `NOT_MEASURED`. The latter caps the branch at LIMITED.
- A `private-local` spec has an aggregate-only `outputs.public` list.
- The resolved command and file list pass the H1 denylist.
- Config arms are written to the arm's own `$HERMES_HOME/config.yaml`. No `HERMES_*` env vars for non-secret config.

---

## 8. Run loop (`xf next`)

This is the Verified OSS Loop with no second scheduler. A worker with spare capacity invokes `xf next` once. Nothing runs on a timer.

0. **Registry check.** Confirm project `hermes-agent` is active in `factory/projects.json` and attach the worker label.
1. **Sweep (A5), read-only.** List the factory-owned open upstream PRs (13 per the designs) and boards #402 and #404. Untriaged CHANGES_REQUESTED, a failing policy check or a conflict produces a top-priority origin work order to the owning lane and sets `promotion_freeze = true`. While the freeze is set, no new board rows are added. Experiments continue (C3).
2. **Daily base**, on the first invocation of the day:
   - Read-only fetch of upstream main into `h.git`, then pin base-of-day.
   - Build or reuse the venv by `uv.lock` hash.
   - Run F14 (the standing set) twice. A verdict change against yesterday's base is posted on #322 as main drift.
   - Re-run `merge-tree` and the drift watch (step 13) for every live STAGING.md, the 40 #404 rows and the 73 READY items.
3. **Select.** Choose queued child work orders whose lease is absent or expired, whose `depends_on` are done, and whose lane is admissible:
   - $0 is always admissible.
   - local needs the GPU or docker lock and its OD.
   - paid needs a `decision` comment whose **GitHub author is the owner's account**. The self-asserted envelope `from` is not enough.
   - Order by `queue_rank`, then creation time.
4. **Claim.** Post a `receipt` envelope (parent = the work order) containing `{base_revision, claimed_at, expires_at (+4 h for $0, +24 h for long runs), scope: one sentence, worker, spec_sha256, decision_rule_sha}`. Re-read the thread. The earliest unexpired receipt wins, and a loser posts `superseded`.
5. **Admission.** Any failure posts a `blocker` and releases the lease.
   - The live need still exists at the cited code on base-of-day.
   - Ownership and duplicate check: `gh search prs/issues` across open and merged, the claimant lanes, the holds and the Hermes-lane PLAN items.
     - An open external PR on the same defect forces `route = salvage-row` (its head becomes an arm) or `support-note`.
     - A Hermes-lane overlap is coordinated by envelope (E1).
   - Spec lint (§7.3) and sandbox preflight (§6).
6. **Plan.**
   - Expand to cells: arms × fixtures × seeds × reps.
   - Compute each `cell_key`, which is sha256 of canonical JSON over:
     - harness blob SHAs, arm tree SHA, fixture digests, params, seed and rep;
     - substrate fingerprint (gguf sha, llama.cpp build, ctx);
     - env fingerprint (python, venv lock, plugins.toml sha, Relay config_paths).
   - Drop cells already frozen. Base cells are shared across candidates.
   - Enforce the budget.
7. **Materialize.**
   - Worktrees by tree SHA (reflink).
   - `merge-tree` PR heads onto base; a conflict marks the arm `CONFLICTING`. A hand-port is a recorded patch with `merge = "handported"` and its own negative control.
   - Apply inject patches. Write config overlays.
8. **Execute.**
   - Every cell runs in a fresh process, in a fresh bwrap, with its own HOME.
   - Output goes to resume-safe create-only JSONL `journal/<id>/<rev>.jsonl`.
   - A retry is a new row with `attempt = n`, never silent.
9. **Proof gates** (red/green kinds). All four columns are asserted:
   - **RED** on base with `red_marker` matched. Coverage shows `production_seam` executed. A static check rejects `monkeypatch` or `mock.patch` of the seam (D3). A failure that also occurs without the inject patch counts as pre-existing.
   - **GREEN** 3/3 on candidate arms. Disagreeing reps mark the result `FLAKY` and re-queue it once at n=6.
   - **SABOTAGE**: each non-test fix hunk reverted alone; at least one must re-RED. Unpinned hunks are reported as excess surface (D9).
   - **ADJACENT**: the same pass/fail set on base and head.
   - **GUARDS**: the arm's F14 verdict map equals base's, or the spec explains the change.
10. **Metric gates.**
    - The A/A floor exists for this harness and substrate fingerprint.
    - Paired bootstrap CI, ABBA order. Wilson intervals for proportions. Median and p95 for latency.
    - `CREDIT` requires CI lower bound > 0 with ≥ 5 pairs, on a human-curated battery (I1).
    - Informativeness: if a majority, constant or keyword baseline clears the threshold, the result is `UNINFORMATIVE`.
    - Forensic and sizing kinds print coverage first and give a number, not a verdict.
11. **Receipt and publish.**
    - Write the cell receipts and `receipt.full.json` to the private store, with a `manifest.sha256` and `chmod a-w`.
    - The privacy exporter keeps allowlisted fields only and regex-scans for secrets, emails, home paths, session ids and message text.
    - It refuses anything from `fixtures/private`. It enforces n ≥ 5 per published bucket and salts hashed ids with an unpublished salt.
    - One ledger commit per loop iteration (`receipt.public.json`), pushed with `--no-follow-tags` from a dedicated ledger worktree.
    - One `result` envelope with the verdict and the SPEC §7 learning record. A falsified hypothesis is recorded as a win (I2).
12. **Branch on the verdict.**
    - `DISCARD` keeps the negative result and kills the hypothesis if its kill criterion is met.
    - `PARTIAL`, `UNINFORMATIVE` or `FLAKY` mints the follow-up spec (more reps, a frozen battery, or a gated paid confirmation).
    - `KEEP` on a branch whose evidence set is complete goes to step 14.
13. **Drift watch**, every loop, for every STAGING.md in `STAGED` or later:
    - `git diff --name-only <frozen_base>..main -- <invalidate_on>` plus `git merge-tree --write-tree main <branch>`.
    - Any hit demotes the branch to `STALE` and re-queues only the proof and guard cells, which are cheap.
    - Metric cells re-run only when `invalidate_on` paths changed.
14. **Stage** (`xf stage`).
    - Own leaf: one commit on fresh main.
      - Author `Kevin Rajan <7121943+kvnloo@users.noreply.github.com>`, `fix(scope):`, `perf(scope):` or `docs(scope):` subject, salvaged authors credited.
      - Never contaminated paths (`hermes_cli/kanban_db.py`, `tests/hermes_cli/test_kanban_external_receipts.py`).
    - Salvage: the unmodified carrier head plus one `Co-authored-by` fold-in commit (if OD-4 allows), otherwise a ledger patch.
    - Pre-push:
      - `ls-remote` collision check;
      - re-parse `.github/workflows/*` on that tree; abort if any push trigger matches the branch;
      - `--no-follow-tags`; never force-push.
    - Write STAGING.md, `body.md` and the patch to the ledger.
    - Post a `work_order` to a **different** worker for blind exact-head verification.
15. **Verify and hand off.**
    - The verifier's QA class goes into STAGING.md.
    - With CLEAN, P1–P12 PASS, no freeze, and fewer than 5 rows outstanding:
      - freeze the cited receipts to z0evals;
      - set `status = "PROMOTION_READY"`;
      - post one `state` comment on #402 (salvage) or #404 (own leaf), behind the existing rows.
    - Stop there. Steps 9–12 of D1 belong to the owner.
16. **Release** the lease, remove worktrees and check disk.
    - When nothing is executable, follow the CONTROL_PLANE continuation ladder. Never post "nothing ready" repeatedly.

---

## 9. Receipt formats

### 9.1 Cell receipt: `xf.cell.v1` (private JSONL, one line per cell)

```json
{
  "schema": "xf.cell.v1",
  "cell_key": "sha256:…",
  "experiment": {"id": "F01", "rev": 1, "spec_sha256": "…", "work_order": "kvnloo/hermes-agent#<n>/comment/<id>", "lease_id": "…"},
  "tokenomics_experiment": {"experiment_id": "F01", "pair_id": "case03-rep2", "task_snapshot_id": "sha256:<fixture>",
    "arm_id": "c54575", "treatment_hash": "sha256(tree|overlay|plugin_shas|provider_tier|model_rev)",
    "verifier_class": "pytest-contract", "replay_grade": "direct-call"},
  "revisions": {"base_main": "e496ccc7d7", "arm_tree": "<sha>", "harness": {"tests/tools/test_fuzzy_match.py": "<blob>"},
    "adapters": "staging/factory-replay-gate@<sha>", "runner": "evolution-lab@<sha>", "dirty": false},
  "env": {"host": "groot", "python": "3.14.7", "venv_lock": "<sha>", "sandbox": "bwrap-none",
    "relay": {"present": false, "plugins_toml_sha256": null, "config_paths": []}, "load1": 4.2},
  "substrate": {"tier": "T1", "model": null, "gguf_sha": null, "router_build": null, "ctx": null},
  "identity": {"turn_ids": [], "api_request_ids": []},
  "cell": {"lane": "cpu", "rep": 2, "seed": 2, "order": "BA", "attempt": 1},
  "exit": {"class": "ok", "rc": 1, "marker_ok": true},
  "proof": {"kind": "red", "result": "FAIL", "reason_marker_matched": true, "seam_covered": true},
  "measurements": [{"name": "cases_failed", "value": 3, "unit": "count", "label": "OBSERVED", "source": "pytest"}],
  "outcome": {"execution_completed": true, "verified_success": null, "verification_source": "pytest-contract"},
  "resource_usage": {"wall_s": 41.2, "cpu_s": 39.0, "gpu_s": 0, "energy_j": null, "tokens": 0, "api_cost_usd": 0.0},
  "safety": {"egress_attempts": 0, "exec_blocked": 0, "home": "isolated"},
  "artifacts": [{"uri": "private://F01/…/stdout.txt", "sha256": "…", "public": false}]
}
```

- `turn_ids` use Hermes `turn_id` (`<session>:<task>:<8hex>`, `turn_facade.py:65`) as the trace identity.
- `outcome` follows Tokenomics `outcome.v0`. `verified_success: null` means unknown.

### 9.2 Experiment receipt: `xf.receipt.v1` (public aggregate, a superset of SPEC §4)

Path: `claude/ledger:factory/xf/receipts/<id>/<run-id>.json`.

```json
{
  "schema": "xf.receipt.v1",
  "id": "F01/r20261002-01",
  "spec": {"path": "factory/xf/specs/F01.toml", "rev": 1, "sha256": "…", "prereg_commit": "<ledger sha>", "decision_rule_sha": "…"},
  "runner_revision": "evolution-lab@<sha>",
  "issue": "kvnloo/hermes-agent#<campaign thread>",
  "origin_refs": ["NousResearch#111116", "NousResearch#54572"],
  "staging": "edit-fuzzy-wrong-region",
  "base_revision": "e496ccc7d7",
  "arms": {
    "base": {"tree": "<sha>"},
    "c54575": {"head": "e28d7c772d", "merge_tree": "<sha>", "merge": "clean|conflict|handported", "patch": null},
    "c125376": {"head": "5f3f5896a4", "merge_tree": "<sha>", "merge": "…"},
    "c125376-leaf": {"cherry_pick": ["5f3f5896a4"], "tree": "<sha>"},
    "both": {"merge": "…"}
  },
  "head_revision": null,
  "changed_files": [],
  "policy_revision": {"AGENTS.md": "<blob@base>", "CONTRIBUTING.md": "<blob@base>", "factory": "FACTORY.md@<ledger sha>"},
  "env": {"host": "groot", "python": "3.14.7", "venv_lock_sha256": "…", "sandbox": "bwrap ro-root netns-none home-masked clearenv pidns"},
  "gates": {
    "validity": "PASS",
    "red": {"arm": "base", "result": "PASS", "observed": "3 failed / 5", "assertion": "…", "seam_covered": true, "reps_agree": "3/3"},
    "green": [{"arm": "c54575", "result": "PASS", "reps_agree": "3/3"}],
    "sabotage": {"per_hunk": [{"arm": "c54575", "hunk": "tools/fuzzy_match.py@@…", "red_again": true}], "unpinned_hunks": []},
    "adjacent": {"files": ["…"], "base": "N passed / M failed", "arm": "N passed / M failed", "identical": true, "pre_existing_failures": []},
    "guards": {"F14": "equal"},
    "flaky": false,
    "noise_floor": null, "credit": null, "informativeness": "N_A",
    "route_scope": "n/a",
    "cache_read_ratio": {"status": "N_A", "before": null, "after": null}
  },
  "ab": null,
  "measurements": [{"name": "cases_failed", "arm": "base", "value": 3, "n": 3, "label": "OBSERVED", "statistic": "count"}],
  "denominators": {"cells": 45, "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
  "evidence_class": {"local": true, "ci": "none", "simulation": false, "runtime": false, "kind": "mechanism"},
  "harness_abi": {"harness": "hermes", "editor_abi": "patch + fuzzy_match"},
  "not_tested": ["model behaviour after refusal"],
  "limitations": ["…"],
  "resource_usage": {"wall_s": 0, "cpu_core_s": 0, "gpu_s": 0, "energy_j": null, "api_cost_usd": 0.0},
  "verdict": "KEEP",
  "carrier_choice": {"winner": "c54575", "why": "GREEN 3/3, sabotage pins it, no unrelated surface; #125376 carries bot_relay #95741 + chore"},
  "learning": {"hypothesis": "…", "result": "KEEP", "observed_evidence": [], "regressions": [], "reusable_lesson": null, "roadmap_effect": "promote"},
  "provenance": "self",
  "frozen": {"bundle_sha": "…", "cells": 45, "supersedes": null},
  "z0evals_study": null,
  "ai_assistance": "Claude Code (Opus 5.5) wrote the contract test; disclosed per repository policy",
  "privacy": "public-aggregate"
}
```

The `carrier_choice` content above is an illustration of the format, not a result.

### 9.3 Receipt rules

- **Labels.** Every number carries `OBSERVED` (wire, usage rows, test results), `MODELED` (reconstruction, replay estimate), `PRIOR` (other harnesses' effect sizes, e.g. the Claude Code −64.7% / −30.3% figures) or `NOT_MEASURED`. Labels are never summed. A headline is OBSERVED only. A MODELED headline cannot make a branch READY.
- **Evidence classes.** Local, CI, simulation and runtime evidence stay in separate fields (D7). An empty or `action_required` CI rollup is recorded as `"none"`.
- **Infra.** `INFRA` rows stay in the completeness denominator. An infra rate above 10% makes the whole experiment `INFRA`.
- **Provenance** uses the CONTROL_PLANE vocabulary: self, independent, origin-supplied, reported, source-only. Only an `independent` verdict can raise a QA class.
- **Cost.** `xf status` rolls up whole-loop cost (F3): CPU-seconds, wall time, joules and $ per KEEP, including killed and failed runs.

---

## 10. Staging-branch manifest: STAGING.md

**Location.** `claude/ledger:factory/xf/staging/<id>/STAGING.md`, next to `body.md`, `<id>.patch` and any fold-in or hand-port patches. STAGING.md is **never committed on the staging branch itself**, because the branch must stay a clean upstream-shaped commit. `xf status` renders `factory/xf/staging/INDEX.md` from all front matter, read-only.

**Branch.** The selected `staging/<id>`. A rebuild uses `staging/<id>-v2`, then `-v3`. Never force-push. Never delete an earlier version. Until OD-0 is resolved, the physical ref is local-only and the ledger patch is the artifact.

**Format.** TOML front matter between `+++` lines, then fixed sections.

```markdown
+++
xf_staging = 1
id = "edit-fuzzy-wrong-region"
version = 1
branch = "staging/edit-fuzzy-wrong-region"
branch_physical = "local-only (OD-0 pending)"
branch_sha = "<sha | null>"
status = "CANDIDATE"     # CANDIDATE | EVIDENCED | STAGED | VERIFYING | PROMOTION_READY | QUEUED | PROMOTED | LANDED | STALE | HOLD | LIMITED | CARRIER | SUPERSEDED_ON_MAIN | KILLED | WITHDRAWN
route = "salvage-row"    # core-leaf | salvage-row | support-note | decision-request | plugin-catalog | docs-leaf | eval-fix | internal | ride-along
feature = "edit-tool-fail-loud-and-meter"
invariant = "A single-line edit whose anchor only fuzzy-matches a different region must fail loud instead of editing that region."

[base]
repo = "NousResearch/hermes-agent"
sha = "e496ccc7d7"
fetched_at = "2026-10-01T…"

[upstream]
issues = ["#111116 (ours)", "#54572"]
eval_prs = [{ pr = 111127, author = "KoNit-K", head = "5444b1a2a8" }]
carrier = { pr = 0, author = "", head = "" }        # filled by F01
competitors = [
  { pr = 54575, author = "MaxFreedomPollard", head = "e28d7c772d", result = "" },
  { pr = 125376, author = "Finn763", head = "5f3f5896a4", result = "", note = "bundles bot_relay #95741 + email chore" },
]
close_after = []
demand = { score = 30, source = "demand reader 2026-10-01" }
maintainer_signal = ""

[[donors]]
sha = "<carrier head>"
author = "<carrier author>"
role = "carrier"

[[donors]]
sha = "<fold-in sha>"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "fold-in test"
trailer = "Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"

[ownership]
searched_at = "…"
queries = ["fuzzy_match wrong region", "#111116", "#54572"]
open_external = [54575, 125376]
merged_overlap = []
claimant_lanes = [127373, 127374, 127375, 127332, 127228]
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none (envelope <id>)"
verdict = "EXTERNAL -> salvage"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]                         # every receipt cited with its sha256; z0int eligibility: hashes must still match
receipts = [
  { id = "E01/r…", path = "factory/xf/receipts/E01/r….json", sha256 = "…" },
  { id = "F01/r…", path = "factory/xf/receipts/F01/r….json", sha256 = "…" },
]
red = { test = "…", main = "e496ccc7d7", marker = "…", receipt = "F01/r…" }
green = { reps = "3/3", receipt = "F01/r…" }
negative_control = { mutation = "per-hunk", result = "RED", receipt = "F01/r…" }
adjacent = { identical = true, pre_existing = [] }
guards = { F14 = "equal" }
quantitative = []                  # OBSERVED only; median + p95 + n + CI
cache_read_ratio = { status = "N_A" }
route_scope = "n/a"
not_tested = ["model behaviour after refusal (E02 deferred: needs >=64K local or paid)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-edit-fuzzy-wrong-region", commit = "" }

[gates]                            # §11; each PASS | FAIL | PENDING | N_A | RECORDED
P1 = "PENDING"
P2 = "PENDING"
P3 = "PENDING"
P4 = "PENDING"
P5 = "PENDING"
P6 = "N_A"
P7 = "PENDING"
P8 = "PENDING"
P9 = "PENDING"
P10 = "PENDING"
P11 = "RECORDED"
P12 = "PENDING"

[verification]
verifier = ""
provenance = "independent"
exact_head = ""
inputs = "raw diff + repo + oracle block only"
verdict = ""                       # APPROVE_EXACT_HEAD | CHANGES_REQUIRED | DISCARD_* | BLOCKED_EXTERNAL
qa_class = ""                      # CLEAN | CHECK | HOLD | FAIL_GAP (never set by the author worker)

[merge_check]
main_sha = ""
checked_at = ""
clean = false
recheck = "git merge-tree --write-tree main staging/edit-fuzzy-wrong-region"

[push]
no_follow_tags = true
workflow_push_matches = 0
pushed_at = ""

[body]
path = "factory/xf/staging/edit-fuzzy-wrong-region/body.md"
kind = "wave-row"                  # wave-row | pr-body | decision-doc | catalog-entry | support-note
tone_gate = { peer = false, no_labor = false, no_internal_leak = false, smallest_ask = false, self_service = false, local_voice = false, easy_decline = false }
jargon_lint = "PENDING"
privacy_scan = "PENDING"

[queue]
board = "kvnloo/hermes-agent#402"
position = "after existing rows"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

## Invariant
One sentence (repeat of front matter), plus the real call path exercised.

## Route and carrier choice
Why this route; why this carrier over each competitor (with the A/B line in WAVE.md row form).

## Evidence
Table: experiment | receipt | verdict | label | n | median/p95 or counts.

## Gate checklist (P1-P12)
One line per gate with the receipt that satisfies it.

## NOT_TESTED
Credential, device, TTY, browser, native-compaction, real-provider-cache boundaries as applicable.

## Origin action (owner only)
The single smallest ask: a wave row on #402, or one comment on the carrier thread, or `gh pr create ... --body-file body.md` (NOT run by the factory).

## History
Append-only: timestamp | status | worker | reason.
```

**Route variants.**
- `salvage-row`: `body.kind = "wave-row"`. The origin action is one wave row or one delta comment on the carrier thread. No new PR. No slot.
- `core-leaf`: `body.kind = "pr-body"`, following `.github/PULL_REQUEST_TEMPLATE.md`. The `gh pr create` command is recorded but never run.
- `plugin-catalog`: a standalone repo plus a SHA-pinned catalog entry.
- `decision-request`: one concise document backed by completed receipts.
- `internal` and `ride-along`: never get a board row of their own.

---

## 11. Promotion-ready

**Definition.** PROMOTION_READY means ready to ask a maintainer. It is never permission to merge (A2) and never claims a slot (A3).

**State machine.**

`CANDIDATE → EVIDENCED → STAGED → VERIFYING → PROMOTION_READY → QUEUED` (row on #402 or #404). After that, the owner moves it to `PROMOTED`, and it becomes `LANDED` when D6 holds (merge SHA with the content present).

Side states: `STALE`, `HOLD`, `LIMITED`, `CARRIER`, `SUPERSEDED_ON_MAIN`, `KILLED`, `WITHDRAWN`.

### 11.1 Gates (all recorded in STAGING.md)

| Gate | Requirement |
|---|---|
| **P1 Need** | RED reproduced on a main SHA whose `invalidate_on` paths have not changed since, and no older than 24 h at queue time. Otherwise `STALE`. Already fixed on main means `SUPERSEDED_ON_MAIN`. |
| **P2 Ownership** | Dedupe across open and merged PRs and issues. The route matches ownership: an external owner means salvage or support. Claimant lanes, holds and Hermes-lane items are clear, or coordinated by envelope (E1–E3). |
| **P3 Shape** | One invariant, the smallest complete surface. No new `HERMES_*` env for non-secret config. No hook without a fire site **and** a named consumer (E6). No re-export shims. No file pushed past about 2k lines. Profile or scope changes carry an A→B→A two-home E2E (H2). |
| **P4 Real path** | The failing call path runs through the production seam, with coverage proof. Only external boundaries (LLM, network, device) are faked. Credential, device, TTY and browser boundaries are marked NOT_TESTED. |
| **P5 Proof** | RED with the marker matched, GREEN 3/3, per-hunk SABOTAGE re-REDs with unpinned hunks listed, ADJACENT identical, F14 guards equal, `flaky = false`. |
| **P6 Numbers** | Required only if the body makes a value claim (tokens, cache, latency, recall). Pre-registered, A/A-calibrated, `CREDIT` (CI lower bound > 0, ≥ 5 pairs) on a human-curated battery, informative, OBSERVED headline, median + p95 + n. Caching-adjacent changes report the cache-read ratio before and after (I6). Otherwise the class is at most `LIMITED`, or the route is `decision-request`. Compaction claims declare route scope. |
| **P7 Package** | One commit on fresh main (or an unmodified carrier plus one fold-in), correct author and subject, contaminated paths excluded, `merge-tree` clean on current main, workflow-trigger scan = 0, `--no-follow-tags`. |
| **P8 Freeze** | Every cited receipt is frozen (write-once bundle, sha256 recorded) and frozen to z0evals. Nothing private is public. Cited hashes still match at the transition (z0int eligibility). |
| **P9 Text** | Template-conformant body with honest NOT_TESTED, all 7 tone-gate items, no factory jargon (no envelope, lane, E##, F##), no @mentions, AI assistance disclosed, privacy scan clean. |
| **P10 Independent read** | A different worker with blind inputs returns `APPROVE_EXACT_HEAD` and QA `CLEAN` on the exact head (B8, SPEC §5). |
| **P11 Demand / not lone substrate** | Demand score and maintainer signal recorded. Test-infra or eval-only content with no consumer is ineligible alone and must ride a real fix (D5). |
| **P12 Queue** | No `promotion_freeze`. Fewer than 5 frontier rows already PROMOTION_READY or QUEUED (staging cap). The row goes behind existing rows (T6). No slot claimed. |

### 11.2 Classes

| Class | Meaning |
|---|---|
| `PROMOTION_READY` | P1–P12 all hold |
| `LIMITED` | Everything holds except P6, which waits on OD-1 or OD-3 or on OBSERVED data. It may ship only as a decision request or support note. |
| `HOLD` | A concrete blocker: a design hold, a CONFLICTING carrier with no safe hand-port, an unresolved ownership question, or OD-0 |
| `KILLED` | The falsifier triggered. The negative result is kept and posted on the fork thread. |
| `STALE` | The merge or RED re-check failed on a newer main |

### 11.3 Global preconditions

- No branch can become PROMOTION_READY until **Wave 0** passes: F15, F14, E48 and F11.
- **E30 is the kill switch.** If the gates cannot separate merged human fixes from reverts, every transition to PROMOTION_READY halts. $0 experiments continue.
- Promotion computes nothing new. It reads frozen receipts and checks their hashes, freshness and the verifier's class.

**Steps outside the factory.** Publication approval (Linear Todo), CI admission (requested once, in the carrier context, G3), read-back merge and current-behaviour closeout (D1 steps 9–12) belong to the owner and the maintainers.

### 11.4 Per-branch ceiling at $0

| Staging id | Route | Upstream anchor | Best class reachable at $0 | Blockers |
|---|---|---|---|---|
| edit-fuzzy-wrong-region | salvage-row → #402 | #111116 (ours), #54572; carriers #54575, #125376; eval PR #111127 | PROMOTION_READY | OD-0 or OD-4 for the branch form. E02 deferred (no value claim needed). |
| compaction-anchor-retention | support-note for #122522 (teknium #122274); anchor-v2 as a later core-leaf | #122522 | LIMITED | E05 → E04 need OD-1 or OD-3; OD-7 for the private lanes |
| tool-result-projection-support | support-note for #107731 (teknium's cache-read bar) | #107731 | LIMITED | E37 live needs OD-3; the readtool guard's model arm needs OD-1 or OD-3 |
| compaction-hook-salvage | salvage-row → #402 | #64231 SALVAGE (#53806 as `on_compression_start`) | PROMOTION_READY (contract only) | Hand-port risk (heads from March to September). A consumer must be named (E6). |
| postmortem-logcalls-zero-hit | eval-fix | `logcalls.py` `_LINE` vs `turn_usage.py` | PROMOTION_READY only with F06/E19 showing the bias (P11) | OD-7 |
| compressor-media-extraction | core-leaf refactor | none known; checked at claim | PROMOTION_READY (parity plus static deltas; no perf claim) | Ownership check; P3 |
| cu-repeat-input-dedup | core-leaf; Hermes lane (E1) | none known | HOLD | OD-6 |
| memory-prefetch-metric | core-leaf | none known | PROMOTION_READY | Ownership check |
| anthropic-context-editing | core-leaf, opt-in, for #526 | #526 (teknium1, open) | LIMITED → decision-request | Caching-adjacent, so P6 needs F10 (OD-3) |
| prefix-parity-journeys | ride-along guard pack (D5) | none | STAGED (never alone) | Needs a real prefix bug to ride with |
| cu-capture-mode-projection | core-leaf | none | HOLD | OD-6; docker image; evidence so far is one Windows sample |
| observer-hooks-doc-drift | docs-leaf (DOCS_ONLY class in #64231) | #64231 | PROMOTION_READY | none known |
| factory-replay-gate | internal (`evals/_factory` adapters plus calibration) | kvnloo#322 | "factory-ready" (Wave 0 pass); never upstream | E20 needs OD-1 and OD-2 |
| plugin-catalog-entries | plugin-catalog (standalone repos, SHA pins) | none | LIMITED until E52 | OD-2 |

The staging cap means at most 5 rows are outstanding. Expected first READY candidates, as an estimate and not a promise: edit-fuzzy-wrong-region, observer-hooks-doc-drift, compaction-hook-salvage, memory-prefetch-metric and compressor-media-extraction. The last two depend on their candidate commits existing; donors are recorded in STAGING.md.

---

## 12. Safety rules (hard)

- **S1.** Zero writes to origin: no NousResearch PRs, comments, reviews, labels or issues. Zero Linear writes. Humans promote.
- **S2.** $0 by default. Paid runs need an owner-authored decision, checked by GitHub comment author, plus caps. Workers never hold credentials; the owner launches paid runs with injected credentials (K3, K4).
- **S3.** Never touch the live install:
  - `/workspace/hermes-home`, `/home/kvn/.hermes`, the live venv, the `hermes_cluster` process (L5), `/workspace/hermes-home/hermes-agent` as a source.
  - Never run `hermes`, `python -m hermes_cli.main` or `hermes update` without OD-2, and then only in bwrap from the disposable venv.
- **S4.** Network:
  - $0 lanes are loopback-only, enforced by netns and asserted by a connect probe.
  - The router profile allowlists only the local model host.
  - Venv builds are the only networked step, with a read-only root except the venv directory.
- **S5.** Privacy:
  - state.db, `agent.log*`, `.usage.json`, curator ledgers and lineages are **copied** into the private store and never read in place.
  - Only aggregates with n ≥ 5 per bucket are published.
  - The validator rejects session ids, home paths, emails, message text and secrets (K1).
- **S6.** Security-class repros stay off the public fork (K2).
- **S7.** Git:
  - No `git stash` (use diff and apply). `--no-follow-tags` on every push. Never force-push. Never delete or rename refs; OD-0 belongs to the owner.
  - Never use `promote/*`, `ready/*`, `wine2e/**` or `wine2e-install/**`.
  - `ls-remote` collision check before every push. No fork PRs. No new workflows. No @mentions.
- **S8.** Fork Actions: parse `.github/workflows/*` on the exact tree before every push and abort if any push trigger matches. No schedules (G1, G2).
- **S9.** No second scheduler. No cron, daemon, watcher or Actions. One claimed work order per invocation. `xf status`, locks and capacity_queue have no authority (C1).
- **S10.** GitHub write caps:
  - at most 5 new fork issues per day;
  - one `result` per verdict;
  - experiments are comments on campaign threads;
  - one ledger commit per loop iteration.
- **S11.** Resources:
  - worktrees and runs on `/mnt/zer0models`, never on `/tmp` tmpfs;
  - adaptive CPU admission; MemAvailable gate;
  - GPU flock, strictly serial, never preempting Quackles.
- **S12.** Never modify dirty or uncommitted checkouts, including `/home/kvn/tmp/evolution-lab`. Work in fresh worktrees and never overwrite another lane's unpushed state.
- **S13.** A worker never sets its own QA class. `execution_completed` never becomes `verified_success`. Promotion recomputes nothing.
- **S14.** Agent-written tests may support invariants only. Credit and value claims use human-curated batteries (I1).
- **S15.** Unlisted harnesses fail closed. A harness is added to the adapter allowlist only after a code read finds no exec, egress or credential access.
- **S16.** Infra failures are never silent. Every blocked exec or connect fails the cell as `INFRA` and is counted.
- **S17.** AI assistance is disclosed in every body, per repository policy.

---

## 13. First 30 queued experiments

**Queue rules.**
- One campaign per staging branch. Each row is a child `work_order`.
- Rows 1–5 are Wave 0. Nothing becomes PROMOTION_READY until rows 1–4 pass, and row 5 is the kill switch.
- Runners:
  - **T0** means replay or static on the `cpu` lane.
  - **T1** means FakeLLMServer, a scripted fake, or direct calls through real code paths on `cpu`.
  - `xf` always wraps the named harness inside the bwrap sandbox.
- **priv** means private inputs: results stay local and only aggregates publish (needs OD-7).

| # | Id | Staging branch | Experiment | Cost | Runner | Primary metric (label) | Status at queue time |
|---|---|---|---|---|---|---|---|
| 1 | F15 (new) | factory-replay-gate | Sandbox canary. From inside the profile, attempt a non-loopback connect, a write outside `$RUN`, a read of `/workspace/hermes-home`, the `$HOME/.hermes` pytest-guard path, an exec of `hermes`, and selection of a denylisted test. Each is blocked. With each guard removed in turn, the probe escapes. | $0 | T0, bwrap | blocked and escaped per guard (OBSERVED); pass = 6/6 blocked and 6/6 sabotage escapes | Wave 0 |
| 2 | F14 (new) | factory-replay-gate | Standing regression set ×2 on `e496ccc7d7`: `token_accounting/{replay_gates, ab_image_cost_calibration, worktree_prompt_prefix}`; `native_compaction/ab_checkpoint_preflight` capture/restore/over_threshold; `provider_fallback/probe_104120\|104260\|104360`; `goal_command_parity`; `compaction/test_region_scoping`; postmortem's 9 non-live probes plus 5 hand-run ones (context_cap, deadline, goal_scope, goal_repaste, finalizer_schedule) with an asserted red-on-base expectation table; readtool fixtures via direct `read_file` only | $0 | T1, upstream evals in-tree | verdict-map equality across runs (OBSERVED); becomes the per-arm guard baseline | Wave 0 |
| 3 | E48 | factory-replay-gate | `xf validate` plus 10 fault fixtures: missing RED, GREEN base, flaky reps, infra exit, GREEN negative control, adjacent regression, private-field leak, MODELED headline, stale base, unpinned PR head | $0 | T0 | 10/10 refused, clean fixture accepted, `verified_success` stays null on faults | Wave 0 |
| 4 | F11 | factory-replay-gate | Runner calibration: reproduce RED, GREEN and negative control on `ready/fork-47-ratelimit-missing-remaining-v2`, `ready/fork-112-kill-race-notify-attribution` and `ready/fork-50-honor-save-over-limit`; refuse 3 negatives taken from `rework.py` review-fix classes | $0 | T1, `run_tests.sh` | 6/6 classifications match recorded verdicts; false-READY = 0 | Wave 0 (exit criterion: 6/6) |
| 5 | E30 | factory-replay-gate | Evolver gate calibration. Positives: merged upstream fixes that add a test. Negatives: Revert commits and reverted PRs. Agreement against the AI-produced PROTOCOL verdicts is reported, not used as ground truth. | $0 | T1 plus evolver `gates.py` @`20eb166106` | false-credit rate on negatives (target 0), sensitivity on positives | Wave 0, **kill switch** |
| 6 | E01 | edit-fuzzy-wrong-region | Re-run the #111127 battery (`evals/edittool` at head `5444b1a2a8`, pinned) against main `e496ccc7d7` with direct tool calls and no model. Settles the critic's 6/6 vs 5/6 attribution question. | $0 | T0, direct calls | per-trap outcome counts (OBSERVED); RED expected on the wrong-region and missing-anchor traps | Runnable after Wave 0 |
| 7 | F01 (new) | edit-fuzzy-wrong-region | Carrier A/B on the contract test (spec in §7.1): main vs #54575 vs #125376 full head vs #125376 leaf vs both. Output is a WAVE.md row. | $0 | T1, `run_tests.sh` | RED, GREEN, NEG, ADJ and guards per arm, 3 reps (OBSERVED) | Runnable after #6 |
| 8 | F05 (new) | compaction-hook-salvage | Carrier A/B of 5 carriers vs main on one contract test (candidates in §0). The hook fires exactly once per local compression at the post-commit site (`_notify_context_engine_compression_complete`, about `conversation_compression.py:2564`; re-resolve the line at claim), never on the native route. The payload carries old and new session ids. The observer is fail-open. | $0 | T1, FakeLLMServer | gate columns per arm; merge class (clean, conflict, handported) | Runnable. Hand-port likely. |
| 9 | E12 | compaction-hook-salvage | `replay_gates` + `test_region_scoping` + `ab_checkpoint_preflight` (capture, restore, over_threshold) on the winning arm(s) | $0 | T1 | verdict maps equal base; 0 stubbed results (OBSERVED) | After #8 |
| 10 | F04 (new) | tool-result-projection-support | Projection byte-stability between boundaries, plus a preserved-thinking route check, on #107731 vs base. Guards: `replay_gates`, `test_region_scoping`, readtool fixtures. | $0 | T1, FakeLLMServer request log | mutations of earlier prefix bytes between boundaries (OBSERVED, loopback wire) = 0; thinking blocks preserved | Runnable |
| 11 | E37-off | tool-result-projection-support | `replay_lineage` on LOCAL state.db copies. Arms: base prune-off (default), base `proactive_prune_tokens = 48000`, #107731. | $0 priv | T0 | billed-input delta (**MODELED**, so it can never make the branch READY); prefix-rewrite count | Needs OD-7 |
| 12 | E03 | compaction-anchor-retention | Gold-identifier survival by category over `reconstruct_lineage` outputs from a LOCAL state.db copy. Results stay local (K1). | $0 priv | T0 | survival rate per category (OBSERVED over reconstructed inputs; input provenance recorded) | Needs OD-7 |
| 13 | F02 (new) | compaction-anchor-retention | Anchor budget audit on frozen lineages: the index stays at or under 7,000 chars and the summary under 32k tokens | $0 priv | T0 | max and p95 of index chars and summary tokens; violation count (OBSERVED) | Needs OD-7 |
| 14 | F06 (new) | postmortem-logcalls-zero-hit | Coverage recount on a LOCAL state.db plus `agent.log*` copy, current vs patched regex (`cache=` optional, default 0, plus `usage=unavailable` lines) | $0 priv | T0, `forensics/logcalls.py` | coverage % and hit-ratio delta (OBSERVED) | Needs OD-7 |
| 15 | E19 | postmortem-logcalls-zero-hit | Cache-read loss around a mid-conversation model switch: baseline with the current regex, rerun after the fix | $0 priv | T0, logcalls + tokens | cache-read ratio before and after the switch, coverage printed first (OBSERVED) | After #14 |
| 16 | E14 | compressor-media-extraction | `static_metrics` + `lookup_sim` before and after, plus `scripts/run_tests.sh tests/agent/` parity | $0 | T0 (separate tiktoken and radon venv) plus T1 | size, complexity and lookup deltas (OBSERVED static); identical pass set | Runnable |
| 17 | E25 | cu-repeat-input-dedup | Re-prove RED and GREEN on main `e496ccc7d7` | $0 | T1 | RED marker matched, GREEN 3/3, NEG RED | Runs. Promotion is HOLD (OD-6). |
| 18 | F07 (new) | cu-repeat-input-dedup | Real-path turn test through FakeLLMServer plus a test-only stub cua backend (none exists on main; `driver_fixture.py` is a package-manager fixture) | $0 | T1 | duplicate actions dispatched per turn (OBSERVED); GREEN 3/3 | Runs. Promotion is HOLD (OD-6). |
| 19 | E17 | memory-prefetch-metric | Delay, hang, empty and error fault probe against a local fake provider, extending the `evals/memory/honcho_current_query.py` pattern, plus a ContextVar scope test | $0 | T1, local HTTP fake | prefetch p50 and p95, outcome class per fault, scope pass or fail (OBSERVED) | Runnable |
| 20 | F08 (new) | memory-prefetch-metric | Per-outcome RED and GREEN with the `record_` call reverted | $0 | T1 | each outcome goes RED when reverted (OBSERVED) | After #19 |
| 21 | F09 (new) | anthropic-context-editing | Gate probe on a fake Anthropic Messages server (`tests/fakes/providers/anthropic_messages.py`). The payload is present only when opted in and eligible. A 400 disables it and retries once. The local compressor still fires over threshold. `replay_gates` is unchanged. | $0 | T1 | 4 assertions plus guards (OBSERVED) | Runnable |
| 22 | F13 (new) | observer-hooks-doc-drift | Code vs docs key diff: AST-collect the kwargs passed to observer hook invocations at e496ccc7d7 and diff them against `website/docs/developer-guide/observer-hooks.md` | $0 | T0, static | undocumented key set. RED on main must include `first_chunk_at`, `context_length` and `moa_references` (0 doc hits verified). The branch must give the empty set. | Runnable |
| 23 | E07 | prefix-parity-journeys | Extend `tests/e2e/core/history/test_prefix_stability.py` with A2A JSON-RPC, the relay `stub_connector`, `/goal` continuation, api_server and ACP journeys. MoA user/user is whitelisted. | $0 | T1 | `prefix_breaks` per journey (1 expected, at compaction) (OBSERVED) | Runnable (ride-along) |
| 24 | E08 | prefix-parity-journeys | Identity joins on Hermes `turn_id` `<session>:<task>:<8hex>` (`turn_facade.py:65`) across entrypoints, with identical `plugins.toml` per arm | $0 | T1, parity helpers | join completeness % per entrypoint (OBSERVED) | Runnable |
| 25 | E09 | prefix-parity-journeys | Submit-to-first-delta latency per surface: FakeLLMServer `delay_per_chunk`, 30 reps, in-process drivers, plus the api_server `_create_agent` share. Re-checks the stale #48204 claim. The `chat -q` arm needs OD-2. | $0 | T1, **cpu-quiet**, exclusive | median and p95 per surface after A/A (OBSERVED) | Runs when load1 < 4 |
| 26 | F12 (new) | plugin-catalog-entries | Offline census of each plugin at its pinned SHA: registered vs declared capabilities, internal-path imports, self-updaters, desktop-surface violations | $0 | T0, static (AST, no import or exec) | violation counts per plugin and class (OBSERVED) | Runnable |
| 27 | E23 | cu-capture-mode-projection | sandbox-desktop image with cua-driver 0.28.2, at least 40 captures per mode per arm, main vs branch | local | `docker` lane | median, p95 and timeouts per mode (OBSERVED) | HELD: OD-6 plus image availability |
| 28 | E05 | compaction-anchor-retention | Compaction exam run-to-run SD at 15 vs 30 questions on a frozen lineage mix (the 78.9 bar = 76.7 / 90.0 / 70.0), aux model via `auxiliary.compression` | local or paid | T2 (`gpu`) or T3 | SD and MDE per question count | GATED: OD-1 (64K preset; the aux path also enforces the floor) or OD-3 |
| 29 | E37-live | tool-result-projection-support | Decisive live cache arm: `cache_concurrency_probe` (about $50 per arm), or shared-metrics `cache_break` + `model_tokens` on py3.14, with prune-off and prune-on baselines | paid | T3 | cache-read ratio before and after (OBSERVED), against teknium's bar | GATED: OD-3; owner launches |
| 30 | F10 (new) | anthropic-context-editing | `cache_read` and `cache_creation` per turn before and after a clear, plus a compaction-exam arm | paid | T3 | cache_read and cache_creation per turn (OBSERVED); exam recall delta | GATED: OD-3; owner launches |

**Queued after the first 30 (parked, with reasons):**
- **E04** (compaction-anchor-retention): anchor-v2 vs current+recovery on a frozen lineage mix. Needs E05's SD first and an aux LLM.
- **E20** (factory-replay-gate): A/A noise floor. Needs OD-1, plus OD-2 because toolperf runs the CLI.
- **E52** (plugin-catalog-entries): `hermes plugins validate` in an isolated HERMES_HOME. Needs OD-2.
- **E02** (edit-fuzzy-wrong-region): needs a ≥64K-context local model or a paid API.
- **E24** (cu-repeat-input-dedup): verdict distribution per action type. Waits for E25 and F07, and OD-6.
- **E11** (prefix-parity-journeys): cells for `/goal` active, kanban worker and MoA adjacency. Must be framed as a narrow control point, because #47092's universal gate was rejected in #64231.

### 13.1 Week-1 sequencing (estimate)

- **Day 1.**
  - Build the `xf` core (spec loader, arms, bwrap, JSONL, gates, receipts, validate), `h.git` and the venv.
  - Run F15, F14, E48 and F11. Exit criteria: F15 6/6, F14 maps identical, E48 10/10, F11 6/6. Fix `xf` before anything else runs.
  - Start E30.
- **Day 2.** E01, F01, F13, F09. Start F05 (hand-ports). Write the fold-in contract tests.
- **Day 3.** E12, F04, E25, F07, E17, F08, E14. Blind-verify the day-2 rows.
- **Day 4.**
  - If OD-7 is granted, the private lanes: F06 → E19, E03, F02, E37-off. They are CPU-light and run in parallel.
  - E07, E08, F12.
- **Day 5.** E09 on the exclusive quiet lane. Blind-verify. Write STAGING.md files and bodies.
- **Days 6–7.**
  - Freshness re-check against the newest main for every KEEP. Post PROMOTION_READY state comments, up to the cap of 5.
  - E23 if OD-6. Gated rows wait on OD-1 and OD-3.

---

## 14. Scaling to hundreds

1. **Generators instead of hand-written specs.** Each template instantiates many specs. Spec count grows by template × input, while authoring cost stays flat.
   - **T-carrier.** Every upstream issue with two or more open external PRs on the same defect becomes an F01-style A/B. Input uses the `clusters-W1/W2.json` schema. The pool is about 420 open external PRs (PLAN §7). This is the main engine, and its output is salvage_cherry rows that need no slot.
   - **T-regress.** Every staging branch × the F14 standing set (about 20 probes).
   - **T-fresh.** A daily `merge-tree` plus RED/GREEN on the 73 READY items, the 40 #404 rows and every live STAGING.md (D8).
   - **T-flip.** One spec per opt-in knob × replay shape (cli, gateway, restore). Knobs: `proactive_prune_tokens`, `micro_compact`, `idle_compact_after_seconds`, `verify_on_stop`, `dashboard.turn_isolation`, the threshold floor, cache TTL 5m vs 1h, delegation effort.
   - **T-size.** One forensics lane per feature on private copies.
   - **T-parity.** Journeys × surfaces.
2. **Never pay twice.**
   - Content-addressed `cell_key` means identical cells never re-run.
   - Base cells are shared, so N candidates on one base cost (N + 1)·k cells instead of 2N·k.
   - Path-scoped `invalidate_on` limits re-runs on a new main to the proof and guard cells, which are cheap.
3. **Throughput (estimates, UNVERIFIED).**
   - A targeted test file takes about 40 s, so a red/green experiment takes about 7–15 CPU-minutes. At 3–4 admitted workers that is about 15–30 experiments per hour.
   - A 100-cell T1 A/B takes about 5 minutes on 6 workers.
   - E09 is the largest single experiment: about 480 cells × 5 s.
   - Hundreds of $0 experiments fit in a few days of CPU. The GPU lane handles about 60–100 serial cells per hour minus Quackles windows, and stays idle for Hermes until OD-1.
4. **The real bottleneck is verification, not compute.**
   - Scale the blind-verifier pool across the Claude, grok and codex lanes, addressed by envelope.
   - Only CLEAN exact-head reads advance. Verifier load is bounded by the staging cap: at most 5 rows outstanding, because main moves about 700 commits a day and 40 rows are already ahead.
5. **Queue and GitHub hygiene at volume.**
   - Campaigns (one per staging branch or generator family), never one issue per experiment.
   - At most 5 new issues per day, one result per verdict, one ledger commit per loop iteration.
   - `QUEUE.md` and `INDEX.md` are read-only projections.
6. **Stop wasting runs.**
   - Per-family kill criterion: 20 consecutive experiments with zero KEEP or CREDIT stops the family and posts a learning record.
   - The informativeness gate stops saturated slices. For reference: 80 autoresearch sessions produced 0 keeps, and a canary was minted on a 32/32 slice.
   - Whole-loop $ and joules per verified success are tracked, including failures (F3).
7. **Lanes that unlock later.**
   - OD-1 enables local metric lanes (E02, E20, E04/E05) under the serial GPU protocol.
   - OD-2 enables toolperf and the CLI lanes.
   - OD-3 enables only budgeted, owner-launched confirmations of LIMITED items, prioritized by demand. Projection, at demand 55, is first.
   - The kind lane is for contention cells only. It adds no capacity.
8. **Evidence growth stays bounded.** z0evals studies are frozen only for receipts a STAGING.md cites. Everything else stays as write-once ledger receipts plus private bundles.

---

## 15. Owner decisions

| Id | Decision | Unblocks |
|---|---|---|
| **OD-0** | Resolve `refs/heads/staging` on kvnloo/hermes-agent (`28790e597c`, 2026-09-10 merge of fork PR #9; diverged 8 ahead / 19,840 behind). (a) Archive it (for example, push a tag or branch with the same SHA under an archive name) and remove the branch. (b) Or pick a different physical prefix and keep `staging/<id>` as the logical id. The factory does neither. | Every staging push |
| **OD-1** | Add a context preset of at least 64K: either on the llama.cpp router (Qwen3-8B q8_0 KV ≈ 9.7 GB, or Qwen3-4B; VRAM fit UNVERIFIED), or via ollama with a served `num_ctx` of at least 64K. The installed qwen2.5 models are natively 32K, so they would need rope scaling. A config override that claims 64K while the server serves less is not allowed. | E02, E04, E05, E20, the readtool model arm, all local Hermes arms |
| **OD-2** | Allow `hermes` CLI entrypoints inside bwrap from the disposable venv, never the live install | E52, E20 (toolperf), the E09 `chat -q` arm, runtime_bench |
| **OD-3** | A paid budget per experiment, a credential holder who is not a worker, and confirmation that the owner launches. Proposed: E37-live at about $50 per arm; F10 small; E05/E04 paid path only if OD-1 is declined. | Rows 28–30, E04 |
| **OD-4** | Push salvage fold-ins as `staging/<id>` (our commit on an unmodified public carrier head), or keep them as ledger patches only | The branch form for edit-fuzzy-wrong-region and compaction-hook-salvage |
| **OD-5** | Approve kvnloo/evolution-lab `exp/hermes-factory-v0` as the executor home. Fallback: hermes-k8s-lab, local, no remote. The evolution-lab owner commits `slice_informativeness.py` and its test (currently untracked). | Pushing runner code; the informativeness gate |
| **OD-6** | CU/Jev hold scope: may E23, E25 and F07 run, and may cu-\* branches reach PROMOTION_READY? Also Hermes-lane ownership of cu-repeat-input-dedup (E1). | Rows 17, 18, 27; E24 |
| **OD-7** | Privacy approval to copy state.db, `agent.log*` and lineages into the private store for aggregate-only lanes | Rows 11–15 |
| **OD-8** | Confirm the staging cap of 5 and strict ordering behind the 40 #404 rows (T6) | P12 |
| **OD-9** | May the factory create `[frontier] <id>` threads, or only reuse existing ones (#322, #310, #311, #332, …)? | Campaign posting |

---

## 16. Risks

1. **Ownership optics.** Most output adjudicates other people's PRs, which can read as spray. Mitigation: one wave post per batch, fold-ins only, one concrete delta per thread, never a parallel PR, and the reason for each carrier choice recorded.
2. **Bundled carriers.** #125376 carries an unrelated `bot_relay` fix. Mitigation: leaf arms and surface accounting in `carrier_choice`. Never cherry-pick a foreign commit into our own leaf without credit.
3. **Hand-port risk.** Hook carriers date from March to September. Mitigation: a hand-port is a recorded patch with its own negative control. A CONFLICTING carrier with no safe port goes to HOLD.
4. **MODELED read as OBSERVED** (projection, prune flips, anchor recall). Mitigation: labels everywhere, the validator rejects MODELED headlines, and these branches stay LIMITED until OD-3 or OD-1 evidence exists.
5. **Agent-written oracles overfitting.** Mitigation: per-hunk sabotage, a coverage-checked seam, carrier and maintainer tests preferred, a blind verifier, and E30 as the kill switch.
6. **Leaks of private data to the public fork.** Mitigation: copies only, an exporter allowlist plus scan, n ≥ 5 buckets, salted ids, OD-7.
7. **Live-install or host damage.** Mitigation: three sandbox layers (§6), F15 re-run on change, and fail-closed harness admission.
8. **Main churn** (about 700 commits a day). Mitigation: daily base, `invalidate_on`, the 24 h freshness gate, the staging cap.
9. **Shared-host noise and OOM** (load 3.7–18.7, Quackles GPU, OOMKilled pods). Mitigation: adaptive admission, an exclusive quiet lane for timing, A/A floors, never whole-app CPU or FPS claims.
10. **Scheduler creep.** Mitigation: S9. Capacity_queue mirrors carry `provenance`. Rank is owner-only.
11. **Dependency risk.** Evolver gates are on a fork branch, `slice_informativeness` is uncommitted, and evolution-lab has red CI on PR #28 (per evidence-first). Mitigation: vendor pinned copies, and Wave 0 validates them before anything depends on them.
12. **Stale catalog and KB claims.** Mitigation: the current-main need check runs at admission, not at mint, and PR heads are resolved and pinned at claim.

---

## 17. Provenance of this blueprint

**Checked in this synthesis:** everything in §0.

**Taken from the designs and not re-checked here:**
- SPEC §2/§4/§5/§7 contents.
- The 13 open factory PRs and the A5 sweep inputs.
- Evolver gate behaviour.
- Throughput and VRAM estimates.
- The cost of `cache_concurrency_probe`.
- nemo-relay installability.
- FakeLLMServer header scripting.
- "Evolution Lab owns execution per the z0 registry".
- Constraint IDs and their wording.
- Demand scores.

**Sources:**
- The three designs (mvp-first, scale-first, evidence-first).
- The selected staging set.
- `/mnt/zer0models/project-artifacts/hermes-agent/{frontier-2026-10-01, promotion-readiness-2026-10-01, salvage-wave-2026-10-01}/`.
- Scratch mirror `h.git` at `e496ccc7d7`.
- Scratch gap-fill reports `core_modules_gapfill.json`, `upstream_evals_reader.json` and `demand/out.json`.
- The repos listed in §0.