# Run 004 addendum — concurrent semantic collision detection

Date: 2026-10-06  
Prompt: upstream feedback on NousResearch/hermes-agent#134008

## Question

The original experiment tested what happens **after** a contribution becomes stale.

A stronger coordination test is earlier:

> Can a stable semantic change identity detect that multiple contributors are implementing the same operation concurrently, before the repo pays for duplicate implementation + duplicate review?

This tests the root-ownership cluster surfaced in #134008.

## Timeline

Four updater PRs were opened on **2026-09-03 within 3h23m**:

| PR | opened UTC | author | core shape |
|---|---|---|---|
| #102199 | 13:25 | @fangliquanflq | preflight foreign-owned `.git/objects`; refuse before backup/mutation |
| #102208 | 13:39 | @Sahilvishnaliya | post-failure permission-specific remediation message |
| #102258 | 15:17 | @Sahilvishnaliya | repair/chown ownership before/after update |
| #102320 | 16:48 | @aniruddhaadak80 | preflight foreign-owned repo tree; refuse before mutation |

Later related work:

- #105608 — planned-stop marker owner handoff in `gateway/status.py`
- #128970 — root-context/user-install admission guard in `update_contract.py`

## Semantic clustering

### Collision A — same operation

**#102199 ≈ #102320**

Both implement:

`OP-refuse-foreign-owned-git-tree-before-mutation`

Shared semantics:

- POSIX ownership scan;
- repo / `.git/objects` ownership as evidence;
- bounded/preflight posture;
- execute before backup/Git mutation;
- refuse rather than mutate;
- print an actionable ownership-repair command.

They differ in exact scan breadth and implementation detail, but those are realization choices under the same operation identity.

This is the collision a machine-readable change layer should surface while the second attempt is still being scoped.

### Overlap B — competing policy for same defect class

**#102258** overlaps Collision A but is not equivalent.

Its semantic operation is:

`OP-repair-install-ownership`

It proposes ownership mutation/chown rather than only refusing.

The existing review already discovered this relationship manually: it tells #102258 to compose with / credit #102199 and declare merge order rather than create two independent ownership policies in the same file.

So the desired system output is not “duplicate, close it.” It is:

> same problem/invariant cluster; different policy decision; coordinate before implementation proceeds.

### Complement C — same root cause, independent UX operation

**#102208** is complementary.

It adds a narrow error-specific remediation message after a stash failure. The review explicitly describes it as complementing #102199's earlier preflight.

A collision detector should attach it to the same Change graph but keep a separate operation node.

### Related but not duplicates

**#105608**: fresh root-written `.gateway-planned-stop.json` ownership at the gateway marker writer.

**#128970**: updater admission policy when a privileged execution context targets a user-owned install.

Both share the user-visible “root-owned files” theme, but neither is the same semantic operation as the `.git/objects` preflight.

This is the false-positive test: similarity of vocabulary/symptom is not sufficient for deduplication.

## Result

The Change IR model can represent the cluster as:

```
Problem cluster: privileged/root-owned artifacts break non-root Hermes installs
│
├─ OP refuse foreign-owned git tree before mutation
│  ├─ realization attempt #102199
│  └─ realization attempt #102320   ← collision
│
├─ OP repair install ownership
│  └─ realization attempt #102258   ← competing policy, needs decision
│
├─ OP permission-error remediation message
│  └─ realization attempt #102208   ← complements
│
├─ OP planned-stop marker owner handoff
│  └─ realization attempt #105608   ← different writer boundary
│
└─ OP refuse privileged updater on user-owned install
   └─ realization attempt #128970   ← different admission boundary
```

## Product implication

The first valuable automation may be **collision detection before stale refresh**.

At issue/PR creation or when an agent starts implementation:

1. extract the proposed semantic operations/invariants;
2. search existing open + merged Change nodes;
3. return relationships:
   - `same_operation`
   - `overlapping_policy`
   - `complements`
   - `supersedes`
   - `related_distinct_boundary`
4. surface existing owners/discussion;
5. require explicit coordination for high-confidence `same_operation` collisions.

This operationalizes existing Hermes policy:

- CONTRIBUTING: search existing issues/PRs and improve an existing PR instead of opening a competing duplicate;
- AGENTS.md: “extending before duplicating (3+ PRs in one category → an ABC + orchestrator).”

## Important authority boundary

This layer must **not** infer acceptance or priority.

It can say:

> #102199 and #102320 implement the same semantic operation.

It cannot say:

> therefore #102199 should merge.

Selection remains a maintainer authority/scheduling decision. Change IR reduces coordination and refresh cost; it does not confer acceptance.

## Verdict

**Collision-detection extension supported by this fixture.**

This sharpens the product thesis:

> The useful machine-readable layer is not only “preserve stale intent.” It is a stable semantic identity layer that lets the repo detect collisions, compose related attempts, preserve provenance, and rematerialize only when an accepted/selected change needs current code.
