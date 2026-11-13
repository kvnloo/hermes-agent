---
name: principle-never-block-on-the-human
description: "Apply when tempted to ask 'should I do X?' on reversible work."
disable-model-invocation: true
---

# Never Block on the Human

The human supervises asynchronously. Agents must stay unblocked. Make reasonable decisions, proceed, and let the human course-correct after the fact. Since code changes are reversible and reviewable, a wrong decision usually costs less than blocking.

- Proceed, then present. Do the work, show the result. Don't ask "should I do X?" Do X, explain why.
- Make the system self-healing. When you notice a problem, log it and fix it in the next round.
- Irreversible actions (force-push, delete production data, send external messages) still require confirmation.
- Reversible actions (write code, edit notes, split tasks) should proceed without blocking.
- Do not end a turn with an offer ("Next I can X, want me to?") when X is reversible and part of the ask. Do X in the same turn and report the result. Stop only when truly blocked: a missing credential or owner decision, an irreversible or external action, or an action that interrupts the owner's running lanes, such as pausing his phone factory. When you stop, name that specific blocker.
- Before reporting "done", ask what the owner's goal still needs: a cause that hasn't been confirmed, a remaining source, or a fix that hasn't been installed. Work through those first. Leave only the genuinely blocked items in the reply.
- Product direction comes from the human. Execution should not block.
