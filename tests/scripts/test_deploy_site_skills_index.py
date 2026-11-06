"""Regression for #122609, on the #134022 carrier by liuhao1024.

A push docs deploy must prefer the latest scheduled index artifact over a
healthy-but-stale live index, even when the scheduled dispatch was displaced.
"""

import json
import os
from pathlib import Path
import subprocess
import textwrap

import pytest


WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/deploy-site.yml"


@pytest.mark.platforms("posix")
def test_push_deploy_uses_scheduled_index_instead_of_live_copy(tmp_path):
    workflow = WORKFLOW.read_text(encoding="utf-8")
    step = workflow.split(
        "      - name: Prepare skills index (unified multi-source catalog)\n", 1
    )[1]
    script = textwrap.dedent(
        step.split("        run: |\n", 1)[1].split(
            "\n      - name: Extract skill metadata for dashboard", 1
        )[0]
    )

    scheduled = tmp_path / "scheduled.json"
    live = tmp_path / "live.json"
    for path, source in ((scheduled, "scheduled"), (live, "live")):
        path.write_text(
            json.dumps({"skills": [{}] * 1500, "source": source}),
            encoding="utf-8",
        )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    gh = fake_bin / "gh"
    gh.write_text(
        r"""#!/bin/sh
set -eu
case "$1:$2" in
  run:list)
    printf 'list\n' >> "$TRACE"
    printf '9001\n'
    ;;
  run:download)
    test "$3" = 9001
    test "$4" = --name
    test "$5" = skills-index
    test "$6" = --dir
    cp "$SCHEDULED_INDEX" "$7/skills-index.json"
    printf 'download\n' >> "$TRACE"
    ;;
  *) exit 91 ;;
esac
""",
        encoding="utf-8",
    )
    gh.chmod(0o755)

    curl = fake_bin / "curl"
    curl.write_text(
        r"""#!/bin/sh
set -eu
printf 'curl\n' >> "$TRACE"
while [ "$#" -gt 1 ]; do
  if [ "$1" = -o ]; then
    cp "$LIVE_INDEX" "$2"
    exit 0
  fi
  shift
done
exit 92
""",
        encoding="utf-8",
    )
    curl.chmod(0o755)

    trace = tmp_path / "calls.txt"
    trace.touch()
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
            "SKILLS_INDEX_RUN_ID": "",
            "REBUILD_SKILLS_INDEX": "false",
            "SCHEDULED_INDEX": str(scheduled),
            "LIVE_INDEX": str(live),
            "TRACE": str(trace),
        }
    )

    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    deployed = json.loads(
        (tmp_path / "website/static/api/skills-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert deployed["source"] == "scheduled"
    assert trace.read_text(encoding="utf-8").splitlines() == ["list", "download"]
