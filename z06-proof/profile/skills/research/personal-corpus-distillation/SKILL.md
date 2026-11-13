---
name: personal-corpus-distillation
description: "Use when auditing or distilling personal chat history."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [memory, graphrag, chatgpt-export, claude-export, knowledge-graph, distillation]
    related_skills: [third-party-stack-research, llm-wiki]
---

# Personal corpus distillation (chat history -> compressed levels)

Choose the requested output before selecting machinery. For a recent-message recount or unfinished-work audit, use a bounded source-message ledger and evidence reconciliation; do not build or refresh GraphRAG. For long-term distillation, turn the user's ChatGPT / Claude / agent history (and every other personal source that is safe) into a hierarchy: L0 one paragraph, L1 a page of themes, L2 theme reports, L3 browsable nested HTML, plus the full knowledge graph, using stock microsoft/graphrag as a batch job. Do not build a new memory system, daemon or store; the user wants an optimized solution, not another system to manage.

Standing preferences:
- Research how others use the tool (blogs, papers, issues, example repos) and design from that before running it; installing a library and running it blindly is not acceptable.
- Ingest everything that is safe, not just chats: repos, Google Takeout, LinkedIn, Keep, Telegram, agent sessions. Safety is decided by local privacy classification, not by leaving sources out.
- Models: the user's subscriptions (Claude, ChatGPT), free tiers and local SLMs first; pay-per-token only on request. Reuse logins already on the host (Hermes, Codex, bws) instead of asking for a new login.
- Exploration and methodical design come before generation; ask before spending large quota on a full run.

Canonical project: `/mnt/zer0models/sft-svlm/data/graphrag/` (private data plane; README there lists the rebuild commands). venv: `/mnt/zer0models/venvs/graphrag`. Fork: `kvnloo/graphrag` (unmodified).

## When to Use

The user wants a recount of recent messages and unfinished work, their accumulated chats/agent sessions compressed into a small md/html summary plus larger linked knowledge bases, or an index rebuilt, extended to a new source, or re-run on another model.

## Recent-message recount and priority audit

1. Fix an explicit start, end and timezone for the requested window. Inventory available histories across harnesses and profiles read-only; distinguish requested scope from retrievable scope. Export stable source IDs and provenance before model analysis. A timed-out index query is a coverage gap, not an empty history: try a bounded existing-source fallback without launching a corpus rebuild.
2. Apply the local privacy/authorship routing manifest before any cloud extraction, as required below. Obvious-secret regex redaction is not privacy classification. Treat user-role records as candidates, not proven owner speech; use conversational continuity and source metadata to exclude agent briefs, notifications and pasted summaries. Do not blanket-exclude a primary session merely because its source is named `oneshot`; ambiguous attribution stays separate. Preserve long owner messages in full for this audit rather than using the capped GraphRAG export.
3. Partition by bounded bytes/tokens, not message count, retaining a manifest of every assigned message ID. Use the extraction and prioritization roles from `token-thrifty-agent-routing`; model access follows privacy eligibility, not convenience. Checkpoint structured extraction after each chunk, including excluded and ambiguous IDs. Every extracted request carries original-message provenance, constraints, repetitions and supersession links.
4. Before frontier synthesis, mechanically compare expected IDs against the union of classified IDs; require no missing IDs, unexpected IDs or duplicate classification. Also validate semantic extraction: each ID needs an allowed authorship/action category, and every actionable request/correction needs a provenance-linked request or explicit disposition. Verify quoted evidence against the canonical source text. A list of IDs or a placeholder ledger with no requests is not proof that extraction finished. Reuse already-validated worker outputs when another seat fails; stop or label partial coverage rather than allowing missing batches to disappear.
5. Give independent prioritizers the same complete ledger and scope gaps. Verify fulfillment using bounded subsequent assistant replies in the exact source session as well as source/deployment evidence; an owner-only corpus cannot establish that a question or research answer was never delivered. Recheck current ownership before calling work unowned, because an earlier inventory can predate a completed slice or resumed owner. Keep implemented, exact-revision-tested, deployed and user-verified distinct; timestamp evidence and flag reported versus independently verified claims. Distinguish active, blocked, interrupted/unowned, intentionally deferred, superseded and completed work. Do not label a task abandoned solely because a worker stopped.
6. Reconcile disagreements into a complete request-to-work-item mapping plus a short ranked next-action list. Mechanically validate each prioritizer's mapping, and report extracted entries, normalized work groups and unfinished items as different counts. Label inferred priorities and effort estimates; explicit urgency, live breakage and blocked dependencies outrank convenient worker availability. If one reviewer fails, preserve the completed opinion and resume only the failed seat; label useful interim findings provisional rather than implying consensus. Include completed/superseded items for accounting and preserve unknowns. A recount authorizes analysis, not new implementation or runtime changes.

For bounded export/query details and coverage checks, use `references/history-recount.md`. Keep audit progress in task artifacts, not persistent memory.

## Long-term distillation procedure

