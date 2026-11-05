"""A fallback pick keeps its configured identity even when the route URL is absent.

Regression for NousResearch/hermes-agent#149320, complementing NaimioChan's #149324.
"""

from unittest.mock import patch

import hermes_yaml as yaml


def test_named_list_provider_stays_routable_without_snapshot_base_url(tmp_path, monkeypatch):
    from agent.auxiliary_client import resolve_provider_client
    from hermes_cli.fallback_cmd import _extract_fallback_from_model_cfg
    from hermes_cli.model_setup_flows_custom import _model_flow_named_custom

    home = tmp_path / "hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / ".env").write_text("", encoding="utf-8")
    config_path = home / "config.yaml"
    config_path.write_text(
        "model:\n"
        "  provider: custom\n"
        "  default: primary-model\n"
        "  base_url: https://primary.example/v1\n"
        "  api_key: sk-primary\n"
        "custom_providers:\n"
        "  - name: Named Endpoint\n"
        "    base_url: https://secondary.example/v1\n"
        "    api_key: sk-secondary\n"
        "    model: secondary-model\n"
        "    discover_models: false\n"
        "    models: [secondary-model]\n",
        encoding="utf-8",
    )
    provider_info = {
        "name": "Named Endpoint",
        "base_url": "https://secondary.example/v1",
        "api_key": "sk-secondary",
        "model": "secondary-model",
        "discover_models": False,
        "models": ["secondary-model"],
    }

    with patch(
        "hermes_cli.model_setup_flows_custom._pick_named_custom_model",
        return_value="secondary-model",
    ):
        _model_flow_named_custom({}, provider_info)

    # Model picker snapshots need not carry base_url; the selected provider
    # must be sufficient to resolve the endpoint after the primary is restored.
    picked = yaml.safe_load(config_path.read_text(encoding="utf-8"))["model"]
    picked.pop("base_url", None)
    fallback = _extract_fallback_from_model_cfg(picked)
    assert fallback is not None
    assert fallback["provider"] == "custom:named-endpoint"
    assert "base_url" not in fallback

    client, _ = resolve_provider_client(
        fallback["provider"], model=fallback["model"], raw_codex=True,
        explicit_base_url=None, explicit_api_key=None,
    )
    assert str(client.base_url).rstrip("/") == "https://secondary.example/v1"
    assert str(client.api_key) == "sk-secondary"
