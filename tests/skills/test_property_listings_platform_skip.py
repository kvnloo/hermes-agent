"""Regression for NousResearch/hermes-agent#154991: unsupported skill loads skip."""

import re
from dataclasses import replace

import pytest

from agent.skill_utils import skill_matches_platform_list
from tools.skills_hub_official import OptionalSkillSource
from test_property_listings_skill import (
    test_optional_catalog_fetch_preserves_a_usable_property_recipe,
)


def test_property_listings_host_incompatible_bundle_skips(tmp_path, monkeypatch):
    """Exercise the actual catalog/load test with a declaration excluding this host."""
    incompatible = next(
        platform
        for platform in ("linux", "macos", "windows")
        if not skill_matches_platform_list([platform])
    )
    real_fetch = OptionalSkillSource.fetch

    def fetch_incompatible_bundle(self, identifier):
        bundle = real_fetch(self, identifier)
        assert bundle is not None
        raw = bundle.files["SKILL.md"]
        skill_md = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        skill_md, changed = re.subn(
            r"(?m)^platforms:\s*\[[^\n]*\]$",
            f"platforms: [{incompatible}]",
            skill_md,
            count=1,
        )
        assert changed == 1, "The fixture must have an explicit platform declaration"
        return replace(bundle, files={**bundle.files, "SKILL.md": skill_md})

    monkeypatch.setattr(OptionalSkillSource, "fetch", fetch_incompatible_bundle)
    with pytest.raises(pytest.skip.Exception, match="not supported on this platform"):
        test_optional_catalog_fetch_preserves_a_usable_property_recipe(
            tmp_path, monkeypatch
        )
