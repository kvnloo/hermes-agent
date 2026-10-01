"""Gate predicate v1 / v2 / v3 against what the real converters put on the wire (T0, $0, no network).

Round-2 successor of ``predicate_direct.py`` (kept unchanged for the round-1 receipt). Each case is
a request in the shape Hermes stores it: assistant rows built by the repo's real normalizers
(``AnthropicTransport.normalize_response`` for Messages, ``normalize_converse_response`` for
Bedrock Converse), copied onto the message the way ``build_assistant_message`` does. For every
case the harness records:

* the three gate decisions, each exec'd from the exact bytes of its ledger patch;
* ``signed_on_wire``: whether a signed thinking block survives the real converter for that route
  (``convert_messages_to_anthropic`` with the case's base URL, ``convert_messages_to_converse``,
  or, for chat completions, ``_route_replays_reasoning_details`` for the base URL);
* ``validating``: whether the endpoint checks Claude thinking signatures (anthropic.com and Nous
  Portal: yes, per the converter's own docstring; Bedrock Converse: assumed; Kimi / MiniMax /
  DeepSeek / AnthropicBedrock-through-the-converter: nothing signed survives or no Claude check;
  OpenRouter chat completions: unknown);
* ``bound`` = ``signed_on_wire and validating`` and, per gate, ``exact`` / ``over_decline``
  (declines with nothing bound) / ``MISS`` (does not decline although something is bound) /
  ``out_of_scope`` (the gate does not cover that wire and the binding there is unknown).

Usage: <venv python> predicate_wire_truth.py <repo> <out.json>
"""

import copy
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


GATES = {"v1": predicate_from_patch("foldin-preserved-thinking-gate.diff"),
         "v2": predicate_from_patch("foldin-preserved-thinking-gate-v2.diff"),
         "v3": predicate_from_patch("foldin-preserved-thinking-gate-v3.diff")}

from agent.anthropic_message_convert import convert_messages_to_anthropic  # noqa: E402
from agent.bedrock_adapter import convert_messages_to_converse, normalize_converse_response  # noqa: E402
from agent.transports.anthropic import AnthropicTransport  # noqa: E402
from agent.transports.chat_completions import _route_replays_reasoning_details  # noqa: E402


def anthropic_row(tool_id: str = "toolu_1", signature: str = "sig-abc") -> Dict[str, Any]:
    """Messages wire: signed thinking + tool_use (the interleaved shape that gets the ordered sidecar)."""
    response = SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking="plan the read", signature=signature),
                 SimpleNamespace(type="tool_use", id=tool_id, name="read_file", input={"path": "notes_00.txt"})],
        stop_reason="tool_use", stop_details=None)
    norm = AnthropicTransport().normalize_response(response)
    row = {"role": "assistant", "content": norm.content or "", "tool_calls": [
        {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.arguments}}
        for tc in norm.tool_calls or []]}
    for key in ("reasoning_details", "anthropic_content_blocks"):
        if (norm.provider_data or {}).get(key):
            row[key] = norm.provider_data[key]
    return row


def plain_assistant(text: str = "noted") -> Dict[str, Any]:
    return {"role": "assistant", "content": text}


