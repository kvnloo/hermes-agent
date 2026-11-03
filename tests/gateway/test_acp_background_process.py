"""An ACP editor viewing a gateway session sees that session's background process run and exit."""
import json
from pathlib import Path
import subprocess
import sys

from tests.gateway.fixtures.local_recovery_probe import child_env


def test_acp_viewer_reports_a_real_background_process_running_then_exited(tmp_path):
    root = Path(__file__).resolve().parents[2]
    home, user = tmp_path / 'state', tmp_path / 'user'
    home.mkdir()
    user.mkdir()
    env = child_env()
    env.update(HOME=str(user), USERPROFILE=str(user), HERMES_HOME=str(home),
               PYTHONPATH=str(root), PYTHONUNBUFFERED='1')
    result = subprocess.run([sys.executable, str(root / 'tests/gateway/fixtures/acp_background_process_peer.py')],
                            cwd=root, env=env, capture_output=True, text=True, timeout=90, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads((home / 'receipt.json').read_text())
    assert receipt['listed_while_running'] == ['running'], receipt
    assert receipt['process_exit_code'] == 3, receipt
    running, exited = receipt['reports']
    assert (running['method'], running['status'], running['toolCallId']) == ('hermes/process', 'running', 'call_1')
    assert (exited['status'], exited['exitCode'], exited['reason']) == ('exited', 3, 'exited'), receipt
    assert exited['processId'] == running['processId']
    assert exited['at_s'] >= 1.5, 'exited is reported after the process ends, not when it starts'
