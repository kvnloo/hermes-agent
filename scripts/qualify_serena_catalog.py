"""Exercise Serena's real MCP initialize/list-tools path on an isolated worker.

This is a catalog/usability smoke check, not semantic task qualification.
"""
import asyncio
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import tempfile
import time


async def run():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    out = Path("serena-smoke")
    out.mkdir(exist_ok=True)
    binary = Path(sys.executable).parent / "serena"
    with tempfile.TemporaryDirectory(prefix="z09-serena-home-") as scratch:
        env = dict(os.environ)
        for key in ["DISPLAY", "WAYLAND_DISPLAY", "SWAYSOCK", "HYPRLAND_INSTANCE_SIGNATURE", "DBUS_SESSION_BUS_ADDRESS"]:
            env.pop(key, None)
        env.update({"HOME": scratch, "XDG_CONFIG_HOME": scratch + "/config", "XDG_CACHE_HOME": scratch + "/cache", "BROWSER": "/bin/false"})
        params = StdioServerParameters(command=str(binary), args=[
            "start-mcp-server", "--transport", "stdio", "--enable-web-dashboard", "false",
            "--open-web-dashboard", "false", "--enable-gui-log-window", "false",
        ], env=env)
        start = time.perf_counter()
        with (out / "server-stderr.log").open("w") as errlog:
            async with asyncio.timeout(60):
                async with stdio_client(params, errlog=errlog) as streams:
                    async with ClientSession(*streams) as session:
                        initialized = await session.initialize()
                        tools = await session.list_tools()
        result = {
            "scope": "Isolated MCP initialize and tools/list only; no semantic task or model call",
            "version": importlib.metadata.version("serena-agent"),
            "initialize": initialized.model_dump(mode="json"),
            "tools": tools.model_dump(mode="json"),
            "wall_ms_initialize_and_catalog": (time.perf_counter() - start) * 1000,
            "production_enabled": False, "provider_usage": None,
        }
        assert tools.tools, "MCP server returned no tools"
        (out / "catalog.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({key: value for key, value in result.items() if key != "tools"}, indent=2))
        print("PASS: initialized real stdio MCP server; listed", len(tools.tools), "tools")


if __name__ == "__main__":
    asyncio.run(run())
