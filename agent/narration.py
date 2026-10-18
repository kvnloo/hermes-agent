"""Display-only qualification of Anthropic/Bedrock connector narration.

Signature header layout follows OMP's anthropic-signature.ts (Can Bölük /
Stencil, MIT). This reads a kind hint, not signature authenticity; never use it
for authority or rewrite the signed provider replay carriers.
"""
from __future__ import annotations

import base64
import binascii


def _varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 35, 7):
        if offset >= len(data):
            raise ValueError("truncated varint")
        byte = data[offset]
        offset += 1
        if shift == 28 and byte > 15:
            raise ValueError("uint32 overflow")
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, offset
    raise ValueError("overlong varint")


def _field(data: bytes, wanted: int) -> bytes:
    offset = 0
    while offset < len(data):
        tag, offset = _varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if not number:
            raise ValueError("invalid field")
        if wire == 0:
            _, offset = _varint(data, offset)
            continue
        if wire == 2:
            size, offset = _varint(data, offset)
        elif wire in (1, 5):
            size = {1: 8, 5: 4}[wire]
        else:
            raise ValueError("unsupported wire type")
        end = offset + size
        if end > len(data):
            raise ValueError("truncated field")
        if number == wanted and wire == 2:
            return data[offset:end]
        offset = end
    return b""


def is_narration_signature(signature: object) -> bool:
    if not isinstance(signature, str):
        return False
    try:
        raw = base64.b64decode(signature, validate=True)
        return _field(_field(_field(raw, 2), 1), 8) == b"narration"
    except (ValueError, binascii.Error):
        return False


def reasoning_presentation(message: object) -> list[dict] | None:
    """Derived, signature-free segments; absent unless a genuine kind marker exists."""
    read = message.get if isinstance(message, dict) else lambda key: getattr(message, key, None)
    details = read("reasoning_details")
    bedrock = read("bedrock_content_blocks")
    if bedrock:
        details = [block["reasoningContent"] for block in bedrock
                   if isinstance(block, dict) and isinstance(block.get("reasoningContent"), dict)]
    parts = []
    for detail in details or []:
        if not isinstance(detail, dict):
            continue
        text = detail.get("thinking") or detail.get("text")
        if isinstance(text, str) and text:
            parts.append({"text": text, "narration": is_narration_signature(detail.get("signature"))})
    return parts if any(part["narration"] for part in parts) else None
