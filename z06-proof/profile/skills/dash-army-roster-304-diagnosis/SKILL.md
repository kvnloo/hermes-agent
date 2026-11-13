---
name: dash-army-roster-304-diagnosis
description: Use when Dash army roster regressions hang on 304.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [dash, playwright, debugging, tester-army]
    related_skills: [systematic-debugging, remote-agent-orchestration]
---

# Dash army conditional-roster diagnosis

## When to Use

Use for a missing-roster army timeout at response completion, especially when conditional HTTP polling was introduced between the known-good and failing revisions.

## Procedure

- Read the named CI failure location before assuming a turn-ownership regression. A timeout at `response.finished()` occurs before Queue/ended-chat assertions and does not establish that ownership failed.
- Download the actual army evidence with `gh run download`; inspect error-context, console, bridge log and trace network records. Summarize only method/path/status/cache headers/failure text; never dump Authorization values from trace archives.
- Compare the bridge-owned streaming guard in `app/src/lib/live-sessions.ts` with the known-good revision. Trace conditional polling through `app/src/lib/roster.ts`, `app/src/net/bridge.ts`, and `bridge/src/pairing-http.ts` separately from ownership reconciliation.
- Do not ship `cache: "no-store"` alone as a cure for the pending 304 completion wait: an army execution has falsified that hypothesis. Revert ineffective product changes rather than claiming a green ownership fix.
- Preserve the existing army assertions. If no execution reaches and fails the ownership assertions, report the synchronization blocker; do not invent a product bug or silently apply a timeout workaround.
- For fresh fleet snapshots, preserve real Git metadata via an input bundle before running `scripts/army.sh`; the snapshot excludes `.git`. Label modified diagnostic runs dirty and never use them as release receipts.
- Use the MBP host lane for the army's nested bwrap PID namespace: the Kueue container lane can reject mounting `/proc`. Distinguish quota pod diagnostics from host-service diagnostics; `fleet-build --node mbp-host` runs a separate systemd service.
- Cancel owned host work with `fleet kill mbp JOB_ID`, which stops its host service before releasing Kueue quota. Deleting its Kubernetes reservation alone does not stop host work. Verify the exact host service is inactive.
- Count only valid tester-army executions as evidence; environment startup failures are not application regressions. Do not touch phones or live bridges to resolve test infrastructure failures.
