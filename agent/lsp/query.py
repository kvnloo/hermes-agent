"""Read-only semantic queries over the existing workspace/trust-gated LSP service."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from urllib.parse import urlsplit

from agent.lsp.client import file_uri, uri_to_path
from agent.lsp.protocol import ERROR_METHOD_NOT_FOUND, LSPProtocolError, LSPRequestError
from agent.lsp.servers import language_id_for

_OPERATIONS = {"references": "textDocument/references", "symbols": "textDocument/documentSymbol", "hover": "textDocument/hover"}


def _range(value):
    def position(point):
        line, col = point["line"], point["character"]
        if type(line) is not int or type(col) is not int or min(line, col) < 0:
            raise ValueError("Invalid LSP position")
        return {"line": line + 1, "col": col + 1}
    start, end = position(value["start"]), position(value["end"])
    if (end["line"], end["col"]) < (start["line"], start["col"]):
        raise ValueError("Reversed LSP range")
    return {"start": start, "end": end}


def _location(value):
    uri = value["uri"]
    parsed = urlsplit(uri)
    if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"} or parsed.query or parsed.fragment:
        raise ValueError("LSP location is not a local file URI")
    path = uri_to_path("file://" + parsed.path)
    if not os.path.isabs(path) or any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise ValueError("Invalid LSP file path")
    return {"path": path, "range": _range(value["range"])}


def _symbols(values, path, parent=""):
    if not isinstance(values, list):
        raise ValueError("Invalid LSP symbols")
    result, occurrences = [], {}
    for item in values:
        name, kind = item["name"], item["kind"]
        if not isinstance(name, str) or type(kind) is not int or not 1 <= kind <= 26:
            raise ValueError("Invalid LSP symbol")
        location = _location(item["location"]) if "location" in item else {"path": path, "range": _range(item["range"])}
        selection = _range(item["selectionRange"]) if "selectionRange" in item else location["range"]
        identity = json.dumps([parent, name, kind, location, selection], sort_keys=True)
        occurrence = occurrences.get(identity, 0)
        occurrences[identity] = occurrence + 1
        key = hashlib.sha256(f"{identity}:{occurrence}".encode()).hexdigest()[:24]
        result.append({"id": key, "name": name, "kind": kind, "location": location, "selection": selection,
                       "children": _symbols(item.get("children", []), path, key)})
    return result


def _hover(value):
    if value is None:
        return [], None
    contents = value["contents"]
    def content(item):
        if not isinstance(item, (str, dict)) or (isinstance(item, dict) and not isinstance(item.get("value"), str)):
            raise ValueError("Invalid hover content")
        if isinstance(item, str):
            return {"format": "plaintext", "text": item, "language": None}
        if "language" in item and isinstance(item["language"], str):
            return {"format": "code", "text": item["value"], "language": item["language"]}
        if item["kind"] not in {"markdown", "plaintext"}:
            raise ValueError("Invalid hover content format")
        return {"format": item["kind"], "text": item["value"], "language": None}
    return [content(item) for item in (contents if isinstance(contents, list) else [contents])], _range(value["range"]) if "range" in value else None


async def _query(service, operation, path, line, col):
    client = await service._get_or_spawn(path)
    if client is None:
        return {"kind": "unavailable", "operation": operation, "message": "Language server could not start", "server": None}
    await client.open_file(path, language_id=language_id_for(path, service._server_for(path)))
    params: dict = {"textDocument": {"uri": file_uri(path)}}
    if operation != "symbols":
        params["position"] = {"line": line - 1, "character": col - 1}
    if operation == "references":
        params["context"] = {"includeDeclaration": True}
    try:
        value = await client.semantic_query(_OPERATIONS[operation], params)
        if operation in {"references", "symbols"} and value is not None and not isinstance(value, list):
            raise ValueError("Expected an LSP result array or null")
        if operation == "references":
            data = {"locations": [_location(item) for item in ([] if value is None else value)]}
        elif operation == "symbols":
            data = {"symbols": _symbols([] if value is None else value, path)}
        else:
            contents, span = _hover(value)
            data = {"contents": contents, "range": span}
        return {"kind": operation, "server": client.server_id, **data}
    except LSPRequestError as exc:
        return {"kind": "unavailable" if exc.code == ERROR_METHOD_NOT_FOUND else "error", "operation": operation,
                "server": client.server_id, "message": str(exc)}
    finally:
        service._touch(client)


def query_sync(service, operation, path, line=1, col=1):
    """Never turn a missing server, failed request or malformed response into an empty success."""
    server = service._server_for(path) if service is not None else None
    base = {"path": path, "server": server.server_id if server else None, "position_encoding": "utf-16"}
    if operation not in _OPERATIONS or type(line) is not int or type(col) is not int or min(line, col) < 1:
        raise ValueError("Invalid semantic LSP query")
    if service is None or not service.enabled_for(path):
        return {"lsp_result": {**base, "kind": "unavailable", "operation": operation,
                               "message": "LSP disabled, unavailable or workspace not eligible"}}
    try:
        result = service._loop.run(_query(service, operation, path, line, col), timeout=service._wait_budget(path) + 3)
    except (asyncio.TimeoutError, OSError, RuntimeError, LSPProtocolError) as exc:
        result = {"kind": "unavailable", "operation": operation, "message": f"LSP request unavailable: {exc}"}
    except (KeyError, TypeError, ValueError, RecursionError) as exc:
        result = {"kind": "error", "operation": operation, "message": f"Invalid LSP response: {exc}"}
    return {"lsp_result": {**base, **result}}
