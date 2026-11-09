"""Regression for profile-local /api/skills single-flight in lolock's #150706."""

import asyncio

from hermes_constants import get_hermes_home, reset_hermes_home_override, set_hermes_home_override
import hermes_cli.web_routers.skills as skills


def test_unnamed_list_uses_effective_native_profile_home(monkeypatch, tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    rebuilt = []

    def scan(profile):
        assert profile is None
        home = get_hermes_home()
        rebuilt.append(home)
        return [{"name": home.name}]

    monkeypatch.setattr(skills, "_skills_list_build", scan)
    skills._invalidate_skills_list_cache()

    async def fetch_under(home):
        token = set_hermes_home_override(home)
        try:
            return await skills.get_skills()
        finally:
            reset_hermes_home_override(token)

    async def scenario():
        return [await fetch_under(first), await fetch_under(second), await fetch_under(first)]

    try:
        assert asyncio.run(scenario()) == [
            [{"name": "first"}], [{"name": "second"}], [{"name": "first"}]]
        assert rebuilt == [first, second]
    finally:
        skills._invalidate_skills_list_cache()
