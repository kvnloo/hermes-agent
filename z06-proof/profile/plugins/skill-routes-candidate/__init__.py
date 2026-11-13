"""Route obvious requests to the right skill, injected per turn (pre_llm_call).

Why: the skills index lists ~430 skills with descriptions cut to 60 chars, and the generic web_search /
web_extract tools sit right in the tool list, so agents skip agent-reach on X/Reddit/YouTube links
(audit 2026-11-04: 49 of 63 sessions with such a link never touched it). Matching the message is cheap
and deterministic; the model still decides, but now it is told which skill applies and why.

Routes live in routes.yaml. A route fires at most once per session and never after the skill was loaded.
Any failure injects nothing; never raises into the turn.
"""
import json
import logging
import re
from pathlib import Path

import hermes_yaml as yaml

_log = logging.getLogger(__name__)
HERE = Path(__file__).resolve().parent
ROUTES = HERE / 'routes.yaml'
SKILLS = HERE.parents[1] / 'skills'
WRAPPERS = re.compile(r'<(runtime_info|t3_code_instructions|pull_request_linking|owner-corrections|sop-updates|'
                      r'sibling-sessions|standing-rule-check|skill-route)>.*?</\1>', re.S)

NOTICE = re.compile(r'\s*\[(?!OUT-OF-BAND USER MESSAGE)')

_cache = {'mtime': None, 'routes': []}


def _routes():
    mtime = ROUTES.stat().st_mtime
    if _cache['mtime'] != mtime:
        compiled = []
        for r in yaml.safe_load(ROUTES.read_text()) or []:
            pattern = re.sub(r'\s*\n\s*', '', r['pattern'])  # folded YAML lines join into one regex
            compiled.append((r['skill'], r.get('reason', ''), re.compile(pattern, re.I)))
        _cache.update(mtime=mtime, routes=compiled)
    return _cache['routes']


def _text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return _text(value.get('content') if 'content' in value else value.get('text'))
    if isinstance(value, (list, tuple)):
        return ' '.join(_text(p) for p in value)
    return ''


def owner_text(raw):
    t = raw or ''
    m = re.search(r'<user_request>(.*?)</user_request>', t, re.S)
    return WRAPPERS.sub('', m.group(1) if m else t)


def _already(skill, history):
    """True if this session already loaded the skill or was already nudged toward it."""
    needle_view = re.compile(r'skill_view.{0,200}?\\?"name\\?"\s*:\s*\\?"' + re.escape(skill) + r'\\?"', re.S)
    for m in history or []:
        if not isinstance(m, dict):
            continue
        blob = json.dumps(m.get('tool_calls') or '') if m.get('role') == 'assistant' else _text(m)
        if needle_view.search(blob) or f'<skill-route skill="{skill}"' in blob:
            return True
    return False


_exists_cache = {}


def _exists(skill):
    if skill not in _exists_cache:
        _exists_cache[skill] = any((p / 'SKILL.md').exists() for p in SKILLS.rglob(skill))
    return _exists_cache[skill]


def route(message, history=None):
    prompt = owner_text(_text(message))
    if NOTICE.match(prompt):  # harness notices (delegation results, process exits) are not Kevin asking
        return ''
    out = []
    for skill, reason, pattern in _routes():
        hit = pattern.search(prompt)
        if hit and _exists(skill) and not _already(skill, history):
            out.append(f'<skill-route skill="{skill}">"{hit.group(0)[:80]}" matches skill {skill} ({reason}). '
                       f'Load it with skill_view(name="{skill}") before using web_search, web_extract or a '
                       f'browser for this.</skill-route>')
    return '\n'.join(out)


def skill_route_hook(user_message=None, conversation_history=None, **_):
    try:
        text = route(user_message, conversation_history)
        return {'context': text} if text else None
    except Exception as exc:
        _log.warning('skill-routes: %s', exc)
        return None


def register(ctx):
    ctx.register_hook('pre_llm_call', skill_route_hook)
    # Z06 tool-routes gate (tool_routes.py + tool_routes.yaml): blocks the first generic call on X/GitHub
    # links and repeats of hard failures (identical retry passes); appends doctor hints to gh-auth and
    # timeout failures. Fails open.
    import importlib.util
    spec = importlib.util.spec_from_file_location('skill_routes_tool_routes', HERE / 'tool_routes.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    ctx.register_hook('pre_tool_call', gate.pre)
    ctx.register_hook('post_tool_call', gate.post)
    ctx.register_hook('transform_tool_result', gate.hint)
