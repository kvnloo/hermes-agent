---
name: bounded-cooperative-job-admission
description: "Use when testing bounded cooperative job scheduling."
---

# Bounded cooperative admission

- Inspect the actual launcher and its child lock owner before adding coordination; nesting independent acquisitions of one lock can self-contend.
- Reload checkpoint state under the cooperative lock because reading before acquisition permits stale writers even when execution is serialized.
- Execute at most one bounded chunk per turn and return on deferral; do not turn resource gating into an idle polling service.
- Gate on fresh effective memory headroom, a measured job peak and a separately calibrated system reserve; availability logs alone are not peak-memory profiles.
- Treat GPU capacity observations as opportunistic advice, never hardware exclusivity; include graphics activity and explicit consent, not just free VRAM.
- Persist running before work and advance only on verified, identity-bound receipts; unknown stale ownership blocks all cooperating heavy work until reconciled.
- Reconcile only the exact failed attempt after verifying its runner, child and owned process group/session have no survivors; retain its original log and queue. Give a fixed pinned-input script a new queue/job identity instead of rewriting the failed request or weakening its admission limits.
- Keep a runner's exit-zero checkpoint distinct from artifact acceptance: independently decode/check output bytes, bind hashes back to the request fingerprint, and publish a separate verification receipt rather than silently upgrading an unverified runner flag.
- Test interruption, omitted orphan records, consent denial, resource deferral, resumption and lock contention with injected callbacks before launching real workloads.
- Preserve a pinned device across checkpoints or create a new proof identity; silent backend changes can mix incompatible evidence.
- Keep subprocess lifetime/descriptor inheritance and real artifact verification as explicit integration dependencies when only in-process fake jobs have been tested.
- Pass the held flock descriptor explicitly through every subprocess boundary and close only the current owner's copy; `LOCK_UN` releases the shared open-file-description lock even while descendants retain descriptors. Validate borrowed FD identity instead of reopening/reacquiring the pathname.
- Test controller SIGKILL and leader-before-descendant exit with real tiny processes; ordinary timeout handling that kills only the direct child can leave live descendants outside the returned result. Keep cleanup scoped to a newly owned process group, reap adopted children, and state that daemonization/descriptor dropping breaks the cooperative contract.
- Cap Linux host MemAvailable by all visible cgroup-v2 ancestor max/high headrooms; a leaf's unlimited setting does not negate a constrained ancestor, and hidden or unreadable hierarchy limits must not be treated as unlimited.
