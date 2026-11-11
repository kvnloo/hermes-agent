"""A claimed kanban run must finish through its configured fallback after HTTP 429."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from tests.gateway.fixtures.local_recovery_probe import child_env


@pytest.mark.parametrize('mode', ['rate_limit', 'billing'])
def test_429_continues_claimed_run_on_fallback(tmp_path, mode):
    repo = Path(__file__).resolve().parents[2]
    env = child_env()
    env.update(HOME=str(tmp_path / 'home'), USERPROFILE=str(tmp_path / 'home'),
               HERMES_HOME=str(tmp_path / 'state'), PYTHONPATH=str(repo),
               KANBAN_PROBE_MODE=mode, KANBAN_PROBE_FALLBACK='1')
    result = subprocess.run(
        [sys.executable, str(repo / 'tests/gateway/fixtures/kanban_owner_probe.py')],
        env=env, cwd=repo, stdin=subprocess.DEVNULL, capture_output=True,
        text=True, timeout=150, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads((tmp_path / 'state/receipt.json').read_text())
    print(json.dumps(receipt, sort_keys=True))
    assert receipt['client_exit'] == ['clean_exit', 0], receipt
    assert receipt['task_status'] == 'done' and receipt['run_outcome'] == 'completed', receipt
    assert receipt['failures'] == 0 and receipt['admissions'] == 1, receipt
    assert receipt['primary_requests'] >= 1 and set(receipt['primary_statuses']) == {429}, receipt
    assert receipt['fallback_models'] == ['fallback-model'], receipt
    assert receipt['tools'] and receipt['task_context'] and receipt['skill_context'], receipt
    assert receipt['hook_effect'] and receipt['goal_continuation'], receipt
