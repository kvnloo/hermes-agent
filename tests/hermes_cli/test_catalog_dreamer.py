"""Regression for Dreamer's catalog capability declarations.

Cosmonautic1's catalog entry must expose its advertised tools and wake hook
through the same loader the CLI and Desktop use.
"""

from hermes_cli import plugin_catalog


def test_dreamer_catalog_exposes_declared_tools_and_wake_hook():
    dreamer = next(
        entry for entry in plugin_catalog.load_catalog() if entry.name == "dreamer"
    )

    assert set(dreamer.capabilities.provides_tools) == {
        "dream_now",
        "dream_journal",
        "dream_status",
    }
    assert dreamer.capabilities.provides_hooks == ["pre_llm_call"]
