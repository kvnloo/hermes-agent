# Run 003 — lazy rematerialization of one surviving operation

Date: 2026-10-06

Source change: NousResearch/hermes-agent#105624  
Durable operation: `OP-observe-sibling-addressed-user`  
Fresh target: `NousResearch/hermes-agent@59a3866ea5a07290afd9a1d137d52d679b77f3ab`  
Materialization branch: `kvnloo/hermes-agent:exp/change-ir-remat-105624-sibling-observe`

## Constraint

Do **not** rebase or replay the 818-addition PR.

Reconstruct only this invariant:

> A user message explicitly addressed to another Telegram bot may be recorded as attributed context by this bot, while the current bot still must not dispatch/respond.

The outbound sibling-response mirror is a separate operation and is intentionally excluded.

## Materialized implementation

Fresh implementation against current main:

- `gateway/config_loader.py`: expose one opt-in Telegram key.
- `plugins/platforms/telegram/adapter.py`:
  - add `_telegram_observe_sibling_bot_messages()`;
  - classify a foreign-bot-addressed **user** message separately from ordinary unmentioned chatter;
  - preserve the current exclusive-bot dispatch gate;
  - return early into observation before free-response/reply/wake-word vetoes that dispatch can never reach for that message;
  - allow the group-observe prompt/attribution path when sibling-observe is the only enabled observation mode.
- `tests/gateway/test_telegram_group_gating.py`: three focused invariants:
  1. sibling-addressed user message is observed but not dispatched;
  2. sibling mode does not start ingesting ordinary chatter;
  3. with sibling mode off, sibling-addressed messages keep current drop behavior.

No outbound mirroring, sibling-profile DB writes, streaming/finalization wiring, docs, or cross-host design is included.

## Size

Original #105624:

- 4 files
- 818 additions / 6 deletions = **824 changed lines**
- diff: **957 lines / 47,601 characters**
- PR body: 9,131 characters
- existing discussion: 10,823 characters
- old review-context total measured here: **67,555 characters**

Rematerialized operation before the CI-only workflow commit:

- 3 files
- 79 additions / 3 deletions = **82 changed lines**
- diff: **137 lines / 6,883 characters**
- Change IR fixture: 5,657 characters
- new review-context total: **12,540 characters**

### Compression

- **90.0% fewer changed code/test lines**
- **81.4% less measured review context**
- old review packet is **5.39× larger**

This is not “AI wrote fewer lines” by itself. The reduction came from classifying the PR first and declining to rematerialize an independent operation (outbound mirroring).

## Semantic safety rule

The semantic-anchor probe did not generate this patch automatically. It identified the current architectural surfaces and uncertainty. The actual materialization was then constrained by the durable invariant and current dispatch/observation order.

That separation remains important: textual anchors provide evidence; they do not prove equivalence.

## Validation

A branch-local GitHub Actions workflow runs:

```
python -m pytest tests/gateway/test_telegram_group_gating.py -q
```

Workflow: `Change IR rematerialization`, run 37547255551.

Validation result is recorded in the final experiment closeout; the workflow file itself is excluded from the compression numbers above.
