"""An explicit failed required check is never masked by a skipped dependent (#149974)."""

from hermes_cli import kanban_pr_acceptance as acceptance


SHA = "a" * 40
PR = "https://github.com/acme/repo/pull/7"


def test_failed_required_check_outweighs_skipped_dependent(monkeypatch):
    """A failed build and its skipped preview share a failed check suite."""
    def fake_api(endpoint, *, query=None, paginate=False, profile_home=None):
        if endpoint == "graphql":
            return {"data": {"repository": {"pullRequest": {
                "headRefOid": SHA, "baseRefName": "main", "state": "OPEN",
                "baseRef": {"branchProtectionRule": {"requiredStatusChecks": [
                    {"context": "a-preview", "app": {"databaseId": 1}},
                    {"context": "z-build", "app": {"databaseId": 1}},
                ]}}}}}}
        if "/rules/branches/" in endpoint or "/statuses" in endpoint:
            return [[]]
        if "/check-runs" in endpoint:
            return [{"total_count": 2, "check_runs": [
                {"id": 42, "name": "a-preview", "head_sha": SHA, "app": {"id": 1},
                 "status": "completed", "conclusion": "skipped", "check_suite": {"id": 7}},
                {"id": 43, "name": "z-build", "head_sha": SHA, "app": {"id": 1},
                 "status": "completed", "conclusion": "failure", "check_suite": {"id": 7}},
            ]}]
        if "/check-suites" in endpoint:
            return [{"total_count": 1, "check_suites": [
                {"id": 7, "status": "completed", "conclusion": "failure"},
            ]}]
        if "/pulls/" in endpoint:
            return {"head": {"sha": SHA}, "base": {"ref": "main"}, "state": "open"}
        raise AssertionError(f"unexpected endpoint {endpoint}")

    monkeypatch.setattr(acceptance, "_api", fake_api)
    receipt = acceptance.collect_acceptance("acme/repo", PR)

    assert receipt["ok"] is False
    assert receipt["classification"] == "failure"
    assert [(check["name"], check["classification"]) for check in receipt["checks"]] == [
        ("a-preview", "infra"), ("z-build", "failure"),
    ]
