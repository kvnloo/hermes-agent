"""Gateway compatibility import for the shared provider-input budget policy."""

from agent.context_budget import (  # noqa: F401
    DEFAULT_TELEGRAM_TOOL_RESULT_BUDGET_CHARS,
    retained_tool_result_chars,
    telegram_history_exceeds_attention_budget,
)

__all__ = [
    "DEFAULT_TELEGRAM_TOOL_RESULT_BUDGET_CHARS",
    "retained_tool_result_chars",
    "telegram_history_exceeds_attention_budget",
]
