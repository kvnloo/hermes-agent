"""Restart after a route switch, by direct call (T0, $0, no network; mechanism, not wire).

Calls the arm's real ``project_stale_tool_results`` on the same stored history, three times:

1. agent 1 on ``chat_completions`` (OpenAI-compatible, no signed thinking): the pass archives rows;
2. the SAME agent after a switch to native Messages (``anthropic_messages``, anthropic.com,
   ``_use_prompt_caching`` on), with one more turn whose assistant rows carry signed thinking built
   by the real ``AnthropicTransport.normalize_response``: sticky rows replay;
3. a NEW agent object (empty ProjectionState: a restart, a resume, or a gateway rebuild) on the same
   route and the same history.

For requests 2 and 3 the harness runs the real Messages converter (``convert_messages_to_anthropic``)
and compares the conversation prefix that the latest signed thinking block is bound to
(``conversation_prefix_digest`` from the test file: system, tools, every earlier message). The block
was produced over request 2's prefix, so a different digest on request 3 means the block is
replayed over a rewritten prefix.

Usage: env -i PATH=/usr/bin:/bin PYTHONHASHSEED=0 <venv python> restart_direct.py <repo> <out.json> <arm>
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO, OUT, ARM = sys.argv[1], sys.argv[2], sys.argv[3]
SCRATCH = os.environ.get("F04_SCRATCH") or "/tmp"
sandbox = Path(tempfile.mkdtemp(prefix="rsd-", dir=SCRATCH))
os.environ.clear()
os.environ.update(HOME=str(sandbox / "home"), HERMES_HOME=str(sandbox / "hermes"), TMPDIR=str(sandbox / "tmp"),
                  PATH="/usr/bin:/bin", TZ="UTC", LANG="C.UTF-8", PYTHONHASHSEED="0",
                  PYTHONDONTWRITEBYTECODE="1", HERMES_DISABLE_MODEL_METADATA_FETCH="1")
for d in ("home", "hermes", "tmp"):
    (sandbox / d).mkdir()
os.chdir(sandbox / "tmp")
sys.dont_write_bytecode = True
sys.path.insert(0, REPO)

import tests.e2e.core.history.test_tool_result_projection_wire as wire  # noqa: E402
from agent.anthropic_message_convert import convert_messages_to_anthropic  # noqa: E402
from agent.tool_result_projection import project_stale_tool_results  # noqa: E402
from agent.transports.anthropic import AnthropicTransport  # noqa: E402

TURNS = 12


def content_for(i: int) -> str:
    return "".join(f"file {i:02d} line {j:04d} alpha beta gamma delta epsilon zeta\n" for j in range(wire.FILE_LINES))


def call(tool_id: str, i: int) -> dict:
    return {"id": tool_id, "type": "function",
            "function": {"name": "read_file", "arguments": json.dumps({"path": f"notes_{i:02d}.txt"})}}


history = [{"role": "system", "content": "You are a test agent."}]
for i in range(TURNS):  # OpenAI-compatible turns: no thinking anywhere
    tid = f"call_{i:02d}"
    history += [{"role": "user", "content": f"read notes_{i:02d}.txt and remember it"},
                {"role": "assistant", "content": "", "tool_calls": [call(tid, i)]},
                {"role": "tool", "tool_call_id": tid, "content": content_for(i)},
                {"role": "assistant", "content": f"noted file {i:02d}"}]
history.append({"role": "user", "content": "read the next file"})


def signed_row(blocks):
    response = SimpleNamespace(content=blocks, stop_reason="tool_use" if any(b.type == "tool_use" for b in blocks)
                               else "end_turn", stop_details=None)
    norm = AnthropicTransport().normalize_response(response)
    row = {"role": "assistant", "content": norm.content or "", "tool_calls": [
        {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.arguments}}
        for tc in norm.tool_calls or []] or None}
    if row["tool_calls"] is None:
        del row["tool_calls"]
    for key in ("reasoning_details", "anthropic_content_blocks"):
        if (norm.provider_data or {}).get(key):
            row[key] = norm.provider_data[key]
    return row


def agent(api_mode: str, caching: bool) -> SimpleNamespace:
    cc = SimpleNamespace(tool_result_projection="auto", tool_result_projection_min_tokens=wire.MIN_TOKENS,
                         tool_result_projection_min_result_chars=4000, tool_result_projection_tail_ratio=0.0,
                         context_length=200_000)
    return SimpleNamespace(context_compressor=cc, api_mode=api_mode, _anthropic_base_url=None, base_url=None,
                           model="claude-opus-5-5", _use_prompt_caching=caching, session_cache_read_tokens=0,
                           _current_task_id=None)


def stubbed(msgs):
    """``tool_call_id -> stub`` for the 12 large chat-completions rows that went out as a stub."""
    return {m["tool_call_id"]: m["content"] for m in msgs
            if m.get("role") == "tool" and str(m.get("tool_call_id", "")).startswith("call_")
            and m.get("content") != content_for(int(m["tool_call_id"].split("_")[1]))}


# 1. chat completions
a1 = agent("chat_completions", caching=False)
req1 = copy.deepcopy(history)
n1 = project_stale_tool_results(a1, req1, env=None)
stubs1 = stubbed(req1)

# 2. same agent, switched to native Messages; one more turn with signed thinking
a1.api_mode, a1._use_prompt_caching = "anthropic_messages", True
i = TURNS
history = history[:-1] + [
    {"role": "user", "content": f"read notes_{i:02d}.txt and remember it"},
    signed_row([SimpleNamespace(type="thinking", thinking=f"plan the read of file {i:02d}", signature="sig-plan"),
                SimpleNamespace(type="tool_use", id="toolu_12", name="read_file", input={"path": f"notes_{i:02d}.txt"})]),
    {"role": "tool", "tool_call_id": "toolu_12", "content": "short result"},
    signed_row([SimpleNamespace(type="thinking", thinking=f"file {i:02d} read", signature="sig-final"),
                SimpleNamespace(type="text", text=f"noted file {i:02d}")]),
    {"role": "user", "content": "read the next file"},
]
req2 = copy.deepcopy(history)
n2 = project_stale_tool_results(a1, req2, env=None)
stubs2 = stubbed(req2)

# 3. new agent (empty ProjectionState), same route, same history
a3 = agent("anthropic_messages", caching=True)
req3 = copy.deepcopy(history)
n3 = project_stale_tool_results(a3, req3, env=None)
stubs3 = stubbed(req3)


def latest_signed_digest(req):
    system, msgs = convert_messages_to_anthropic(copy.deepcopy(req), base_url=None, model="claude-opus-5-5")
    body = {"system": system, "tools": [], "messages": msgs}
    idx = max((m for m, msg in enumerate(msgs) if msg.get("role") == "assistant" and isinstance(msg.get("content"), list)
               and any(isinstance(b, dict) and b.get("type") == "thinking" and b.get("signature") for b in msg["content"])),
              default=None)
    return idx, (wire.conversation_prefix_digest(body, idx) if idx is not None else None), sum(
        1 for msg in msgs if isinstance(msg.get("content"), list) for b in msg["content"]
        if isinstance(b, dict) and b.get("type") == "thinking" and b.get("signature"))


idx2, dig2, signed2 = latest_signed_digest(req2)
idx3, dig3, signed3 = latest_signed_digest(req3)


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


out = {
    "label": "OBSERVED (direct call on the arm's real projection and converter; mechanism, not wire)",
    "arm": ARM, "repo_head": git("rev-parse", "HEAD"), "dirty_files": git("status", "--porcelain").splitlines(),
    "projection_module_blob": git("hash-object", "agent/tool_result_projection.py"),
    "step1_chat_completions": {"rows_projected": n1, "stubbed_rows": len(stubs1)},
    "step2_same_agent_native_messages": {"rows_projected": n2, "stubbed_rows": len(stubs2),
                                         "same_stub_bytes_as_step1": sum(1 for t, c in stubs1.items() if stubs2.get(t) == c),
                                         "signed_thinking_blocks_on_wire": signed2},
    "step3_new_agent_native_messages": {"rows_projected": n3, "stubbed_rows": len(stubs3),
                                        "same_stub_bytes_as_step2": sum(1 for t, c in stubs2.items() if stubs3.get(t) == c),
                                        "rows_archived_in_step2_now_full": sum(1 for t in stubs2 if t not in stubs3),
                                        "signed_thinking_blocks_on_wire": signed3},
    "latest_signed_block": {"message_index_step2": idx2, "message_index_step3": idx3,
                            "bound_prefix_unchanged": dig2 == dig3 and dig2 is not None},
    "python": sys.version.split()[0],
}
Path(OUT).write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=1))
