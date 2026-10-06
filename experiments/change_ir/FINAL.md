# Change IR experiment — final assessment

Date: 2026-10-06  
Tracker: #453  
Upstream motivation: NousResearch/hermes-agent#134008

## Verdict

**SUPPORTED.**

The experiment supports treating a pull-request diff as an **ephemeral realization** of a more durable contribution object.

The durable unit that survived repository churn was not the commit or branch. It was:

```
problem
  → desired outcomes
  → invariants / non-goals
  → architectural decisions + open questions
  → independently classifiable semantic operations
  → semantic anchors + verification contracts
  → realization(s) against specific tree states
```

The implementation should be materialized lazily near review/merge time instead of continuously keeping every old patch synchronized.

This is evidence for an **intent-carrying change / Change IR** workflow. It is not evidence that textual matching alone can autonomously rewrite arbitrary stale code.

## Experiments

### E1 — semantic drift: #105624

The Telegram sibling-context contribution retained coherent design invariants while the concrete architecture moved underneath it.

The durable intent survived:

- observation must not imply dispatch;
- observed context remains context-only;
- participation remains opt-in and allowlist-scoped;
- final-response context should follow the actual final-delivery path.

The old patch did not survive unchanged: main refactored sending through `_send_chunks` and changed bot-sender observation behavior. Refresh required semantic reconciliation, not only conflict resolution.

**Result:** design identity can survive implementation drift.

### E2 — independently aging operations: #31157

One PR decomposed into operations with different current states:

- MCP refresh/teardown guard → `already_on_main + moved`
- hard-coded GitNexus repository instruction → `invalidated`
- GWS generated-credential behavior → `needs_decision`

The MCP operation also demonstrated provenance chaining:

1. @sege66 proposed the earlier guard in #31157.
2. @patrykkopycinski later supplied a production diagnosis in #109824.
3. @salch-cred implemented the fix in `1c82c22e`, with @Tranquil-Flow, @ildunari, @andrexibiza, and @ly6751 credited as co-authors.
4. @austinpickett added behavior-contract coverage in `37eb4d0b`, with @ly6751 and @salch-cred credited.

No single later commit should erase that chain.

**Result:** PR-level state is too coarse; operations and provenance need graph identity.

### E3 — 17-PR Vox stale-wave

Vox Lockin #78207 provides an unusually good longitudinal sample: all 17 PRs were stale-base work, refreshed against then-current main and reported green on 2026-08-04.

Two months later:

| Current semantic state | Count |
|---|---:|
| Clearly implemented / superseded on main | 8 |
| Mixed state inside one PR | 2 |
| Requires fresh design / priority decision | 7 |
| Safely replayable as-is | **0** |

The sample falsified four tempting shortcuts:

- `closed ⇒ dead`
- `green after rebase ⇒ still mergeable later`
- `missing old filename ⇒ work disappeared`
- `same PR ⇒ every hunk has the same current state`

**Result:** continuous patch freshness is the wrong durable abstraction.

## Real lazy rematerialization

A fresh branch was cut from upstream main:

`exp/change-ir-remat-105624-sibling-observe`

Instead of replaying all of #105624, only one surviving operation was reconstructed:

> Observe a human message addressed to a sibling Telegram bot as context without dispatching/responding.

The outbound sibling-response mirror remained a separate operation and was intentionally excluded.

### Measured reduction

| | Original #105624 | Rematerialized operation |
|---|---:|---:|
| Changed code/test lines | 824 | 82 |
| Diff lines | 957 | 137 |
| Measured review context | 67,555 chars | 12,540 chars |
| Files | 4 | 3 |

Reduction:

- **90.0% fewer changed lines**
- **81.4% less measured review context**
- original review packet was **5.39× larger**

The reduction came from semantic decomposition and selective materialization, not from mechanically shortening the old diff.

## Success criteria

### 1. Preserve design/invariants across a stale implementation — PASS

#105624 kept stable behavioral invariants while send/observation implementation details changed.

### 2. Classify independently aging operations — PASS

#31157 and #78033 both produced multiple simultaneous current states inside one old PR.

### 3. Produce a materially smaller current-head realization — PASS

The #105624 operation rematerialization reduced changed lines by 90% and measured review context by 81.4%.

### 4. Preserve provenance and contributor credit — PASS

