# Run 002 — Vox Lockin 17-PR stale-wave classification

Date: 2026-10-06  
Baseline: Vox Lockin #78207, 2026-08-04  
Target: `NousResearch/hermes-agent@59a3866ea5a07290afd9a1d137d52d679b77f3ab`

## Question

Two months after the campaign fast-forwarded 17 stale-base PRs and verified them green, what is the durable state of the work?

The unit under test is semantic intent, not GitHub's open/closed bit.

## Result

| class now | PRs | count |
|---|---|---:|
| clearly implemented/superseded on main | #78036, #77724, #77748, #77756, #77751, #77759, #77752, #77719 | 8 |
| mixed: some operations absorbed, some still unresolved | #78033, #77708 | 2 |
| requires a fresh design/priority decision | #77911, #77907, #77909, #77706, #77707, #77710, #77711 | 7 |

**Blindly replayable as-is: 0/17.**

That is the important measurement. Every branch was green after a current-main refresh on 2026-08-04. By 2026-10-06, none of the 17 should be treated as “just rebase and merge.”

## Clear supersession / implementation

### #78036 — TUI `shell.exec` environment boundary

Current `tui_gateway/methods_tools.py` constructs `build_subprocess_env()` at the registered `shell.exec` path before child execution. The old change intent is therefore `already_on_main`.

The PR's October closure was explicitly capacity-driven (“not a statement on the merits”), which demonstrates why GitHub state alone is insufficient: a closed PR can simultaneously represent work that later became real product behavior.

### Gateway decomposition slices

Maintainer comments explicitly record these as superseded by the shipped `66366d3*` decomposition:

- #77724 — `TurnRunner` → `gateway/run_turn_runner.py`
- #77748 — runtime-config cluster → `run_config_loaders.py`, `run_agent_cache.py`, `run_turn.py`, `run_inbound.py`
- #77756 — dispatch cluster → `run_inbound.py`, `run_turn.py`, `run_busy.py`
- #77751 — media cluster → `run_inbound.py`, `run_voice.py`, `run_notifications.py`
- #77759 — adapter lifecycle → `run_adapters.py`
- #77752 — turn execution → `run_turn.py`, `run_agent_cache.py`, `run_shutdown.py`
- #77719 — config/runtime decomposition intent → shipped facade + `run_*.py` architecture

The filenames differ from the stale branches, but the architectural intent survived. A filename/patch matcher alone would miss that.

## Mixed cases

### #78033 — plugin sidecar child environments

This PR cannot be represented by one state anymore.

Already absorbed:
- ByteRover uses `build_subprocess_env` + `strip_launch_profile_env` and restores its own scoped `BRV_API_KEY`.
- Buzz uses `hermes_subprocess_env` and restores its own `BUZZ_PRIVATE_KEY`.

Still requiring current-main analysis:
- Google Meet's process manager still constructs the bot child from `{**os.environ, ...}`.
- Photon still has install/process/sidecar child paths based on `with_hermes_node_path`; whether each path should inherit or scrub credentials must be re-derived from today's boundary contract.

This is a direct demonstration that **one PR can have both `already_on_main` and `still_needed/needs_decision` descendants**.

Credit preserved: @andrexibiza authored the patch; @egilewski identified residual sidecar boundaries; @jonpol01 identified the ByteRover key/multiplex interaction.

### #77708 — env/bootstrap extraction

The two old operations diverged:
- the startup SSL certificate mutation/guard has been removed from the architecture;
- `_bridge_max_turns_from_config` remains a live public helper in the `gateway.run` facade.

So replaying the old “extract both into env_helpers.py” patch would resurrect dead architecture while moving a still-live facade seam without a current design decision.

## Fresh-decision cases

### #77911 — god-file campaign canon

The decomposition that the document described as pending later shipped, while the proposed `i-killed-the-godfile.md` file is absent on main. The durable artifact is now “document the decomposition and its lessons,” not the historical text/diff. Regenerate or drop; do not replay.

### #77907 / #77909 — bundled skills

Both were closed for contributor-volume narrowing and their skill paths remain absent. There is no evidence of rejection, but there is also no maintainer acceptance that would justify automatic rematerialization. State: `needs_decision`.

### #77706 / #77707 / #77710

Their helper symbols remain in `gateway/run.py`, now serving as public facade seams imported by newer `run_*.py` modules. Their original “move these helpers out” intent is still intelligible, but today's facade convention did not automatically absorb it. State: `needs_decision`.

### #77711

The history helpers remain in `gateway/run.py`, but `_select_cached_agent_history` has semantically evolved since the stale extraction: current main requires a real non-ephemeral unpersisted row before preferring live history. Replaying the old extracted body would reintroduce the bug guarded on main. State: `needs_decision` with explicit semantic drift.

## What this falsifies

A naive stale-PR service built around any of these rules would be wrong:

- `closed ⇒ dead`
- `green after rebase ⇒ still mergeable later`
- `missing target filename ⇒ work disappeared`
- `same PR ⇒ same current state for every hunk`

The 17-PR sample contains counterexamples to all four.

## What survived

The useful durable pieces were:

1. the intended architectural boundary or behavior;
2. invariants and tests;
3. semantic operations small enough to classify independently;
4. provenance: diagnosis, proposed implementation, review discovery, and eventual implementation can have different authors.

The raw branch was useful as evidence, but not as the durable identity.

## Machine-readable source

See `fixtures/78207.json` and `relations.json`.
