"""Wrong-region fuzzy edits must fail loud on the live patch path.

When old_string is not in the file, the similarity fallbacks must not overwrite
a region whose text differs from it: the patch reports an error and the file
stays byte-identical, so the model re-reads instead of corrupting code. Near
misses on the same text still apply, and the matcher names the non-exact
strategy that matched them.
Refs #54572, #111116.
"""

import pytest

from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations
from tools.fuzzy_match import STRATEGIES, fuzzy_find_and_replace

# case -> (file content, old_string, new_string)
WRONG_REGION = {
    # #54572: first and last lines line up; the middle names a different statement.
    "block_anchor_middle": (
        "def handler(request):\n    audit_log(request.user_id)\n    return process(request)\n",
        "def handler(request):\n    validate(request.token)\n    return process(request)",
        "def handler(request):\n    rate_limit(request)\n    return process(request)",
    ),
    # #125376: one line that differs only in the method name (similarity 0.92).
    "single_line_wrong_token": (
        "def f(v):\n    return value.strip()\n",
        "    return value.trim()",
        "    return value.fixed()",
    ),
    # #111127 battery, missing_anchor trap: the same without indentation. (The
    # battery's new_string is a substring of the file, so it takes the
    # already-applied path instead; any other replacement shows the defect.)
    "single_line_missing_anchor": (
        "def normalize(value):\n    return value.strip()\n",
        "return value.trim()",
        "return value.casefold()",
    ),
    # Review on #125376: one logical line plus its line terminator.
    "single_line_trailing_newline": (
        "def f(v):\n    return value.strip()\n",
        "    return value.trim()\n",
        "    return value.fixed()\n",
    ),
}

# case -> (file content, old_string, new_string, text that must land)
NEAR_MISS = {
    # #54575: same block, indentation drifted and one remembered value off.
    "block_drift": (
        "def foo():\n    x = 1\n    y = 2\n    return x + y\n",
        "def foo():\n  x = 1\n  y = 9\n  return x + y",
        "def foo():\n    return 0\n",
        "return 0",
    ),
    # #111127 battery, indentation_drift trap: two spaces sent, four in the file.
    "indentation_drift": (
        "def retry_delay():\n    return 250\n",
        "\n  return 250\n",
        "\n  return 500\n",
        "return 500",
    ),
}


@pytest.fixture
def ops(tmp_path):
    return ShellFileOperations(LocalEnvironment(cwd=str(tmp_path), timeout=15), cwd=str(tmp_path))


def _v4a(path, old, new):
    hunk = [f"-{line}" for line in old.split("\n")] + [f"+{line}" for line in new.split("\n")]
    return "\n".join(["*** Begin Patch", f"*** Update File: {path}", "@@", *hunk, "*** End Patch"])


@pytest.mark.parametrize("mode", ["replace", "v4a"])
@pytest.mark.parametrize("case", list(WRONG_REGION))
def test_wrong_region_edit_fails_loud_and_leaves_file_untouched(ops, tmp_path, case, mode):
    content, old, new = WRONG_REGION[case]
    target = tmp_path / "target.py"
    target.write_text(content, encoding="utf-8")
    _, count, strategy, err = fuzzy_find_and_replace(content, old, new)

    if mode == "replace":
        result = ops.patch_replace(str(target), old, new)
    else:
        result = ops.patch_v4a(_v4a(str(target), old, new))

    on_disk = target.read_text(encoding="utf-8")
    assert result.error is not None and not result.success and on_disk == content, (
        f"wrong region replaced via {strategy}: count={count}, error={err!r}\n{on_disk}")


@pytest.mark.parametrize("case", list(NEAR_MISS))
def test_near_miss_edit_still_applies_via_a_non_exact_strategy(ops, tmp_path, case):
    content, old, new, landed = NEAR_MISS[case]
    target = tmp_path / "target.py"
    target.write_text(content, encoding="utf-8")

    _, count, strategy, err = fuzzy_find_and_replace(content, old, new)
    assert (count, err) == (1, None)
    assert strategy in {name for name, _fn in STRATEGIES} - {"exact"}

    result = ops.patch_replace(str(target), old, new)
    assert result.success and result.error is None, result.error
    assert landed in target.read_text(encoding="utf-8")
