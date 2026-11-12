"""DeepSeek summary telemetry reports the real on-wire output reservation (#126305)."""

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agent.context_compressor import ContextCompressor


def test_deepseek_compression_telemetry_reserves_wire_cap():
    model = "deepseek-flash"
    endpoint = "https://api.deepseek.com/v1"
    client = MagicMock()
    client.base_url = endpoint
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content="Complete summary"),
        )],
        model=model,
    )
    compressor = ContextCompressor(
        model=model, provider="deepseek", base_url=endpoint,
        api_key="test-only", config_context_length=160_000,
    )
    telemetry = compressor._begin_compression_telemetry(current_tokens=80_000)

    with (
        patch(
            "agent.auxiliary_client._resolve_task_provider_model",
            return_value=("deepseek", model, endpoint, "test-only", None),
        ),
        patch(
            "agent.auxiliary_client._get_cached_client",
            return_value=(client, model),
        ),
        patch("agent.auxiliary_client._provider_requires_stream", return_value=False),
    ):
        assert compressor._call_summary_llm(
            "Summarize the long session.", time.monotonic(),
        ) == "Complete summary"

    sent = client.chat.completions.create.call_args.kwargs
    assert sent["max_tokens"] == 32768
    assert telemetry["aux_output_reservation"] == sent["max_tokens"]
