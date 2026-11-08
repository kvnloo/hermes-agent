"""Provider-scoped OAuth diagnostics for NousResearch/hermes-agent#151049."""

from hermes_cli import auth, doctor


def test_doctor_oauth_cannot_borrow_another_profiles_provider(tmp_path, monkeypatch):
    root = tmp_path / ".hermes"
    profile = root / "profiles" / "bot"
    profile.mkdir(parents=True)
    (root / ".env").write_text("MINIMAX_API_KEY=shared-root-secret\n", encoding="utf-8")
    (profile / ".env").write_text("TELEGRAM_BOT_TOKEN=profile-token\n", encoding="utf-8")
    config_path = profile / "config.yaml"
    config_path.write_text("model:\n  provider: openai-api\n", encoding="utf-8")

    monkeypatch.setenv("HERMES_HOME", str(profile))
    monkeypatch.setattr(doctor, "HERMES_HOME", profile)
    for name in (
        "get_nous_auth_status_local",
        "get_codex_auth_status",
        "get_xai_oauth_auth_status",
        "get_qwen_auth_status_local",
    ):
        monkeypatch.setattr(auth, name, lambda: {"logged_in": False})
    monkeypatch.setattr(
        auth, "get_minimax_oauth_auth_status", lambda: {"logged_in": True}
    )

    assert not doctor._has_provider_env_config((profile / ".env").read_text())
    # A MiniMax login cannot satisfy an explicitly configured OpenAI API route.
    assert doctor._oauth_auth_configured_for_doctor() is False

    # The same profile's MiniMax OAuth route can use that healthy login.
    config_path.write_text("model:\n  provider: minimax-oauth\n", encoding="utf-8")
    assert doctor._oauth_auth_configured_for_doctor() is True
