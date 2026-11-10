"""Attested sibling gateways must recover through their own Windows Scheduled Task (#91675).

The active-profile fallbacks in PR #115495 do not reach the per-profile cold-start
loop. A direct child reaped inside the updater's Job Object must not leave beta down
while a different profile/task is active. The recovery also must not borrow a
sibling's readiness PID.
"""

from __future__ import annotations

from hermes_cli import gateway, gateway_windows, profiles, update_cmd_windows


def test_attested_sibling_relaunch_uses_own_task(monkeypatch, tmp_path, capsys):
    root = tmp_path / "hermes"
    home = root / "profiles" / "beta"
    home.mkdir(parents=True)

    monkeypatch.setattr("hermes_constants.get_default_hermes_root", lambda: root)
    monkeypatch.setattr(gateway, "_native_service_homes", lambda: set())
    monkeypatch.setattr(gateway, "_bare_unit_pinned_home", lambda: None)
    monkeypatch.setattr(gateway_windows, "_assert_windows", lambda: None)
    monkeypatch.setattr(profiles, "get_profile_dir", lambda _name: home)

    spawned = []
    monkeypatch.setattr(gateway_windows, "_live_gateway_pids", lambda *, home: [])
    monkeypatch.setattr(
        gateway_windows, "_spawn_detached", lambda *, home: spawned.append(home) or 1234
    )
    state = {"scheduled": False}
    calls = []

    def schtasks(args):
        calls.append(args)
        if args == ["/Run", "/TN", "Hermes_Gateway_beta"]:
            state["scheduled"] = True
        return (0, "", "")

    def ready(*, home=None, **_kwargs):
        assert home == root / "profiles" / "beta"
        return [4444] if state["scheduled"] else []

    monkeypatch.setattr(gateway_windows, "_exec_schtasks", schtasks)
    monkeypatch.setattr(gateway_windows, "_wait_for_gateway_ready", ready)
    consumed = []
    written = []
    monkeypatch.setattr(
        gateway_windows, "_consume_start_attestation",
        lambda generation, home=None: consumed.append((generation, home)),
    )
    monkeypatch.setattr(
        gateway_windows, "_write_start_attestation",
        lambda pids, via, home=None: written.append((pids, via, home)),
    )

    token = {"cold_start_profiles": {"beta": "generation-1"}}
    update_cmd_windows._cold_start_attested_profiles(token)

    assert spawned == [home]
    assert calls == [
        ["/Query", "/TN", "Hermes_Gateway_beta"],
        ["/Run", "/TN", "Hermes_Gateway_beta"],
    ]
    assert consumed == [("generation-1", home)]
    assert written == [([4444], "cold-start after update (profile beta, scheduled task)", home)]
    assert token == {}
    assert "Gateway profile beta started via cold-start after update (scheduled task) (PID: 4444)" in capsys.readouterr().out
