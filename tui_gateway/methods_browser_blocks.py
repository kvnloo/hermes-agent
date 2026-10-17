"""User-only browser block intents; never exposed as model tools."""
from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method


def _browser_block_intent(rid, params, intent):
    from subprocess import SubprocessError
    from tools.browser_tern import get_provider, block_id

    sid = _str_param(params, "session_id")
    _, owner = _current_session_steer_authority(sid)
    if owner is None or not owner.get("session_key"):
        return _err(rid, 4001, "session not found or not owned by this transport")
    try:
        if intent != "blocks":
            block_id(params.get("target_id"))
        provider = get_provider()
        if provider is None:
            if intent == "blocks":
                return _ok(rid, {"available": False, "blocks": []})
            return _err(rid, 5031, "Tern browser interface unavailable")
        task = owner["session_key"]
        if intent == "blocks":
            return _ok(rid, {"available": True, "blocks": provider.listing(task)})
        if _current_session_steer_authority(sid)[1] is not owner:
            return _err(rid, 4001, "session authority changed before browser intent")
        # Handover while a model tool is executing can retarget its next command.
        if intent == "adopt" and owner.get("running"):
            return _err(rid, 4015, "Wait for the current turn before handing over a browser block")
        operations = {"adopt": provider.adopt_by_user, "focus": provider.focus}
        result = operations[intent](task, params["target_id"])
        return _ok(rid, result)
    except (RuntimeError, ValueError, OSError, SubprocessError) as error:
        return _err(rid, 5031, str(error))


@method("browser.blocks")
@_registry.profile_scoped
def _browser_blocks(rid, params):
    return _browser_block_intent(rid, params, "blocks")


@method("browser.adopt")
@_registry.profile_scoped
def _browser_adopt(rid, params):
    return _browser_block_intent(rid, params, "adopt")


@method("browser.focus")
@_registry.profile_scoped
def _browser_focus(rid, params):
    return _browser_block_intent(rid, params, "focus")


def register(server):
    bind_module(globals(), server)
    server._LONG_HANDLERS = server._LONG_HANDLERS | _registry.names()
