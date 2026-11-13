---
name: interrogate
description: "Use for \"interrogate\", \"adversarial review\", \"multi-model review\", \"challenge this\", \"stress test this code\", \"find blind spots\", or \"tear this apart\". Multiple LLM reviewers challenge changes from independent angles."
disable-model-invocation: true
---

# Interrogate

Spawn one reviewer per configured model to adversarially review code changes. The adversarial signal comes from model diversity, not assigned personas. The deliverable is a synthesized verdict. Do NOT auto-apply changes.

## Step 1, Scope

Identify what to review from context:

- If the user points at specific files or a diff, use that.
- If on a feature branch, run `git diff main...HEAD` (or the appropriate base branch) for the full changeset.
- If the user's message references recent work, gather the relevant files.

Package the diff or file contents with any surrounding context files the reviewers need to understand the code.

## Step 2, Intent

Before spawning reviewers, state the intent in one clear paragraph from the user's message, commit messages, the PR description if one exists, and the code. If you're unsure about the intent, ask the user before proceeding.

## Step 3, Spawn Reviewers

Resolve the requested participants and authorized subscription routes before launching. Explicit user model choices override configured reviewers and table defaults. For this user's councils, keep non-Google reviewers inside Hermes on their existing subscriptions; use Antigravity for the Google subscription. Treat harness, model, credentials and entitlement as separate checks; catalog visibility proves neither entitlement nor successful inference. Follow `terminal-agent-orchestration` for route verification and recovery.

Launch independent reviewers together through the host's supported delegation interface. When the user has not named participants, use one reviewer per entry on the `interrogate reviewers` line in `~/.cursor/rules/pstack-models.mdc`, labeled Reviewer A, B, and so on; if that line is missing, use the table defaults. Translate the reviewer contract to the actual host interface rather than assuming a Cursor Task tool exists.

| Subagent | Default model |
|----------|---------------|
| Reviewer A | `claude-opus-5-5-xhigh` |
| Reviewer B | `grok-4.7-xhigh-fast` |

Each reviewer gets `subagent_type: generalPurpose`, `readonly: true`, and `model` set to its configured entry, or its table default when there is no configured line. Omit `model` for an `auto` or `inherit-parent` entry, so that reviewer runs on the parent model.

If selection fails, inspect the exact session-opening or model-selection error and the live catalog before retrying. Preserve the requested harness and subscription; do not guess model spellings or move to a different paid route. Use an alternative model only within an explicitly authorized fallback, or report the missing participant. For unspecified reviewers, a supported same-family equivalent within the existing authorized route is acceptable if disclosed. Never treat an alias as a rejected slug. A review request does not authorize a provider/configuration change, implementation, publication or a separate maintenance PR.

Read `references/reviewer-prompt.md` and fill in the same template for every reviewer with the stated intent, the diff or file contents, the rubric from `references/rubric.md`, and the code-quality lens from `references/code-quality-review.md`. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **poteto-mode** skill.

### Socratic seminar variant

When the user asks for a council discussion or Socratic seminar, use actual multi-round participation rather than independent essays presented as dialogue:

1. Give each reviewer the same source packet and scope, without peer openings. Request questions, provisional answers, cited evidence, falsifiers and the strongest questions for peers. Label facts, inferences and proposals separately.
2. Verify each actual response and its source coverage before admitting it to the discussion. Track missing participants explicitly; launch acceptance is not participation. A substantive response captured during a failed run may inform peers only with its partial/error qualification attached.
3. Give reviewers the actual peer statements in a fresh review round. Require direct answers to peers' questions, identification of unsupported premises, and explicit revisions or retained objections. Never invent another participant's reply. Preserve prior findings and unresolved objections in every round's brief.
4. Keep facilitator challenges distinct from reviewer contributions. Challenge assertions such as “the only valid design,” altered treatment boundaries or forced common histories: agreement is not evidence, and a variance-reduction proposal can change the estimand.
5. Synthesize only after real cross-examination. Record who changed position and why, remaining disagreement, accepted recommendations, and proposals requiring a user decision. Preserve adopted acceptance gates verbatim; reviewer thresholds and suggested controls do not amend them.
6. Call the requested seminar complete only when every requested participant has contributed and had a real peer-response opportunity. Otherwise report the partial coverage and precise blocker without claiming consensus.

