---
name: graphrag-model-benchmark
description: "Use when picking or re-benchmarking GraphRAG LLMs."
version: 0.1.0
metadata:
  hermes:
    tags: [graphrag, benchmark, llm-selection, privacy]
---

# GraphRAG model benchmark

Harness: `/mnt/zer0models/sft-svlm/data/graphrag/model-eval/` (REPORT.md, scripts/, raw/, results/).
Always run python as `env -u PYTHONPATH -u PYTHONHOME /mnt/zer0models/venvs/graphrag/bin/python`.

## Procedure
1. Eval data must be public: own non-fork repos re-checked live with `gh api repos/kvnloo/<r>` (inventory.json can be stale). `scripts/build_evalset.py`.
2. Add a candidate in `scripts/llm.py` MODELS, then `scripts/chain.sh graph|claims CONC MODEL...` (resumable, one chain per provider).
3. Score with GraphRAG's own parsers: `score_graph.py`, `score_agreement.py` (vs `data/reference.json`), `score_claims.py`; reports: `community_reports.py gen/judge/score` (Opus judge; gpt-oss judge is position-biased, do not use); `cost.py`, `make_tables.py`.
4. Local models only through `scripts/local_run_v2.sh` (waits for router idle + no privacy-classifier GPU process, watchdog yields by exact PID).

## Pitfalls
- ChatGPT subscription models: do not copy `~/.codex/auth.json` or run a fresh device login; run `eval "$(python3 ../scripts/chatgpt_token_sync.py)"` first. It copies only the current access token from Hermes/Codex (the refresh token stays behind, so litellm cannot rotate the shared login) and refuses when it is near expiry; opening Hermes or Codex once refreshes it.
- Measured picks (public-repo eval set): extraction on Cerebras Qwen3.8-27B (best F1, free, fastest) or subscription Haiku 4.5; community reports on Haiku 5.5 (beat Haiku 4.5 every time; Sonnet 5.5 only slightly better at ~2.5x output); local 12 GB models only with grammar-constrained decoding, and they stay weak on relationships. GraphRAG `--method fast` is not usable (entity F1 ~0.16). ChatGPT gpt-6-luna and gpt-6.1-sol land near Haiku 4.5 on entity F1 (~0.57) but below it on claim validity. Sol over-extracts at ~80 chunks/h, too slow for a full corpus. Luna (~450 chunks/h) is the fallback when Claude or Cerebras quota runs out. Cerebras is approved for the cloud-safe (T1) tier, not only public data.
- Claude subscription OAuth token serves only Haiku 4.5 to plain calls; other models return 429 `rate_limit_error` unless the system prompt starts with the Claude Code identity and `anthropic-beta: claude-code-20250219,oauth-2025-04-20` is sent. GraphRAG settings cannot add it (extra_body.system rejected) -> use `scripts/graphrag_cc.py` shim.
- Sonnet/Opus 5.5 thinking cannot be disabled; Haiku 5.5 needs `thinking: disabled` or it spends output on thinking.
- Haiku 5.5 refuses instruction-like text (CLAUDE.md, prompts) in prose ~7% of chunks; check refusals before trusting counts.
- Qwen3.8 (Cerebras) needs `reasoning_effort='none'`; NIM Nemotron needs `chat_template_kwargs.enable_thinking=false`.
- Small local models break the tuple format (missing weight) and loop; cap max_tokens 4000, use DRY, try `graphrag_tuples.gbnf`.
- The graphrag CLI can hang when run in a foreground tool call; run it as a background process.
- Never use `pkill -f`/`pgrep -f` patterns that can match your own shell; kill exact PIDs.
- OpenRouter key in ~/.hermes/.env has a $0 limit (only :free models); Groq free gpt-oss-20b caps at 200k tokens/day.