def bedrock_row() -> Dict[str, Any]:
    """Converse wire: signed reasoningText + toolUse, as the sync normalizer stores it."""
    response = {"output": {"message": {"role": "assistant", "content": [
        {"reasoningContent": {"reasoningText": {"text": "plan the read", "signature": "sig-xyz"}}},
        {"toolUse": {"toolUseId": "toolu_1", "name": "read_file", "input": {"path": "notes_00.txt"}}}]}},
        "stopReason": "tool_use", "usage": {"inputTokens": 10, "outputTokens": 5}, "modelId": "anthropic.claude-opus-5-5"}
    msg = normalize_converse_response(response).choices[0].message
    row = {"role": "assistant", "content": msg.content or "", "tool_calls": [
        {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
        for tc in msg.tool_calls or []]}
    if msg.reasoning_details:
        row["reasoning_details"] = msg.reasoning_details
    if msg.bedrock_content_blocks:
        row["bedrock_content_blocks"] = msg.bedrock_content_blocks
    return row


def without(row: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    return {k: v for k, v in row.items() if k not in keys}


def unsigned(row: Dict[str, Any]) -> Dict[str, Any]:
    strip = lambda blocks: [{k: v for k, v in b.items() if k != "signature"} for b in blocks]  # noqa: E731
    return {**row, **{k: strip(row[k]) for k in ("reasoning_details", "anthropic_content_blocks") if k in row}}


def user(text: str = "read notes_00.txt") -> Dict[str, Any]:
    return {"role": "user", "content": text}


def tool(tool_id: str = "toolu_1") -> Dict[str, Any]:
    return {"role": "tool", "tool_call_id": tool_id, "content": "x" * 100}


def signed_on_messages_wire(msgs, base_url, model) -> bool:
    _system, wire = convert_messages_to_anthropic(copy.deepcopy(msgs), base_url=base_url, model=model)
    return any(isinstance(b, dict) and b.get("type") in ("thinking", "redacted_thinking")
               and (b.get("signature") or b.get("data"))
               for m in wire if m.get("role") == "assistant" and isinstance(m.get("content"), list)
               for b in m["content"])


def signed_on_converse_wire(msgs) -> bool:
    _system, wire = convert_messages_to_converse(copy.deepcopy(msgs))
    for m in wire:
        for b in m.get("content") or []:
            rc = b.get("reasoningContent") if isinstance(b, dict) else None
            if isinstance(rc, dict) and ((rc.get("reasoningText") or {}).get("signature") or rc.get("redactedContent")):
                return True
    return False


def signed_on_chat_wire(msgs, base_url) -> bool:
    has_signed_rd = any(isinstance(d, dict) and (d.get("signature") or d.get("data"))
                        for m in msgs if m.get("role") == "assistant" for d in (m.get("reasoning_details") or []))
    return has_signed_rd and _route_replays_reasoning_details(base_url)


MINIMAX = "https://api.minimax.io/anthropic"
KIMI = "https://api.kimi.com/coding"
PORTAL = "https://inference-api.nousresearch.com/v1"
BEDROCK_RUNTIME = "https://bedrock-runtime.us-east-1.amazonaws.com"
OPENROUTER = "https://openrouter.ai/api/v1"
a, b = anthropic_row(), bedrock_row()
older_signed = [user(), anthropic_row("toolu_0", "sig-old"), tool("toolu_0"), plain_assistant("done"),
                user("next"), {"role": "assistant", "content": "", "tool_calls": [
                    {"id": "toolu_1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}]},
                tool("toolu_1")]
# (label, api_mode, base_url, model, messages, validating)
CASES = [
    ("Messages, anthropic.com: latest row signed (reasoning_details + anthropic_content_blocks)",
     "anthropic_messages", None, "claude-opus-5-5", [user(), a, tool()], True),
    ("Messages, anthropic.com: reasoning_details stripped (turn_recovery retry), anthropic_content_blocks replayed",
     "anthropic_messages", None, "claude-opus-5-5", [user(), without(a, "reasoning_details"), tool()], True),
    ("Messages, anthropic.com: thinking without a signature", "anthropic_messages", None, "claude-opus-5-5",
     [user(), unsigned(a), tool()], True),
    ("Messages, anthropic.com: only an OLDER assistant row is signed; the latest has no thinking",
     "anthropic_messages", None, "claude-opus-5-5", older_signed, True),
    ("Messages, Nous Portal: latest row signed", "anthropic_messages", PORTAL, "claude-opus-5-5",
     [user(), a, tool()], True),
    ("Messages, MiniMax (third-party): stored rows signed", "anthropic_messages", MINIMAX, "MiniMax-M2.7",
     [user(), a, tool()], False),
    ("Messages, Kimi coding (third-party, replays blocks as-is, no Claude check)", "anthropic_messages", KIMI,
     "kimi-k3", [user(), a, tool()], False),
    ("Messages via AnthropicBedrock SDK (bedrock-runtime base URL): stored rows signed", "anthropic_messages",
     BEDROCK_RUNTIME, "anthropic.claude-opus-5-5", [user(), a, tool()], True),
    ("Converse: signed reasoningText in bedrock_content_blocks", "bedrock_converse", BEDROCK_RUNTIME,
     "anthropic.claude-opus-5-5", [user(), b, tool()], True),
    ("Converse: row carries only Messages copies (session moved from native Messages to Converse)",
     "bedrock_converse", BEDROCK_RUNTIME, "anthropic.claude-opus-5-5", [user(), a, tool()], True),
    ("chat_completions, OpenRouter: Claude row with signed reasoning_details", "chat_completions", OPENROUTER,
     "anthropic/claude-opus-5-5", [user(), a, tool()], None),
    ("codex_responses: Bedrock row on another wire", "codex_responses", "https://chatgpt.com/backend-api/codex",
     "gpt-6.1", [user(), b, tool()], False),
]


def classify(decline: bool, bound, in_scope: bool) -> str:
    if not in_scope:
        return "out_of_scope" if not decline else "declines_out_of_scope"
    if decline == bound:
        return "exact"
    return "over_decline" if decline else "MISS"


results = []
for label, mode, base_url, model, msgs, validating in CASES:
    if mode == "anthropic_messages":
        on_wire = signed_on_messages_wire(msgs, base_url, model)
    elif mode == "bedrock_converse":
        on_wire = signed_on_converse_wire(msgs)
    elif mode == "chat_completions":
        on_wire = signed_on_chat_wire(msgs, base_url)
    else:
        on_wire = None  # not computed: no signed Claude thinking on this wire
    in_scope = mode in ("anthropic_messages", "bedrock_converse")
    bound = bool(on_wire and validating) if validating is not None else None
    agent = SimpleNamespace(api_mode=mode, _anthropic_base_url=base_url, base_url=base_url, model=model)
    row = {"case": label, "api_mode": mode, "base_url": base_url, "model": model,
           "signed_on_wire": on_wire, "validating": validating if validating is not None else "unknown",
           "bound": bound if bound is not None else "unknown", "gate_scope": in_scope}
    for name, gate in GATES.items():
        decline = bool(gate(agent, msgs))
        row[name] = decline
        row[f"{name}_vs_wire"] = classify(decline, bound, in_scope) if (bound is not None or not in_scope) else "unknown"
    results.append(row)

summary = {name: {kind: sum(1 for r in results if r[f"{name}_vs_wire"] == kind)
                  for kind in ("exact", "over_decline", "MISS", "out_of_scope", "declines_out_of_scope")}
           for name in GATES}
out = {"label": "OBSERVED (direct call against the real converters; mechanism, not wire)",
       "python": sys.version.split()[0], "cases": results, "summary": summary,
       "misses": {name: [r["case"] for r in results if r[f"{name}_vs_wire"] == "MISS"] for name in GATES}}
Path(OUT).write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({"summary": summary, "misses": out["misses"]}, indent=1))
for r in results:
    print(f"{r['case'][:80]:80} wire={r['signed_on_wire']!s:5} bound={r['bound']!s:7} v1={r['v1_vs_wire']:13} "
          f"v2={r['v2_vs_wire']:13} v3={r['v3_vs_wire']}")
