# Code-health precision study — completed

Study for upstream PR #132646. No production edits or upstream comments were made during this study.

## Exact results

109 labeled cases across all 14 `HX*` / `PS-*` rules: 101 constructed contract cases, plus 8 source-derived controls/counterfactuals from four real Hermes source families. These are not 109 historical incidents or a representative production precision estimate.

| Unchanged implementation | Source SHA | Expected contracts matched | Suppress/overreport mutants caught |
|---|---|---:|---:|
| Earlier upstream | `96bb97a7892c3ea9497aab494dce69484ebc6b36` | 83/109 | 28/28 |
| Our experimental fixes | `3aad0cd6f0dac07ecd383670fbe33e5b20d1dc42` | 91/109 | 28/28 |
| Current tested upstream | `ccafc30d13f7ca1a6a8e5a19466e3c4de841c1f9` | 100/109 | 28/28 |

Every fixture completed. Zero measurement errors. Production Git/Ruff measurement and a separately invoked public JSON CLI agreed on target-rule diagnostics. Mutations were process-local, other rules were unchanged, and restoration parity was checked. A mutation counted as caught only when a previously passing assertion failed.

Additional checks: **195 existing upstream code-health tests passed in 54.07 seconds; 10 independent behavioral witnesses passed.** Environment: Linux, CPython 3.13.5, Ruff 0.15.10; TypeScript 6.0.3 for the existing suite. The 28 mutants per implementation are one suppress and one overreport mutation per rule, not exhaustive mutation testing.

## Current-head disagreements

Seven false-positive diagnostics and two missed diagnostics against the curated labels.

Four false-positive candidates affect currently blocking rules:

- `HX004`: an unused nested function inside an exception handler contains an environment read, but the handler only re-raises. Independent execution records zero fallback reads.
- `HX007`: an unrelated object's pure `load_config()` method is treated as blocking config I/O.
- `HX008`: a parameter named `asyncio` is treated as the actual module when calling its `get_event_loop()` method.
- `HX009`: an unconditional reassignment of gathered results to an ordinary integer list does not invalidate result provenance. The subsequent `Exception` check is on integers, not gathered results.

Advisory rules:

- `PS-P05` and `PS-P06` each flag assigned warning/prose strings and miss executable operations split across lines. The wrapped and single-line controls have identical ASTs.
- `HX012` flags the real `agent/memory_provider.py::spawn_context_thread` implementation using `ctx_bound`. The real helper propagates context: the worker sees `secondary`. Removing only `target=ctx_bound(target)` makes it see `default`. Both variants receive a static warning. This does not mean the unchanged, grandfathered helper currently blocks main.

The source-derived pairs cover `ctx_bound`/`spawn_context_thread`, the per-call reconnect threshold fix documented as #115635, Yuanbao gathered-media result checks, and the Windows holder's token-based subcommand classifier. Counterfactual variants are explicitly distinguished from historical original source.

## Correction to the previous replay interpretation

The `HX006` hit in #132664 is **not an established missing-timeout bug**. `pm/libatomic.py::install_before_lock` deliberately permits an interactive sudo/package operation outside the package-manager lock without a timeout, to avoid killing a slow prompt or package installation. The earlier description of that child as noninteractive was wrong.

Pinned source: https://github.com/NousResearch/hermes-agent/blob/af90026aa09949579bd423d24def3d38f743cde0/pm/libatomic.py#L90-L129

The `HX012` watchdog hit in #132219 likewise does not demonstrate a profile-isolation defect merely because it constructs a raw thread. The shown callers implement process-lifetime observation and fenced retirement.

Pinned source: https://github.com/NousResearch/hermes-agent/blob/7533bd2756b9526b52f527f737420a19e57331d7/hermes_cli/web_server_skew_exit.py#L48-L105

## Recommendation

Keep the existing six-rule advisory boundary. Address the four blocking false-positive candidates through bounded regressions and repairs, not a replacement architecture. `HX002`, `HX005`, `HX006`, and `HX011` matched every included current-head contract case, but this does not establish universal semantic correctness or justify blanket blocking from the replay sample alone. `HX002` and `HX011` are governance/style policies, not runtime defect detectors.

Our earlier 49-test success was insufficient evidence for promotion: the larger same-input study still exposes gaps in our fork.

## Reproducibility and limits

The complete portable study bundle supplied with the report contains the 109-case frozen JSON corpus, exact checker modules/policy inputs for all three versions, runnable measurement/mutation harness, behavioral witnesses, per-case result JSON and hashes. It executes fixture parsing, real Ruff, real Git comparisons and the public CLI; it does not run fixture subprocess commands or access real credentials.

The source collection is retained in the fork workflow: https://github.com/kvnloo/hermes-agent/actions/runs/37253101107

No Windows/macOS run or population-wide precision estimate is claimed. An auxiliary whole-tree candidate scan timed out and is excluded from every reported total. The finite 109-case study and its validation runs completed.
