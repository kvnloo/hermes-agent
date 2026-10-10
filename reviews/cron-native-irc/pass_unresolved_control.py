"""Unshipping diagnostic experiment: default the shared resolver fallback flag.

This monkeypatch affects all callers of the shared resolver in the test process
that omit pass_unresolved_references. It is not scoped to the new validator and
is not a ready fix: the adjacent Telegram negative intentionally still fails.
Only this explanatory docstring was corrected after the recorded test runs.
"""


def pytest_sessionstart(session):
    from tools import send_message_targets

    original = send_message_targets.resolve_send_target

    def with_cron_policy(platform_name, target_ref, **kwargs):
        kwargs.setdefault("pass_unresolved_references", True)
        return original(platform_name, target_ref, **kwargs)

    send_message_targets.resolve_send_target = with_cron_policy
