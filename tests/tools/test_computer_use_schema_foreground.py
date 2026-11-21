"""Keep the model-facing foreground guidance aligned with the computer-use skill.

Regression for NousResearch/hermes-agent#149417 (IsseiMatsuzoe).
"""

from tools.computer_use.schema import get_computer_use_schema


def test_foreground_guidance_allows_freshly_verified_noop_without_escalation_hint():
    schema = get_computer_use_schema()
    delivery = schema["parameters"]["properties"]["delivery_mode"]["description"]

    for guidance in (delivery, schema["description"]):
        assert "verify_fresh_state" in guidance
        assert "fresh capture" in guidance
        assert "no effect" in guidance
        assert "escalation hint" in guidance

    assert "approval" in delivery
