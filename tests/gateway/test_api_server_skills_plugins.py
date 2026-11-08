"""GET /v1/skills lists plugin skills as well as filesystem skills."""

from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import PlatformConfig
from gateway.platforms.api_server import APIServerAdapter


@pytest.mark.asyncio
async def test_v1_skills_includes_plugin_skill():
    adapter = APIServerAdapter(PlatformConfig(enabled=True, extra={}))
    app = web.Application()
    app["api_server_adapter"] = adapter
    app.router.add_get("/v1/skills", adapter._handle_skills)
    plugin_skill = {
        "name": "example:hello",
        "description": "Plugin-provided skill",
        "category": "plugin",
        "frontmatter": {},
    }
    with patch("hermes_cli.plugins.discover_plugins"), patch(
        "hermes_cli.plugins.get_plugin_manager"
    ) as get_manager:
        get_manager.return_value.list_plugin_skill_metadata.return_value = [plugin_skill]
        async with TestClient(TestServer(app)) as client:
            response = await client.get("/v1/skills")
            assert response.status == 200
            payload = await response.json()

    assert payload["object"] == "list"
    assert {
        "name": "example:hello",
        "description": "Plugin-provided skill",
        "category": "plugin",
    } in payload["data"]
