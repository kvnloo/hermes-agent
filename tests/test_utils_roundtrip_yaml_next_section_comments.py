"""`hermes config set <key> []` / `{}` must not delete the comment block that introduces the *next* key.

ruamel stores the comment lines that follow a collection's last entry (blank line, a section banner,
the next key's own description) on that last entry. Emptying or truncating the collection drops the
entry and the next section's comments with it, while the file still loads, so nothing reports it.
"""

import difflib
from pathlib import Path

import pytest

import hermes_yaml as yaml

from utils import atomic_roundtrip_yaml_save, atomic_roundtrip_yaml_update

EXAMPLE = Path(__file__).resolve().parents[1] / "cli-config.yaml.example"


@pytest.mark.parametrize(
    "removed, doc",
    [
        ("emptied list", "sec:\n  - a\n  # NOTE below\nb: 2\n"),
        ("emptied map", "a: 1\nsec:\n  x: 1\n# NOTE below\nb: 2\n"),
        ("list tail", "sec:\n  - a\n  - b\n\n# NOTE below\nb: 2\n"),
        ("whole section", "a: 1\nsec:\n  x: 1\n  w: 2\n\n# NOTE below\nb: 2\n"),
    ],
)
def test_save_keeps_the_next_keys_comment(tmp_path, removed, doc):
    path = tmp_path / "config.yaml"
    path.write_text(doc, encoding="utf-8")
    state = yaml.safe_load(doc)
    if removed == "whole section":
        state.pop("sec")
    elif removed == "list tail":
        state["sec"].pop()
    else:
        state["sec"].clear()

    atomic_roundtrip_yaml_save(path, state)

    text = path.read_text(encoding="utf-8")
    assert "# NOTE below" in text, text
    assert yaml.safe_load(text) == state


def _last_line(node) -> int:
    """0-based line of the last data entry inside a non-empty round-trip collection."""
    if isinstance(node, dict):
        key = next(reversed(node))
        child, line = node[key], node.lc.data[key][2]
    else:
        child, line = node[-1], node.lc.data[len(node) - 1][0]
    return _last_line(child) if isinstance(child, (dict, list)) and child else line


def _shipped_cases():
    data = yaml.roundtrip_yaml().load(EXAMPLE.read_text(encoding="utf-8"))
    cases = []
    for key, value in data.items():
        if isinstance(value, (dict, list)) and value:
            cases.append(pytest.param(key, _last_line(value), id=key))
            if isinstance(value, dict):
                cases += [
                    pytest.param(f"{key}.{k}", _last_line(v), id=f"{key}.{k}")
                    for k, v in value.items()
                    if isinstance(v, (dict, list)) and v
                ]
    return cases


@pytest.mark.parametrize("key_path, last", _shipped_cases())
def test_config_set_empty_keeps_every_comment_after_the_block(tmp_path, key_path, last):
    """Every collection in the shipped example config: emptying it may drop the block's own
    commented options, never a comment line that comes after the block's last data line."""
    src = EXAMPLE.read_text(encoding="utf-8")
    lines = src.splitlines()
    current = yaml.safe_load(src)
    for part in key_path.split("."):
        current = current[part]
    path = tmp_path / "config.yaml"
    path.write_text(src, encoding="utf-8")

    atomic_roundtrip_yaml_update(
        path, key_path, [] if isinstance(current, list) else {}
    )

    after = path.read_text(encoding="utf-8").splitlines()
    ops = difflib.SequenceMatcher(None, lines, after, autojunk=False).get_opcodes()
    lost = [
        lines[i]
        for tag, i1, i2, _, _ in ops
        if tag in ("delete", "replace")
        for i in range(i1, i2)
        if i > last and lines[i].lstrip().startswith("#")
    ]
    assert not lost, (
        f"config set {key_path} deleted the next section's comments:\n"
        + "\n".join(lost)
    )