### Sequential scan-then-sanity variant

When the user names an order ("scan with ChatGPT, then a final sanity check with Sonnet"), run reviewers in series, not in parallel:

1. **Pin the exact head.** For a PR, clone into the scratch dir and `git fetch origin pull/<N>/head:prN && git checkout prN`; confirm with `git log --oneline -3`. `gh pr checkout -q` can leave you on the base branch without a visible error, which means you review the wrong code. Record the head SHA and the base SHA.
2. **First reviewer = claim verifier.** List every claim the author makes (from the PR body or the user's paste) and require it to check each one against the code. It must also report the commands it ran with pass/fail counts and end with a one-line verdict. Anything in another repo is reported as "unverified", never as passed.
3. **Second reviewer = adversarial confirmer.** Paste the first reviewer's findings and require a concrete reproduction (exact rendered text or output) that confirms or refutes each one. It must also run any failing tests on the base SHA in a temporary `git worktree`, then remove it, so the report can say whether failures existed before the change. A finding "confirmed by two models" counts only when the second model reproduced it, not when it just repeated it.
4. **Model names in T3 for this user:** "ChatGPT" = `hermes-clean-acp` / `openai-codex:gpt-6.1-sol`, and "Sonnet" = `hermes-clean-acp` / `anthropic:claude-sonnet-5-5`. Use `delegate_task` with `mode:"wait"`, `role:"review"` and a read-only brief (no edits, commits, pushes or GitHub posts; leave `git status` clean).
5. **Before offering to fix,** check push access: `gh api repos/<head-owner>/<repo> --jq .permissions`. If the PR comes from someone else's fork, report the fix with file:line instead of making it locally. Do not link a PR to the thread when you only reviewed it.
6. **Final reply:** start with the verdict, then each must-fix with the reproduced text and the suggested fix, then what was confirmed, and base-vs-head test results. Link the reviewer threads.

## Step 4, Synthesize

As results come back, build a unified picture. Parse every reviewer's findings. Merge findings that describe the same issue differently, and note which models raised each one. Weight independently raised findings more strongly, but distinguish independent reasoning from independent evidence: reviewers citing the same supplied audit do not independently verify its underlying claims. Trace consequential factual claims and numerical thresholds back to the canonical source, and keep unverified shared claims labeled as such. Read a lone model's finding, but weight it accordingly. Note disagreements. If one model flags something and another explicitly says the opposite, that is context for the verdict.

## Step 5, Lead Judgment

You are the lead reviewer, a pragmatic senior engineer, not a neutral aggregator. Read `references/lead-judgment.md` for the full framework. Put every finding in one of four buckets, with the model(s) that raised it and a one-line rationale.

- **Act on**. Real issues affecting correctness, security, or maintainability given the actual goals. They would block a real PR.
- **Consider**. Legitimate, but you're not sure they outweigh the cost of addressing them now. Worth the user's attention.
- **Noted**. Technically valid but not actionable. Context-dependent, premature optimization, or low-impact at this stage.
- **Dismissed**. Wrong, nitpicky, or missing context, with a brief reason.

## Output Format

### Intent
> [The stated intent paragraph from Step 2]

### Reviewers
- Reviewer [label]: [model name], [N findings] (one bullet per reviewer)

### Act On
[Each: description, which models raised it, why it matters.]

### Consider
[Each: description, which models raised it, the tradeoff.]

### Noted
[Brief list.]

### Dismissed
[Each with a brief rationale.]

### Agreement Map
[Where models agreed and diverged, and what that pattern tells us.]