1. **Inventory sources read-only** under `/mnt/zer0models/sft-svlm/data/raw/` (openai-extracted conversations-*.json, anthropic zips incl. memories) and AgentsView. Estimate tokens per source with a dry-run export before spending anything.
2. **Export one text file per conversation** (`scripts/export_text.py`): user/assistant text only, cap long messages, skip ChatGPT `is_do_not_remember`, always keep saved memories.
3. **Classify privacy tier, authorship and route locally, before any cloud model sees content.** Project: `/mnt/zer0models/sft-svlm/data/privacy/` (README has the rerun commands; `manifest.jsonl` is the input filter for every index). Layers: regex/checksum detectors, GLiNER2-PII NER, a local qwen3-4b pass for contextual labels, then a pure policy function. Tiers, model eligibility and routes: `references/privacy-tiers.md`. Do not classify with Haiku or any cloud model: the classifier exists to decide what cloud models may see.
4. **Pick models per tier from the benchmark** (skill `graphrag-model-benchmark`): T0/T1 extraction on subscription Haiku 4.5 or Cerebras free Qwen3.8-27B, community reports on Haiku 5.5 via the Claude Code shim, T2/T3 on local models only. ChatGPT subscription models (gpt-6.1-sol, gpt-6-luna) run through `scripts/chatgpt_token_sync.py` (copies Hermes' access token only, never the refresh token). Warn that a full run draws on the same 5 h / weekly limits as interactive sessions; schedule overnight.
5. **Pilot on a recent slice** (`--since`, ~150 conversations), check the levels read as being about the user, then run the full index in the background (terminal background+notify, not nohup).
6. **Render levels**: `scripts/render_levels.py` (L1/L2/L3 from parquet, no LLM) and `scripts/l0.sh` (`graphrag query --method global`).

Settings that matter and the reasons: `references/graphrag-settings.md`. Tier table and routing rules: `references/privacy-tiers.md`.

## Before any full run

Read `DESIGN.md` in the project. It routes by source type: self (user-written text, assistant turns capped), repo cards (no code), a separate learning index for coursework, and taste digests for event logs (raw events never go to the LLM). Classify every document into privacy tiers and authorship first (`/mnt/zer0models/sft-svlm/data/privacy/`), with local models only, and use the routing manifest as the input filter. Tune prompts (`graphrag prompt-tune`), enable claims, normalise the owner's aliases, and compare variants against gold preference sets (twin.db `preferences`, oss-factory passport, Hermes USER) before the full run.

## Pitfalls

- The ChatGPT account is shared with the owner's sister Megan (med student). Her projects (`conversation_template_id` g-p-681655..., g-p-681663...) and personal statements/resumes are her personal data: route them to their own bucket, never into the owner's self index. Medical knowledge can still go in the learning index.
- Stock extraction on chats is dominated by assistant explanations. The user's own turns carry the identity signal; weight them and cap assistant text.
- `graphrag update` never removes deleted documents, and cache/ plus update_output/ keep their content. Decide inclusion before indexing; removal means a full re-index plus clearing cache/.
- Route author=unknown chats out of the self index on the first run: the local attribution model agrees with the reference only ~73%, and shared-account coursework looks like the owner's own questions.
- Exclude user-role text that an agent composed (delegation briefs, task notifications, compaction summaries, skill bodies); it is most of the agent-session "user" turns and is not the owner's voice.
- Separate source accessibility from extraction success: short paginated reads may fix truncation while the worker still stops before extracting requests. Diagnose the returned artifact before retrying, and reduce the next assignment to a bounded, independently checkable batch rather than repeatedly resending the whole corpus. Preserve original text, provenance, completed outputs and failure logs; do not loosen approvals to obtain coverage. See `references/history-recount.md` for recovery and validation.
- GraphRAG merges entities by exact title only, so the owner splits into KEVIN / KEVIN RAJAN / USER / THE USER, and source errors (a saved memory naming him "Kevin Wang") propagate. Normalise aliases in the extraction prompt and with a resolution pass before finalize_graph.
- Behavioural event logs (search, YouTube, Chrome, Maps) become deterministic monthly digests; raw events never go to an LLM, and digests are labelled inferred, weaker than stated preferences.
- Repos become one card each (description, README head, own commit count/subjects); a fork with zero own commits is interest, not authorship. No code goes into GraphRAG.

- Load API keys/tokens at run time in a wrapper (`scripts/run.sh` greps one line from the profile `.env`); never write them into the project `.env` or settings.
- GraphRAG multiplies corpus tokens several times over (long extraction prompt per 1200-token chunk, gleaning pass, description and community summaries). Estimate full-run cost from a pilot's measured spend, not from the corpus size times the price.
- Run the venv python with `env -u PYTHONPATH -u PYTHONHOME`; Hermes' ambient PYTHONPATH injects a numpy built for another Python and pandas fails to import.
- Put multi-step pipelines that call a launcher stored in a variable (`PY="env -u ... python"; $PY ...`) in a bash script: the terminal shell is zsh, which does not word-split `$PY`, so every step exits 127.
- For a request-only recount where a general worker repeatedly stops early, use small tool-free batches on the same explicitly authorized subscription route rather than repeated full-agent resumes. Reuse Hermes's native auxiliary resolver, validate exact endpoint and returned model, disable provider fallbacks/storage and unbounded retries, and cache only schema/provenance-validated batches. This avoids agent/tool overhead without changing approval policy.
- Validate extracted source IDs and literal quotes independently from coverage counts. A model can account for every message yet silently paraphrase half its purported quotations. Give reviewers the failed quote IDs and originals; never present paraphrases as verbatim. Preserve raw model responses and log any parent restoration of exact original wording.
- An index run that stops making progress with no errors is a hung LLM call: set `call_args.timeout`, kill the exact PID, and rerun; the json cache replays every finished call for free.
- Stop superseded runs by exact PID before starting a new one in the same root; two runs share `output/` and `cache/`.
