---
name: vllm-sr-turbo-router
description: "Use when running vLLM Semantic Router for Hermes turbo."
version: 0.1.0
metadata:
  hermes:
    tags: [vllm-sr, semantic-router, k3s, helm, turbo, routing]
    related_skills: [home-k3s-fleet, root-pressure-safe-cleanup, api-key-secret-storage]
---

# vllm-sr-turbo-router

Use when configuring, diagnosing, qualifying or consuming the vLLM Semantic Router turbo/free lanes, privacy routing or model-evaluation profiles for Hermes and T3.

## Rules

1. Keep vLLM Semantic Router as the semantic router and Kerdoios as placement/optimization. Extend existing z0intelligence turbo work rather than rebuilding it. Keep turbo inside Hermes clean as a provider/model; implement objectives as virtual-model entrypoints and recipes, not new Hermes profiles or router processes.
2. Execute O14's objective `(TTFT + out_tokens/tps) * (1 + lambda*pace) / p_accept`, with lambda=1 explicitly unmeasured and unknown inputs unscored. Reuse routing_objective.plan_routing, kerdoios capacity and the dispatch ledger. Feed certified task-fit through z0int policy ingest and generate_catalog.py --findings; keep Hermes Index data a dated prior rather than p_accept and expose missing provider/capacity inputs.
3. Resolve the current Service and GET /v1/models before declaring a lane absent. Treat the containment source `/mnt/zer0models/z0-wt/z0int-vllm-sr-turbo/deploy/vllm-sr/config.yaml` and router-containment-20261104/REPORT.md as the recorded disabled-endpoint state, not evidence of fresh inference health. Preserve disabled paid/unqualified endpoints until approved; report 429 quota failures as failures.
4. Turbo is the burst-work mode (owner, 2026-11-05): `sr:free` lanes at each provider's published free-tier limits (Cerebras, Groq; honor Retry-After, never exceed), plus the ChatGPT and DeepSeek phone apps driven to their in-app limits, to finish many small, defined units fast. Keep each unit small and checkable; coding units still need the coding-probe pass for their tier. Use available approved free lanes for background work. Keep primary Claude direct, route GPT coding through fx/pi and keep Claude subscriptions out of router translation or fingerprint workarounds. Treat native account choice and Hermes pool choice as separate, still-unverified burn-aware paths.
5. Expand the approved free endpoint toward working Groq, Cerebras, OpenRouter :free, NIM, Nous and Vercel routes using per-model limits.json buckets. Treat owner-authorized prepaid Groq/Cerebras balances separately from recurring free quota and new billing; verify account evidence before declaring funds exhausted, and obtain approval for top-ups or new billing. Move 429/413 calls to the next eligible model instead of hammering one provider.
6. Enforce privacy per lane and run deploy/vllm-sr/privacy_lanes.py after pool edits. Treat turbo as T0 only. Attribute public sessions from every touched real repository, then scrub each transmitted row for secrets, identifiers and private paths. Keep private experiment families local and enforce a public-family manifest guard for router executors. With fail-open Hermes middleware, pin the consuming default and every auxiliary model to vllm-sr/local without aliases or fallbacks.
7. Keep Google API keys out of deployment, BWS/DSH injection and Hermes scopes; Gemini access remains agy OAuth only. Transfer provider secrets through scoped broker injection and deploy.sh --allow entries. Keep refresh-token ownership in one credential pool and print only metadata. Preserve unresolved privacy-lane deployment limits rather than assuming documented lane names are exposed.
8. Deploy from z0intelligence deploy/vllm-sr/deploy.sh using the pinned chart and chart-local.patch. Validate config.yaml first, place fallback beside algorithm and update configMap.applyValuesRevision from the config hash. Use CPU minimal mode, keep both chart values files at Guaranteed requests=limits of 512Mi/1 CPU, and qualify rollout status and image digest rather than relying on CLI exit alone.
9. Define one logical model per provider/model and use the OpenAI compatibility gateway for hosted providers with provider: vllm, openai_compat_gateway: true and a /v1 base URL. Canonicalize strict-decoder fields in the proxy. Probe streaming and non-streaming, selected-model headers and nonempty content; HTTP 200 alone is insufficient.
10. Diagnose admission/webhook and CoreDNS health before blaming providers for global 503s. Preserve the router pod when admission cannot recreate it and route durable webhook fixes through owner IaC. Honor groot-admit capacity and existing memory limits; keep infrastructure-failed benchmark runs separate from model results.
11. Reuse existing unexpired receipts and canonical z0evals studies before probing drift. Discard pre-shared-SSL TTFT artifacts and measure long-answer tok/s rather than chunk rate. Report per-model TTFT/tok/s, aggregate parallel throughput, serial-versus-parallel wall time and credit-backed share; redact provider account IDs before publishing.
12. Plan task-fit batteries with plan_taskfit.py, frozen limits and certify.py; run run_taskfit.py rather than hand-written loops. Use deterministic auto-graded public-safe non-code tasks, a hard tier, frozen hashes, per-model pacing and resumable JSONL. Keep ruled-out 413 cells out of scores, count eligible failures as wrong and report reliability, accuracy and latency separately. Use GitHub Actions one run at a time or admitted MBP harness work as documented.
13. Use references/experiment-executor.md for answer-token evaluation: parse actual protocol tokens, label one-hot hard-vote probabilities and log X-Vsr-Selected-Model per call. Honor Retry-After and the next-eligible-model rule on 429/413. Resolve the historical eight-attempt retry scope in REVIEW.md before bulk execution. Keep about eight workers, smoke 40 rows, remove infrastructure-error rows before resuming and sanitize model names in filenames. Apply the background free-lane and public-data constraints even though the reference names turbo.
14. Repoint all consumers in the same change when disabling or renaming a model, including clean delegation.model, aliases, fallback_providers, T3 favorites and scheduled model_selection_json. Read native session model/model_config/billing_provider alongside T3 selection; reconcile returned events before retrying failed model mutations. Confirm the resolved direct response model instead of trusting an Opus label or queued configuration event.
15. Report desired owner backend coverage, recorded deployed pool, fresh route qualification, billing and unimplemented account selection separately. Suggested companions are token-thrifty-agent-routing and offline-rate-limit-catalog; consult their existing receipts as needed rather than compulsory loading or redundant probing.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
