"""A malformed persisted Bot Mode value must not poison either profiles.list wire path.

Regression for #154905: /api/profiles now rejects non-finite YAML ui_meta, but both
the canonical owner roster and legacy JSON-RPC roster must do the same.
"""

import json
from types import SimpleNamespace

from gateway.session_contract import SessionActor
from gateway.session_group_controls import _profiles
from hermes_cli.profiles import read_profile_meta
from hermes_state import SessionDB
import tui_gateway.server as legacy


def test_nonfinite_bot_mode_metadata_keeps_both_roster_wires_valid(tmp_path, monkeypatch):
    home = tmp_path / "state"
    home.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / "config.yaml").write_text("model:\n  default: fixture\n", encoding="utf-8")

    sibling = home / "profiles" / "client"
    sibling.mkdir(parents=True)
    (sibling / "config.yaml").write_text("model:\n  default: fixture\n", encoding="utf-8")

    for profile, title in ((home, "Builder"), (sibling, "Client")):
        (profile / "profile.yaml").write_text(
            "ui_meta:\n  hermes-bots:\n    title: " + title +
            "\n    sectionId: delivery\n    malformed: .nan\n",
            encoding="utf-8",
        )

    actor = SessionActor("viewer", str(home), frozenset({"session:read"}), "fixture")
    with SessionDB(home / "state.db") as db:
        authority = SimpleNamespace(db=db, profile_id=str(home))
        owner = {"jsonrpc": "2.0", "id": 1, "result": _profiles(authority, actor, home, {})}
        fallback = legacy._methods["profiles.list"](2, {})
        for response in (owner, fallback):
            # The Desktop's JSON.parse cannot consume NaN, even though Python's
            # default json.dumps would silently emit it.
            json.dumps(response, allow_nan=False)
            rows = {row["name"]: row for row in response["result"]["profiles"]}
            assert rows["default"]["ui_meta"] == {}
            assert rows["client"]["ui_meta"] == {}

    # Rejecting invalid ui_meta must not drop the ordinary Bot Mode title.
    assert read_profile_meta(home)["bot_title"] == "Builder"
