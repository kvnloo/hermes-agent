"""Regression for LaunchAgent TCC attribution: doctor must distinguish job-root identity from its own."""
import plistlib

from hermes_cli import doctor_platform


def test_osascript_launchagent_reports_ungrantable_gateway_identity(tmp_path):
    plist = tmp_path / "ai.hermes.gateway.plist"
    plist.write_bytes(plistlib.dumps({
        "ProgramArguments": ["/usr/bin/osascript", "-l", "JavaScript", "-e", "gateway"],
    }))
    notice = doctor_platform._launchd_tcc_notice(plist)
    assert "osascript" in notice
    assert "Hermes.app" in notice
    assert "managed Python" in notice
    assert "gateway.launchd_network_identity: direct" in notice
    assert "Local Network" in notice

    # The carrier's opt-in direct mode changes the responsible process.
    plist.write_bytes(plistlib.dumps({
        "ProgramArguments": ["/some/venv/bin/python", "-m", "hermes_cli.stderr_timestamp"],
    }))
    assert doctor_platform._launchd_tcc_notice(plist) is None

    # An unreadable or malformed definition must not disrupt doctor.
    plist.write_bytes(b"<plist><bad")
    assert doctor_platform._launchd_tcc_notice(plist) is None
