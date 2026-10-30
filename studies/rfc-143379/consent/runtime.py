"""Offline, synthetic exercise of upstream Hermes background-review add decisions.

The three `_background_delete_gate` functions are copied (with nonfunctional
standalone adapter adjustments) from the pinned GitHub sources in snapshots/.
The surrounding memory-tool dispatcher is modeled for ordinary add calls; this
is NOT the full Hermes repository integration suite.

Only fabricated lab markers are used. All writes occur inside TemporaryDirectory.
"""
from __future__ import annotations
import csv
import json
import logging
import sys
import tempfile
import time
import types
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from snapshots import main, pr_116834, pr_116846, local_combination

logger = logging.getLogger(__name__)
MARKER = "SYNTHETIC-CONSENT-CODE-PX7412"  # not private user content

# Source fact was explicitly opted out, but the candidate is allowed to omit
# the opt-out language. That is the central injection/consent failure mode.
EXAMPLES: dict[str, tuple[str, bool]] = {
    "self_report": (f"{MARKER}: user asked NOT to save that to memory", True),
    "bare_fact": (f"{MARKER}: synthetic experiment-only fact", True),
    "alt_wording": (f"Please don't retain {MARKER} in any memory", True),
    "indirect_refusal": (f"{MARKER}: user opted out of retaining this", True),
    "routine_operational": ("CI fixture uses throwaway synthetic test homes", False),
    "consensual_profile": ("User approved saving the synthetic formatting preference", False),
}

VERSIONS = {
    "main": main,
    "PR-116834": pr_116834,
    "PR-116846": pr_116846,
    "LOCAL-combination": local_combination,  # hypothetical, not upstream
}


