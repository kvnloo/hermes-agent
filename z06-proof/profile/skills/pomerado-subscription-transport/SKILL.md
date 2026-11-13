---
name: pomerado-subscription-transport
description: Use when changing Pomerado's subscription transport.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [pomerado, typescript, subscription, transport, testing]
    related_skills: [typescript-best-practices, github]
---

# Pomerado subscription transport qualification

## When to Use

Use for Pomerado ChatGPT subscription wire compatibility, SDK patch translation, auth-safe smoke tests, or transport regression qualification.

- Keep compatibility changes in `typescript/src/models/chatgpt-subscription.ts` and its patch helper, not the mint/Guardian/outcome-review callers. Use the SDK's real Runner and a local HTTP/SSE fixture server to test the seam.
- Translate native `apply_patch` into a same-name function with an operation schema; convert incoming function calls to `apply_patch_call` and replay calls/results as function history. Preserve call IDs while removing stored item IDs. Streaming patch arguments must be assembled before emitting an executable native item; test both streamed and collected turns with real SDK editor execution.
- Normalize terminal SSE failures before the Agents SDK converts `response.failed` to ModelBehaviorError, which drops status/code. Test error, response.error, and response.failed for both modes, plus redaction and spent-quota normalization. OpenAI 7.23 API error subclasses have `.name === "Error"`; don't confuse their constructor names with `.name`.
- Strip cache breakpoints at item and content-part levels, drop provider cache options and reasoning context, skip prewarm locally, and preserve encrypted compaction checkpoints without output-only fields. Explicitly reject unsupported compaction triggers and stored item references rather than silently deleting history. The existing idle compactor disables itself on refusal.
- Use Node 24.21 from the installed fnm version when the ambient shell is newer. Run unit/browser suites sequentially with at most two workers. On heavily loaded hosts, rerun the full unit suite with one worker and a bounded larger test timeout; report initial flakes.
- Install Playwright's exact browser revision in its default cache as well as any custom cache when executor child processes sanitize environment variables. A custom PLAYWRIGHT_BROWSERS_PATH alone does not cover those children. Use a tracked background process for long browser runs and poll it; short foreground tool deadlines may kill otherwise passing runs.
- For an authorized one-request live smoke, copy auth into a mode-0600 isolated temporary store and use reread mode to prohibit rotating shared refresh tokens. Guard the fetch count, force the patch tool, and inspect the returned native item. Compare source-auth digests before/after without printing credentials; delete the isolated copy. Do not repeat the live request merely to rerun offline checks.
