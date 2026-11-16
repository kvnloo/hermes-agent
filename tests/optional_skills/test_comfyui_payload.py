"""Regression for NousResearch/hermes-agent#156594: submit API nodes, not annotations."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


SKILL_ROOT = (
    Path(__file__).resolve().parents[2] / "optional-skills" / "creative" / "comfyui"
)


def test_bundled_workflows_submit_only_prompt_nodes(monkeypatch):
    """All bundled graphs must survive metadata filtering at the HTTP boundary."""
    scripts_dir = SKILL_ROOT / "scripts"
    monkeypatch.syspath_prepend(str(scripts_dir))
    spec = importlib.util.spec_from_file_location(
        "hermes_comfyui_skill_runner_regression",
        scripts_dir / "run_workflow.py",
    )
    assert spec is not None and spec.loader is not None
    runner_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner_module)

    captured = []

    def fake_post(url, **kwargs):
        assert url.endswith("/prompt")
        captured.append(kwargs["json_body"])
        return SimpleNamespace(status=200, json=lambda: {"prompt_id": "test-prompt"})

    monkeypatch.setattr(runner_module, "http_post", fake_post)
    workflow_paths = sorted((SKILL_ROOT / "workflows").glob("*.json"))
    assert workflow_paths, "ComfyUI skill has no bundled workflows"

    for path in workflow_paths:
        workflow = json.loads(path.read_text(encoding="utf-8"))
        workflow["_comment"] = "annotation, not a node"
        workflow["_metadata"] = {"description": "also not a node"}
        expected_nodes = {
            key: value
            for key, value in workflow.items()
            if isinstance(value, dict) and "class_type" in value
        }
        assert expected_nodes, f"{path.name} has no API nodes"

        runner = runner_module.ComfyRunner(client_id="regression-client")
        assert runner.submit(workflow) == {"prompt_id": "test-prompt"}
        assert captured[-1]["prompt"] == expected_nodes, path.name
        assert captured[-1]["client_id"] == "regression-client"
        assert workflow["_comment"] == "annotation, not a node"
