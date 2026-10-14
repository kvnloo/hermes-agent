#!/usr/bin/env bash
set -euo pipefail
: "${HERMES_PYTHON:?Set HERMES_PYTHON to a PM-built dev/test interpreter for this checkout.}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
test "$(git hash-object gateway/run_agent_cache.py)" = "c3bd5885125d536dbc68963d3edc5512a911dd66"
RUN_HOME="$(mktemp -d "${TMPDIR:-/tmp}/hermes-pin-reuse-home.XXXXXX")"
trap 'rm -rf -- "$RUN_HOME"' EXIT
env -i PATH="$PATH" HOME="$RUN_HOME" HERMES_PYTHON="$HERMES_PYTHON" \
  bash scripts/run_tests.sh -j 1 --file-retries 0 \
  tests/gateway/test_internal_event_pin_wiring.py \
  -k 'test_sethome_refreshes_pinned_context_for_preserving_turn or test_sethome_unchanged_config_keeps_pin_verbatim' \
  -p evidence.pin_reuse_20261014.offline_guard --tb=short
