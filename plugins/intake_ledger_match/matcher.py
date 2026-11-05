"""Local lexical/character-embedding matcher and locked ledger transaction."""
from __future__ import annotations

from collections import Counter
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import time

STOP = set('a an and are as at be been but by can could did do does for from had has have how i if in into is it its just like me my not of on or our pls please so some that the their them then there these they this those thru to too u us was we were what when where which who why will with would you your yeah also all really get make run use using want asked ask'.split())
STOP.update('about actually again already any anything because better bro build check come done dont etc everything find first fix full gimme go going guess here idea know lets look lot maybe mean mention need never new now only out people properly put re real really right said say seem send set setup should since something still stuff sure take tell things through time today try very way well without working work wtf'.split())
ALIASES = {'pw': 'password', 'creds': 'credentials', 'sr': 'semantic router',
           't3code': 't3', 'bws': 'vault', 'autoprune': 'prune', 'pruning': 'prune',
           'subagents': 'worker', 'subagent': 'worker', 'workers': 'worker',
           'worktrees': 'worktree', 'trees': 'worktree', 'see': 'view',
           'froze': 'frozen', 'freezing': 'frozen', 'crashed': 'failure', 'crash': 'failure',
           'disappears': 'expired', 'disappeared': 'expired', 'clearing': 'cleanup',
           'clean': 'cleanup', 'cleaning': 'cleanup', 'ontological': 'ontology',
           'multi': 'multidimensional', 'dimensional': 'multidimensional',
           'separate': 'separate', 'docs': 'documentation', 'forget': 'failure'}


def words(text: str) -> list[str]:
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    expanded = [word for token in tokens for word in ALIASES.get(token, token).split()]
    result = []
    for token in expanded:
        if token in STOP or len(token) < 2:
            continue
        if len(token) > 5 and token.endswith('ing'):
            token = token[:-3]
        elif len(token) > 4 and token.endswith('s') and not token.endswith('ss'):
            token = token[:-1]
        result.append(token)
    return result


def char_embedding(tokens: list[str]) -> Counter:
    """Sparse signed feature-hash embedding, 4096 dimensions, no model/download."""
    vector = Counter()
    for word in set(tokens):
        padded = '^' + word + '$'
        for i in range(len(padded) - 2):
            value = int.from_bytes(hashlib.blake2s(padded[i:i + 3].encode(), digest_size=4).digest(), 'little')
            vector[value % 4096] += 1 if value & 4096 else -1
    return vector


def cosine(a: dict, b: dict) -> float:
    norm = math.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))
    return sum(v * b.get(k, 0) for k, v in a.items()) / norm if norm else 0.0


def match(text: str, rows: list[dict]) -> tuple[str | None, float]:
    explicit = {row['id'] for row in rows if re.search(r'(?<![\w/])' + re.escape(row['id']) + r'(?!\w)', text)}
    if len(explicit) == 1:
        return explicit.pop(), 1.0
    documents = [words(row['id'] + ' ' + row['ask'] + ' ' + row.get('check', '')) for row in rows]
    query = words(text)
    if not query or not documents:
        return None, 0.0
    frequency = Counter(token for doc in documents for token in set(doc))
    idf = {token: math.log((len(rows) + 1) / (count + 1)) + 1 for token, count in frequency.items()}
    q = {token: idf[token] for token in set(query) if token in idf}
    if not q:
        return None, 0.0
    embedding = char_embedding(query)
    ranked = []
    for row, tokens in zip(rows, documents):
        doc = {token: idf[token] for token in set(tokens)}
        overlap = q.keys() & doc.keys()
        coverage = sum(q[token] for token in overlap) / sum(q.values())
        lexical = 0.65 * coverage + 0.35 * cosine(q, doc)
        score = 0.8 * lexical + 0.2 * max(0.0, cosine(embedding, char_embedding(tokens)))
        # A repository path is a stronger identifier than generic words around its URL.
        paths = re.findall(r'(?:https?://[^/\s]+/)([\w.-]+/[\w.-]+)', text)
        if any(path.lower() in row['ask'].lower() for path in paths):
            score += 0.35
        ranked.append((score if len(overlap) >= 2 else 0.0, row['id']))
    ranked.sort(reverse=True)
    best, row_id = ranked[0]
    margin = best - (ranked[1][0] if len(ranked) > 1 else 0)
    return (row_id if best >= 0.30 and margin >= 0.025 else None), round(best, 6)


def short_ask(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^(?:please |pls |can (?:you|u) |could you )+', '', text, flags=re.I)
    return text[:177].rstrip() + '...' if len(text) > 180 else text


def validate_rows(value) -> list[dict]:
    if not isinstance(value, list):
        raise ValueError('ledger must be a list')
    ids = set()
    for row in value:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not isinstance(row.get('ask'), str):
            raise ValueError('invalid ledger row')
        if row['id'] in ids or not isinstance(row.get('check', ''), str):
            raise ValueError('invalid row id or check')
        if not isinstance(row.get('mentions', []), list):
            raise ValueError('mentions must be a list')
        ids.add(row['id'])
    return value


def update_ledger(path: Path, message_id: str, text: str, *, lock_timeout: float = 5.0) -> dict:
    """Read, match and write under a stable sidecar lock, including dedup and ID allocation."""
    if not message_id or not text.strip():
        raise ValueError('message id and text are required')
    with path.with_suffix(path.suffix + '.lock').open('a') as lock:
        deadline = time.monotonic() + lock_timeout
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('ledger lock busy')
                time.sleep(0.02)
        raw = path.read_bytes()
        mode = stat.S_IMODE(path.stat().st_mode)
        rows = validate_rows(json.loads(raw))
        for row in rows:
            if row.get('source_msg_id') == message_id or message_id in row.get('mentions', []):
                return {'action': 'duplicate', 'row_id': row['id'], 'message_id': message_id}
        row_id, score = match(text, rows)
        if row_id is None:
            numbers = [int(row['id'][1:]) for row in rows if re.fullmatch(r'I\d+', row['id'])]
            row_id = f'I{max(numbers, default=0) + 1:03d}'
            rows.append({'id': row_id, 'owner': 'ayo', 'status': 'open', 'ask': short_ask(text),
                         'source_msg_id': message_id, 'mentions': [message_id]})
            action = 'new'
        else:
            next(row for row in rows if row['id'] == row_id).setdefault('mentions', []).append(message_id)
            action = 'match'
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix='.' + path.name + '.', delete=False) as out:
                temporary = Path(out.name)
                os.fchmod(out.fileno(), mode)
                json.dump(rows, out, ensure_ascii=False, indent=1)
                out.write('\n')
                out.flush()
                os.fsync(out.fileno())
            # Detect a non-cooperating writer during scoring rather than knowingly overwrite it.
            if path.read_bytes() != raw:
                raise RuntimeError('ledger changed outside sidecar lock')
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return {'action': action, 'row_id': row_id, 'message_id': message_id, 'score': score}
