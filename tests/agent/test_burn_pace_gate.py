"""The Hermes seam hands provider/rows/model/profile to the z0 twin and fails open without it."""
from types import SimpleNamespace

from agent import burn_pace_gate as g


def test_seam_passes_facts_to_twin(tmp_path, monkeypatch):
    twin = tmp_path / "burn_pace.py"
    twin.write_text("def admit(provider, entries, model, profile):\n"
                    "    return [e for e in entries if (provider, model, profile) == ('anthropic', 'm', 'clean')]\n")
    monkeypatch.setenv("HERMES_POOL_ADMISSION", str(twin))
    import hermes_cli.profiles as prof
    monkeypatch.setattr(prof, "current_profile_name", lambda default=None: "clean")
    rows = [SimpleNamespace(label="a")]
    assert g.admit("anthropic", rows, "m") == rows
    assert g.admit("anthropic", rows, "other") == []


def test_missing_twin_fails_open(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_POOL_ADMISSION", str(tmp_path / "nope.py"))
    rows = [SimpleNamespace(label="a")]
    assert g.admit("anthropic", rows, "m") == rows
