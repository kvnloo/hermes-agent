"""Video analyzer to Gemini-native boundary regression (issue #141763)."""

import asyncio
import base64
import json
from unittest.mock import AsyncMock, patch

from agent.gemini_native_adapter import build_gemini_request
from tools.vision_tools import video_analyze_tool


def test_video_analyze_preserves_video_in_native_gemini_request(tmp_path):
    """A successful analyzer call must not translate its video into text-only."""
    video_bytes = b"\x00\x00\x00\x18ftypisomfixture"
    video = tmp_path / "clip.mp4"
    video.write_bytes(video_bytes)

    with (
        patch("tools.interrupt.is_interrupted", return_value=False),
        patch("tools.vision_tools.async_call_llm", new_callable=AsyncMock) as auxiliary,
        patch("tools.vision_tools.extract_content_or_reasoning", return_value="clip analyzed"),
    ):
        result = json.loads(asyncio.run(video_analyze_tool(str(video), "Describe this clip.")))

    assert result["success"] is True
    auxiliary.assert_awaited_once()
    assert auxiliary.await_args.kwargs["task"] == "vision"
    request = build_gemini_request(messages=auxiliary.await_args.kwargs["messages"])
    assert request["contents"][0]["parts"] == [
        {"text": "Describe this clip."},
        {"inlineData": {
            "mimeType": "video/mp4",
            "data": base64.b64encode(video_bytes).decode("ascii"),
        }},
    ]
