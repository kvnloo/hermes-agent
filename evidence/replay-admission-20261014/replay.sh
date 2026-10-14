#!/usr/bin/env bash
# Evidence-only replay. The expected result is two guard assertion failures.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
: "${HERMES_PYTHON:?Set HERMES_PYTHON to this checkout's canonical PM test interpreter}"
: "${HOME:?Use a disposable HOME for test execution}"
"$HERMES_PYTHON" -c 'import sys, pytest; assert sys.version_info[:2] == (3, 14); print(sys.version); print("pytest", pytest.__version__)'
echo 'Expected: 11 passed and 2 failed; this is a reproducer, not a passing fix.'
exec scripts/run_tests.sh \
  tests/gateway/test_compression_replay_delivery_safety.py \
  tests/gateway/test_compression_exhaustion_replay.py \
  tests/gateway/test_auto_reset_clean_context.py \
  tests/gateway/test_duplicate_user_message.py \
  --file-retries 0 -j 1
