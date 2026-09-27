"""Control-socket profile identity verbs must validate names like the CLI does.

The CLI canonicalizes both names with ``hermes_cli.profiles._canon_valid`` before
sending them over the control socket, but the server-side handlers only ``.strip()``ped.
Any same-user local process can drive the socket, so a client could send
``new='../../outside/victim'`` and the migrate handler would interpolate it into
``<routing_home>/profiles/<new>/state.db`` and open+write that DB — a path-traversal
write in the control plane. Every name arriving over the socket gets the CLI rule.
"""

import types


def _handlers():
    from gateway.run_profile_reconcile import (
        migrate_profile_identity_verb,
        purge_profile_identity_verb,
    )

    calls = {}
    store = types.SimpleNamespace(_routing_db=None, _routing_home=None)

    def rekey(old, new):
        calls["rekey"] = (old, new)
        return 3

    def purge(name):
        calls["purge"] = name
        return 5

    store.rekey_profile_routing = rekey
    store.purge_profile_routing = purge
    runner = types.SimpleNamespace(session_store=store)
    return migrate_profile_identity_verb(runner), purge_profile_identity_verb(runner), calls


def test_migrate_rejects_traversal_new_name():
    migrate, _, calls = _handlers()
    res = migrate({"old": "oldvictim", "new": "../../outside/victim"})
    assert res["ok"] is False
    assert "rekey" not in calls  # rejected before any store was touched


def test_migrate_rejects_traversal_old_name():
    migrate, _, calls = _handlers()
    res = migrate({"old": "../evil", "new": "newvictim"})
    assert res["ok"] is False
    assert "rekey" not in calls


def test_purge_rejects_traversal_name():
    _, purge, calls = _handlers()
    res = purge({"name": "../../outside"})
    assert res["ok"] is False
    assert "purge" not in calls


def test_valid_names_rekey_with_canonical_ids():
    migrate, purge, calls = _handlers()
    res = migrate({"old": "OldVictim", "new": "NewVictim"})
    assert res["ok"] is True
    assert calls["rekey"] == ("oldvictim", "newvictim")  # same rule the CLI sends
    res = purge({"name": "OldVictim"})
    assert res["ok"] is True
    assert calls["purge"] == "oldvictim"
