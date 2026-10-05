"""Feishu response diagnostics shared by message and media delivery."""

from typing import Any, Optional

from gateway.platforms.base import SendResult


def response_error_result(
    response: Any, *, default_message: str, override_error: Optional[str] = None,
) -> SendResult:
    code = getattr(response, "code", "unknown")
    # lark's BaseResponse.msg is Optional[str]: getattr substitutes the default only when
    # the attribute is absent, so a present-but-None msg needs its own fallback or it
    # renders as the literal "None".
    msg = getattr(response, "msg", None) or default_message
    # override_error is only a headline ("missing file_key" never says why); the API's
    # code/msg carries the diagnosis (e.g. 99991672 = app lacks the im:resource scope),
    # so keep both. This string is logged by the caller, never echoed into chat.
    error = f"{override_error} [{code}] {msg}" if override_error else f"[{code}] {msg}"
    # The appended platform verdict must not leak into substring classification (an
    # upload error carrying "[230002] chat not found" reads as a dead-chat marker to
    # text-based classifiers), so pin the kind instead of letting them infer one.
    return SendResult(
        success=False, error=error, raw_response=response, error_kind="unknown")
