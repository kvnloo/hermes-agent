# Captain attention policy — implementation report

## Scope

Implemented in the authoritative gateway Kanban watcher. Task state, subscriptions, task events, dispatcher behavior, `/freeze`, and worker execution are unchanged. The feature is disabled by default and destination-scoped.

## Delivery behavior

- Emergency/immediate: typed `needs_input`, typed unrecoverable `capability`, security/trust/credential/privileged-action text, repeated-failure triage, requested changes, and final milestones explicitly asking for Captain/operator/human sign-off.
- Routine/digest: child completions, status churn, ordinary review requests, deliberate focus pauses, duplicate/superseded/no-action blocks.
- Child events group by direct parent and become one bounded delta digest with task IDs.
- Atomic subscription cursors remain canonical. Deferred events are CAS-rewound; successful digests retain their claimed cursor. A mixed urgent/routine claim stays atomic on the immediate path, so neither subset can be silently acknowledged or independently replayed.
- An active conversation defers routine delivery only when its canonical session key exactly matches the subscribed chat/thread; activity elsewhere on the same adapter has no effect. Emergency events still interrupt.
- Destination selectors may include `thread_id`; sibling topics remain on legacy delivery unless separately selected.
- Secrets matching key/token/password/secret/bearer assignments are redacted and output is capped by `max_chars`.

## Presentation modes

- `brainstorm`: queues all non-emergency events. It does not pause, freeze, block, or mutate tasks.
- `pm`: emits bounded parent/portfolio digests at the configured interval.
- `copilot`: emits routine digest entries only for `focus_task_ids` (hard maximum: first three); emergencies remain immediate.
- An in-process mode transition out of a suppressive mode makes the queued delta eligible immediately. A restart also safely discovers the queued delta from the unchanged event/cursor state.
- Explicit `hermes kanban status`/board status remains live board truth and requires no notification mutation.

## Activation (after independent review)

Use `hermes config set`; do not hand-edit YAML. Replace the destination values with the subscribed profile/chat identity:

```text
hermes config set kanban.notification_policy.destinations.0.profile first-mate
hermes config set kanban.notification_policy.destinations.0.platform telegram
hermes config set kanban.notification_policy.destinations.0.chat_id <CAPTAIN_CHAT_ID>
hermes config set kanban.notification_policy.mode pm
hermes config set kanban.notification_policy.interval_seconds 900
hermes config set kanban.notification_policy.max_chars 900
hermes config set kanban.notification_policy.enabled true
```

Copilot focus (maximum three):

```text
hermes config set kanban.notification_policy.mode copilot
hermes config set kanban.notification_policy.focus_task_ids.0 <TASK_ID_1>
hermes config set kanban.notification_policy.focus_task_ids.1 <TASK_ID_2>
hermes config set kanban.notification_policy.focus_task_ids.2 <TASK_ID_3>
```

Brainstorm silence for non-emergency presentation only:

```text
hermes config set kanban.notification_policy.mode brainstorm
```

## Immediate rollback / kill switch

```text
hermes config set kanban.notification_policy.enabled false
```

The watcher reloads configuration each tick; no task-state rollback is needed.

## Synthetic verification (no Telegram calls)

Command:

```text
HERMES_PYTHON=/workspace/hermes-home/hermes-agent/venv/bin/python scripts/run_tests.sh tests/gateway/test_kanban_attention.py tests/hermes_cli/test_kanban_notify.py tests/gateway/test_kanban_notifier.py tests/gateway/test_kanban_notifier_zero_sub_gate.py
```

Result: 47 passed, 0 failed. Coverage includes 10 child completions to one parent digest, deliberate pause classification, Captain/security/final-signoff urgency, chat and thread destination isolation, exact-session conversation debounce, mixed urgent/routine atomic claims, restart cursor dedupe, duplicate replay, grouping, length cap/redaction, and legacy notifier behavior.

No live destination was configured and no Telegram message was sent.
