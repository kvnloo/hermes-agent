"""Source-aware replies preserve existing language and catalog fallback contracts."""

from agent import i18n
from gateway.run import _sanitize_gateway_final_response


def test_rate_reply_uses_profile_catalog_and_english_fallback(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    home.mkdir()
    (home / "config.yaml").write_text("display:\n  language: de\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.delenv("HERMES_LANGUAGE", raising=False)
    i18n.reset_language_cache()
    try:
        throttle = _sanitize_gateway_final_response("telegram", "HTTP 429 OpenAI rate limit exceeded")
        assert "Der KI-Modelldienst begrenzt" in throttle
        quota = _sanitize_gateway_final_response("telegram", "HTTP 429 Codex quota exhausted; retry after 600s")
        assert "Das Nutzungslimit des KI-Modelldienstes" in quota
        assert "/model" in quota
        discord = _sanitize_gateway_final_response("telegram", "HTTP 429 Discord API rate limit exceeded")
        assert "Discord is rate-limiting" in discord
        unknown = _sanitize_gateway_final_response("telegram", "HTTP 429 Too Many Requests")
        assert "An upstream service is rate-limiting" in unknown
    finally:
        i18n.reset_language_cache()
