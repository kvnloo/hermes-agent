"""A dependency-generation tree maps back to the checkout that owns it (#131164).

``owning_install_root`` is the reverse mapping a persisted command needs before
it may name a generation tree: generation workspaces/venvs are keyed by their
own path and GC-able, while the owning install's state records the checkout in
``inputs/.project-root``.
"""
from pathlib import Path

from pm.environments import install_state_dir, owning_install_root


def _generation_layout(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    checkout = tmp_path / "checkout"
    (checkout / "pm").mkdir(parents=True)
    (checkout / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    state = install_state_dir(checkout)
    workspace = state / "environments" / ("g" * 32) / "workspace"
    workspace.mkdir(parents=True)
    (state / "inputs").mkdir(parents=True)
    (state / "inputs" / ".project-root").write_text(str(checkout), encoding="utf-8")
    return checkout, state, workspace


def test_generation_tree_maps_to_owning_checkout(tmp_path, monkeypatch):
    checkout, _state, workspace = _generation_layout(tmp_path, monkeypatch)
    venv = workspace.parent / "venv"
    venv.mkdir()

    assert owning_install_root(workspace) == checkout.resolve()
    assert owning_install_root(venv) == checkout.resolve()
    assert owning_install_root(workspace.parent) == checkout.resolve()


def test_stamp_pointing_at_another_checkout_is_rejected(tmp_path, monkeypatch):
    checkout, state, workspace = _generation_layout(tmp_path, monkeypatch)
    # A stamp naming a checkout whose install key hashes elsewhere must not
    # answer for this generation's state dir.
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "pyproject.toml").write_text("[project]\nname = 'y'\n", encoding="utf-8")
    (state / "inputs" / ".project-root").write_text(str(foreign), encoding="utf-8")

    assert owning_install_root(workspace) is None


def test_plain_roots_answer_none(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    plain = tmp_path / "plain"
    plain.mkdir()

    assert owning_install_root(plain) is None
