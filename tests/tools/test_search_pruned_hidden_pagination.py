"""File-search regression for NousResearch/hermes-agent#156629."""

import os

import pytest

from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations


@pytest.mark.platforms("posix")
def test_directory_supplement_never_exposes_pruned_paths(tmp_path):
    """The find fallback must not turn excluded directories into matches."""
    root = tmp_path / "repo"
    live_file = root / "live" / "registry" / "nodes.yaml"
    live_file.parent.mkdir(parents=True)
    live_file.write_text("active: true\n")
    os.utime(live_file, (1_700_000_000, 1_700_000_000))

    # More than the public search() default page size (50), all newer.
    for index in range(60):
        hidden = root / f".cache-{index:02d}"
        hidden.mkdir()
        os.utime(hidden, (2_000_000_000, 2_000_000_000))

    ops = ShellFileOperations(LocalEnvironment("/"))
    dirs, limit_reason = ops._search_directories_with_find(
        "*nodes.yaml", str(root), 51
    )

    assert dirs == []
    assert limit_reason is None
