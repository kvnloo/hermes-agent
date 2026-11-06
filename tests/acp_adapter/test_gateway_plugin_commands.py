"""Plugin slash commands on the shipped ACP gateway path: advertised to the editor, run by the owner.

An actual ``hermes acp`` stdio process against an isolated gateway with the bundled
``stats-dashboard`` plugin enabled. ``/stats status`` is side-effect free (no export, no server).
"""
import pytest

from tests.acp_adapter.test_gateway_session_metadata import _reply, _updates
from tests.acp_adapter.test_gateway_sessions import editor
from tests.waiting import async_wait_until


@pytest.mark.platforms('linux')
@pytest.mark.asyncio
@pytest.mark.parametrize('daemon', [{'plugins': {'enabled': ['stats-dashboard']}}], indirect=True)
async def test_plugin_command_is_advertised_and_answered_by_the_owner(daemon, tmp_path):
    async with editor(daemon, tmp_path) as acp:
        await acp.rpc('initialize', protocolVersion=1, clientCapabilities={})
        sid = (await acp.rpc('session/new', cwd=str(tmp_path), mcpServers=[]))['result']['sessionId']
        # The built-in menu goes out first; the owner's plugin commands follow in a later update.
        def menus():
            return [{c['name']: c for c in u['availableCommands']}
                    for u in _updates(acp, sid, 'available_commands_update')]

        await async_wait_until(lambda: any('stats' in menu for menu in menus()))
        advertised = menus()[-1]
        assert 'stats' in advertised, sorted(advertised)
        assert 'help' in advertised  # the built-in menu is still there

        # The owner runs it (slash.exec) and its text is the command's reply, never a model turn.
        assert 'Trace dashboard is not running' in await _reply(acp, sid, '/stats status')
