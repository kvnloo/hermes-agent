# ADR: Hermes Harness Debug Mode

- Status: Proposed; implementation and live activation require independent review
- Decision owner: Captain
- Architecture task: `t_bcfe53e8`
- Audit hub: `t_7e31b02a`
- Repository baseline: `62c9ef27a494fca6e89c6fdf2d13660cd2dbf066`
- Scope: governed orchestration verification; no production mutation or automatic repair

## 1. Decision

Hermes will expose Harness Debug Mode through one command family:

```text
/orchestration debug status [--run RUN_ID] [--json]
/orchestration debug start SUITE --duration DURATION --fanout N --cpu-seconds N --memory-mib N --disk-mib N [--seed UINT64]
/orchestration debug stop RUN_ID
/orchestration debug report RUN_ID [--format json|markdown]
/orchestration debug cleanup RUN_ID [--expired]
```

`SUITE` is required and is one of `smoke`, `lifecycle`, `adversarial`, `restart-recovery`, or `full`. `full` additionally requires a second explicit Captain confirmation bound to the proposed run manifest hash. There is no implicit suite, unbounded mode, unattended promotion, or production repair.

The slash command is the operator surface; the implementation should share an internal `hermes orchestration debug ...` argparse service entry so CLI and gateway do not duplicate policy. The existing command registry does not currently define `orchestration`; implementation therefore adds that command family rather than overloading the unrelated existing `/debug` diagnostic-upload command. The existing Kanban dashboard `/orchestration` HTTP endpoint remains configuration UI and is not the execution authority.

Entering debug creates one run-scoped capability envelope and a disposable board. Production is read-only. All synthetic tasks, comments, events, faults, workers, locks, and workspaces belong to the disposable namespace. A debug run may produce a report or reviewed repair-card proposal, but never changes production state.

## 2. Context and evidence

Repository patterns used by this design:

- `hermes_cli/commands.py` is the canonical slash-command registry.
- `hermes_cli/kanban.py` uses nested argparse subcommands and a global board scope.
- `tools/kanban_tools.py::_connect` resolves `HERMES_KANBAN_DB` before `HERMES_KANBAN_BOARD`, current symlink, and default. Debug workers must not use this ambient chain.
- `hermes_cli/kanban_db.py::dispatch_once` already emits exact dispatch reasons and bounded dispatch-health telemetry, including `nonspawnable_profile`, `global_capacity`, per-profile capacity, claim SLA, stale, timeout, and single-dispatcher-lock outcomes.
- Runtime activity bridges to claim and worker heartbeats, while stale run IDs are rejected.
- Existing tests already exercise poison-head fairness, bounded queue rotation, capacity, claim/heartbeat/reclaim, review/change cycles, crash reconciliation, and dispatch locking. Debug mode composes these real APIs against a disposable DB rather than reimplementing the state machine.

Measured audit findings that become mandatory regression fixtures:

1. 165 of 239 live `task_links` rows were dangling.
2. 24 ready and 3 review rows showed capacity waiting, including historical `global_capacity` reasons.
3. Synthetic `capture-fixture` attention receipts existed unnamespaced in the production board.
4. The production `current` symlink was absent while explicit `HERMES_KANBAN_DB` and `HERMES_KANBAN_BOARD` pinned the board.
5. Worker logs reported an unknown `kanban_cluster` toolset and deprecated `TERMINAL_CWD` configuration.

These observations are inputs only. Debug mode must not copy production rows into its mutable DB or attempt repair.

## 3. Authority and trust boundaries

### Roles

| Role | Authority |
|---|---|
| Captain | Starts/stops runs, approves `full`, authorizes later repair work |
| debug controller | Validates capability envelope, snapshots production read-only, creates sandbox, enforces budget, seals evidence |
| Sol medium orchestrator | Owns debug hub and bounded fixture schedule; cannot certify |
| Luna max-effort specialist | Executes one assigned fixture class; cannot expand scope or certify |
| independent verifier | Runs mechanical oracles from sealed evidence; cannot build fixture under review |
| critic | Reviews threat coverage and UNKNOWN classifications; cannot convert UNKNOWN/FAIL to PASS |

Builder/test author cannot be the sole certifier. A PASS requires controller checks plus a verifier identity different from every fixture author identity. Human approval is not inferred from `$USER`, process owner, chat sender fallback, or ambient profile.

### Capability envelope

