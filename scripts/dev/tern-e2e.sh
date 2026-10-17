#!/bin/sh
# One entry point; all lifecycle logic is in the test-only runner.
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
exec python3 "$root/ui-tsp/e2e/lane.py" "$@"
