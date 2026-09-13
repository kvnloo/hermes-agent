"""Regression tests for the cross-``try`` ``mem_config`` unbound-name bug.

``init_agent`` configures two independent memory subsystems: the built-in
file store (``MEMORY.md`` / ``USER.md`` via ``tools.memory_tool``) and an
external memory-provider plugin (``memory.provider`` via ``plugins.memory`` /
``agent.memory_manager``). The built-in store's ``try`` block was the *only*
assignment site for the function-local ``mem_config``; the external-provider
block reads ``mem_config`` across its own separate ``try`` boundary. When the
built-in block failed before the assignment -- notably when
``from tools.memory_tool import ...`` raised -- ``mem_config`` stayed unbound,
the provider block raised a swallowed ``UnboundLocalError``, and the external
provider a user explicitly configured was silently dropped.

The fix binds a raw-config default for ``mem_config`` *before* the built-in
``try`` (the success path overwrites it with the normalized value), so the
external provider activates even when the built-in store's import fails. A
deduped warning is now emitted from the built-in block's ``except`` so the
import failure is diagnosable instead of silent.

These tests guard the two-part fix against future regressions: (1) the
cross-``try`` ``mem_config`` default that keeps the external provider alive
when the built-in import fails, and (2) the deduped diagnostic warning that
keeps the built-in import failure observable (and spam-free under the
gateway's fresh-``AIAgent``-per-message model) instead of silent.
"""

import contextlib
import logging
import sys
import types
from unittest.mock import patch

from agent import agent_init


class RecordingMemoryProvider:
    """Stand-in provider that records its ``initialize()`` call."""

    name = "recording"

    def __init__(self):
        self.init_kwargs = None
        self.init_session_id = None

    def is_available(self):
        return True

    def initialize(self, session_id, **kwargs):
        self.init_session_id = session_id
        self.init_kwargs = dict(kwargs)

    def get_tool_schemas(self):
        return []

    def shutdown(self):
        pass


class _BrokenMemoryToolModule(types.ModuleType):
    """A ``tools.memory_tool`` stand-in whose body is unimportable.

    ``from tools.memory_tool import X`` resolves the module from ``sys.modules``
    then ``getattr``s ``X``; raising ``ImportError`` (not ``AttributeError``)
    from ``__getattr__`` propagates straight out of the ``from ... import``
    statement rather than falling through to a submodule import, faithfully
    mimicking a broken-install / circular-import failure.
    """

    def __getattr__(self, name):
        raise ImportError(
            f"cannot import name {name!r} from 'tools.memory_tool' "
            "(simulated broken install)"
        )


def _broken_memory_tool():
    return _BrokenMemoryToolModule("tools.memory_tool")


def _broken_shim_patch():
    """A fresh ``tools.memory_tool`` -> broken-module patch each call."""
    return patch.dict(sys.modules, {"tools.memory_tool": _broken_memory_tool()})


# Common seams reused from tests/run_agent/test_memory_provider_init.py --
# these are what a minimal real ``AIAgent`` construction needs patched.
_COMMON_PATCHES = (
    patch("agent.model_metadata.get_model_context_length", return_value=204_800),
    patch("run_agent.get_tool_definitions", return_value=[]),
    patch("run_agent.check_toolset_requirements", return_value={}),
    patch("run_agent.OpenAI"),
)


def _config_with_provider(provider="recording"):
    return {"memory": {"provider": provider}, "agent": {}}


def _clear_warn_state():
    """Reset the module-level dedup guards for a hermetic test. The built-in
    guard is added by the fix; tolerate its absence so these same tests also
    run (and fail at the behavioral assertions) on the pre-fix tree."""
    agent_init._warned_unavailable_providers.clear()
    _builtin = getattr(agent_init, "_warned_builtin_memory_unavailable", None)
    if _builtin is not None:
        _builtin.clear()


def _build_agent(*, cfg, skip_memory, session_id="sess-fix", extra_patches=()):
    provider = RecordingMemoryProvider()
    patches = [
        patch("hermes_cli.config.load_config", return_value=cfg),
        patch("hermes_cli.config.load_config_readonly", return_value=cfg),
        patch("plugins.memory.load_memory_provider", return_value=provider),
        *_COMMON_PATCHES,
        *extra_patches,
    ]
    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        from run_agent import AIAgent

        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=skip_memory,
            session_id=session_id,
        )
    return agent, provider


def _warning_messages(caplog, *needles):
    out = []
    for r in caplog.records:
        if r.levelno < logging.WARNING:
            continue
        msg = r.getMessage()
        if all(n in msg for n in needles):
            out.append(msg)
    return out


def test_provider_activates_when_builtin_memory_tool_import_fails():
    """Primary fix: the external provider activates from raw config even when
    ``tools.memory_tool`` cannot be imported (built-in store down)."""
    _clear_warn_state()
    cfg = _config_with_provider("recording")

    agent, provider = _build_agent(
        cfg=cfg,
        skip_memory=False,
        extra_patches=(
            patch.dict(sys.modules, {"tools.memory_tool": _broken_memory_tool()}),
        ),
    )

    assert agent._memory_manager is not None, (
        "external provider must activate from raw config when the built-in store import fails"
    )
    assert provider.init_session_id == "sess-fix"
    # The built-in store is down (import failed) -- its flags stay at defaults.
    assert agent._memory_store is None
    assert agent._memory_enabled is False


def test_builtin_unavailable_warning_emitted_on_import_failure(caplog):
    """Companion: the built-in store's silent ``except`` now surfaces the
    failure (once) so a ``tools.memory_tool`` import failure is diagnosable."""
    _clear_warn_state()
    cfg = _config_with_provider("recording")

    with caplog.at_level(logging.WARNING, logger="run_agent"):
        _build_agent(
            cfg=cfg,
            skip_memory=False,
            extra_patches=(
                patch.dict(sys.modules, {"tools.memory_tool": _broken_memory_tool()}),
            ),
        )

    warnings = _warning_messages(caplog, "Built-in memory store unavailable")
    assert len(warnings) == 1, (
        f"expected one built-in-unavailable warning, got {warnings}"
    )
    assert "tools.memory_tool" in warnings[0], (
        f"warning should name the failing import: {warnings[0]!r}"
    )


def test_builtin_unavailable_warning_deduped_across_inits(caplog):
    """The built-in-unavailable warning is deduped per process so it does not
    recur on every turn of a gateway session (fresh AIAgent per message)."""
    _clear_warn_state()
    cfg = _config_with_provider("recording")

    with caplog.at_level(logging.WARNING, logger="run_agent"):
        _build_agent(cfg=cfg, skip_memory=False, extra_patches=(_broken_shim_patch(),))
        _build_agent(
            cfg=cfg,
            skip_memory=False,
            session_id="sess-fix-2",
            extra_patches=(_broken_shim_patch(),),
        )

    warnings = _warning_messages(caplog, "Built-in memory store unavailable")
    assert len(warnings) == 1, (
        f"built-in-unavailable warning must dedupe across inits, got {warnings}"
    )
