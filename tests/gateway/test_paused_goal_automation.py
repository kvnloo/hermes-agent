"""A paused /goal retains canonical completion admission until resume (#153241)."""
from types import SimpleNamespace

import pytest

from gateway.config import Platform
from gateway.session import SessionSource
from gateway.session_authority import LiveSession, SessionAuthority
from gateway.session_contract import SessionRef
from hermes_cli.goals import GoalState
from hermes_state import SessionDB
from hermes_state_runtime import (
    RuntimeStoreError, admit_session_input, begin_runtime_epoch, get_session_admission,
)


@pytest.mark.asyncio
async def test_paused_goal_retains_completion_and_resume_wakes_original_head(tmp_path, monkeypatch):
    from gateway import session_envelope, session_authorities
    from gateway.slash_commands_goals import GatewayGoalCommandsMixin
    from hermes_cli import goal_command, goals

    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    db = SessionDB(tmp_path / 'state.db')
    try:
        db.create_session('owner', source='telegram')
        epoch = begin_runtime_epoch(db, instance_id='current')
        admission = admit_session_input(
            db, epoch=epoch, session_id='owner', principal_id='automation:route',
            request_id='completion-1', payload={'text': 'background job finished',
                'native_text_v1': {'automation': {'owner': 'owner', 'identity': 'completion-1'}}})
        db.set_meta('goal:owner', GoalState(goal='finish the task', status='paused').to_json())
        source = SessionSource(platform=Platform.TELEGRAM, chat_id='chat', user_id='human')
        runner = SimpleNamespace(_draining=False, config=SimpleNamespace(multiplex_profiles=False),
                                 _adapter_for_source=lambda source: None)
        authority = SessionAuthority(runner, profile_id='p', instance_id='current', db=db, epoch=epoch)
        live = authority.sessions['owner'] = LiveSession(source, 'route')
        ref = SessionRef('p', 'owner')

        async def validated_route(*args):
            return None
        monkeypatch.setattr(session_envelope, 'check_native_route', validated_route)
        monkeypatch.setattr(authority, '_classic_turn_holds', lambda route: False)
        with pytest.raises(RuntimeStoreError, match='goal_paused'):
            await authority._claim_next(ref, live)
        assert get_session_admission(db, admission_id=admission['admission_id'])['status'] == 'queued'
        assert db.get_session('owner')['runtime_generation'] == 0

        wakes, appended = [], []
        monkeypatch.setattr(authority, '_schedule', lambda target: wakes.append(target))
        monkeypatch.setattr(session_authorities, 'active_authority', lambda runner: authority)
        monkeypatch.setattr(goals, 'last_user_message_from_db', lambda session_id: None)

        class GoalRunner(GatewayGoalCommandsMixin):
            async def _get_goal_manager_for_event(self, event):
                origin = SessionSource(platform=Platform.LOCAL, chat_id='owner', user_id='human')
                return SimpleNamespace(session_id='owner'), SimpleNamespace(origin=origin)

            async def _run_in_executor_with_context(self, dispatch):
                return dispatch()

            def _clear_goal_continuations(self, event, verb):
                pass

            def _enqueue_goal_turn(self, event, prompt, *, label, kickoff):
                appended.append(prompt)

        for verb in ('resume', 'clear'):
            monkeypatch.setattr(goal_command, 'dispatch_goal_command',
                lambda *args, verb=verb, **kwargs: goal_command.GoalCommandResult(
                    'ok', prompt='continue' if verb == 'resume' else None,
                    clear_pending='clear' if verb == 'clear' else None))
            event = SimpleNamespace(get_command_args=lambda verb=verb: verb)
            assert await GoalRunner()._handle_goal_command(event) == 'ok'
        assert wakes == [ref, ref]
        assert appended == []

        db.set_meta('goal:owner', GoalState(goal='finish the task', status='active').to_json())
        claimed, original = await authority._claim_next(ref, live)
        assert claimed['admission_id'] == original['admission_id'] == admission['admission_id']
        assert claimed['generation'] == 1
    finally:
        db.close()
