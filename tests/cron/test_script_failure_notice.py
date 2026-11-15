"""Regression for NousResearch/hermes-agent#156227: pre-model errors stay out of chat."""

from cron.scheduler import _summarize_cron_failure_for_delivery


def test_pre_model_cron_script_failures_do_not_echo_output():
    errors = (
        ("Script exited with code 1\nstderr:\n"
         "provider 429 timeout; token=opaque-sensitive-value", "script failed"),
        ("Script execution failed: provider 503 timeout; token=opaque-sensitive-value", "script failed"),
        ("monitor_url fetch failed: provider 429 timeout; token=opaque-sensitive-value", "monitor source failed"),
        ("monitor_url must be http(s): 'token=opaque-sensitive-value'", "monitor source failed"),
    )
    # Both script-only jobs and agent-backed jobs can fail *before* model invocation.
    for no_agent in (False, True):
        job = {"id": "cron-check", "name": "Daily check", "no_agent": no_agent}
        for error, cause in errors:
            notice = _summarize_cron_failure_for_delivery(job, error)
            assert cause in notice.lower()
            assert "token=opaque-sensitive-value" not in notice
            assert "provider" not in notice.lower()
            assert "fallback chain" not in notice.lower()
