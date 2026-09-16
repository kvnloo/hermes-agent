# Exact ctx.llm API refs (read-only; not a new routing framework)

Source copies inspected (do not edit running Hermes / mission worktree):

- `/workspace/jev-mimic/bridge-wave2/02-hook/host/agent/plugin_llm.py`
  - `PluginLlm.complete` kwargs: messages, provider, model, temperature, max_tokens, timeout, agent_id, profile, purpose, task
  - `PluginLlm.complete_structured` kwargs: instructions, input, json_schema, json_mode, schema_name, system_prompt, provider, model, temperature, max_tokens, timeout, agent_id, profile, purpose, task
  - Result: `PluginLlmStructuredResult(text, provider, model, agent_id, usage, parsed, content_type, audit)`
  - Trust: `_check_task` — plugin-registered aux keys allowed; built-in keys need `allow_task_override`; unknown keys raise `PluginLlmTrustError` (never silent auto)
  - Host path: `agent.auxiliary_client.call_llm` via `_host_kwargs` (`task`, `provider`, `model`, `messages`, `temperature`, `max_tokens`, `timeout`, `extra_body`, `route_info`)
  - Test helper: `make_plugin_llm_for_test`

- `/workspace/jev-pr-113020-review/website/docs/developer-guide/plugin-llm-access.md`
  - Public docs for the same surface; `task` is a plugin-registered auxiliary slot.

- `/workspace/jev-pr-113020-review/tests/agent/test_plugin_llm_task_routing.py`
  - Baseline: default path unchanged; foreign/unknown task rejected; own registered key allowed.

Issue #113008 (OPEN) full thread:

- Body: keep `ctx.register_auxiliary_task()` + `ctx.llm.complete_structured(task=...)` as the generative aux abstraction; do not replace auxiliary LLM tasks; vendor confidence is not automatically calibrated.
- Comment 5701211508: DecisionProvider is north-star, not a blocker; integrate via existing plugin surfaces first.

This lane uses **only** `complete_structured` with a plugin-owned `task` key. It does not register a DecisionProvider, does not rewrite host `_AUX_TASKS`, and does not change context-tool prompts.
