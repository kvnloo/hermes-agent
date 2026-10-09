"""Post-switch ACP evidence for o8#3388; no provider inference or credentials.

The real SDK router and session manager must report the rebuilt agent's state,
not the requested alias, the resolver's proposal, or a successful empty ACK.
"""

from types import SimpleNamespace

import pytest
from acp.agent.router import build_agent_router
from acp.exceptions import RequestError

from acp_adapter.server import HermesACPAgent
from acp_adapter.session import SessionManager
from hermes_cli.model_switch import ModelSwitchResult


def _setup(monkeypatch, tmp_path, *, live_model="active-model", live_provider="anthropic"):
    builds = []

    def make_agent():
        agent = SimpleNamespace(
            model="default" if not builds else live_model,
            provider="anthropic" if not builds else live_provider,
            base_url="https://api.anthropic.com", api_key="NEVER-EMIT-THIS",
        )
        builds.append(agent)
        return agent

    manager = SessionManager(agent_factory=make_agent)
    state = manager.create_session(str(tmp_path))
    agent = HermesACPAgent(session_manager=manager)
    monkeypatch.setattr("hermes_cli.model_switch.switch_model", lambda **_kw: ModelSwitchResult(
        success=True, target_provider="anthropic", new_model="resolver-proposal"))
    return agent, state, builds


@pytest.mark.asyncio
async def test_router_confirms_actual_rebuilt_model_without_catalog_or_replay(monkeypatch, tmp_path):
    agent, state, builds = _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(agent, "_build_model_state", lambda *_: pytest.fail("must not query catalog"))
    monkeypatch.setattr(agent, "load_session", lambda *_: pytest.fail("must not replay session"))
    result = await build_agent_router(agent, use_unstable_protocol=True)("session/set_model", {
        "sessionId": state.session_id, "modelId": "anthropic:requested-alias",
    }, False)
    assert len(builds) == 2 and state.agent is builds[1]
    assert state.model == "resolver-proposal"
    assert result == {"_meta": {"hermes": {"activeModelId": "anthropic:active-model"}}}
    assert state.history == [] and not state.command_op


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["model", "provider"])
async def test_incomplete_live_identity_does_not_invent_confirmation(monkeypatch, tmp_path, field):
    kwargs = {f"live_{field}": ""}
    agent, state, _builds = _setup(monkeypatch, tmp_path, **kwargs)
    result = await build_agent_router(agent, use_unstable_protocol=True)("session/set_model", {
        "sessionId": state.session_id, "modelId": "anthropic:requested-alias",
    }, False)
    assert result == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["rejected", "build", "busy"])
async def test_failed_switch_never_confirms_requested_model(monkeypatch, tmp_path, failure):
    agent, state, builds = _setup(monkeypatch, tmp_path)
    original = state.agent
    if failure == "rejected":
        monkeypatch.setattr("hermes_cli.model_switch.switch_model", lambda **_kw: ModelSwitchResult(
            success=False, error_message="unsupported model"))
    elif failure == "build":
        def fail_build(**_kwargs):
            raise RuntimeError("construction failed")
        monkeypatch.setattr(agent.session_manager, "_make_agent", fail_build)
    else:
        state.is_running = True
    with pytest.raises((RequestError, RuntimeError)) as exc:
        await build_agent_router(agent, use_unstable_protocol=True)("session/set_model", {
            "sessionId": state.session_id, "modelId": "anthropic:requested-alias",
        }, False)
    if failure != "build":
        assert exc.value.code == (-32602 if failure == "rejected" else -32603)
    else:
        assert "construction failed" in str(exc.value)
    assert state.agent is original and state.model == "default" and len(builds) == 1
