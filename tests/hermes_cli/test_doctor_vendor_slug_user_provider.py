"""Regression for mkoeds-spec's PR #156064: a user router owns vendor/model names."""

from hermes_cli import doctor_config


def test_doctor_accepts_vendor_model_slug_on_user_configured_router(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "model:\n"
        "  provider: requesty\n"
        "  default: sference/deepseek-v4.1-flash\n"
        "providers:\n"
        "  requesty:\n"
        "    base_url: https://router.requesty.ai/v1\n"
        "    api_key_env: REQUESTY_API_KEY\n",
        encoding="utf-8",
    )

    issues: list[str] = []
    doctor_config._validate_model_config(config_path, issues)

    assert not [issue for issue in issues if "vendor-prefixed" in issue], issues
