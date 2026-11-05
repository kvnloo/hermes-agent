"""Regression for NousResearch/hermes-agent#149281: default description stays in the install root."""

from argparse import Namespace
from pathlib import Path

import pytest

from hermes_cli.profile_cmd import _profile_describe
from hermes_cli.profiles import read_profile_meta, write_profile_meta
from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)


@pytest.mark.parametrize("active_via", ("environment", "context"))
def test_describe_default_reads_and_writes_root_not_active_profile(
    tmp_path, monkeypatch, capsys, active_via,
):
    root = tmp_path / ".hermes"
    active = root / "profiles" / "coach"
    active.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(active if active_via == "environment" else root))
    write_profile_meta(root, description="default description")
    write_profile_meta(active, description="coach description")

    token = set_hermes_home_override(active) if active_via == "context" else None
    try:
        assert get_hermes_home() == active

        with pytest.raises(SystemExit) as read_exit:
            _profile_describe(Namespace(profile_name="default"))
        assert read_exit.value.code == 0
        assert capsys.readouterr().out.strip() == "default description"

        with pytest.raises(SystemExit) as write_exit:
            _profile_describe(Namespace(profile_name="default", text="updated default"))
        assert write_exit.value.code == 0
        assert read_profile_meta(root)["description"] == "updated default"
        assert read_profile_meta(active)["description"] == "coach description"
    finally:
        if token is not None:
            reset_hermes_home_override(token)