Before any sandbox write, the controller seals:

```json
{
  "runId": "hd_<uuid7>",
  "captainIdentity": "explicit-platform-scoped-id",
  "commandNonce": "random-256-bit",
  "suite": "smoke",
  "seed": 0,
  "codeRevision": "git-sha",
  "model": {"orchestrator": "gpt-5.6-sol", "specialist": "gpt-5.6-luna"},
  "provider": "openai-codex",
  "budget": {"durationSeconds": 300, "fanout": 2, "cpuSeconds": 240, "memoryMiB": 2048, "diskMiB": 512, "taskCount": 24, "eventCount": 1000},
  "allowedRoots": ["<managed-debug-root>/<runId>"],
  "denied": ["production-write", "public-network", "root", "credential-read", "current-symlink-write"],
  "inputSnapshotHash": "sha256:..."
}
```

The command parser may lower requested limits but never raise suite ceilings. Model/provider resolution is exact and fail-closed; no fallback substitutes for Sol or Luna.

## 4. Isolation transaction

Managed root:

```text
$HERMES_HOME/kanban/debug-runs/<runId>/
  RUN_MARKER.json
  envelope.json
  snapshot/
  board/kanban.db
  board/board.json
  workspaces/
  logs/
  evidence/
  report.json
  report.md
  SEALED
```

`RUN_MARKER.json` contains schema version, run ID, explicit Captain identity, owner process identity, creation time, TTL, random nonce, and canonical production sentinel hash. The debug board slug is `debug-<runId>` and is never registered as current.

Creation is fail-closed and ordered:

1. Resolve every production DB candidate: explicit DB env, board env, current symlink target, default DB, and all discovered board DBs. Open production only in SQLite read-only URI mode with `PRAGMA query_only=ON`.
2. Snapshot the production sentinels before creating the sandbox: canonical config bytes/hash, board DB file identity and SQLite logical sentinel, current-link identity or absence, service/plugin inventory receipts, and selected task/event identities. Secrets are represented only as `{present, source, sha256(redacted-or-key-name)}`; values never enter evidence.
3. Create the run root using exclusive creation; reject symlinks in every path component. Require owner-only permissions.
4. Create the candidate DB with exclusive creation. Before schema initialization and again before first mutation, compare `realpath`, `st_dev`, and `st_ino` against every production DB and compare parent roots. Reject hard links, symlinks, bind aliases when detectable, paths outside the run root, or inability to stat a candidate.
5. Write marker and board metadata before dispatch. The board metadata must identify `kind=harness-debug`, run ID, TTL, and `production=false`.
6. Spawn children with a minimal environment built from an allowlist. Explicitly set `HERMES_KANBAN_DB=<run board absolute path>` and `HERMES_KANBAN_BOARD=debug-<runId>`; remove inherited Kanban DB/board/task/run/claim variables first. Do not pass production credentials, `.env`, tokens, `TERMINAL_CWD`, network proxies, or a current-board link.
7. Open child DB handles only through an API that requires the sealed run context and exact DB path. Do not call ambient `_connect(None)` in debug code.

Isolation proof is a prerequisite state, not a warning. Any unresolved alias, unreadable sentinel, changed production identity during preflight, unexpected inherited variable, or unsupported sandbox boundary yields `REFUSED_ISOLATION` with zero synthetic task writes.

## 5. State machine and reason codes

```text
PROPOSED
  -> PREFLIGHTING
  -> REFUSED_* | SNAPSHOTTED
  -> SANDBOX_READY
  -> RUNNING
  -> STOPPING | VERIFYING
  -> PASS | FAIL | UNKNOWN | ABORTED
  -> SEALED
  -> CLEANED
```

Terminal evidence status and storage lifecycle are separate: `PASS/FAIL/UNKNOWN/ABORTED` is sealed before `CLEANED`. Cleanup never turns a result into PASS.

Required exact reason-code families:

