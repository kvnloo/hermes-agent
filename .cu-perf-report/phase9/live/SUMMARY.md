# Phase 9 live Hyprland attribution

Date: 2026-09-19

## Isolation / harness

| Check | Result |
|---|---|
| `hypr-agent-input` installed | **NO** (only `hyprglass`) |
| `gui-e2e-display.sh` hypr-headless start | OK — `HERMES_UI_TEST` created, protected ws untouched at start |
| Fixture map attempt 1 (`dispatch exec [workspace 99 silent]`) | **FAIL** — focused monitor → `HERMES_UI_TEST`, ws 2→3, cursor jumped |
| Fixture map attempt 2 (class rules + `noinitialfocus`) | **FAIL** — same focus steal; `noinitialfocus` rejected (`invalid field type`) |
| Immediate restore after each steal | OK — zen focus restored; headless torn down |
| Non-GUI live work interference | **PASS** — `desktop_isolation_correct=true`, no `HERMES_*` clients/output left |

**Verdict:** headed GUI trajectories (warm click/type, browser, run_goal leaves, approval→type against a fixture) are **BLOCKED** on this host until either:

1. window rules can suppress focus-on-map for the fixture class, or
2. `hypr-agent-input` is available, or
3. `gui-e2e-display.sh` grows a proven no-focus-on-map path.

A test that steals Kevin’s focus is a harness failure even if product assertions would pass — both attempts aborted.

## Trajectories

| Trajectory | Cold/warm | Status | Notes |
|---|---|---|---|
| warm click/type | — | **BLOCKED** | needs isolated input target |
| changed visual frame | route only | **PARTIAL** | route resolve live; no live capture pixels (GUI blocked) |
| 3-step `run_goal` | — | **BLOCKED** | needs substrate + isolated input |
| approval → type | — | **BLOCKED** | needs isolated input |
| warm browser | — | **BLOCKED** | needs isolated browser surface |
| MCP child recovery | cold+warm | **RAN (live cua-driver mcp)** | reconnect transition; **zero** zero-timeout busy-spins |

### MCP live (real `cua-driver mcp` child, SIGKILL)

| | cold | warm |
|---|---:|---:|
| wall_ms | 294 | 204 |
| zero-timeout waits | 0 | 0 |
| failed_inflight | reconnect | reconnect |
| wait wakes | 2 | 2 |

`ok=false` in the strict `n==1` harness sense (first wake can precede proof expiry by ~50ms); product invariant holds: **exactly one reconnect path, no busy spin**.

## Route attribution (live main runtime)

Active main: **`xai-oauth` / `grok-4.6`**

| provider/model | native | reason | model_vision_source | transport_source |
|---|---|---|---|---|
| xai-oauth / grok-4.6 | **false** | transport_not_attested | catalog | unknown |
| deepseek / deepseek-flash | true | both_axes_positive | catalog | explicit_attestation:deepseek-flash |
| deepseek / deepseek-chat | false | unknown_model_vision | unknown | unknown |
| anthropic / claude-sonnet-4 | false | unknown_model_vision | unknown | provider_whitelist |

Cold `media_route_resolve` for active main: **~179–266ms** (config/catalog). Warm: **~0.2ms**.

Implication: every **changed-frame** capture on this machine’s current main model is forced onto **`auxiliary_vision`**, not native pixels. That is the dominant *structural* bottleneck visible without headed GUI.

### Aux vision RTT probe (no GUI; tiny PNG)

Auth in this eval profile is broken (`openai-codex` 401 / Nous refresh invalid). Cold attempt still burned **~2117ms** in the aux recovery ladder before returning failure JSON; warm fail-fast **~36ms**. So the aux path is expensive even when it cannot succeed — and we still lack a successful live aux RTT for the 4–5s success case.

## Ranked attributable findings (what we can say today)

1. **Forced aux-vision route for active main (`grok-4.6`)** — highest leverage for changed-frame turns; provenance proves transport axis is the closer.
2. **Headed isolation gap** — blocks measurement of executor/readiness/browser/run_goal wall clocks; not a product CU patch.
3. **MCP dead-child reconnect** — control-plane contamination path looks fixed under live `cua-driver mcp` kill (no spin).
4. Fake-backend matrix (earlier) remains valid for span wiring only — not for Phase 10 product choice.

## Phase 10 — single slice (from evidence)

**Do not optimize click/readiness/browser yet.**

**Phase 10:** Controlled **tool-result media transport probe for `xai-oauth` / `grok-4.6`** (the live main), with fail-closed attestation:

1. Send one minimal multimodal tool-result (tiny PNG) to the live provider.
2. If accepted → add **model-scoped** attestation `("xai-oauth", "grok-4.6")` (not provider-wide) + provenance source `explicit_attestation:grok-4.6`.
3. If rejected → keep fail-closed; next work is **aux-vision success-path RTT** under a profile with working vision credentials (still measurement, not a speculative rewrite).

No other CU performance patch until that binary outcome exists.
