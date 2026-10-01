"""Direct-call check of the fold-in gate predicate, v1 vs v2 (T0, $0, no network).

Each case is an assistant row in the shape Hermes stores it, produced by the repo's real normalizers
(``AnthropicTransport.normalize_response`` for the Messages wire, ``normalize_converse_response`` for
Bedrock Converse) and copied onto the message the way ``build_assistant_message`` copies
``reasoning_details`` and the ``*_content_blocks`` sidecars (agent/chat_completion_helpers.py). The
two predicates are exec'd from the exact bytes of ``patches/foldin-preserved-thinking-gate.diff``
(v1) and ``patches/foldin-preserved-thinking-gate-v2.diff`` (v2), so the check is pinned to the
patches, not to a re-typed copy.

Usage: <venv python> predicate_direct.py <repo> <out.json>
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Sequence  # noqa: F401 - names the exec'd patch code uses

REPO, OUT = sys.argv[1], sys.argv[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, REPO)


def predicate_from_patch(name: str):
    """The module-level code a patch adds before ``_resolve_active_env`` (first hunk), exec'd alone."""
    added, in_first_hunk = [], False
    for line in (HERE.parent / "patches" / name).read_text(encoding="utf-8").splitlines():
        if line.startswith("@@"):
            if in_first_hunk:
                break
            in_first_hunk = True
            continue
        if in_first_hunk and line.startswith("+"):
            added.append(line[1:])
    namespace: Dict[str, Any] = {"Any": Any, "Dict": Dict, "List": List, "Sequence": Sequence}
    exec("\n".join(added), namespace)  # noqa: S102 - our own ledger patch, read-only check
    return namespace["replays_bound_thinking"]


v1 = predicate_from_patch("foldin-preserved-thinking-gate.diff")
v2 = predicate_from_patch("foldin-preserved-thinking-gate-v2.diff")

from agent.bedrock_adapter import normalize_converse_response  # noqa: E402
from agent.transports.anthropic import AnthropicTransport  # noqa: E402


def anthropic_row() -> Dict[str, Any]:
    """Messages wire: signed thinking + tool_use (the interleaved shape that gets the ordered sidecar)."""
    response = SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking="plan the read", signature="sig-abc"),
                 SimpleNamespace(type="tool_use", id="toolu_1", name="read_file", input={"path": "notes_00.txt"})],
        stop_reason="tool_use", stop_details=None)
    norm = AnthropicTransport().normalize_response(response)
    row = {"role": "assistant", "content": norm.content or "", "tool_calls": [
        {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.arguments}}
        for tc in norm.tool_calls or []]}
    for key in ("reasoning_details", "anthropic_content_blocks"):
        if (norm.provider_data or {}).get(key):
            row[key] = norm.provider_data[key]
    return row


def bedrock_row() -> Dict[str, Any]:
    """Converse wire: signed reasoningText + toolUse, as the sync normalizer stores it."""
    response = {"output": {"message": {"role": "assistant", "content": [
        {"reasoningContent": {"reasoningText": {"text": "plan the read", "signature": "sig-xyz"}}},
        {"toolUse": {"toolUseId": "tooluse_1", "name": "read_file", "input": {"path": "notes_00.txt"}}}]}},
        "stopReason": "tool_use", "usage": {"inputTokens": 10, "outputTokens": 5}, "modelId": "anthropic.claude-opus-5-5"}
    msg = normalize_converse_response(response).choices[0].message
    row = {"role": "assistant", "content": msg.content or ""}
    if msg.reasoning_details:
        row["reasoning_details"] = msg.reasoning_details
    if msg.bedrock_content_blocks:
        row["bedrock_content_blocks"] = msg.bedrock_content_blocks
    return row


def without(row: Dict[str, Any], key: str) -> Dict[str, Any]:
    return {k: v for k, v in row.items() if k != key}


def unsigned(row: Dict[str, Any]) -> Dict[str, Any]:
    strip = lambda blocks: [{k: v for k, v in b.items() if k != "signature"} for b in blocks]  # noqa: E731
    return {**row, **{k: strip(row[k]) for k in ("reasoning_details", "anthropic_content_blocks") if k in row}}


user = {"role": "user", "content": "read notes_00.txt"}
tool = {"role": "tool", "tool_call_id": "toolu_1", "content": "x" * 100}
a, b = anthropic_row(), bedrock_row()
cases = [
    ("anthropic_messages: signed thinking in reasoning_details and anthropic_content_blocks",
     "anthropic_messages", a, True),
    ("anthropic_messages: reasoning_details stripped (turn_recovery thinking-signature retry), "
     "anthropic_content_blocks still replayed", "anthropic_messages", without(a, "reasoning_details"), True),
    ("anthropic_messages: thinking without a signature (nothing bound)", "anthropic_messages", unsigned(a), False),
    ("bedrock_converse: signed reasoningText in bedrock_content_blocks", "bedrock_converse", b, True),
    ("chat_completions: same Anthropic row on an OpenAI-compatible route", "chat_completions", a, False),
    ("codex_responses: same Bedrock row on another wire", "codex_responses", b, False),
]
results = []
for label, mode, row, expected in cases:
    agent = SimpleNamespace(api_mode=mode)
    msgs = [user, row, tool]
    got1, got2 = bool(v1(agent, msgs)), bool(v2(agent, msgs))
    results.append({"case": label, "api_mode": mode, "row_keys": sorted(k for k in row if k != "content"),
                    "expected_decline": expected, "v1": got1, "v2": got2, "v2_correct": got2 == expected})
out = {"label": "OBSERVED (direct call; mechanism, not wire)", "python": sys.version.split()[0],
       "cases": results, "v2_all_correct": all(r["v2_correct"] for r in results),
       "v1_misses": [r["case"] for r in results if r["v1"] != r["expected_decline"]]}
Path(OUT).write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=1))