- `REFUSED_AUTHORITY`, `REFUSED_SUITE`, `REFUSED_MODEL`, `REFUSED_BUDGET`
- `REFUSED_ISOLATION`, `REFUSED_PRODUCTION_CHANGED`, `REFUSED_SECRET_SURFACE`
- `BUDGET_DURATION`, `BUDGET_FANOUT`, `BUDGET_CPU`, `BUDGET_MEMORY`, `BUDGET_DISK`, `BUDGET_TASKS`, `BUDGET_EVENTS`
- `ORACLE_STATE_TRACE`, `ORACLE_EVENT_TRACE`, `ORACLE_DUPLICATE_SPAWN`, `ORACLE_WRITE_BOUNDARY`, `ORACLE_SENTINEL`, `ORACLE_NETWORK`, `ORACLE_REDACTION`
- `UNKNOWN_INSTRUMENTATION`, `UNKNOWN_EXTERNAL_SUPERVISOR`, `UNKNOWN_NONDETERMINISM`
- `STOP_REQUESTED`, `WORKER_CRASH`, `CLEANUP_INCOMPLETE`

No free-form-only failure. Each finding contains a code, fixture ID, expected, observed, evidence paths, and minimal repro.

## 6. Deterministic fixture and fault catalog

Every fixture has a stable ID, schema version, seed derivation `SHA256(runSeed || fixtureId || fixtureVersion)[:8]`, exact initial rows, ordered actions, expected state/event trace, write-set glob, budget, fault point, and oracle list. Wall-clock values use an injected logical clock. Task IDs and spawn PIDs are normalized to fixture aliases only in comparisons; raw evidence retains actual values.

| Fixture family | Required cases | Principal oracle |
|---|---|---|
| lifecycle | create, promotion, claim, spawn, lease, heartbeat, stale reclaim, crash reclaim, retry, timeout, review, changes, done, archive | exact task/run/event transition graph; stale run cannot mutate current attempt |
| dependencies | fan-out/fan-in, missing parent, missing child, dangling edge, cycle, blocked parent, superseded task | no promotion unless every extant required parent is done; malformed graph gets exact refusal/diagnostic |
| profiles | unknown, nonspawnable control lane, capability-poor, exact model unavailable | `nonspawnable_profile` or capability reason; no silent profile/model fallback |
| capacity/fairness | global cap, per-profile cap, poison head, persistent poison prefix, starvation | bounded rotation; dispatchable tail progresses; exact capacity reason; no duplicate spawn |
| goal judge | unavailable judge, protocol-invalid verdict, exhausted turns, dependency deadlock | documented fail-open only for unavailable judge; invalid protocol is UNKNOWN/FAIL, never completion |
| policy | freeze, focused, debug allow/deny, stale receipt, mismatched receipt hash | receipt bound to mode/revision/manifest; stale cache cannot authorize |
| attention | `/chat` delivery while execution runs, coalescing, fixture replay | attention is delivery, not execution authority; one receipt per idempotency key |
| contamination | inherited DB env, current-link fallback, canonical sentinel, unnamespaced fixture | debug DB receives all fixture writes; production bytes/logical sentinel unchanged |
| restart/recovery | controller restart, stale PID/lock, dispatcher restart, duplicate notifier | one live owner/listener/dispatcher; recovery resumes from sealed journal without duplicate side effect |
| plugins/config | plugin load identity, missing surface receipt, config precedence | loaded implementation hash/surface is explicit; precedence matches expected source |
| untrusted input | secret-shaped values, prompt injection in body/comment, path traversal | content remains data; no policy expansion, secret leak, or out-of-root write |
| storage faults | busy DB, bounded corruption copy, migration failure/rollback | only sandbox copy faulted; last good snapshot recoverable; production unopened for write |

The dangling-dependency fixture must include a sandbox copy of the *shape* `165 dangling / 239 links` without production IDs or bodies, plus a small minimal case. The capacity fixture must include 24 ready and 3 review synthetic rows with stable aliases. The contamination fixture must plant `capture-fixture` records only in the debug DB and assert the production attention sentinel remains identical.

## 7. Mutation/adversarial protocol

An adversarial case is valid only when it demonstrates both states using the same fixture and oracle implementation:

1. Establish GREEN baseline.
2. A mutation operator deliberately breaks one sandbox invariant (for the first slice: hard-wire one debug connector to a guarded production-sentinel alias or simulated alias; the guard must refuse before SQLite write).
3. Oracle must turn RED with the expected exact reason code.
4. Remove mutation and rerun from a fresh sandbox with the same seed.
5. Oracle must return GREEN.

Never repair a mutated run in place and call it restored. Each leg has a separate board and evidence hash linked by `mutationPairId`. A verifier who did not author the mutation signs the comparison.

## 8. Oracles

Mechanical certification consumes sealed records, not dashboard state or worker prose.

