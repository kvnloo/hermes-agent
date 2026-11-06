"""agent/burn_pace_gate.admit_cls/route_cls must equal the proven Bend law table.

bend/burn_pace/TABLE.bend evaluates MODEL.admit over every (Fresh, Used, Pace) and
MODEL.route over both inputs; PROOF.bend proves LAWS.bend over MODEL. Both run here
whenever the pinned bend binary is installed, so editing either side without the
other fails CI.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from agent import burn_pace_gate as g

ROOT = Path(__file__).resolve().parents[2] / "bend" / "burn_pace"
BEND = shutil.which("bend") or str(Path.home() / ".bend/bin/bend")
needs_bend = pytest.mark.skipif(not Path(BEND).exists(), reason="bend not installed")

ORDER = [(f, u, p, w) for f in (g.FRESH, g.STALE) for u in (g.UNDER, g.AT_CAP) for p in (g.COOL, g.UNKNOWN, g.HOT)
         for w in (g.OWNER, g.BULK)]


def _bend_table():
    out = subprocess.run([BEND, "TABLE.bend"], cwd=ROOT, capture_output=True, text=True, timeout=120, check=False).stdout
    line = next(l for l in out.splitlines() if l.startswith("["))
    return [x.strip() == "True{}" for x in line.strip("[]").split(",")]


@needs_bend
def test_python_twin_matches_bend_table_exhaustively():
    table = _bend_table()
    assert len(table) == len(ORDER) + 2
    assert [g.admit_cls(*k) for k in ORDER] == table[: len(ORDER)]
    assert [g.route_cls(True) == "paid", g.route_cls(False) == "paid"] == table[len(ORDER):]


@needs_bend
def test_laws_prove():
    kernel = os.environ.get("BENDTT") or next(iter(sorted((Path.home() / ".bend/bendtt").glob("*/bendtt"))), None)
    if kernel is None:
        pytest.skip("no built bendtt kernel")
    r = subprocess.run([BEND, "PROOF.bend", "--verdict"], cwd=ROOT, capture_output=True, text=True,
                       timeout=180, check=False, env={**os.environ, "BENDTT": str(kernel)})
    assert "ALL PROOFS CHECK" in r.stdout, r.stdout + r.stderr


def test_classify_maps_readings_into_law_domain():
    from datetime import UTC, datetime
    now = datetime.now(UTC).isoformat()
    rd = {"at": now, "lanes": {"a": {"weekly_used_pct": 100.0, "pace_ratio": None},
                                "b": {"weekly_used_pct": 40.0, "pace_ratio": 0.99},
                                "c": {"weekly_used_pct": 12.0, "pace_ratio": 1.5}}}
    assert g.classify("a", rd)[:3] == (g.FRESH, g.AT_CAP, g.UNKNOWN)
    assert g.classify("b", rd)[:3] == (g.FRESH, g.UNDER, g.COOL)
    assert g.classify("c", rd)[:3] == (g.FRESH, g.UNDER, g.HOT)
    assert g.classify("zz", rd)[0] == g.STALE
    # projected exhaustion before reset is HOT even under 1.5x (claude2 on 2026-11-05: 44% + 0.645%/h * 99.8h)
    rd["lanes"]["d"] = {"weekly_used_pct": 44.0, "pace_ratio": 1.15, "observed_pct_per_h": 0.645, "hours_to_reset": 99.8}
    rd["lanes"]["e"] = {"weekly_used_pct": 12.0, "pace_ratio": 0.85, "observed_pct_per_h": 0.514, "hours_to_reset": 144.7}
    assert g.classify("d", rd)[2] == g.HOT
    assert g.classify("e", rd)[2] == g.COOL
    assert g.classify("b", {"at": "2020-01-01T00:00:00+00:00", "lanes": rd["lanes"]})[0] == g.STALE


def test_owner_is_only_human_opus_in_owner_profile(monkeypatch):
    import hermes_cli.profiles as prof
    from agent.turn_author import human_turn_scope

    lanes = {"owner_profiles": ["clean"]}
    monkeypatch.setattr(prof, "current_profile_name", lambda default=None: "clean")
    assert g.who_for("claude-opus-5-5", lanes) == g.BULK
    with human_turn_scope(True):
        assert g.who_for("claude-opus-5-5", lanes) == g.OWNER
        assert g.who_for("claude-haiku-5-5", lanes) == g.BULK
        assert g.who_for(None, lanes) == g.BULK
        monkeypatch.setattr(prof, "current_profile_name", lambda default=None: "ossfactory")
        assert g.who_for("claude-opus-5-5", lanes) == g.BULK
