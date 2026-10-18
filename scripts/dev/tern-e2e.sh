#!/bin/sh
# One entry point; all lifecycle logic is in the test-only runner.
# `tern-e2e.sh <worktree> a11y` audits AX/buttons/focus without model calls;
# signed-out native windows stay BLOCKED, distinct from tern-serve receipts.
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
exec python3 "$root/ui-tsp/e2e/lane.py" "$@"
