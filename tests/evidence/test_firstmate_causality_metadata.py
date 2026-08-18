import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = ROOT / "proactivity-root-cause.json"
SELECTOR_PATH = ROOT / "evidence/firstmate-causality/select_current.py"
SPEC = importlib.util.spec_from_file_location("firstmate_select_current", SELECTOR_PATH)
assert SPEC and SPEC.loader
SELECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SELECTOR)


@pytest.fixture
def metadata():
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


def test_current_revision_selects_sealed_v3(metadata):
    current = SELECTOR.select_current(metadata)
    assert current["runCount"] == 24
    assert current["isolatedTaskCount"] == 5
    assert current["matrix"]["actionable"] == {
        "none": "2/3", "narrowedPresented": "0/3", "focusedAllowlist": "3/3"
    }
    for descriptor in (current["manifest"], current["treatments"], current["isolatedBoard"]):
        artifact = ROOT / descriptor["path"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == descriptor["sha256"]


def test_obsolete_six_run_data_is_only_superseded(metadata):
    current = SELECTOR.select_current(metadata)
    old = metadata["superseded"]["v2"]
    assert old["status"] == "superseded"
    assert old["runCount"] == 6
    assert old["isolatedTaskCount"] == 2
    assert old["artifact"]["path"].endswith("replay-results.json")
    assert current["manifest"]["path"].endswith("v3/run-manifest.json")
    assert "artifact" not in current


@pytest.mark.parametrize("mutation", ["missing", "unknown", "superseded", "duplicate"])
def test_selector_rejects_missing_or_ambiguous_current(metadata, mutation):
    broken = copy.deepcopy(metadata)
    if mutation == "missing":
        broken.pop("currentRevision")
    elif mutation == "unknown":
        broken["currentRevision"] = "v99"
    elif mutation == "superseded":
        broken["superseded"]["v3"] = copy.deepcopy(broken["revisions"]["v3"])
    else:
        broken["revisions"]["other"] = {"status": "current"}
    with pytest.raises(SELECTOR.MetadataError):
        SELECTOR.select_current(broken)


def test_confidence_domains_cannot_be_conflated(metadata):
    confidence = metadata["confidence"]
    assert confidence["artifactAuthenticityAndReproducibility"]["level"] == "high"
    assert confidence["conditionalTreatmentEffectMagnitudeAndCausality"]["level"] == "low_to_moderate"
    assert confidence["historicalPrimaryCause"]["level"] == "none"
    assert len({key for key in confidence if key != "otherClaims"}) == 3