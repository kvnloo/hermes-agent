---
name: hermes-api-only-worker
description: Use when wiring a safe live Hermes API worker.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, gateway, api, sessions, isolation, voice]
---

# Safe persistent Hermes API workers

## When to Use

Use for persistent app/voice workers beside a live Hermes CLI, especially when shared messaging credentials or host-wide schedulers must stay untouched.

## Procedure

- Load `hermes-agent` and the official docs index, then inspect installed `gateway/platforms/api_server*.py` before choosing a transport; installed surfaces can differ from generic gateway examples.
- Check live CLI ownership first. Never resume or write an existing live classic CLI session from a second process. Create a distinct named session in the authorized profile and use a file digest to coordinate with the main conversation.
- Verify adapter AND scheduler scope separately. `gateway.multiplex_profiles: false` and temporary `gateway.standalone: true` can restrict adapters while `gateway/run.py::_start_gateway_start_cron_and_housekeeping` still ticks every profile. A local app worker must not silently become the host cron/kanban scheduler.
- When host-wide scheduler startup is out of scope, host the native `APIServerAdapter(PlatformConfig(...))` directly on loopback using the installed Hermes interpreter, explicit HERMES_HOME and TERMINAL_CWD. Do not construct GatewayRunner or patch shared source. Verify its connect/disconnect contract against the installed version.
- Require a private API key file mode 0600 and explicit loopback host/port. Never dump process or systemd environments: they can contain unrelated secrets. Read selected nonsecret properties only.
- Create a dedicated session through `POST /api/sessions` with title, ID, provider/model and model lock. Serialize `POST /v1/runs` against the explicit session ID; retain the exact body and Idempotency-Key before network I/O. Poll `/v1/runs/{id}` and handle completed, failed, cancelled AND interrupted terminal statuses.
- Persist source JSONL byte offsets/inodes and incomplete-tail behavior; never acknowledge a partial line. Advance inbox offsets only on native acceptance. Keep failure receipts and avoid automatically replaying a run whose tools may already have changed state.
- Read replies through SQLite mode=ro, filtering the exact chat lineage, assistant role and active rows; never expose main/delegated sessions accidentally. Follow compression continuations.
- Inspect the actual app contract before seeding tool instructions: phone drive queues often require increasing integer IDs rather than UUIDs, and phrase aliases may target action IDs rather than normalized text.
- Verify real model execution: one terminal preflight, a literal test appended through the real inbox, actual assistant output read through the app endpoint, restart recovery without reseeding, and logs proving only the intended API adapter started. Toolset configuration alone is not execution evidence; browser_exec intentionally suppresses legacy browser_* gates when browser-harness is active.
- Document any unexpected startup side effects plainly; do not modify another profile's scheduler files to hide or undo them without authorization.
- Freeze cross-client inbox framing explicitly: verify complete real HTTP JSON for populated and empty pages, nullable speech/action/session fields, object params, monotonic cursors and pagination. Test the sibling client's actual parser before renaming a stable wrapper to fix an old parsing error; keep server-side schema regression tests.
- Qualify broker restart while an admitted native run is in flight: retain the same run ID, read its real reply through inbox/SSE, then restart the API host only after work settles and verify there is still exactly one setup seed. Separate headless-local action receipts from physical phone execution claims.
