---
name: dash-summary-transport-qualification
description: "Use when qualifying Dash @smol summary transports."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [dash, summaries, oauth, qualification]
    related_skills: [dash-turbo-live-preview, hermes-agent, rendered-ui-qualification]
---

# Dash summary transport qualification

## When to Use

Use for a missing Dash thinking/tool summary, OAuth summary transport changes,
or qualification of an exact-model @smol request without deploying the bridge.

## Procedure

- Isolate from the served turbo SHA in a new worktree. Preserve the shared bridge and Metro; transport implementation is not deployment authorization.
- Resolve the configured `smol` assignment exactly. Do not infer that the owner's OAuth account is unavailable because `ANTHROPIC_API_KEY` is absent, and do not silently forward a failed request to tiny or another provider.
- Load Hermes provider docs before using its native client. Inspect `hermes proxy providers` instead of assuming the proxy implements Codex. The native `agent.auxiliary_client.resolve_provider_client("openai-codex", model=<bare>, raw_codex=True)` can reuse authorized profile-scoped OAuth without launching a general agent or copying credentials into Dash.
- Use Dash's fixed `bridge/src/summary-oauth.py` helper via stdin. It resolves the native Python with `hermes --print-runtime-command`, sends a tool-free request to the official endpoint, disables SDK retries/storage, validates the resolved and returned model, and emits only allowlisted structured output. Never print its credentials or raw provider diagnostics.
- Own a wall timer across runtime discovery and inference, and kill the helper on abort. A short cloud summary can take several seconds including startup; measure before selecting a subsecond deadline. Cancel stale live blocks, keep final/turn generation parallel, cache only success, and expose safe degraded status over `status.summary`.
- Prove only synthetic text via `bun scripts/probe-thinking-summary.ts --luna` with explicit owner authorization. The probe checks disabled/cached behavior too. A local authorized transport probe is not a phone/live-bridge render receipt.
- Run CPU suites, typechecks, render tests and mutation checks through `fleet-build --node mbp`. Fresh tar snapshots need root/app/bridge frozen dependency installs; unlink only a shipped dangling app/node_modules symlink on the remote job. Git-dependent tests need an initialized remote fixture with indexed sources. Do not treat missing dependency/native-addon failures as application regressions until these prerequisites are installed.
- Pair mutation targets with the new transport tests. When extending `TARGETS`, extend its declarative contract test and scale the dry-run sampling budget without lowering required branch coverage.
- Record the exact commit SHA, fleet job IDs, synthetic probe output, remaining provider restrictions, baseline lint failures and absence of device/deployment evidence in the run report. Keep Haiku API-key support distinct from unimplemented Anthropic OAuth.
