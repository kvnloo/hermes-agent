"""Read-only native operational reports against real isolated profile configs (#579)."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import hermes_yaml as yaml

from tui_gateway import server


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    from agent.secret_scope import set_multiplex_context, reset_multiplex_context
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    root = tmp_path / ".hermes"
    homes = {name: root / "profiles" / name for name in ("work", "other")}
    root.mkdir()
    (root / "config.yaml").write_text("{}\n")
    for name, home in homes.items():
        home.mkdir(parents=True)
        (home / ".env").write_text("")
        (home / "config.yaml").write_text(yaml.safe_dump({
            "terminal": {"backend": "ssh", "ssh_host": f"{name}.example", "ssh_user": name,
                         "ssh_port": 2222, "ssh_key": f"/private/{name}-key"},
            "mcp_servers": {f"{name}-svc": {"url": "https://user:inert-password@example.test/mcp?token=inert-query",
                "headers": {"Authorization": "Bearer inert-header"}, "env": {"KEY": "inert-env"},
                "command": "inert-command", "args": ["--token", "inert-arg"]}}
        }))
    monkeypatch.setenv("HERMES_HOME", str(root))
    monkeypatch.setattr(server, "_hermes_home", root)
    for key in ("_cfg_cache", "_cfg_sig", "_cfg_path"):
        monkeypatch.setattr(server, key, None)
    transport = SimpleNamespace(write=lambda frame: True)
    owners = {name: {"session_key": name, "profile_home": str(home), "transport": transport, "agent": None}
              for name, home in homes.items()}
    monkeypatch.setattr(server, "_sessions", owners)
    # Fail if any read accidentally probes/starts a server or rebuilds an agent.
    connect = Mock(side_effect=AssertionError("Read-only reports must not connect"))
    monkeypatch.setattr("tools.mcp_tool_discovery._connect_server", connect)
    monkeypatch.setattr(server, "_make_agent", Mock(side_effect=AssertionError("No agent rebuild")))
    token = set_multiplex_context(True)

    def rpc(view="mcp-list", sid="work", via=transport, **extra):
        bound = server.bind_transport(via)
        try:
            return server.handle_request({"id": 1, "method": "operations.report",
                                          "params": {"session_id": sid, "view": view, **extra}})
        finally:
            server.reset_transport(bound)

    yield rpc, homes, owners, connect
    reset_multiplex_context(token)


def seed(home, config):
    (home / "config.yaml").write_text(yaml.safe_dump(config))


def test_config_list_is_session_profile_owned_and_auth_details_are_secret_free(runtime):
    rpc, homes, _, connect = runtime
    before = {home: ((home / "config.yaml").read_bytes(), (home / ".env").read_bytes()) for home in homes.values()}
    for profile in homes:
        result = rpc(sid=profile)["result"]
        assert result["scope"] == profile
        assert result["read_only"] is True and result["state"] == "ready"
        assert [row["name"] for row in result["rows"]] == [f"{profile}-svc"]
        encoded = json.dumps(result)
        for secret in ("inert-password", "inert-query", "inert-header", "inert-env", "inert-command", "inert-arg", "/private/"):
            assert secret not in encoded
        assert "Headers configured" in encoded
    assert before == {home: ((home / "config.yaml").read_bytes(), (home / ".env").read_bytes()) for home in homes.values()}
    connect.assert_not_called()


def test_status_and_tool_names_are_cached_exact_profile_snapshots_not_probes(runtime, monkeypatch):
    rpc, homes, _, connect = runtime
    from tools import mcp_tool as core
    # Equal server names in two profiles exercise the connection-ledger ownership fence.
    for home in homes.values():
        seed(home, {"mcp_servers": {"same": {"command": "fixture"}}})
    keys = {name: (str(home.resolve()), "same") for name, home in homes.items()}
    servers = {key: SimpleNamespace(session=object(), _registered_tool_names=[f"mcp_same_{name}_read"], _sampling=None)
               for name, key in keys.items()}
    monkeypatch.setattr(core, "_servers", servers)
    monkeypatch.setattr(core, "_server_tool_scopes", {key: {key[0]} for key in keys.values()})
    for name in homes:
        row = rpc("mcp-status", sid=name)["result"]["rows"][0]
        assert row == {"name": "same", "details": ["connected", "1 cached tools"]}
        row = rpc("mcp-tools", sid=name)["result"]["rows"][0]
        assert row["details"] == [f"mcp_same_{name}_read"]
    connect.assert_not_called()


def test_empty_mcp_and_ssh_are_real_empty_inventories_not_unavailable(runtime):
    rpc, homes, _, connect = runtime
    seed(homes["work"], {"terminal": {"backend": "local"}, "mcp_servers": {}})
    for view in ("mcp-list", "mcp-status", "mcp-tools", "ssh-list"):
        result = rpc(view)["result"]
        assert result["state"] == "ready" and result["rows"] == []
    connect.assert_not_called()


def test_ssh_reads_only_hermes_terminal_target_without_identity_path_or_claimed_connection(runtime):
    rpc, _, _, connect = runtime
    result = rpc("ssh-list")["result"]
    assert result["rows"] == [{"name": "work.example", "details": ["User: work", "Port: 2222",
                               "Identity configured (path withheld)", "Active SSH backend", "Connection not probed"]}]
    assert "unsupported" in result["message"] and "OpenSSH/OMP" in result["message"]
    assert "/private/" not in json.dumps(result)
    connect.assert_not_called()


def test_service_failure_and_invalid_ssh_target_are_unavailable_and_never_echo_secrets(runtime, monkeypatch):
    rpc, homes, _, _ = runtime
    monkeypatch.setattr(server, "_mcp_server_rows", Mock(side_effect=RuntimeError("Bearer inert-secret-error")))
    result = rpc()["result"]
    assert result["state"] == "unavailable" and result["rows"] == []
    assert "inert-secret" not in json.dumps(result)
    for bad in ("user:inert-password@host", "host --proxy-command=bad"):
        seed(homes["work"], {"terminal": {"backend": "ssh", "ssh_host": bad}})
        result = rpc("ssh-list")["result"]
        assert result["state"] == "unavailable" and result["rows"] == []
        assert bad not in json.dumps(result)


def test_every_server_is_retained_in_long_inventory_and_catalog_uses_hermes_catalog(runtime):
    rpc, homes, _, connect = runtime
    seed(homes["work"], {"mcp_servers": {f"server-{i:03}": {"command": "fixture"} for i in range(237)}})
    result = rpc()["result"]
    assert len(result["rows"]) == 237
    assert result["rows"][0]["name"] == "server-000" and result["rows"][-1]["name"] == "server-236"
    from hermes_cli import mcp_catalog
    expected = [entry.name for entry in mcp_catalog.list_catalog()]
    assert [row["name"] for row in rpc("mcp-catalog")["result"]["rows"]] == expected
    connect.assert_not_called()


def test_mutations_profile_override_unknown_session_and_foreign_transport_are_rejected(runtime):
    rpc, _, owners, connect = runtime
    assert rpc("mcp-remove")["error"]["code"] == 4000
    assert rpc(profile="other")["error"]["code"] == 4000
    assert rpc(sid="stale")["error"]["code"] == 4001
    assert rpc(via=SimpleNamespace(write=lambda frame: True))["error"]["code"] == 4001
    owners["work"]["_finalized"] = True
    assert rpc()["error"]["code"] == 4001
    connect.assert_not_called()


def test_lazy_tool_inventory_does_not_wake_a_server(runtime, monkeypatch):
    rpc, homes, _, connect = runtime
    from tools import mcp_tool as core
    seed(homes["work"], {"mcp_servers": {"lazy": {"command": "fixture", "lazy": True}}})
    key = (str(homes["work"].resolve()), "lazy")
    monkeypatch.setattr(core, "_servers", {})
    monkeypatch.setattr(core, "_lazy_server_configs", {key: {"command": "fixture"}})
    monkeypatch.setattr(core, "_lazy_server_tool_names", {key: ["mcp_lazy_read"]})
    assert rpc("mcp-status")["result"]["rows"][0]["details"] == ["lazy", "1 cached tools"]
    assert rpc("mcp-tools")["result"]["rows"][0]["details"] == ["mcp_lazy_read"]
    connect.assert_not_called()


def test_profile_change_on_same_live_record_discards_snapshot(runtime, monkeypatch):
    rpc, homes, owners, _ = runtime
    def move(view):
        owners["work"]["profile_home"] = str(homes["other"])
        return [{"name": "must-not-escape", "details": []}]
    monkeypatch.setattr(server, "_OPERATIONS_READERS", {"mcp-list": move})
    result = rpc()
    assert result["error"]["code"] == 4001
    assert "must-not-escape" not in json.dumps(result)


def test_session_replacement_during_read_discards_result(runtime, monkeypatch):
    rpc, _, owners, _ = runtime
    def replace(view):
        owners["work"] = dict(owners["work"])
        return [{"name": "must-not-escape", "details": []}]
    monkeypatch.setattr(server, "_OPERATIONS_READERS", {"mcp-list": replace})
    result = rpc()
    assert result["error"]["code"] == 4001
    assert "must-not-escape" not in json.dumps(result)
