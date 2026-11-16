"""A worker scratch export must not resurrect dead profile homes (#156438)."""

import shutil

import pytest

from hermes_constants import (
    SCRATCH_DIR_MARKER_ENV,
    SCRATCH_TMP_ENV_VARS,
    apply_subprocess_home_env,
    get_scratch_dir,
    mark_named_profile_deleted,
)


def test_profile_worker_scratch_home_requires_live_identity(tmp_path):
    profiles = tmp_path / ".hermes" / "profiles"
    live = profiles / "alive"
    live.mkdir(parents=True)
    (live / "config.yaml").write_text("{}\n", encoding="utf-8")

    # The healthy-profile arm must still route child temp files under its home.
    active = {"HERMES_HOME": str(live)}
    apply_subprocess_home_env(active)
    scratch = live / "cache" / "scratch"
    assert scratch.is_dir()
    assert active["TMPDIR"] == str(scratch)

    for name in ("unprovisioned", "deleted"):
        home = profiles / name
        home.mkdir()
        if name == "deleted":
            (home / "config.yaml").write_text("{}\n", encoding="utf-8")
            mark_named_profile_deleted(home)
            shutil.rmtree(home)

        # A routed worker inherits temp vars equal to the parent scratch marker.
        env = {"HERMES_HOME": str(home), SCRATCH_DIR_MARKER_ENV: str(scratch)}
        env.update({key: str(scratch) for key in SCRATCH_TMP_ENV_VARS})
        apply_subprocess_home_env(env)

        assert not (home / "cache").exists()
        assert all(key not in env for key in (*SCRATCH_TMP_ENV_VARS, SCRATCH_DIR_MARKER_ENV))
        with pytest.raises(FileNotFoundError):
            get_scratch_dir(home, prune=False)