1. **State graph:** compare every task/run terminal state and transition against the fixture trace.
2. **Event graph:** exact ordered kind and normalized payload; unexpected, missing, or duplicate events fail.
3. **Write boundary:** inventory inode/path/hash before and after; every changed path must be under the run root. Production SQLite logical sentinel includes schema version, table row counts, max event ID, and canonical hashes of selected identity rows; WAL/SHM churn alone is avoided by read-only connections.
4. **Spawn uniqueness:** at most one successful spawn per `(taskId, runId, claimLock)`; process and event evidence agree.
5. **Reason codes:** queue and refusal reasons match the contract, including capacity and nonspawnable cases.
6. **Resource ceiling:** cgroup/job-object or equivalent supervisor measurements prove duration, process/fanout, CPU, RSS, disk, task, and event limits.
7. **Network ceiling:** default deny at the process boundary. Socket telemetry alone is not sufficient enforcement. Mock loopback endpoints for network fixtures are explicitly declared in the envelope.
8. **Redaction:** canary secret values never appear in prompts, task bodies, comments, logs, reports, process argv, or environment captures.
9. **Production sentinel:** before/after canonical config bytes, current link identity, production DB logical identity, and controlled service inventory are equal. A concurrent legitimate production change makes the result UNKNOWN, not PASS or automatic rollback.

Status aggregation is strict: any FAIL -> FAIL; otherwise any UNKNOWN -> UNKNOWN; otherwise all required fixtures PASS -> PASS. Skipped required fixtures are UNKNOWN.

## 9. Suites and budgets

Hard ceilings are implementation constants; config may only lower them. Resource figures are initial conservative targets and require review against CI hosts.

| Suite | Duration | Luna fanout | Tasks/events | CPU | RSS | Disk | Network |
|---|---:|---:|---:|---:|---:|---:|---|
| smoke | 300 s | 2 | 24 / 1,000 | 240 s | 2 GiB | 512 MiB | denied |
| lifecycle | 1,800 s | 4 | 160 / 10,000 | 1,800 s | 6 GiB | 2 GiB | denied |
| adversarial | 1,800 s | 6 | 240 / 20,000 | 3,600 s | 10 GiB | 4 GiB | denied |
| restart-recovery | 1,800 s | 4 | 120 / 12,000 | 2,400 s | 8 GiB | 4 GiB | loopback mocks only |
| full | 7,200 s | 10 | 600 / 50,000 | 10,800 s | 16 GiB | 10 GiB | denied except declared mocks |

The controller counts itself and Sol separately from Luna fanout. Global process ceiling is `fanout + 3` (controller, Sol, verifier). Only one active specialist per rejection class. After two failures of one class, stop resubmitting the same approach; after three, terminate the suite and require Captain review. WIP is fixture-class bounded, not merely global worker bounded.

## 10. Snapshot, manifest, and reporting schema

Snapshot collection is read-only and includes:

- code revision plus dirty-state metadata without copying foreign file contents;
- redacted effective config provenance and hashes;
- profile names, existence/spawnability, declared model/provider/toolsets, and capability receipts;
- board paths/metadata and read-only logical sentinels;
- dispatcher/gateway/service identity and health receipts;
- plugin manifest, source hash, SDK/surface, and observed load receipt;
- capacity counters and policy receipt identities;
- current-link existence/target identity.

`report.json` is canonical and contains:

```text
schemaVersion, runId, suite, seed, command, authorityReceipt,
envelopeHash, codeRevision, configHash, snapshotHash,
boardIdentity, modelIdentities, budgets{requested,effective,observed},
fixtures[{id,version,seed,status,reasonCodes,expected,observed,evidence,repro}],
oracles[], mutationPairs[], productionSentinel{before,after,equal},
redactionSummary, cleanup, overallStatus, verifierIdentity, sealedAt
```

`report.md` is a projection from JSON and starts with:

```text
STATUS / SUITE / RUN / SEALED HASH
✅ passed invariants
❌ failed invariants
❓ unknown/unmeasured
🧹 cleanup and retained evidence
➡️ minimal repro / reviewed next action
```

Every run also records the exact fixture-code hash, config hash, schema version, model/provider strings, seed, and minimal repro. Repro commands create a new sandbox; they never reuse or mutate sealed evidence. Evidence entries include byte size and SHA-256. Reports never assert that a dashboard view is proof.

## 11. UX contract

