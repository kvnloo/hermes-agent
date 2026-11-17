"""An unanswered ACP edit-approval prompt must not be reported as a client denial (#63302)."""

import asyncio
from concurrent.futures import Future, TimeoutError as FutureTimeout
from unittest.mock import AsyncMock, MagicMock, patch

import acp  # noqa: F401  -- the requester imports acp.schema lazily

from acp_adapter.edit_approval import (
    make_acp_edit_approval_requester,
    maybe_require_edit_approval,
    reset_edit_approval_requester,
    set_edit_approval_requester,
)


def test_unanswered_edit_approval_is_reported_as_timeout_not_denial(tmp_path):
    future = MagicMock(spec=Future)
    future.result.side_effect = FutureTimeout()
    with patch("agent.async_utils.asyncio.run_coroutine_threadsafe", return_value=future):
        requester = make_acp_edit_approval_requester(
            AsyncMock(name="request_permission"), MagicMock(spec=asyncio.AbstractEventLoop), "s1", timeout=0.01)
        token = set_edit_approval_requester(requester)
        try:
            target = tmp_path / "f.txt"
            result = maybe_require_edit_approval("write_file", {"path": str(target), "content": "x"})
        finally:
            reset_edit_approval_requester(token)

    assert result is not None and not target.exists()  # still fails closed
    assert "denied by ACP client" not in result
    assert "timed out" in result