`relations.json` stores explicit provenance/supersession/materialization edges instead of replacing an earlier author with the latest implementation.

### 5. Do not confuse textual anchors with semantic equivalence — PASS

The probe deliberately reports only `present / partial / missing` anchor evidence.

This mattered immediately:

- the GitHub code-search index returned incomplete zero-hit results and was rejected as absence evidence;
- `_refresh_tools` disappeared from its old file, but investigation found the behavior moved to `mcp_tool_health.py` and was independently fixed;
- #77711 retained the same conceptual helper while its semantics changed, so simple symbol presence would have been unsafe.

## Validation boundary

The rematerialized branch has a targeted GitHub Actions workflow for:

```
python -m pytest tests/gateway/test_telegram_group_gating.py -q
```

Run: 37547255551.

At experiment closeout, GitHub still reports it **queued**, not failed. The fork has 29 queued Actions runs, including unrelated jobs queued for much longer.

Therefore:

- **No targeted test pass is claimed for the new branch.**
- The workflow remains on the isolated experiment branch as an auditable execution receipt.
- The original refreshed #105624 reported 77 targeted tests passing.
- The rematerialization target is 378 commits ahead of that tested base, but none of the three touched source/test files changed during those 378 commits.

Those facts reduce uncertainty but do not substitute for the queued branch execution.

This execution-queue limitation does **not** change the representation/workflow result above; production promotion of the rematerialized code should still require its own green test receipt.

## Resulting model

The useful abstraction is:

### Stable identity

`ChangeID`

### Durable nodes

- Problem
- Outcome
- Invariant
- Non-goal
- Decision
- Open question
- Semantic operation
- Verification contract
- Evidence
- Realization

### Useful edges

- `requires`
- `derived_from`
- `implements`
- `proves`
- `superseded_by`
- `invalidated_by`
- `moved_to`
- `materialized_by`
- `conflicts_with`

### Refresh states

- `still_needed`
- `already_on_main`
- `moved`
- `invalidated`
- `needs_decision`
- `unknown`

The refresh pipeline should never directly map `missing anchor → rewrite patch`.

It should be:

```
Change IR
  + old realization(s)
  + discussion/review evidence
  + current main
        ↓
anchor/evidence collection
        ↓
semantic operation classification
        ↓
drop already-on-main / invalidated operations
        ↓
escalate needs-decision operations
        ↓
materialize only still-needed operations
        ↓
verify invariants
        ↓
new patchset / realization
```

## What this should replace

Not Git. Not GitHub PRs.

It should replace **the assumption that a PR diff is the canonical identity of a contribution**.

Git remains the realization/evidence store. GitHub remains the social review surface.

Change IR sits one level above them and gives discussion, architecture, tests, contributors, and implementations a stable shared identity.

## Production recommendation

Build the next version as a small review/triage layer, not an autonomous code-rewriter first.

Minimum useful product:

1. Extract or author a Change packet when a non-trivial PR is opened.
2. Keep invariant/decision/provenance nodes attached to a stable Change ID.
3. On stale review, classify operations against current main.
4. Emit a compact refresh packet:
   - what is already on main;
   - what moved;
   - what is invalidated;
   - what needs a human decision;
   - what still needs code.
5. Only then ask an agent to materialize the surviving operations.
6. Present the new realization as another patchset under the same discussion identity.

That attacks the root synchronization tax without creating an endless “bot rebases every branch” service.

## Artifacts

- `README.md` — experiment model
- `refresh_probe.py` — conservative evidence collector
- `fixtures/105624.json` — semantic-drift fixture
- `fixtures/31157.json` — independently-aging operation fixture
- `fixtures/78207.json` — 17-PR longitudinal fixture
- `relations.json` — provenance/supersession graph
- `runs/001-current-main.md` — first current-main classification
- `runs/002-vox-17-prs.md` — 17-PR longitudinal result
- `runs/003-rematerialization.md` — real rematerialization + compression measurement

## Final conclusion

The original intuition holds:

> **Code is a realization, not the durable contribution.**

In a high-churn AI-native repository, the scalable unit is a stable graph of intent, invariants, decisions, evidence, semantic operations, and provenance, with code materialized against current architecture when it is actually needed.

The next step is productization, not more proof-of-concept evidence.
