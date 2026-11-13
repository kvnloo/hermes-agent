---
name: home-k3s-fleet
description: "Use when setting up or verifying the owner's K3s fleet."
version: 0.2.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [k3s, kubernetes, kueue, nvidia, tailscale, iac, dotfiles]
    related_skills: [session-recovery, hermes-agent, secrets-manager-bws]
---

# home-k3s-fleet

Use when setting up, onboarding, verifying, extending, or debugging the owner's K3s fleet and Tailscale access.

## Rules

1. Keep cluster bootstrap and fleet policy in .files IaC; keep application values/config/deploy scripts in their product repo. Retain generated inventories as receipts, not hand-maintained config.
2. Pass KUBECONFIG explicitly, identify the IaC branch matching live state and avoid duplicate stacks. Follow the CPU/acceptance/GPU/queue/node critical path; advance unblocked steps and report deferred systems.
3. Report fresh fleet-status evidence grouped as built/proven, broken now and not started. Check cordon reasons, pressure, restart counts and readiness history; distinguish host resource envelopes from untrusted-pod security isolation.
4. Prove guarantees RED then GREEN with named smoke tokens, logs and exact cleanup. Test quota, restricted Pod Security, gateway-only private access and at-start isolation; require the netpol-ready init/admission gate and keep race-failing nodes tainted.
5. Use Kueue for placement and test/build/bench priorities, not another scheduler. Admit only genuinely checkpoint-safe benches to bench-lanes; preserve evicted/requeued jobs and stages, and record class/queue independently of pod exit status.
6. Submit repo work through the existing factory/fleet contracts. Route builds and tests through fleet-build to MBP or compatible phone workers; use groot only for GPU or unique toolchains and honor exit-75/held-queue gates.
7. Inspect target toolchains, memory, heat and GPU co-tenants before work. Keep toolchains pinned in IaC, split CPU/GPU tests, capture durable stage outputs and bind exact-head receipts to the actual shipped source.
8. Inventory Android and guest tailnet identities separately; repair remote PATH before reinstalling. Preserve verified host keys and per-device vault identities; prove owner SSH in both directions plus repeat, revoke, unauthorized and offline cases.
9. Keep owner-user SSH parity separate from the restricted agentjob lane. Join nodes tainted, transport join tokens root-only over SSH and admit only after pinned-node isolation; preserve owner approval for privileged operations.
10. Treat PRoot phones as leased host-lane workers, never Kubernetes Ready or cgroup-isolated. Preserve opt-in, durable Stop, pause/call hooks, focus and sleep-time ADB/install/mic prohibitions; apply no agent resource caps. See references/android-phone-workers.md.
11. Diagnose Android-service and guest-supervisor lifecycles separately. Use event-driven foreground supervision with bounded recovery, stable locks and side-effect-safe leases; qualify package signer, spare-device behavior and overnight reliability separately from source tests.
12. Coordinate storage recovery with its owner and retention authority; preserve active/receipt-less stages, measure both fleet and kubelet pressure gates and prove normal reconciliation plus smoke. Stage exact owned paths, refresh live branch/PR state and report tokens, timestamps and unverified criteria.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
