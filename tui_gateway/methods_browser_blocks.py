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
        from .contracts.browser_blocks import BrowserBlockParams, BrowserFrameParams
        from .contracts.common import SessionParams
        models = {"blocks": SessionParams, "frame": BrowserFrameParams}
        models.get(intent, BrowserBlockParams).model_validate(params)
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
        if intent in {"adopt", "frame", "release"} and owner.get("running"):
            return _err(rid, 4015, "Wait for the current turn before changing browser ownership or frame")
        operations = {"adopt": provider.adopt_by_user, "focus": provider.focus,
                      "release": lambda task, target: provider.release_by_user(task, target),
                      "frame": lambda task, target: provider.select_frame(task, target, params["frame"])}
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


@method("browser.frame")
@_registry.profile_scoped
def _browser_frame(rid, params):
    return _browser_block_intent(rid, params, "frame")


@method("browser.release")
@_registry.profile_scoped
def _browser_release(rid, params):
    return _browser_block_intent(rid, params, "release")


def register(server):
    bind_module(globals(), server)
    server._LONG_HANDLERS = server._LONG_HANDLERS | _registry.names()
