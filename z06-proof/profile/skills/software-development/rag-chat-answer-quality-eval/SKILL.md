---
name: rag-chat-answer-quality-eval
description: "Use when tuning or picking models for a RAG chat app."
---

# RAG chat answer-quality eval loop

## When to Use

For public, evidence-grounded chat sites (retrieval → prompt → model → streamed answer with `[n]` citations), when the owner asks for "high quality" or "test exhaustively with free-tier models, keep iterating if bad". The owner expects real runs and scores, not opinions; keep going until scores plateau, not after one pass.

## Procedure

1. **Harness first, through the real code.** Write `eval/run.mjs` that imports the app's actual Worker/server handler and the browser's actual SSE parser, swaps only the model binding for an adapter, and mocks anti-bot (Turnstile) verification. Never re-implement retrieval or prompting in the harness — divergence hides the bugs you are looking for.
2. **Question set** (`eval/questions.json`, ~30–40): identity, each tool/project, opinions, voice/style, contributions with numbers, how-to/next-step, multi-turn follow-ups (with `history`), private-data refusal, false premise, unknown/gap, off-topic (weather, coding help), prompt injection / "pretend you're him", and the user addressing the bot as the person ("why do u write lowercase"). Each item: `expect` (owner note on a great answer), `any` term groups, `none` regexes.
3. **Grade two ways.** Deterministic: answered, no reasoning leak, every `[n]` in range, citations present for factual kinds, required terms, not truncated (ignore answers ending in a URL/code), not overlong. Judge: a larger free model gets the exact sources the model saw, lists claims (supported/cited), scores grounded/citations/helpful/behavior/style 0–2. Tell the judge that statements about the bot itself need no source. Read flagged answers yourself.
4. **Save evidence per row** so `--regrade <tag> [--ids a,b]` can re-judge after judge 429s or judge-prompt fixes without re-calling the model. Add `report.mjs` that recomputes scores from row files (summary lines from partial runs mislead).
5. **Run every path the site offers**: default free model streamed and non-streamed, each bring-your-own-key provider through the real handler (`--byo`), and the on-device path (`--local`, reusing the browser's pure planning function, with an Ollama model of the same family as stand-in). Screen candidate models in a batch, then rerun the top 2–3 on the final prompt.
6. **Iterate**: fix the top failure class, run a targeted probe (`--only ids`), then a full rerun to check for regressions in other categories, since prompt fixes often trade one failure for another.
7. **Click through the real UI** (local dev server serving site + handler with the adapter) with a multi-turn conversation, an off-topic turn, and a screenshot; check citation chips link correctly and sources are distinguishable.
8. **Ship**: tests for every fix (stream normalization, citation normalization, retrieval routing, renderer safety), README table of scores/latency/cost per path with the chosen defaults and why, commits with the owner's identity, push, check CI on the PR.

Model/provider quirks and the fixes that worked: `references/model-quirks.md`.

## Pitfalls

- Turn off visible reasoning per model and provider. Reasoning tokens count against `max_tokens`, so a thinking model can return an empty answer. The switch differs per provider: a param one provider requires can make another return HTTP 400.
- Choose the default by score *and* cost/latency. A model that ties on quality but uses 2× neurons/latency loses.
- When adding an out-of-scope rule, also name in-scope edge cases (follow-ups, questions about writing style, questions about the site itself). Otherwise the model starts refusing valid questions. A source that merely shares the topic (e.g. a weather-API fork) does not make a request in scope.
- Frame the visitor text as a message to answer under fixed rules ("Visitor:\n…"), not as a bare instruction. Small models obey injected "ignore previous instructions" otherwise. Small local models parrot a quoted refusal sentence even on-topic, so give them the plain framing.
- Small models skip `[n]` markers. Post-hoc attach a marker only when an answer has none, and only to sentences with strong keyword overlap with one source; prefer a source whose title the sentence names. Split sentences on `[.!?]` followed by whitespace so `6.5`, `TOOLS.md` and URLs stay whole. For streams, send the corrected text as a final SSE event that the client swaps in.
- Merge retrieved parts of the same section into one numbered source, and label sources by origin (`title · FILE.md`, `title · Boplog`). Duplicate titles read as bugs.
- Make the harness fail fast (exit after the first N rows all error). A dead proxy or exhausted quota otherwise produces a full run of errors that looks like a score. Retry 429/5xx with jittered backoff, and keep judge concurrency low (1–2).
- Workers AI without Cloudflare credentials: `npx wrangler@4 deploy --temporary` a 10-line proxy Worker (`{model,input}` → `env.AI.run`, guarded by a shared-secret header passed via `--var`). Temporary accounts expire within about an hour, so redeploy and update the URL when every call fails.
- Avoid `:` in run tags (Ollama ids such as `qwen3:4b`); they make awkward filenames, so sanitize them.
- Gitignore `eval/results/` and build-generated copies. Make `test` build first, and pass test files by glob (`node --test tests/*.test.mjs`): Node 22 treats a bare directory argument as a file, so CI fails even though tests pass locally.
