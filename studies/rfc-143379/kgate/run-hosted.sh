#!/usr/bin/env bash
# Hosted-only; CI-parity setup must already export HERMES_PYTHON.
set -euo pipefail
STUDY_ROOT=$(git rev-parse --show-toplevel)
OUT="$STUDY_ROOT/rfc-out"
mkdir -p "$OUT"
: "${HERMES_PYTHON:?source the canonical CI setup first}"
: "${RUNNER_TEMP:?hosted runner scratch directory required}"
MAIN_SHA=e82bf01eec9bb58848209b07f0bc7d8895a39f9b
MAIN_ROOT="$RUNNER_TEMP/rfc143379-pinned-main"
git rev-parse HEAD > "$OUT/study-sha.txt"
git fetch --depth=1 https://github.com/NousResearch/hermes-agent.git "$MAIN_SHA"
git worktree add --detach "$MAIN_ROOT" "$MAIN_SHA"
cd "$MAIN_ROOT"
git rev-parse HEAD > "$OUT/main-sha.txt"
export HERMES_HOME="$RUNNER_TEMP/rfc143379-test-home"
export HERMES_RUNTIME_DIR="$RUNNER_TEMP/rfc143379-test-runtime"
export PYTHONPATH="$MAIN_ROOT:$STUDY_ROOT/studies/rfc-143379/kgate"
export RFC_OUT="$OUT"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
unset OPENAI_API_KEY OPENROUTER_API_KEY ANTHROPIC_API_KEY NOUS_API_KEY
cp "$STUDY_ROOT/studies/rfc-143379/kgate/frozen-manifest.json" "$OUT/manifest.json"
"$HERMES_PYTHON" -m pytest -q --noconftest \
  "$STUDY_ROOT/studies/rfc-143379/demote-gap/test_demote_gap.py" \
  "$STUDY_ROOT/studies/rfc-143379/kgate/test_stats.py" \
  "$STUDY_ROOT/studies/rfc-143379/kgate/test_harness.py" \
  --junitxml="$OUT/study-tests.xml" 2>&1 | tee "$OUT/study-tests.log"
"$HERMES_PYTHON" "$STUDY_ROOT/studies/rfc-143379/kgate/harness.py" \
  --out "$OUT" 2>&1 | tee "$OUT/harness.log"
# Original upstream tests are separate from study tests and retain their conftest.
"$HERMES_PYTHON" -m pytest -q tests/agent/test_ghost_skill_pruning.py \
  --junitxml="$OUT/upstream-ghost-tests.xml" 2>&1 | tee "$OUT/upstream-ghost-tests.log"
