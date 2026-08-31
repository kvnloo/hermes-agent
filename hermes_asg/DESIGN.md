# Intelligent provider and cloud-agent autoscaling (Hermes)

Request: `REQ-20260830-HERMES-ASG-DURABLE-PROTOTYPE-001`
Prior design: `REQ-20260830-HERMES-ASG-001` (t_20cf71dd)
Company: `company_zer0` · Portfolio: `portfolio_infrastructure` · Product: `product_hermes_agent`

Status: **shadow-mode library prototype in isolated worktree**. Does not patch live routing.
Merge to development remains Kevin-gated.

## Base revision

Worktree: `/mnt/zer0models/workspaces/hermes-agent-worktrees/t_d4ea2367`
Branch: `wt/t_d4ea2367` tracking `origin/main`
Parent: `4f22543509d1b91dc45bcb369447126c5eb14fb7`

## Prototype layout

```
hermes_asg/                 # library (no imports of live gateway)
  __init__.py
  types.py
  controller.py
tests/test_asg.py           # unittest, no network
```

## Hermes seams (this tree)

| Source | Fact |
|---|---|
| `gateway/platforms/api_server.py` | Global in-flight cap; 429 `rate_limit_exceeded` |
| `hermes_cli/config_defaults.py` | `max_concurrent_runs: 10` |
| `agent/error_classifier.py` | Distinct buckets: rate_limit, overloaded, billing, auth |
| `agent/nous_rate_guard.py` | 429 may be account RPM or upstream model; breaker must not be provider-wide |
| `agent/credential_pool.py` | Same-provider multi-key; cooldown on exhausted; never rotate on overload |
| `gateway/wake.py` | Treats 429 concurrency cap as transient backoff |

## External primary-source reconciliation

Not vendored; mapped to this prototype's invariants:

| Source | Mapping |
|---|---|
| LiteLLM Router | Per-deployment `max_parallel_requests`, cooldown on 429, `lowest_latency` / usage-based routing. We use per CapacityKey AIMD + key-scoped breaker instead of provider-wide cooldown. |
| KEDA | `cooldownPeriod`, `minReplicaCount`, fail-closed when scaler metrics stale. Worker TTL dropping slots to 0 is the analog of missing metrics → scale to min (here min=0 for stale workers). |
| Kubernetes HPA | Stabilization window on scale-down; never scale above maxReplicas. AIMD never raises above `declared_limit`. |
| Temporal workers | Task-queue isolation, poller count, sticky execution. CapacityKey includes `worker_id`; half-open allows one trial (like a single poller probe). |

Conflicts accepted: LiteLLM may rotate keys on 429; Hermes credential_pool must **not** rotate on overload — this prototype follows Hermes.

## Shadow mode

`RoutingReceipt.shadow=True` and `live_path_unchanged=True`. Callers may compute a receipt without changing `max_concurrent_runs`.
