"""Repeated ACP-client guidance blocks (T3 Code) are delivered once per agent session."""

import pytest

from acp_adapter.host_blocks import HostBlockFilter

RUNTIME = "<runtime_info>In case you're asked: you are running in T3 Code through the acpRegistry harness.</runtime_info>"
PR = "<pull_request_linking>\nLink each PR you create.\n</pull_request_linking>"
INSTR = "<t3_code_instructions>\n## T3 Code interaction mode: Default\n\nPrefer assumptions.\n</t3_code_instructions>"


def t3_prompt(request: str, instructions: bool = False, runtime: str = RUNTIME) -> str:
    body = f"{INSTR}\n\n<user_request>\n{request}\n</user_request>" if instructions else request
    return f"{body}\n\n{runtime}\n\n{PR}"


def test_first_prompt_keeps_every_block():
    f = HostBlockFilter()
    text = t3_prompt("fix the bug", instructions=True)
    assert f.filter_text(text, "s1") == text


def test_repeated_blocks_are_dropped_and_request_unwrapped():
    f = HostBlockFilter()
    f.filter_text(t3_prompt("first", instructions=True), "s1")
    assert f.filter_text(t3_prompt("second"), "s1") == "second"
    # A re-injected instruction block (client compaction/reopen) is unwrapped to the request.
    assert f.filter_text(t3_prompt("third", instructions=True), "s1") == "third"


def test_changed_block_is_delivered():
    f = HostBlockFilter()
    f.filter_text(t3_prompt("first"), "s1")
    changed = RUNTIME.replace("acpRegistry harness", "acpRegistry harness, as opus")
    out = f.filter_text(t3_prompt("second", runtime=changed), "s1")
    assert changed in out and PR not in out and out.startswith("second")


def test_merged_queued_prompts_keep_one_copy():
    f = HostBlockFilter()
    merged = "\n\n".join(t3_prompt(f"ask {i}") for i in range(3))
    out = f.filter_text(merged, "s1")
    assert out.count("<runtime_info>") == 1 and out.count("<pull_request_linking>") == 1
    assert all(f"ask {i}" in out for i in range(3))


def test_agent_session_rotation_redelivers():
    f = HostBlockFilter()
    f.filter_text(t3_prompt("first"), "s1")
    # Hermes compression rotated the internal session: earlier copies may be summarised away.
    assert RUNTIME in f.filter_text(t3_prompt("second"), "s2")


def test_plain_and_slash_prompts_untouched():
    f = HostBlockFilter()
    assert f.filter_text("/model opus", "s1") == "/model opus"
    assert f.filter_text("compare <a> and <b>", "s1") == "compare <a> and <b>"


def test_opt_out_env(monkeypatch):
    monkeypatch.setenv("HERMES_ACP_KEEP_HOST_BLOCKS", "1")
    f = HostBlockFilter()
    text = t3_prompt("again")
    f.filter_text(text, "s1")
    assert f.filter_text(text, "s1") == text


def test_multimodal_parts_filtered_and_empty_text_part_dropped():
    f = HostBlockFilter()
    f.filter_text(t3_prompt("first"), "s1")
    parts = [{"type": "text", "text": f"{RUNTIME}\n\n{PR}"}, {"type": "image_url", "image_url": {"url": "data:x"}}]
    assert f.filter_content(parts, "s1") == [parts[1]]


@pytest.mark.asyncio
async def test_gateway_viewer_submits_filtered_text_and_retry_still_matches(monkeypatch):
    """Production path: ``hermes acp`` is a GatewayACPAgent viewer that submits to the daemon."""
    from acp.schema import TextContentBlock

    import acp_adapter.gateway_media as media
    from acp_adapter.gateway_server import GatewayACPAgent

    async def stage(content, home):
        return content, []

    monkeypatch.setattr(media, "stage_user_content", stage)
    agent = GatewayACPAgent()
    block = lambda req: [TextContentBlock(type="text", text=t3_prompt(req))]
    first = await agent._prepare_submit("s", block("one"))
    assert RUNTIME in first[2][0]
    second = await agent._prepare_submit("s", block("two"))
    assert second[2][0] == "two"
    # An un-acked submit retried by the editor keeps its identity (fingerprint is on the raw prompt).
    agent._unacked["s"] = second
    assert await agent._prepare_submit("s", block("two")) is second
    # Sessions are independent.
    assert RUNTIME in (await agent._prepare_submit("other", block("x")))[2][0]
