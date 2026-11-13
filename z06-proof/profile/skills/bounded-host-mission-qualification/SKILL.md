---
name: bounded-host-mission-qualification
description: Use when qualifying an existing host supervisor.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [supervisor, qualification, systemd, safety]
    related_skills: [hermes-agent, frozen-source-cohort]
---

# Existing host mission qualification

## When to Use

Use for read-only qualification of an existing persistent agent controller or its proposed host binding. Separate mechanism tests from current mission, ownership, refusal and spending admission.

## Procedure

- Pin the existing controller's exact HEAD and compare executed files to committed blobs before and after tests; a branch name or historical receipt does not attest current bytes.
- Separate source-byte provenance from executable AST equivalence: document comment-only differences rather than treating them as mechanism changes, but never waive an explicitly required retained-test byte match using AST equivalence.
- Inspect every test's reachable subprocess behavior before execution. Prefer unchanged cheap fixture tests under a denied-network namespace, minimal environment, disabled bytecode, private scratch and isolated Git hooks/config. Never substitute model calls for deterministic host qualification.
- Redirect `PYTHONPYCACHEPREFIX` to an empty private scratch directory as well as disabling bytecode writes for exact-source tests; `python -B` alone may still load pre-existing checkout bytecode. Preserve existing ignored caches rather than deleting them during read-only qualification.
- Verify a denied-network namespace using its namespace ID, `socket.if_nameindex()` and route entries without attempting an external connection; inherited `/sys/class/net` mounts can display host interfaces after `unshare --net`, and an empty route file need not contain a header.
- Compare imported safety test method bodies and case lists against their original revision, then adapt only owned fixtures to new admission prerequisites; explicit scope and a local allowed-origin Git fixture prevent an earlier unrelated rejection from masquerading as a passing safety test.
- Separate mechanism success from mission authorization. A passing test that requires broad cross-project continuation can directly conflict with a later exclusive mission; inspect the rendered prompt, not only an appended focus hint.
- Inspect effective user units and drop-ins, not just unit descriptions. Distinguish router, shadow-learning tick, delivery watcher, gateway-restart supervisor and actual agent continuation ownership.
- Filter manager environment to an explicit non-secret key allowlist before output or persistence. Never print raw `systemctl --user show-environment`; unrelated credentials can be inherited there.
- Check refusal, quota, approval and idle outcomes independently. Generic nonprogress retries and exit zero do not implement a terminal safety-refusal gate. Preserve refused work without automatically replaying it.
- Qualify marker-admission repairs with a synthetic A/B: run the original rejecting assertions unchanged on exact baseline blobs, then require the repaired source to block two fresh same-state invocations before any worker or shift launches. Preserve positive nonzero and success controls, compare operator-marker identity/content after each invocation, and scope acceptance to the enumerated marker shape rather than every possible persistence failure.
- Check durable state consumption as well as state writing. Per-shift logs are not a restart checkpoint if a new process resets wall budget, stall count, refusal state and aggregate spending.
- Treat lane-local locks and same-config worktree checks as limited exclusion. Require canonical owner transfer and one shared mission admission boundary before replacing an active writer.
- Distinguish fixed cooldown from adaptive backoff and heartbeat from useful progress. Require operator-set resource thresholds and account-bound consumption limits; subscription access and a wall timer are not unlimited spending authorization.
- Propose the smallest existing single-lane host binding only after those gates qualify. Do not use Restart=always or a repeating timer to reset failed, refused or exhausted work. If gates are absent, return precise blockers rather than inventing a scheduler or claiming configuration alone fixes them.
- Keep fixture results, historical launch receipts and actual mission efficacy separate. Record no gain until independent paired outcomes and full cost/time evidence meet the user's target.
