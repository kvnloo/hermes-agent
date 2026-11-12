"""Exercise discovery, real file I/O, registry dispatch, and the transform hook."""

import json
import os
import shutil
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]


@pytest.fixture
def real_read(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    bundled = tmp_path / "empty-bundled"
    bundled.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(bundled))
    for name in ("MAX_CHARS", "HEAD", "TAIL", "DEDUPE_HEAD", "OFF", "OWNER_PATHS"):
        monkeypatch.delenv("Z21_TRIM_" + name, raising=False)
    source = Path(os.environ.get("HZ21_TEST_PLUGIN_SOURCE", str(PLUGIN)))
    shutil.copytree(source, home / "plugins" / "tool-context-trim",
                    ignore=shutil.ignore_patterns("__pycache__", "tests"))
    (home / "config.yaml").write_text('plugins:\n  enabled: [tool-context-trim]\n', encoding="utf-8")

    import model_tools
    from hermes_cli import plugins
    from tools import file_tools
    from tools.environments.local import LocalEnvironment
    from tools.file_operations import ShellFileOperations
    from tools.registry import registry

    plugins._reset_plugin_managers_for_tests()
    plugins.discover_plugins()
    manager = plugins.get_plugin_manager()
    [loaded] = [p for p in manager.list_plugins() if p["name"] == "tool-context-trim"]
    assert loaded["enabled"] and not loaded.get("error"), loaded
    assert plugins.has_hook("transform_tool_result")

    public = tmp_path / "example.txt"
    public.write_text(("abcdefghij" * 7 + "\n") * 425, encoding="utf-8")
    ops = ShellFileOperations(LocalEnvironment(str(tmp_path)))
    monkeypatch.setattr(file_tools, "_get_file_ops", lambda task_id: ops)
    args = {"path": str(public), "limit": 2000}
    raw = registry.dispatch("read_file", args, task_id="hz21-raw")
    parsed = json.loads(raw)
    assert not parsed.get("error"), parsed
    assert 32_000 <= len(raw) <= 40_000, len(raw)
    transformed = model_tools.handle_function_call(
        "read_file", args, task_id="hz21-dispatch", session_id="hz21-dispatch",
        tool_call_id="hz21-call", skip_pre_tool_call_hook=True)
    print(f"real read_file: chars={len(raw)} keys={sorted(parsed)} result_chars={len(transformed)}")
    try:
        yield raw, transformed, plugins, args
    finally:
        plugins._reset_plugin_managers_for_tests()


def test_real_metadata_bearing_read_stays_exact(real_read):
    raw, transformed, _plugins, _args = real_read
    assert transformed == raw
    assert "[z21 tool-output trim" not in transformed


def test_real_read_content_single_key_projection_is_capped(real_read):
    """Projection is explicit: the actual metadata-bearing payload above is NOT trimmed."""
    raw, _transformed, plugins, args = real_read
    projected = json.dumps({"content": json.loads(raw)["content"]})
    results = plugins.invoke_hook(
        "transform_tool_result", tool_name="read_file", args=args,
        result=projected, session_id="hz21-projected", task_id="hz21-projected")
    [out] = [value for value in results if isinstance(value, str)]
    inner = json.loads(out)["content"]
    assert inner.find("[z21 tool-output trim") == 2402
    assert len(out) < 4200
    print(f"single-key projection: input={len(projected)} output={len(out)} marker={inner.find('[z21 tool-output trim')}")
