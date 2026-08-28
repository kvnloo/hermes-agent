from hermes_cli.profiles import profile_clone_credential_notice


def test_normal_clone_notice_says_oauth_is_not_copied():
    notice = profile_clone_credential_notice(clone_all=False)

    assert "OAuth credentials were not copied" in notice
    assert "hermes -p <profile> auth login <provider>" in notice


def test_clone_all_notice_calls_oauth_copy_a_point_in_time_snapshot():
    notice = profile_clone_credential_notice(clone_all=True)

    assert "point-in-time OAuth snapshot" in notice
    assert "not shared" in notice
