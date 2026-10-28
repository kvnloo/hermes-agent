# Goal policy extension

Goal policies opt a session into an installed plugin's continuation decision. Ordinary goals retain their existing judge behavior. The host owns persisted goal state, gates, budgets, waits, and user controls.

## Registration

An in-process plugin calls `ctx.register_goal_policy(policy)` during `register(ctx)`. The host registers the object under that plugin's ID and removes it when the plugin unloads. `plugins.isolation: host` explicitly refuses this initial implementation.

The object implements `hermes_cli.goal_policy.GoalPolicy`.

```python
class Policy:
    def prepare(self) -> str:
        return load_existing_workflow()

    def decide(self, observation: GoalObservation) -> GoalPolicyDecision:
        return GoalPolicyDecision("replan", "Reconsider the original goal.")
```

`prepare()` returns actual loaded workflow text, not a model assertion. An empty result or exception pauses the opted-in goal. The host returns the text when arming and includes it in continuation messages. A persisted content digest identifies the last delivered workflow. Changed or missing content requires `load_workflow` before goal work continues.

`GoalObservation` contains the original goal, judge verdict, workflow readiness, current check result, and optional host-observed wake ID. `GoalPolicyDecision.action` is `load_workflow`, `execute`, `replan`, `finish`, or `wait`. The host rejects `finish` without successful current checks and a DONE judge verdict. It rejects `wait` without an observable source and registers the actual native barrier before returning a wait decision.

## Agent-callable arming

A plugin tool can call `ctx.arm_goal(goal, max_turns=..., gates=...)`. This requires all of the following:

- A task-local native session ID.
- The plugin's owning profile.
- `plugins.entries.<plugin-id>.settings.allow_arm: true`.
- No existing goal row, including paused, done, or cleared goals.
- A positive turn budget and nonempty acceptance gates.
- Successful workflow loading and persisted-state readback.

Gates are native `hermes_cli.goals.GoalGate` values. Plugins must obtain commands from operator-reviewed configuration, never unrestricted model tool arguments. The concrete consumer accepts a configured mission name and cannot rewrite the mission or raise its budget.

Arming never resumes, replaces, clears, or refills a goal. Users retain native goal controls. A new session can arm another mission. Emergency stop prevents arming and continuation. Permission checks on ordinary tools remain unchanged.

## Persistence and completion

Optional `policy`, `policy_checks`, and `policy_workflow_digest` fields extend the existing goal JSON. Rows without these fields keep default behavior. A missing consumer pauses its opted-in goal instead of silently completing it.

Every configured acceptance command must remain registered. Every current gate must return zero before completion. The adapter retains native gate timeouts and retry budgets. Added natural-language subgoals prevent completion until an operator supplies an explicit acceptance mapping in a new mission. A command that returns zero without checking the intended outcome is not a sound acceptance check.

State readback before and after evaluation rejects user controls changed during a blocking workflow load, gate, or judge call. This is not a database transaction spanning evaluation and downstream admission. Native admission and interrupt semantics still own final scheduling.

## Delivery limits

The extension runs through native `GoalManager.evaluate_after_turn`. The gateway retains its messaging FIFO and LOCAL `admit_route_wake` paths. The classic viewer refreshes goal state after tools before applying its existing interrupt and continuation logic.

This extension does not add a daemon, polling loop, durable delivery retry, or wall-clock run budget. It does not certify wake delivery or reconnect liveness. An installed plugin is not live enforcement. The core code must be rolled out safely, the plugin must be discovered in the correct profile, and its tool must be available in a fresh session.
