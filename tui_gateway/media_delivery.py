"""Bounded image reads for Tern's SDK blob upload; never interpret compute-host paths locally."""
from __future__ import annotations

import base64
import json
import os
import stat

MAX_IMAGE_BYTES = 16 * 1024 * 1024
_IMAGE_MIMES = {"PNG": "image/png", "JPEG": "image/jpeg", "GIF": "image/gif", "WEBP": "image/webp",
                "BMP": "image/bmp", "TIFF": "image/tiff"}


def _image_reference_paths(content) -> set[str]:
    from tui_gateway.session_history import _IMAGE_REF_RE
    if isinstance(content, list):
        return set().union(*(_image_reference_paths(part) for part in content))
    if isinstance(content, dict):
        return _image_reference_paths(content.get("text", ""))
    if not isinstance(content, str):
        return set()
    paths = set()
    for line in content.splitlines():
        match = _IMAGE_REF_RE.fullmatch(line)
        if match:
            value = match[1]
            paths.add(value[1:-1] if value[0] in ('`', '"', "'") else value)
    return paths


def _tool_image_path(history: list, call_id: str, cwd: str) -> str | None:
    """Canonical completed read/browser result only, never a client-supplied read target."""
    calls = {}
    for message in history:
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or []:
                function = call.get("function") or {}
                arguments = function.get("arguments") or {}
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except (ValueError, TypeError):
                        continue
                calls[call.get("id")] = (function.get("name"), arguments)
        if message.get("role") != "tool" or message.get("tool_call_id") != call_id:
            continue
        name, args = calls.get(call_id, (message.get("name"), message.get("args") or {}))
        result = message.get("content")
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (ValueError, TypeError):
                continue
        if not isinstance(result, dict) or result.get("error") or result.get("success") is False:
            continue
        if not isinstance(args, dict):
            continue
        if name == "read_file":
            path = result.get("resolved_path") or args.get("path") or args.get("file_path")
        elif isinstance(name, str) and name.startswith("browser"):
            meta = result.get("meta") or {}
            path = result.get("screenshot_path") or (meta.get("screenshot_path") if isinstance(meta, dict) else None)
        else:
            continue
        if isinstance(path, str):
            return os.path.abspath(os.path.join(cwd, path))
    return None


def read_session_image(session: dict, path: str, tool_call_id: str | None) -> dict:
    """Authorize against existing staging/history; no new store, handles, or byte cache."""
    from tui_gateway import server
    # Staged user images live on the gateway, irrespective of the terminal backend.
    history = list(session.get("history") or [])
    if tool_call_id:
        if server._bound_terminal_backend(session.get("profile_home")) != "local":
            raise ValueError("Compute-host image preview is not supported")
        allowed = {_tool_image_path(history, tool_call_id, session.get("cwd") or os.getcwd())}
    else:
        allowed = set(session.get("attached_images") or [])
        for message in history:
            if message.get("role") == "user":
                allowed.update(_image_reference_paths(message.get("content", "")))
    if path not in allowed:
        raise ValueError("Image is not attached to this session or the attachment is stale")
    # Do not follow a replaced symlink or block on a FIFO/device. Bound reads even after fstat.
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_IMAGE_BYTES:
            raise ValueError("Image must be a regular file no larger than 16 MiB")
        data = file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds 16 MiB")
    # PIL reads the format from bytes, never the filename. Do not decode pixels here.
    from io import BytesIO
    from PIL import Image
    with Image.open(BytesIO(data)) as image:
        mime = _IMAGE_MIMES.get(image.format or "")
    if not mime:
        raise ValueError("Unsupported image format")
    return {"content_base64": base64.b64encode(data).decode("ascii"), "mime": mime, "bytes": len(data)}
