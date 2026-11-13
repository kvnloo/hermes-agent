---
name: qmp-review-fail-closed-receipts
description: "Use when repairing reviewed QMP lifecycle failures."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [qmp, testing, lifecycle, evidence]
    related_skills: [upstream-contribution, test-driven-development]
---

# QMP review follow-up receipts

## When to Use

Use for a bounded review-driven repair of QMP transport or owned-child lifecycle failures with immutable reviewer evidence.

- Preserve frozen reviewer probes byte-for-byte. If an old probe expects continued success after malformed input but the approved contract requires closing transport, retain its assertion failure as a semantic disposition; add a separate public-API rejection/cleanup probe instead of weakening the original.
- For failed-start cleanup, observe the original handshake error, recorded SIGTERM refusal, SIGKILL exit/reaping, ESRCH on the owned PID, and absence of active Timeout resources before retry. Prompt rejection alone can conceal an orphan.
- Clear only the fixture's stale Unix socket after a forcibly terminated peer and before healthy restart. A synthetic server killed with SIGKILL cannot unlink it; a restart EADDRINUSE is a fixture fault, not automatically a production defect.
- Supervise hostile peer tests in owned process groups with a subreaper. Successful cases must exit naturally with no supervisor rescue; crashing RED cases must be reaped without touching unrelated processes.
- Keep production-only candidate, chronological RED/GREEN evidence branch, and direct-held-source RED branch separate. Bundle all provenance refs, restore the bundle, and replay unchanged controls plus stronger contract tests before delivery.
- Exercise error-description conversion with JSON whose `desc` object cannot convert to a primitive; require every pending public request to reject. Constructing an Error can throw, so deleting the pending entry first can strand its promise even when parsing is guarded.
- Send an invalid frame followed by correlated valid replies in one socket write to verify fail-closed dispatch stops processing that batch. Preserve the original assertions and add this as separate contract evidence.
- Test cancellation retries in the immediate stop-settlement continuation, without awaiting the earlier start rejection first. Repeat failed-spawn/start/stop/restart through actual executables to expose stale cleanup or timer ownership races.
- Distinguish supervisor rescue from a fixture's own finally-block SIGKILL. A failed legacy assertion that reaches cleanup does not prove public stop; require a separate passing control to verify stop, reaping, timers and natural host exit before accepting a semantic mismatch.
- Leave final independent review and publication authorization explicit. A repair implementer's replay is not independent approval.
