import importlib.util
from pathlib import Path

import pytest

_P = Path(__file__).resolve().parents[2] / "plugins" / "wait-once-guard" / "__init__.py"
_spec = importlib.util.spec_from_file_location("wait_once_guard", _P)
assert _spec and _spec.loader
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))


@pytest.mark.parametrize("cmd", [
    "sleep 400; tail -1 wait.log",
    "sleep 240; grep -v notice r1.err",
    "for i in $(seq 16); do gh pr checks 3; sleep 30; done",
    "./start.sh & sleep 35; curl localhost:8080",
    "sleep 2m",
    "sleep 5 5 5",
    "python3 -c 'import time; time.sleep(60)'",
])
def test_blocks_long_foreground_sleep(cmd):
    r = G.check(tool_name="terminal", args={"command": cmd}, session_id="s")
    assert r and r["action"] == "block" and "background=true" in r["message"]


@pytest.mark.parametrize("cmd", [
    "sleep 3; adb shell input tap 1 2",
    "timeout 300 bash -c 'until curl -sf x; do sleep 5; done'",
    "sleep 10",
    "sleep 0.5",
    "echo nosleep 99",
    "grep -c 'sleep' log.txt",
    "sleep $N",
])
def test_allows_short_or_unparsed(cmd):
    assert G.check(tool_name="terminal", args={"command": cmd}) is None


def test_background_and_other_tools_pass():
    assert G.check(tool_name="terminal", args={"command": "sleep 600", "background": True}) is None
    assert G.check(tool_name="execute_code", args={"code": "sleep 600"}) is None


def test_block_is_logged_without_command(tmp_path):
    G.check(tool_name="terminal", args={"command": "sleep 99; cat secret"}, session_id="s1")
    line = (tmp_path / "wait-once-guard" / "decisions.jsonl").read_text()
    assert '"sleep_s": 99.0' in line and "secret" not in line
