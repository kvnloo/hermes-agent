"""Required CI lanes must be schedulable on forks.

``ubuntu-latest-32-core`` is a GitHub *larger runner* provisioned for the
NousResearch org only. On a fork (e.g. a personal ``owner/hermes-agent``
clone running CI on its own PRs) no runner ever matches that label, so the
job sits queued until GitHub cancels it at the 24h limit, and the aggregate
``All required checks pass`` gate reports ``cancelled`` as a failure.

Every job in a reusable workflow that ``ci.yaml`` fans out to (and therefore
feeds the required gate) must select the larger runner only for the
NousResearch org and fall back to the standard hosted ``ubuntu-latest``
everywhere else. Upstream behavior is unchanged: PRs from forks *into*
NousResearch run in the base repo, where ``github.repository_owner`` is
``NousResearch``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS = _ROOT / ".github" / "workflows"
_LARGER_LINUX = "ubuntu-latest-32-core"
_FALLBACK = (
    "${{ github.repository_owner == 'NousResearch' && "
    "'ubuntu-latest-32-core' || 'ubuntu-latest' }}"
)


def _ci_reusable_workflows() -> list[str]:
    text = (_WORKFLOWS / "ci.yaml").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"uses:\s*\./\.github/workflows/([\w.-]+\.ya?ml)", text)))


def _runs_on_values(path: Path) -> list[tuple[int, str]]:
    out = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"\s*runs-on:\s*(.+?)\s*$", line)
        if m:
            out.append((lineno, m.group(1)))
    return out


def test_ci_fans_out_to_reusable_workflows():
    names = _ci_reusable_workflows()
    # Guard the discovery itself so the parametrized test can't go vacuous.
    for required in ("tests.yml", "js-tests.yml", "e2e-desktop-core.yml", "e2e-desktop-update.yml"):
        assert required in names


@pytest.mark.parametrize("workflow", _ci_reusable_workflows())
def test_required_lane_larger_linux_runner_has_fork_fallback(workflow):
    offenders = [
        f"{workflow}:{lineno}: runs-on: {value}"
        for lineno, value in _runs_on_values(_WORKFLOWS / workflow)
        if _LARGER_LINUX in value and value != _FALLBACK
    ]
    assert not offenders, (
        "larger runner selected unconditionally (never schedules on forks; "
        "job is cancelled at 24h and fails 'All required checks pass'):\n"
        + "\n".join(offenders)
    )
