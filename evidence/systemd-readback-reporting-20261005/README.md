# HOLD: service repair readback failure is reported as success

Owner PR: https://github.com/NousResearch/hermes-agent/pull/133030
Original head and parent of this evidence: `f5849f4ad6c6b560b2b091d2eae17c821cb47b9f`.
PR account: tomasWade. Original commit author: haotianyu <haotianyu1@163.com>.
The original owner commit and ancestry are preserved without reimplementation.

Checked 2026-10-05: owner head unchanged, PR open, one existing comment reports
9/9 install-binding tests. No existing readback-failure consumer or review found.
This is independent diagnostic evidence for the owner, not a competing fix.

[Consumer test](../../tests/pm/test_repair_service_readback.py) runs the real
`pm.cli._heal_generation_launcher_service_units` against a temporary poisoned
systemd unit definition. Refresh is stubbed to return False without changing the
file. A readable control and a post-refresh PermissionError case differ only in
whether the helper can read the same unchanged file. All subprocess.run calls
are blocked; no systemctl, launchctl, services, real configurations or credentials
are used.

Canonical command on the exact original owner source plus this test:

```sh
HERMES_PYTHON=/workspace/.onboarding/hermes-tests/bin/python scripts/run_tests.sh -j 2 --file-retries 0 tests/pm/test_repair_service_readback.py
```

Result: **1 passed, 1 failed**. The readable control passes. In the unreadable
case, refresh returned False and the unit still contains the original generation
launcher, yet stdout says:

```text
✓ Rewrote the gateway user service off the dependency-generation launcher
```

The expected behavior is no verified-rewrite claim after a failed readback.
The failed test asserts that contract without xfail or production changes.
In the owner helper, the post-refresh OSError handler assigns `still = None`,
which the following branch treats as proof of successful repair. The same shape
exists in its launchd sibling; this test makes no executed macOS/launchd claim.
It does not exercise real service refresh, PM environment rebuilding, or the
full `hermes pm repair` command. Current main does not contain this new helper;
the comparison is two controlled scenarios on the owner head, not a claim that
current main regressed. No hosted CI was run for this evidence.

Root independent review approved the narrow negative proof before commit.
The owner head predates `scripts/check` and has no such script; no current-main
checker result is claimed. Local whitespace/fatal-Ruff results are recorded in
the workspace handoff receipt. Existing parked systemd124082 integration and
previous qualified refs remain unchanged.
