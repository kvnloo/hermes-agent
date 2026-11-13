"""Private operational replay of the installed plugins, using real Hermes hooks.

Network tool handlers return recorded responses. This checks deterministic routing,
not a model's willingness to follow a hint or the health of an external service.
"""
import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[2] / 'z06-proof'
CANDIDATE = HERE / 'profile/plugins/skill-routes-candidate'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def routes(monkeypatch):
    from hermes_cli import plugins
    home = Path(os.environ['HERMES_HOME'])
    shutil.copytree(CANDIDATE, home / 'plugins/skill-routes')
    shutil.copytree(HERE / 'profile/skills', home / 'skills', dirs_exist_ok=True)
    (home / 'config.yaml').write_text('plugins:\n  enabled: [skill-routes]\n')
    manager = plugins.PluginManager()
    monkeypatch.setattr(plugins, '_plugin_manager', manager)
    plugins.discover_plugins()
    assert plugins.has_hook('pre_tool_call')
    return home


def test_recorded_x_failure_and_identical_retry_reach_real_dispatch(routes, monkeypatch):
    import model_tools
    from tools.registry import registry
    executed = []
    def handler(name, args, **kwargs):
        executed.append((name, args))
        return json.dumps({'success': True, 'recorded_handler': name})
    monkeypatch.setattr(registry, 'dispatch', handler)
    args = {'urls': ['https://x.com/EnriTarta/status/2115426496240124413'], 'char_limit': 5000}
    first = model_tools.handle_function_call('web_extract', args, session_id='x-replay')
    assert 'tool-routes:x-via-agent-reach' in first
    assert 'twitter -c tweet' in first and 'fxtwitter' in first
    assert executed == []
    second = model_tools.handle_function_call('web_extract', args, session_id='x-replay')
    assert json.loads(second)['success'] is True
    assert len(executed) == 1
    other = model_tools.handle_function_call('web_extract', args, session_id='another-owner')
    assert 'tool-routes:x-via-agent-reach' in other
    assert len(executed) == 1


def test_recorded_credit_error_trips_breaker_but_not_other_tools(routes, monkeypatch):
    import model_tools
    from tools.registry import registry
    executed = []
    def handler(name, args, **kwargs):
        executed.append(name)
        if name == 'x_search':
            return json.dumps({'error': 'personal-team-blocked:spending-limit: You have run out of credits'})
        return json.dumps({'success': True})
    monkeypatch.setattr(registry, 'dispatch', handler)
    model_tools.handle_function_call('x_search', {'query': 'first'}, session_id='credits')
    second = model_tools.handle_function_call('x_search', {'query': 'second'}, session_id='credits')
    assert 'tool-routes:x-search-no-credits' in second
    assert executed == ['x_search']
    assert json.loads(model_tools.handle_function_call('read_file', {'path': 'safe'}, session_id='credits'))['success']
    assert executed == ['x_search', 'read_file']


def test_github_route_doctor_hint_and_timeout_do_not_strand_calls(routes, monkeypatch):
    import model_tools
    from tools.registry import registry
    monkeypatch.setattr(registry, 'dispatch', lambda name, args, **kw: json.dumps({
        'output': 'To get started with GitHub CLI, please run:  gh auth login', 'exit_code': 4,
    }))
    url = {'urls': ['https://github.com/NousResearch/hermes-agent/issues/77111']}
    assert 'tool-routes:github-via-gh' in model_tools.handle_function_call('web_extract', url, session_id='gh')
    out = model_tools.handle_function_call('terminal', {'command': 'gh issue view 77111'}, session_id='gh')
    assert 'gh auth status' in out and 'tool-routes:gh-not-logged-in' in out
    again = model_tools.handle_function_call('terminal', {'command': 'gh issue view 77111'}, session_id='gh')
    assert 'tool-routes:gh-not-logged-in' not in again
    monkeypatch.setattr(registry, 'dispatch', lambda *a, **kw: json.dumps({'output': '[Command timed out after 180s]'}))
    args = {'command': 'find / -name headless-group-chat.md'}
    out = model_tools.handle_function_call('terminal', args, session_id='timeout')
    assert 'background=true' in out
    again = model_tools.handle_function_call('terminal', args, session_id='timeout')
    assert 'tool-routes:same-command-timed-out' not in again


def test_mid_session_route_notices_and_corrupt_config_fail_open():
    route = load(CANDIDATE / '__init__.py', 'z06_routes')
    message = 'Read https://x.com/EnriTarta/status/2115426496240124413'
    history = [{'role': 'user', 'content': 'Earlier unrelated request'}]
    hint = route.skill_route_hook(user_message=message, conversation_history=history)
    assert 'agent-reach' in hint['context']
    assert route.skill_route_hook(user_message='[Process exited] ' + message) is None
    viewed = history + [{'role': 'assistant', 'tool_calls': [{'function': {
        'name': 'skill_view', 'arguments': '{"name":"agent-reach"}',
    }}]}]
    assert route.skill_route_hook(user_message=message, conversation_history=viewed) is None
    route.ROUTES = HERE / 'missing-routes.yaml'
    assert route.skill_route_hook(user_message=message) is None
    gate = load(CANDIDATE / 'tool_routes.py', 'z06_gate')
    gate.CFG = HERE / 'missing-tool-routes.yaml'
    assert gate.pre('web_extract', {'urls': [message]}, session_id='fail-open') is None
    assert gate.post('x_search', {}, 'out of credits', session_id='fail-open') is None
    assert gate.hint('terminal', {}, 'HTTP 401: Requires authentication', session_id='fail-open') is None


def test_rank_replay_and_mid_session_fallback(monkeypatch):
    rank = load(HERE / 'profile/plugins/skill-rank/__init__.py', 'z06_rank')
    labels = [json.loads(line) for line in (HERE / 'labels-noedit.jsonl').read_text().splitlines()]
    import hashlib
    manifest = json.loads((HERE / 'manifest.json').read_text())
    for record in manifest:
        path = HERE / record['snapshot']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256'], path
    print(f'Frozen skill documents loaded: {len(rank.load_docs())}')
    hit = sum(any(f'skill_view(name="{s}")' in rank.suggest(row['q']) for s in row['skills']) for row in labels)
    print(f'Installed snapshot rank replay: n={len(labels)} hit@3={hit/len(labels):.3f}')
    assert labels and rank.suggest('search twitter posts')
    history = [{'role': 'user', 'content': 'Earlier unrelated task'}]
    assert rank.suggest('a short follow-up', history) == ''
    long_task = ' '.join(['search twitter research posts'] * 10)
    assert rank.suggest(long_task, history)
    assert rank.suggest('[Process exited] ' + long_task, history) == ''
    def broken_index():
        raise OSError('replay index failure')
    monkeypatch.setattr(rank, 'index', broken_index)
    assert rank.skill_rank_hook(user_message=long_task) is None
