"""Regression for NousResearch/hermes-agent#152152: one root gateway per container."""

import json

import pytest

from hermes_cli.container_boot import reconcile_profile_gateways


@pytest.mark.parametrize(
    ("argv", "no_supervise_env", "expected"),
    [
        (["main-wrapper.sh", "gateway", "run", "--no-supervise"], False, "registered"),
        (["main-wrapper.sh", "gateway", "run"], True, "registered"),
        (["main-wrapper.sh", "gateway", "run"], False, "started"),
        (["main-wrapper.sh", "gateway", "run", "--no-supervise"], True, "registered"),
    ],
)
def test_foreground_run_does_not_autostart_s6_gateway(
    tmp_path, monkeypatch, argv, no_supervise_env, expected
):
    (tmp_path / "gateway_state.json").write_text(
        json.dumps({"gateway_state": "running", "desired_state": "running"}),
        encoding="utf-8",
    )
    if no_supervise_env:
        monkeypatch.setenv("HERMES_GATEWAY_NO_SUPERVISE", "1")
    else:
        monkeypatch.delenv("HERMES_GATEWAY_NO_SUPERVISE", raising=False)

    actions = reconcile_profile_gateways(
        hermes_home=tmp_path,
        scandir=tmp_path / "services",
        dry_run=True,
        container_argv=argv,
    )

    assert actions[0].profile == "default"
    assert actions[0].action == expected
