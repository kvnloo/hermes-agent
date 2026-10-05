"""Plugin discovery must feed the live command inventory requested in #113700."""

import json
import socket
import sys


def test_commands_json_includes_discovered_plugin(tmp_path, monkeypatch, capsys):
    home = tmp_path / "hermes"
    plugin = home / "plugins" / "inventory_fixture"
    plugin.mkdir(parents=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [inventory_fixture]\n", encoding="utf-8"
    )
    (plugin / "plugin.yaml").write_text(
        "name: inventory_fixture\nversion: 1.0.0\n", encoding="utf-8"
    )
    (plugin / "__init__.py").write_text(
        'def register(ctx):\n'
        '    def setup(parser):\n'
        '        parser.add_subparsers(dest="fixture_action").add_parser(\n'
        '            "inspect", help="Inspect the synthetic fixture")\n'
        '    ctx.register_cli_command("fixture_inventory", '
        '"Synthetic inventory plugin", setup)\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HOME", str(tmp_path / "os-home"))
    monkeypatch.delenv("HERMES_ENABLE_PROJECT_PLUGINS", raising=False)
    monkeypatch.setattr(sys, "argv", ["hermes", "commands", "--json"])

    network_attempts = []

    def deny_network(*args, **kwargs):
        network_attempts.append(args[1:])
        raise AssertionError("The command inventory must remain local")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_network)
    from hermes_cli import main, plugins
    from plugins import memory

    # Limit discovery inputs to the authored plugin; its enable/load/register path is real.
    monkeypatch.setattr(plugins, "get_bundled_plugins_dir", lambda: tmp_path / "empty-bundled")
    monkeypatch.setattr(plugins.importlib.metadata, "entry_points", lambda: [])
    monkeypatch.setattr(memory, "discover_plugin_cli_commands", lambda: [])
    manager = plugins.get_plugin_manager()
    try:
        parser, subparsers = main._build_cli_parser()
        args = main._parse_cli_args(parser, subparsers, sys.argv[1:])
        args.func(args)

        assert network_attempts == []
        inventory = json.loads(capsys.readouterr().out)
        [discovered] = [
            node for node in inventory["subcommands"] if node["name"] == "fixture_inventory"
        ]
        assert discovered["help"] == "Synthetic inventory plugin"
        assert [node["name"] for node in discovered["subcommands"]] == ["inspect"]
    finally:
        manager.unload()
