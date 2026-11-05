"""Drop ACP-client guidance blocks the session has already received.

ACP has no system/developer field, so clients such as T3 Code put their guidance in
the user prompt: ``<runtime_info>`` and ``<pull_request_linking>`` on every prompt,
``<t3_code_instructions>`` again after each client-side compaction or reopen. Hermes
keeps its own history, so every copy stays in context and later copies outweigh the
real request. A block byte-identical to the last one delivered for the same tag in
this agent session is removed. A changed block (new model, new mode) is kept.

The record is tied to the agent's internal session id: when Hermes compression rotates
it, earlier copies may have been summarised away, so the next copy is delivered again.
``HERMES_ACP_KEEP_HOST_BLOCKS=1`` turns the filter off.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any

HOST_BLOCK_TAGS = (
    "t3_code_instructions",
    "t3_code_orchestration_instructions",
    "runtime_info",
    "pull_request_linking",
)

_BLOCK_RE = re.compile(r"<(" + "|".join(HOST_BLOCK_TAGS) + r")>.*?</\1>", re.DOTALL)
_USER_REQUEST_RE = re.compile(r"\A\s*<user_request>\n?(.*?)\n?</user_request>\s*\Z", re.DOTALL)


class HostBlockFilter:
    """Per-ACP-session record of delivered host blocks (tag -> digest)."""

    def __init__(self) -> None:
        self._delivered: dict[str, str] = {}
        self._agent_session_id: Any = None

    def _sync(self, agent_session_id: Any) -> None:
        if agent_session_id != self._agent_session_id:
            self._delivered.clear()
            self._agent_session_id = agent_session_id

    def filter_text(self, text: str, agent_session_id: Any = None) -> str:
        if not text or os.environ.get("HERMES_ACP_KEEP_HOST_BLOCKS") == "1" or "<" not in text:
            return text
        self._sync(agent_session_id)
        removed = False

        def _replace(match: re.Match[str]) -> str:
            nonlocal removed
            digest = hashlib.sha256(match.group(0).encode()).hexdigest()
            if self._delivered.get(match.group(1)) == digest:
                removed = True
                return ""
            self._delivered[match.group(1)] = digest
            return match.group(0)

        out = _BLOCK_RE.sub(_replace, text)
        if not removed:
            return text
        if not _BLOCK_RE.search(out):
            only_request = _USER_REQUEST_RE.match(out)
            if only_request:
                return only_request.group(1)
        return re.sub(r"\n{3,}", "\n\n", out).strip()

    def filter_content(self, content: Any, agent_session_id: Any = None) -> Any:
        """Apply to a Hermes user payload: a string or a list of OpenAI-style parts."""
        if isinstance(content, str):
            return self.filter_text(content, agent_session_id)
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = self.filter_text(part.get("text", ""), agent_session_id)
                    if not text:
                        continue
                    part = {**part, "text": text}
                parts.append(part)
            return parts
        return content
