"""Gateway fallback effort remains bound when the next turn still names the primary.

Regression for NousResearch/hermes-agent#151304: a cached agent can continue on
its fallback during an Anthropic cooldown, while turn admission resolves the
configured primary's effort again. An explicit new effort must still take effect.
"""

from types import SimpleNamespace

from gateway.run_turn_runner import TurnRunner


def _gateway_fallback():
    primary_effort = {"enabled": True, "effort": "medium"}
    fallback_effort = {"enabled": True, "effort": "xhigh"}
    agent = SimpleNamespace(
        model="gpt-6-astra-900k",
        provider="openai-codex",
        reasoning_config=dict(fallback_effort),
        _fallback_bound_reasoning=dict(fallback_effort),
        _fallback_activated=True,
        _primary_runtime={"reasoning_config":dict(primary_effort)},
    )
    ctx = SimpleNamespace(
        progress_callback=None,
        native_tool_start_callback=None,
        voice_ack_callback=None,
        _voice_ack_guild=[None],
        voice_turn=False,
        _native_slack_task_cards=False,
        native_tool_complete_callback=None,
        _step_callback_sync=None,
        _hooks_ref=SimpleNamespace(loaded_hooks=[]),
        _status_callback_sync=None,
        _event_callback_sync=None,
        _status_adapter=None,
        session_key="fallback-session",
        user_config={},
        source=SimpleNamespace(platform="telegram"),
        mute_notification_reply=False,
        _thinking_enabled=False,
        agent_holder=[None],
        tools_holder=[None],
        process_task_id=None,
        process_baseline=None,
        run_generation=0,
    )
    holder = SimpleNamespace(
        _ctx=ctx,
        _approval_owner=None,
        _runner=SimpleNamespace(
            _service_tier=None,
            _consume_pending_turn_sidecar_notes=lambda key: [],
        ),
        _make_bg_review_callbacks=lambda: (lambda message: None, lambda: None),
        _merge_turn_request_overrides=TurnRunner._merge_turn_request_overrides,
        _clarify_callback_sync=lambda *args, **kwargs: None,
        _notice_callback_sync=lambda *args, **kwargs: None,
        _attach_session_title_callback=lambda agent, ctx: None,
    )
    return agent, holder, primary_effort, fallback_effort


def test_gated_fallback_retains_effort_between_turns():
    agent, holder, primary_effort, fallback_effort = _gateway_fallback()

    # The first failover already bound the fallback effort. Later turns are
    # admitted against the primary, but its restore is still cooldown-gated.
    for _ in range(2):
        TurnRunner._wire_turn_agent_callbacks(
            holder, agent, {}, dict(primary_effort), None, None, False,
        )
        assert agent.model == "gpt-6-astra-900k"
        assert agent.reasoning_config == fallback_effort

    # A changed per-turn/session choice must not be masked by fallback state.
    changed = {"enabled": True, "effort": "high"}
    TurnRunner._wire_turn_agent_callbacks(
        holder, agent, {}, changed, None, None, False,
    )
    assert agent.reasoning_config == changed
