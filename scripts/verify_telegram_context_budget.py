#!/usr/bin/env python3
"""Deterministic lifecycle witness for the Telegram attention guard."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent.context_budget import (
    DEFAULT_TELEGRAM_TOOL_RESULT_BUDGET_CHARS,
    retained_tool_result_chars,
    telegram_history_exceeds_attention_budget,
)
from agent.model_metadata import estimate_messages_tokens_rough
from model_tools import get_tool_definitions


def _schema_hash() -> tuple[int, str]:
    tools = get_tool_definitions(enabled_toolsets=["messaging"], quiet_mode=True)
    payload = json.dumps(tools, sort_keys=True, separators=(",", ":")).encode()
    return len(tools), hashlib.sha256(payload).hexdigest()


def main() -> None:
    # Historical recurrence shape: 299 persisted tool rows carrying exactly
    # 1,657,358 result characters. No production/session data is read.
    sizes = [5_543] * 298 + [5_544]
    history = [
        {"role": "tool", "tool_call_id": f"call-{i}", "content": "x" * size}
        for i, size in enumerate(sizes)
    ]
    schema_count_before, schema_hash_before = _schema_hash()
    report = {
        "fixture_tool_rows": len(history),
        "fixture_tool_result_chars": retained_tool_result_chars(history),
        "rough_request_tokens_before": estimate_messages_tokens_rough(history),
        "declared_budget_chars": DEFAULT_TELEGRAM_TOOL_RESULT_BUDGET_CHARS,
        "provider_request_allowed_after_failed_compaction": not telegram_history_exceeds_attention_budget(history),
        "provider_request_tokens_after_guard": 0,
        "messaging_tool_schema_count_before": schema_count_before,
        "messaging_tool_schema_sha256_before": schema_hash_before,
    }
    schema_count_after, schema_hash_after = _schema_hash()
    report.update(
        messaging_tool_schema_count_after=schema_count_after,
        messaging_tool_schema_sha256_after=schema_hash_after,
        tool_schema_unchanged=(
            schema_count_before == schema_count_after
            and schema_hash_before == schema_hash_after
        ),
    )
    assert report["fixture_tool_result_chars"] == 1_657_358
    assert report["provider_request_allowed_after_failed_compaction"] is False
    assert report["tool_schema_unchanged"] is True
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