- `status` is read-only and shows controller state, elapsed/remaining budget, active worker count by exact profile/model, current fixture, redacted board identity, production-sentinel status, and last reason code.
- `start` prints a proposed envelope and requires explicit Captain confirmation. Noninteractive starts require a signed/nonce-bound approval argument supplied by the trusted gateway control plane, not a general task body.
- `stop` immediately closes admission, signals children, waits a bounded grace period, kills only PIDs proven to belong to the run, then verifies and seals ABORTED/FAIL/UNKNOWN evidence.
- `report` reads only sealed or explicitly `--include-running` evidence; running output is prominently uncertified.
- `cleanup` refuses while owned workers are live, evidence is unsealed, production sentinel is unresolved, or target marker/run ID does not match. It never follows symlinks.

Suggested compact status:

```text
🧪 Harness Debug  hd_…  RUNNING  smoke  seed=…
🤖 Sol 1/1 · Luna 2/2 · verifier 0/1
⏱ 01:42/05:00  💾 83/512 MiB  tasks 12/24
🛡 production read-only; sentinel unchanged (last check 4s)
➡ lifecycle/heartbeat-reclaim
```

## 12. Threat model

| Threat | Control | Failure result |
|---|---|---|
| inherited production DB env | clear then explicit run DB; sealed connector context | `REFUSED_ISOLATION` |
| symlink/hardlink/bind alias | no-follow path walk; realpath/device/inode checks; root containment | `REFUSED_ISOLATION` |
| production SQLite touched by snapshot | URI read-only + query-only; logical sentinel | FAIL/UNKNOWN |
| malicious task body changes instructions | immutable capability envelope outside prompts; bounded tools; content treated as data | `ORACLE_WRITE_BOUNDARY` or policy failure |
| secret extraction via config/plugin/env | allowlisted collector and env; value canaries; report redaction oracle | `ORACLE_REDACTION` |
| model/profile fallback | exact identity receipt before spawn | `REFUSED_MODEL` |
| worker self-certification | independent verifier identity constraint | UNKNOWN |
| duplicate controller/dispatcher | exclusive run lock and claim tuple uniqueness | `ORACLE_DUPLICATE_SPAWN` |
| stale policy receipt/cache | bind receipt to mode, revision, envelope, nonce, TTL | `REFUSED_AUTHORITY` |
| budget escape or fork bomb | external supervisor/cgroup, process allowlist, kill boundary | budget reason + FAIL |
| public network action | network namespace/firewall policy; loopback mock exception in envelope | `ORACLE_NETWORK` |
| cleanup deletes foreign data | marker + nonce + root + sealed manifest + no-follow deletion | `CLEANUP_INCOMPLETE`; retain |
| concurrent legitimate production activity changes sentinel | no rollback; classify UNKNOWN and show delta metadata | `REFUSED_PRODUCTION_CHANGED`/UNKNOWN |
| DB corruption crosses boundary | fault only a post-copy sandbox DB; production descriptors unavailable to worker | FAIL |
| notification replay | idempotency key `(runId, fixtureId, eventKind, revision)` and durable ack | event-trace FAIL |

## 13. Cleanup and retention

Stop admission first, then signal exact owned PIDs, verify exit, close DB handles, checkpoint only the debug DB, seal report/evidence, and recompute production sentinels. Compact evidence retained by default: envelope, marker, report JSON/Markdown, fixture traces, failures, mutation pair, redacted logs, and hashes. Heavy workspaces and successful raw DBs expire after suite TTL (default seven days; failures 30 days) only after `SEALED` exists and its manifest hash verifies.

Cleanup is idempotent. Same marker/hash is a no-op; same run ID with different marker content is a conflict. If any process, mount, unknown file, or hash is unresolved, leave the run quarantined and report `CLEANUP_INCOMPLETE`. Never invoke generic board removal against the production board registry.

## 14. Rollback

Before activation, rollback is removal of the new command registration and debug modules; no migration or production data rollback is required. After activation:

1. disable debug admission with one config gate whose default is false during preview;
2. stop active runs through their owned supervisors;
3. seal ABORTED reports and retain markers;
4. remove command exposure only at a session boundary to preserve prompt caching;
5. leave production Kanban schema untouched in the first slice.

No debug schema migration may run against ordinary boards. Version debug manifests and DB-local metadata independently.

## 15. Implementation plan

### Slice 1 — minimum recommended implementation

Implement only `status`, `start smoke`, `stop`, `report`, and `cleanup`:

