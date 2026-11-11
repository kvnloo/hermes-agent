"""Public upload failure guidance for the support workflow in #151408."""

from types import SimpleNamespace

import pytest


def test_public_upload_failure_suggests_private_support_without_uploading(
    tmp_path, monkeypatch, capsys
):
    from hermes_cli import debug
    from hermes_cli import diagnostics_upload

    home = tmp_path / "hermes-home"
    logs = home / "logs"
    logs.mkdir(parents=True)
    (logs / "agent.log").write_text("INFO: support fixture\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))
    uploads = []

    def fail_public_upload(content, expiry_days=1):
        uploads.append(content)
        raise RuntimeError("public paste services unavailable")

    def unexpected_private_upload(*args, **kwargs):
        pytest.fail("failure guidance must not automatically upload privately")

    monkeypatch.setattr(debug, "upload_to_pastebin", fail_public_upload)
    monkeypatch.setattr(diagnostics_upload, "share_to_nous", unexpected_private_upload)
    args = SimpleNamespace(
        lines=10, expire=1, local=False, nous=False, no_redact=False, yes=True
    )
    with pytest.raises(SystemExit) as exc:
        debug.run_debug_share(args)

    assert exc.value.code == 1
    assert len(uploads) == 1
    assert "support fixture" in uploads[0]
    captured = capsys.readouterr()
    assert "public paste services unavailable" in captured.err
    assert "hermes debug share --nous" in captured.out
    assert "private" in captured.out.lower()
    assert "Nous support" in captured.out
    assert captured.out.rindex("--nous") < captured.out.rindex("--local")
    assert "without uploading" in captured.out

def test_private_share_success_names_all_allowed_viewers(monkeypatch, capsys):
    """The upload receipt must not promise staff-only access to moderator-visible bundles."""
    from hermes_cli import debug, diagnostics_upload

    monkeypatch.setattr(debug, "_best_effort_sweep_expired_pastes", lambda: None)
    monkeypatch.setattr(debug, "collect_share_bundle",
                        lambda **kwargs: {"report": "sanitized support fixture"})
    uploads = []

    def fake_private_upload(payload):
        uploads.append(payload)
        return {
            "viewUrl": "https://support.nousresearch.com/diagnostics/fixture",
            "expiresAt": "2026-11-24T00:00:00Z",
        }

    monkeypatch.setattr(diagnostics_upload, "share_to_nous", fake_private_upload)
    args = SimpleNamespace(
        lines=10, expire=1, local=False, nous=True, no_redact=False, yes=True
    )
    debug.run_debug_share(args)

    output = capsys.readouterr().out
    success = output.split("Share this private link with the Nous team", 1)[1]
    assert len(uploads) == 1
    assert "View URL  https://support.nousresearch.com/diagnostics/fixture" in output
    assert "Nous staff and allowlisted Discord mods" in success
    assert "only Nous staff" not in success