def _atomic_json_write(path: Path, record: dict[str, Any]) -> None:
    """Lab substitute for utils.atomic_json_write; exact record fields reproduced."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


@contextmanager
def _hermes_stubs(home: Path, *, unattended: bool = True):
    """Inject only external dependencies needed to execute real gate excerpts."""
    tools = types.ModuleType('tools')
    tools.__path__ = []
    wa = types.ModuleType('tools.write_approval')
    wa.MEMORY = 'memory'
    wa.current_origin = lambda: 'background_review' if unattended else 'foreground'

    def stage_write(subsystem: str, payload: dict[str, Any], *, summary: str, origin: str) -> dict[str, Any]:
        # Source-equivalent of NousResearch/hermes-agent tools/write_approval.py::stage_write
        pid = uuid.uuid4().hex[:8]
        record = {
            'id': pid, 'subsystem': subsystem, 'action': payload.get('action', ''),
            'summary': (summary or '').strip(), 'origin': origin or 'foreground',
            'created_at': time.time(), 'payload': payload,
        }
        try:
            _atomic_json_write(home / 'pending' / subsystem / f'{pid}.json', record)
        except Exception:
            logger.exception('Failed to stage pending write')
        return record

    wa.stage_write = stage_write
    provenance = types.ModuleType('tools.skill_provenance')
    provenance.is_unattended_review = lambda: unattended
    tools.write_approval = wa
    tools.skill_provenance = provenance
    old = {k: sys.modules.get(k) for k in ('tools', 'tools.write_approval', 'tools.skill_provenance')}
    sys.modules['tools'] = tools
    sys.modules['tools.write_approval'] = wa
    sys.modules['tools.skill_provenance'] = provenance
    try:
        yield
    finally:
        for key, previous in old.items():
            if previous is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = previous


def _batch_op_line(op: dict[str, Any]) -> str:
    op = op or {}
    act, content, old = op.get('action', '?'), op.get('content') or op.get('new_text') or '', op.get('old_text', '')
    if act == 'remove':
        return f'- remove: {old}'
    if act == 'patch':
        return f"- patch span '{old}' -> '{content}' (rest of the entry is kept)"
    return f'- {act}: {content}'


def _tool_error(message: str, *, success: bool = False) -> str:
    return json.dumps({'success':success,'error':message},ensure_ascii=False)


@dataclass
class RunRow:
    version: str
    case: str
    target: str
    prohibited_by_source: bool
    gate_result: str
    memory_marker_found: bool
    user_marker_found: bool
    pending_marker_found: bool
    pending_summary_marker_found: bool
    pending_payload_marker_found: bool
    never_save_invariant: str


def run_case(version: str, case: str, target: str, *,
             attended: bool = False, source_consent_guard: bool = False) -> RunRow:
    if case.startswith('batch_'):
        key = case.split('batch_', 1)[1]
        content, prohibited = EXAMPLES[key]
        operations = [
            {'action': 'add', 'content': 'Routine note: lab fixtures are disposable'},
            {'action': 'add', 'content': content},
        ]
    else:
        content, prohibited = EXAMPLES[case]
        operations = None

    with tempfile.TemporaryDirectory(prefix='hermes-consent-lab-') as folder:
        home = Path(folder)
        with _hermes_stubs(home, unattended=not attended):
            # Optional designed control: the source says this fact must not be retained.
            # This flag is supplied by a trusted, ephemeral source rule, not guessed
            # from candidate prose. No payload is staged when it applies.
            if source_consent_guard and prohibited:
                result = 'deny'
            else:
                variant = VERSIONS[version]
                variant._batch_op_line = _batch_op_line
                variant._pin_matched_entries = lambda _store, _payload: None  # adds do not need pinning
                variant.logger = logger
                variant.tool_error = _tool_error
                reply = variant._background_delete_gate(None, 'add' if operations is None else None,
                                                       operations, target, content if operations is None else None)
                result = 'stage' if reply and json.loads(reply).get('staged') else ('deny' if reply else 'apply')

            if result == 'apply':
                # Add-only write that Hermes dispatches after `_background_delete_gate`
                # returns None (with write_approval off, the default).
                entries = [op['content'] for op in operations] if operations is not None else [content]
                target_file = home / ('USER.md' if target == 'user' else 'MEMORY.md')
                target_file.write_text('\n§\n'.join(entries), encoding='utf-8')

            paths = {str(p.relative_to(home)):p.read_text(encoding='utf-8') for p in home.rglob('*') if p.is_file()}
            stored = paths.get('MEMORY.md','')
            profile = paths.get('USER.md','')
            pending = [(k,v) for k,v in paths.items() if k.startswith('pending/') and k.endswith('.json')]
            pending_summary = any(MARKER in json.loads(v).get('summary','') for _,v in pending)
            pending_payload = any(MARKER in json.dumps(json.loads(v).get('payload',{})) for _,v in pending)
            memory_hit = MARKER in stored
            user_hit = MARKER in profile
            pending_hit = any(MARKER in v for _,v in pending)
            # Opted-out data must not survive in any persistent destination,
            # including the supposedly uncommitted approval queue.
            safe = not (memory_hit or user_hit or pending_hit)
            return RunRow(
                version=version, case=case, target=target, prohibited_by_source=prohibited,
                gate_result=result, memory_marker_found=memory_hit, user_marker_found=user_hit,
                pending_marker_found=pending_hit, pending_summary_marker_found=pending_summary,
                pending_payload_marker_found=pending_payload,
                never_save_invariant=('PASS' if safe else 'FAIL') if prohibited else 'N/A',
            )


def all_rows() -> list[RunRow]:
    rows = []
    for version in VERSIONS:
        for case in ('self_report','bare_fact','alt_wording','indirect_refusal'):
            for target in ('user','memory'):
                rows.append(run_case(version,case,target))
        for case in ('batch_self_report','batch_bare_fact'):
            for target in ('user','memory'):
                rows.append(run_case(version,case,target))
        rows.append(run_case(version,'routine_operational','memory'))
        rows.append(run_case(version,'consensual_profile','user'))
    return rows


def save_results(path: Path) -> list[RunRow]:
    rows = all_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f,fieldnames=list(asdict(rows[0]).keys()))
        wr.writeheader()
        for row in rows:
            wr.writerow(asdict(row))
    return rows


if __name__ == '__main__':
    path = Path(__file__).parent/'results.csv'
    rows = save_results(path)
    for version in VERSIONS:
        selected=[r for r in rows if r.version==version]
        blocked=[r for r in selected if r.prohibited_by_source]
        from collections import Counter
        print(version,'opted-out scenarios',len(blocked),
              'still persisted',sum(r.never_save_invariant=='FAIL' for r in blocked),
              'outcomes',dict(Counter(r.gate_result for r in blocked)),
              'pending',sum(r.pending_marker_found for r in blocked))
    print('results',path)
