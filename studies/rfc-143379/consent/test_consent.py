"""Deterministic, synthetic consent-invariant tests on upstream-derived gate snippets.
Use `python -m pytest -q test_consent.py` from this folder.
"""
import json
from pathlib import Path
import pytest
from runtime import EXAMPLES, MARKER, VERSIONS, run_case, _hermes_stubs
from snapshots import pr_116846

@pytest.mark.parametrize('version', list(VERSIONS))
@pytest.mark.parametrize('target', ['user','memory'])
@pytest.mark.parametrize('case', ['self_report','bare_fact','alt_wording','indirect_refusal'])
def test_prohibited_fact_persists_in_current_designs(version, target, case):
    r=run_case(version,case,target)
    assert r.prohibited_by_source
    # This is a RED safety property, expressed as an expected vulnerability in
    # the *existing* designs. A future fix should invert the expectation.
    assert r.never_save_invariant == 'FAIL'
    assert r.memory_marker_found or r.user_marker_found or r.pending_marker_found

@pytest.mark.parametrize('version', list(VERSIONS))
@pytest.mark.parametrize('target', ['user','memory'])
@pytest.mark.parametrize('case', ['batch_self_report','batch_bare_fact'])
def test_batch_retains_prohibited_fact_in_current_designs(version,target,case):
    r=run_case(version,case,target)
    assert r.never_save_invariant=='FAIL'

@pytest.mark.parametrize('target', ['user','memory'])
def test_116846_explicit_self_report_goes_to_pending_with_raw_payload_and_summary(target):
    r=run_case('PR-116846','self_report',target)
    assert r.gate_result=='stage'
    assert r.pending_marker_found and r.pending_summary_marker_found and r.pending_payload_marker_found
    assert not (r.memory_marker_found or r.user_marker_found)

@pytest.mark.parametrize('target', ['user','memory'])
def test_116846_cleaned_fact_bypasses_no_save_regex(target):
    r=run_case('PR-116846','bare_fact',target)
    assert r.gate_result=='apply'
    assert not r.pending_marker_found
    assert r.memory_marker_found or r.user_marker_found

@pytest.mark.parametrize('target', ['user','memory'])
def test_116834_target_based_difference(target):
    r=run_case('PR-116834','bare_fact',target)
    assert r.gate_result==('stage' if target=='user' else 'apply')

@pytest.mark.parametrize('version', list(VERSIONS))
def test_routine_memory_add_remains_allowed(version):
    r=run_case(version,'routine_operational','memory')
    assert r.gate_result=='apply'
    assert r.never_save_invariant=='N/A'

@pytest.mark.parametrize('version',list(VERSIONS))
@pytest.mark.parametrize('target',['user','memory'])
@pytest.mark.parametrize('case',['self_report','bare_fact','alt_wording','indirect_refusal'])
def test_trusted_source_denial_skips_both_disk_and_pending(version,target,case):
    # Designed mitigation control, NOT implemented upstream.
    r=run_case(version,case,target,source_consent_guard=True)
    assert r.gate_result=='deny'
    assert r.never_save_invariant=='PASS'
    assert not (r.memory_marker_found or r.user_marker_found or r.pending_marker_found)

@pytest.mark.parametrize('version', list(VERSIONS))
@pytest.mark.parametrize('target',['user','memory'])
def test_consent_denial_blocks_entire_mixed_batch(version,target):
    r=run_case(version,'batch_bare_fact',target,source_consent_guard=True)
    assert r.gate_result=='deny' and r.never_save_invariant=='PASS'

@pytest.mark.parametrize('version',list(VERSIONS))
def test_unattended_gate_does_not_touch_attended_review(version):
    r=run_case(version,'bare_fact','user',attended=True)
    assert r.gate_result=='apply'
    assert r.never_save_invariant=='FAIL'

@pytest.mark.parametrize('string,expected',[
    ('asked NOT to save this',True),
    ('User asked us not to remember that',True),
    ("don't save this",True),
    ('Please do not store this',True),
    ("Please don't retain my synthetic code",False),
    ('User opted out of recording these details',False),
    ('I do not want this in memory',False),
    ('User did not consent to remembering their code',False),
    ("please don't save my synthetically generated key",False),
    ('private note with no refusal terms',False),
])
def test_regex_detector_scope(string,expected):
    assert bool(pr_116846._BG_NO_SAVE_RE.search(string)) is expected

@pytest.mark.parametrize('target',['user','memory'])
@pytest.mark.parametrize('case',['self_report','bare_fact'])
def test_local_combination_still_persists_prohibited_fact(target,case):
    r=run_case('LOCAL-combination',case,target)
    assert r.never_save_invariant=='FAIL'
    if target=='user' or case=='self_report':
        assert r.gate_result=='stage' and r.pending_payload_marker_found
    else:
        assert r.gate_result=='apply' and r.memory_marker_found