1. Register `/orchestration` and route `debug` through shared CLI/gateway service logic.
2. Add a `HarnessDebugRun` controller with exclusive run-root creation, marker, exact envelope, allowlisted snapshot collector, production DB read-only connector, and realpath/device/inode isolation guard.
3. Create a disposable DB by calling existing Kanban schema/state APIs with an explicit `db_path`; never change ordinary board resolution or schema.
4. Implement three stable-seed smoke fixtures using existing Kanban APIs:
   - lifecycle: create -> claim -> heartbeat -> reclaim -> retry -> review -> changes -> done;
   - fairness: unknown poison head plus valid tail under global capacity;
   - contamination: dangling-link shape + namespaced attention canary and production sentinel non-mutation.
5. Implement exact state/event, duplicate-spawn, write-boundary, redaction, budget, and production-sentinel oracles.
6. Add one RED/GREEN mutation pair proving the connector guard refuses a production-sentinel alias before a write.
7. Produce and seal JSON first, then render Markdown. Add idempotent owned-process stop and marker-guarded cleanup.
8. Test with temporary `HERMES_HOME`, an explicitly separate production sentinel DB, and real imports. Assert the production DB/config/current-link bytes and logical identity are unchanged.

Slice 1 uses no real Luna network inference: workers are deterministic local fixture executors with declared Sol/Luna configuration recorded but not spawned. This is the smallest way to prove isolation and oracles before spending or granting agent capabilities. A follow-up reviewed slice may enable exact Sol/Luna workers after the controller is independently certified.

### Later slices

- lifecycle suite expansion;
- bounded exact-model agent supervisor and independent verifier;
- adversarial library;
- restart-recovery external sandbox supervisor;
- full suite and repair-card proposal workflow.

Do not implement dashboard controls, production repair, new core model tools, public networking, or ordinary-board schema changes in Slice 1.

## 16. Test matrix

| Level | Test | Acceptance |
|---|---|---|
| unit | path identity guard across direct path, symlink, hardlink, traversal | every alias refused before DB open-for-write |
| unit | envelope canonicalization and approval binding | content/nonce/revision change invalidates receipt |
| unit | suite budget lowering | request above ceiling refused; below ceiling exact |
| unit | seed and logical clock | same input yields same expected trace |
| unit | status aggregation | FAIL > UNKNOWN > PASS |
| integration | temp production DB + debug run | all writes under run root; production bytes/logical sentinel equal |
| integration | inherited env contamination | inherited DB/board/task variables cannot redirect debug connector |
| integration | smoke lifecycle | exact normalized state/event trace |
| integration | capacity/poison | valid tail progresses; exact reasons; bounded considerations |
| integration | RED/GREEN mutation | same oracle fails mutated fresh run and passes restored fresh run |
| integration | stop/cleanup | only owned PIDs stopped; unsealed/foreign target retained |
| recovery | controller interruption at each journal step | resume or seal UNKNOWN without duplicate task/spawn/event |
| security | prompt injection, secret canary, path traversal | no authority expansion, leak, or out-of-root write |
| E2E | shared command route in CLI and gateway with temp home | identical envelope/report semantics and no production mutation |

Use `scripts/run_tests.sh` for Python tests. Tests must not patch the interpreter into another OS; platform-specific supervisor enforcement runs on its native CI host.

## 17. Open decisions for independent review

1. Which trusted identity/nonce receipt format binds a gateway Captain confirmation across Telegram, Desktop, and CLI without ambient-user fallback?
2. Which cross-platform supervisor is mandatory for hard RSS/CPU/process/network enforcement? Until implemented, affected resource/network oracles are UNKNOWN and only smoke with no agent workers may run.
3. Whether the debug command should initially be CLI-only while the trusted gateway authority receipt is implemented. Architecture keeps one family either way.
4. Exact retention limits after measuring first-slice evidence size.

These questions do not weaken isolation: unsupported enforcement refuses the suite or reports UNKNOWN; it never silently passes.

## 18. Consequences

Benefits: deterministic reproduction, explicit authority, proof that oracles detect failures, no synthetic production contamination, exact machine reports, and a bounded path from findings to reviewed repair candidates.

Costs: separate controller/state schema, external resource enforcement, retained evidence, and independent verifier capacity. Debug mode intentionally cannot auto-fix production or infer approval, so operator workflow is slower but auditable.
