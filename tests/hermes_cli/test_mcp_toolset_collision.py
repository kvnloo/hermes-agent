"""MCP server/toolset name collisions (dandomin report; original fix by jlxq0, #137882)."""

import json
from types import SimpleNamespace

import pytest

from hermes_cli import tools_config
from model_tools import _select_tool_names
from tools.registry import ToolRegistry

HA = "mcp__homeassistant__GetLiveContext"
GH = "mcp__github__search"
CFG = {"mcp_servers": {"homeassistant": {"url": "http://ha"}, "github": {"command": "gh"}}}


@pytest.fixture(autouse=True)
def collision_registry(monkeypatch):
    reg = ToolRegistry()
    for name, group in (("ha_get_state", "homeassistant"), (HA, "mcp-homeassistant"), (GH, "mcp-github")):
        reg.register(
            name=name, toolset=group,
            schema={"name": name, "description": name, "parameters": {"type": "object", "properties": {}}},
            handler=lambda args, **kw: "{}",
        )
    reg.register_toolset_alias("homeassistant", "mcp-homeassistant")
    reg.register_toolset_alias("github", "mcp-github")
    monkeypatch.setattr("tools.registry.registry", reg)
    monkeypatch.setattr(tools_config, "_get_plugin_toolset_keys", lambda: {"homeassistant"})
    monkeypatch.setattr(tools_config, "_settled_plugin_toolset_keys", lambda: {"homeassistant"}, raising=False)
    monkeypatch.setattr("hermes_cli.plugins.get_portable_mcp_server_names_nowait", lambda: set())
    return reg


def selected(names):
    return _select_tool_names(sorted(names), None, True)


@pytest.mark.parametrize("requested,present,absent", [
    (["hermes-cli"], {HA, GH, "ha_get_state"}, set()),
    (["hermes-cli", "no_mcp"], {"ha_get_state"}, {HA, GH}),
    (["hermes-cli", "github"], {"ha_get_state", GH}, {HA}),
])
def test_plugin_collision_preserves_mcp_selection_and_allowlist(requested, present, absent):
    cfg = {**CFG, "platform_toolsets": {"cli": requested}}
    names = tools_config._get_platform_tools(cfg, "cli")
    tools = selected(names)
    assert present <= tools
    assert not absent & tools


def test_static_collision_adds_server_not_builtin_web(collision_registry):
    from toolsets import resolve_toolset

    collision_registry.register(
        name="mcp__web__fetch", toolset="mcp-web",
        schema={"name": "mcp__web__fetch", "description": "fetch", "parameters": {"type": "object"}},
        handler=lambda args, **kw: "{}",
    )
    cfg = {"mcp_servers": {"web": {"command": "w"}}, "platform_toolsets": {"cli": ["file"]}}
    names = tools_config._get_platform_tools(cfg, "cli")
    tools = selected(names)
    assert "mcp-web" in names and "web" not in names
    assert "mcp__web__fetch" in tools
    native_web = set(resolve_toolset("web", include_registry=False)) - set(resolve_toolset("file", include_registry=False))
    assert not native_web & tools


def test_disabling_plugin_name_also_removes_server_tool():
    cfg = {**CFG, "agent": {"disabled_toolsets": ["homeassistant"]}}
    names = tools_config._get_platform_tools(cfg, "cli")
    assert "mcp-homeassistant" not in names
    assert HA not in _select_tool_names(["homeassistant", "mcp-homeassistant"], ["homeassistant"], True)


def test_cron_allowlist_and_late_connection_keep_mcp_key():
    from agent.inline_tool_executors import _scope_in_connected_mcp_servers
    from cron.scheduler import _merge_mcp_into_per_job_toolsets

    assert HA in selected(_merge_mcp_into_per_job_toolsets(["web", "homeassistant"], CFG))
    assert GH not in selected(_merge_mcp_into_per_job_toolsets(["web", "homeassistant"], CFG))
    agent = SimpleNamespace(enabled_toolsets=["file", "homeassistant"])
    _scope_in_connected_mcp_servers(agent, json.dumps({"targets": [
        {"kind": "mcp", "name": "homeassistant", "state": "connected", "tools": ["GetLiveContext"]}
    ]}))
    assert HA in selected(agent.enabled_toolsets)
