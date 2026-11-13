"""Consumer qualification against native discovery and actual staged workflows.

Use stage_tests.py to stage the named read-only sources for the canonical runner.
"""
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent


def load_contract():
    name = "continuity_contract_test"
    spec = importlib.util.spec_from_file_location(name, ROOT / "contract.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_all_shared_contract_branches():
    c = load_contract()
    c.verify_source(str(ROOT / "fixtures" / "contract.bend"))
    cases = [
        (c.Goal.Paused, c.Decision.RespectPause),
        (c.Goal.Stopped, c.Decision.RespectStop),
        (c.Goal.Complete, c.Decision.Finish),
        (c.Active(c.Receipts.Missing), c.Decision.LoadWorkflow),
        (c.Active(c.Loaded(c.Next.AuthorizedWork)), c.Decision.Execute),
        (c.Active(c.Loaded(c.Next.ExhaustedPlan)), c.Decision.Replan),
        (c.Active(c.Loaded(c.ExternalDependency(c.Wake.Unregistered))), c.Decision.Replan),
        (c.Active(c.Loaded(c.ExternalDependency(c.Registered(37)))), c.Wait(37)),
    ]
    for state, expected in cases:
        assert c.decide(state) == expected


def test_hash_mismatch_is_rejected(tmp_path):
    path = tmp_path / "contract.bend"
    path.write_text("wrong contract")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_contract().verify_source(str(path))


def test_fresh_discovery_arm_reload_and_profile_isolation(tmp_path):
    home = tmp_path / "one"
    plugin = home / "plugins" / "goal-continuity"
    plugin.mkdir(parents=True)
    for name in ("__init__.py", "contract.py", "plugin.yaml"):
        shutil.copyfile(ROOT / name, plugin / name)
    shutil.copytree(ROOT / "fixtures" / "skills", home / "skills")
    contract = ROOT / "fixtures" / "contract.bend"
    command = f"{shlex.quote(sys.executable)} -c 'print(\"real acceptance check\")'"
    config = {"plugins": {"enabled": ["goal-continuity"], "entries": {"goal-continuity": {"settings": {
        "allow_arm": True, "contract_path": str(contract),
        "missions": {"demo": {"goal": "Original acceptance goal", "max_turns": 4,
                              "gates": [{"command": command}]}}}}}}}
    (home / "config.yaml").write_text(json.dumps(config))
    script = '''
import json
from pathlib import Path
from unittest.mock import patch
from gateway.session_context import scoped_current_session_id
from hermes_cli.plugins import discover_plugins, get_plugin_manager
from hermes_cli.goals import GoalManager
from tools.registry import registry

discover_plugins()
pm = get_plugin_manager()
assert "goal-continuity" in pm._goal_policies, [(p.manifest.name, p.error) for p in pm._plugins.values()]
entry = registry.get_entry("goal_continuity_arm")
assert entry is not None
with scoped_current_session_id("demo-session"):
    result = json.loads(entry.handler({"mission": "demo"}))
assert result["armed"], result
assert "Poteto mode" in result["workflow"]
assert "Feature" in result["workflow"]
assert "Model the Domain" in result["workflow"]
mgr = GoalManager("demo-session")
assert mgr.state.policy == "goal-continuity"
with patch("hermes_cli.goals.judge_goal", return_value=("blocked", "plan exhausted", False, None, False)):
    decision = mgr.evaluate_after_turn("I am blocked")
assert decision["should_continue"], decision
assert decision["verdict"] == "replan"
assert "Original acceptance goal" in decision["continuation_prompt"]
assert GoalManager("demo-session").state.turns_used == 1
with scoped_current_session_id("demo-session"):
    refused = json.loads(entry.handler({"mission": "demo"}))
assert not refused["armed"]
print(json.dumps({"armed": True, "workflow_loaded": True, "replan": True, "reloaded_turns": 1}))
'''
    env = {**os.environ, "HERMES_HOME": str(home), "HERMES_SKILLS_DIR": str(home / "skills")}
    run = subprocess.run([sys.executable, "-c", script], env=env, text=True, capture_output=True, timeout=90)
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(run.stdout.splitlines()[-1])["replan"]
    other = tmp_path / "two"
    other.mkdir()
    env["HERMES_HOME"] = str(other)
    env.pop("HERMES_SKILLS_DIR")
    run = subprocess.run([sys.executable, "-c", '''
from hermes_cli.plugins import discover_plugins, get_plugin_manager
from hermes_cli.goals import load_goal
discover_plugins()
assert "goal-continuity" not in get_plugin_manager()._goal_policies
assert load_goal("demo-session") is None
'''], env=env, text=True, capture_output=True, timeout=90)
    assert run.returncode == 0, run.stdout + run.stderr
