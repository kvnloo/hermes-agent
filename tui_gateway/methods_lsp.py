"""User-only, read-only semantic inspection. No synthetic model tool or transcript rows."""
from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method


@method("lsp.query")
@_registry.profile_scoped
def _lsp_query(rid, params):
    from pathlib import Path
    from pydantic import ValidationError
    from agent.lsp import get_service
    from agent.lsp.query import query_sync
    from agent.lsp.workspace import is_inside_workspace
    from .contracts.lsp import LspQueryParams, LspQueryResult

    try:
        query = LspQueryParams.model_validate(params)
    except ValidationError as exc:
        return _err(rid, 4000, str(exc))
    _, session = _current_session_steer_authority(query.session_id)
    if session is None:
        return _err(rid, 4001, "session not found or not owned by this transport")
    with _session_profile_runtime_scope(session):
        cwd = session.get("cwd")
        if not _session_is_local_backend(session) or not cwd or not Path(cwd).is_absolute():
            return _ok(rid, {"lsp_result": {"kind": "unavailable", "operation": query.operation, "path": query.path,
                                          "server": None, "position_encoding": "utf-16",
                                          "message": "Semantic LSP requires a local session workspace"}})
        path = str((Path(cwd) / query.path).resolve())
        if not is_inside_workspace(path, cwd):
            return _err(rid, 4000, "LSP target must be inside the session workspace")
        if _current_session_steer_authority(query.session_id)[1] is not session:
            return _err(rid, 4001, "session authority changed before LSP query")
        result = query_sync(get_service(), query.operation, path, query.line, query.col)
        return _ok(rid, LspQueryResult.model_validate(result).model_dump(mode="json"))


def register(server):
    bind_module(globals(), server)
    server._LONG_HANDLERS = server._LONG_HANDLERS | _registry.names()
