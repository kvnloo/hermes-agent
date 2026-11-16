"""Auxiliary task defaults must register runtime-configurable fallback chains."""

from hermes_cli.config import DEFAULT_CONFIG


def test_vision_fallback_chain_is_a_registered_config_key():
    assert DEFAULT_CONFIG["auxiliary"]["vision"]["fallback_chain"] == []
