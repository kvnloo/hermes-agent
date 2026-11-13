---
name: decision-runtime-contract-review
description: Use when reviewing typed decision runtime contracts.
---
# Decision runtime contract review

- For quick local typed-decision smoke tests, discover both installed models and loaded models before inference; distinguish CPU and GPU Ollama servers using `/api/ps` `size_vram`, not port assumptions. Never unload another session's models to accelerate a benchmark.
- Separate schema validity from semantic accuracy: preserve exact labels, per-call latency, and sample counts; probe positive and negative boolean cases independently. A small model can return valid JSON while missing every positive retry case. Keep deterministic retry/authorization checks outside the model and all integration advisory until evaluated.
- Validate cloud credential shape without printing it; environment variables named API_KEY may contain URLs. Reject URL-shaped values before network use, discover model IDs at official endpoints, and record numeric HTTP failures without persisting error bodies or substituting providers.
- For helper processes needing fresh vault credentials, use the installed Hermes venv and `hermes_cli.env_loader.load_hermes_dotenv()` with the explicitly selected `HERMES_HOME`; consume the injected standard provider variable before a stale custom alias, without serializing the environment. Cerebras may expose `CEREBRAS_API_KEY`; distinguish successful `/models` auth from HTTP 402 inference billing failures. Send an explicit application User-Agent when urllib's default receives a gateway 403.
- Preserve host plugin setting policy when a plugin reads a reserved key such as `model`: `PluginContext.get_config('model')` can be rejected and the plugin can silently use its default. Use a documented compatibility alias and report the real backend identity rather than weakening host policy. Sparse one-hot compatibility scores are heuristic hard labels, not probability evidence or a genuine top-k ranking.
- Pin the exact reviewed head in a separate checkout; run canonical repo tests with isolated HOME/HERMES_HOME and no credentials. Preserve runnable probes and output beside the review.
- Test privacy by making a fake backend echo a sentinel from state into ValueError, another exception type, and abstention reason. Inspect both persisted telemetry and warning logs: omitting a state field does not prevent indirect leakage.
- Probe ambient ContextVars separately from request.state, including mutable aliasing and scoped fake credentials. Distinguish trusted in-process plugin access from remote payload egress; do not strip profile/auth scope blindly when the host requires it.
- Use Event-blocked providers to measure outstanding workers after repeated timeouts and disposal. Release and join all probe workers. A caller deadline does not bound background resource use.
- Supply an explicit selected label different from probability argmax when checking top-1 evaluation. Validate the entire corpus before any backend call; malformed expected labels must fail equally for unavailable, abstaining and threshold-rejected providers.
- Exercise shadow with an ordinary availability-based consumer. Separate a telemetry mode label from an actual baseline-equivalence guarantee; do not claim a production action regression without a real consumer path.
- Test registry lifecycle across real temporary A→B→A profile scopes, cross-context disposal, duplicate disposal, manager unload, and both replacement-disposal orders. Preserve existing profile-secret binding while testing isolation.
