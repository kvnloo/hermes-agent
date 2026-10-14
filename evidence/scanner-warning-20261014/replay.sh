#!/usr/bin/env bash
set -euo pipefail
: "${HERMES_PYTHON:?Set HERMES_PYTHON to a fresh PM-built dev/test interpreter.}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
test "$(git hash-object agent/skill_commands.py)" = "9e44f48516b3c3d20621c77ccf156e2ab6644ebe"
RUN_HOME="$(mktemp -d "${TMPDIR:-/tmp}/hermes-scanner-warning-home.XXXXXX")"
printf 'Disposable HOME: %s\n' "$RUN_HOME"
exec env -i PATH="$PATH" HOME="$RUN_HOME" HERMES_PYTHON="$HERMES_PYTHON" \
  bash scripts/run_tests.sh \
  tests/agent/test_skill_collision_warning_contract.py \
  tests/agent/test_skill_cache_thrash.py --file-retries 0 -j 1
