"""Rank skills by their full SKILL.md body and name the top matches on fresh owner turns (pre_llm_call).

Why: the system prompt lists ~450 skills with descriptions cut to 60 chars, which is not enough to pick from.
Offline eval on 149 real owner-started sessions (operations/token-thrift-tools-20261104/skill-eval):
BM25 over name + description gets the skill the session loaded into the top 3 in 38% of sessions;
BM25 over the full body gets 74% (top-1 22% -> 62%). No model, no network, ~10 ms per turn.

The hint goes into the user turn (pre_llm_call context), never the system prompt, so the cached
prefix stays byte-stable. It fires on the first owner turn of a session and on later turns that read
like a new task (>= NEW_TASK_WORDS words), names at most TOP_K skills not already loaded or suggested,
and injects nothing on any failure.
"""
import json
import logging
import math
import os
import re
import time
from collections import Counter
from pathlib import Path

_log = logging.getLogger(__name__)
SKILLS = Path(__file__).resolve().parents[2] / 'skills'
TOP_K = 3
NEW_TASK_WORDS = 30
QUERY_CHARS = 2000
REINDEX_SECONDS = 300

WRAPPERS = re.compile(r'<(runtime_info|t3_code_instructions|pull_request_linking|owner-corrections|sop-updates|'
                      r'sibling-sessions|standing-rule-check|skill-route|skill-rank)>.*?</\1>', re.S)
NOTICE = re.compile(r'\s*\[(?!OUT-OF-BAND USER MESSAGE)')
STOP = set('the a an and or to of in on for with is it this that be as are at by from use when you we i me my '
           'can do not'.split())


def tokens(s):
    return [w for w in re.findall(r'[a-z0-9]+', s.lower()) if w not in STOP and len(w) > 1]


class Index:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.names = [n for n, _ in docs]
        self.tf = [Counter(tokens(t)) for _, t in docs]
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = sum(self.len) / max(1, len(self.len))
        self.k1, self.b = k1, b
        df = Counter(w for c in self.tf for w in c)
        n = len(docs)
        self.idf = {w: math.log(1 + (n - d + 0.5) / (d + 0.5)) for w, d in df.items()}

    def rank(self, query):
        q = set(tokens(query))
        scored = []
        for name, c, length in zip(self.names, self.tf, self.len):
            s = 0.0
            for w in q:
                f = c.get(w)
                if f:
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self.avg))
            if s > 0:
                scored.append((s, name))
        scored.sort(reverse=True)
        return [n for _, n in scored]


def load_docs(root=SKILLS):
    docs = {}
    for dirpath, _dirs, files in os.walk(root, followlinks=True):
        rel = os.path.relpath(dirpath, root)
        if '/.' in '/' + rel or 'node_modules' in rel or 'SKILL.md' not in files:
            continue
        text = (Path(dirpath) / 'SKILL.md').read_text(errors='ignore')
        m = re.match(r'---\n(.*?)\n---\n(.*)', text, re.S)
        if not m:
            continue
        fm, body = m.groups()
        name = re.search(r'^name:\s*(.+)$', fm, re.M)
        if not name:
            continue
        n = name.group(1).strip().strip('"\'')
        desc = re.search(r'^description:\s*(.+)$', fm, re.M)
        docs.setdefault(n, f"{n.replace('-', ' ')} {desc.group(1) if desc else ''} {body}")
    return sorted(docs.items())


_state = {'index': None, 'built': 0.0}


def index():
    if _state['index'] is None or time.time() - _state['built'] > REINDEX_SECONDS:
        _state['index'] = Index(load_docs())
        _state['built'] = time.time()
    return _state['index']


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
    return WRAPPERS.sub('', m.group(1) if m else t).strip()


def seen_skills(history):
    """Skills this session already loaded or was already pointed at (by this plugin or skill-routes)."""
    seen, owner_turns = set(), 0
    for m in history or []:
        if not isinstance(m, dict):
            continue
        if m.get('role') == 'assistant':
            for c in m.get('tool_calls') or []:
                f = (c or {}).get('function') or {}
                if f.get('name') == 'skill_view':
                    try:
                        seen.add(json.loads(f.get('arguments') or '{}').get('name'))
                    except Exception:
                        pass
        elif m.get('role') == 'user':
            t = _text(m)
            seen.update(re.findall(r'<skill-route skill="([^"]+)"', t))
            for block in re.findall(r'<skill-rank>(.*?)</skill-rank>', t, re.S):
                seen.update(re.findall(r'skill_view\(name="([^"]+)"\)', block))
            if not NOTICE.match(owner_text(t)):
                owner_turns += 1
    return seen, owner_turns


def suggest(message, history=None):
    prompt = owner_text(_text(message))
    if not prompt or NOTICE.match(prompt):
        return ''
    seen, prior_owner_turns = seen_skills(history)
    if prior_owner_turns and len(prompt.split()) < NEW_TASK_WORDS:
        return ''
    picks = [n for n in index().rank(prompt[:QUERY_CHARS]) if n not in seen][:TOP_K]
    if not picks:
        return ''
    listed = ', '.join(f'skill_view(name="{n}")' for n in picks)
    return (f'<skill-rank>Skills whose full text best matches this request, best first: {listed}. '
            f'Load the one that fits before starting; skip them if none do.</skill-rank>')


def skill_rank_hook(user_message=None, conversation_history=None, **_):
    try:
        text = suggest(user_message, conversation_history)
        return {'context': text} if text else None
    except Exception as exc:
        _log.warning('skill-rank: %s', exc)
        return None


def register(ctx):
    ctx.register_hook('pre_llm_call', skill_rank_hook)
