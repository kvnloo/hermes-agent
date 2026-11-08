"""Bundled platform manifest read failure must not waive OAuth ownership (#151208)."""

from hermes_cli import config, plugin_oauth


def test_corrupt_bundled_manifest_does_not_relax_oauth_env_guard(tmp_path, monkeypatch):
    bundled = tmp_path / "plugins" / "platforms" / "demo"
    bundled.mkdir(parents=True)
    manifest_path = bundled / "plugin.yaml"
    monkeypatch.setattr(config, "get_project_root", lambda: tmp_path)

    env_name = "BUNDLED_DEMO_CLIENT_SECRET"
    manifest = {"oauth": [{
        "id": "rooms",
        "authorize_url": "https://login.example.com/authorize",
        "token_url": "https://login.example.com/token",
        "scopes": ["read"],
        "client_id_env": "OWN_OAUTH_CLIENT_ID",
        "client_secret_env": env_name,
        "hosts": ["api.example.com"],
    }]}

    # A readable bundled declaration protects its env name.
    manifest_path.write_text(
        f"name: demo\nkind: platform\nrequires_env:\n  - {env_name}\n",
        encoding="utf-8",
    )
    clients, problems = plugin_oauth.parse_oauth_clients(manifest)
    assert not clients
    assert any(env_name in problem for problem in problems)

    # A malformed bundled declaration is skipped, even with strict=True.
    # Missing metadata must never turn that same env name into an owned client secret.
    manifest_path.write_text("kind: [\n", encoding="utf-8")
    clients, problems = plugin_oauth.parse_oauth_clients(manifest)
    assert not clients
    assert any(env_name in problem for problem in problems)
