"""Regression for #71242: translated Anthropic usage must reach the session ledger."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agent.aux_accounting import (
    record_aux_usage,
    reset_accounting_context,
    set_accounting_context,
)
from agent.auxiliary_client import _AnthropicCompletionsAdapter
from hermes_state import SessionDB


def test_native_anthropic_aux_call_records_fresh_and_cached_tokens(tmp_path):
    """The native-provider path must not silently drop the entire usage row."""
    raw_usage = SimpleNamespace(
        input_tokens=561,
        output_tokens=402,
        cache_read_input_tokens=57_199,
        cache_creation_input_tokens=134,
    )
    with (
        patch(
            "agent.anthropic_adapter.build_anthropic_kwargs",
            return_value={"model": "claude-fable-5", "messages": [], "max_tokens": 64},
        ),
        patch(
            "agent.anthropic_adapter.create_anthropic_message",
            return_value=SimpleNamespace(usage=raw_usage),
        ),
        patch("agent.transports.get_transport") as get_transport,
    ):
        get_transport.return_value.normalize_response.return_value = SimpleNamespace(
            content="ok", tool_calls=None, reasoning=None, finish_reason="stop"
        )
        response = _AnthropicCompletionsAdapter(
            MagicMock(), "claude-fable-5", is_oauth=False
        ).create(
            model="claude-fable-5",
            messages=[{"role": "user", "content": "Summarize this"}],
            max_tokens=64,
        )

    db = SessionDB(tmp_path / "state.db")
    try:
        db.create_session("aux-anthropic", source="cli")
        token = set_accounting_context(db, "aux-anthropic")
        try:
            record_aux_usage(response, "title_generation", provider="anthropic")
        finally:
            reset_accounting_context(token)

        row = db.auxiliary_usage_by_task("aux-anthropic").get("title_generation")
        assert row is not None, "a cached Anthropic auxiliary call recorded no usage row"
        assert (
            row["input_tokens"],
            row["output_tokens"],
            row["cache_read_tokens"],
            row["cache_write_tokens"],
        ) == (561, 402, 57_199, 134)
    finally:
        db.close()
