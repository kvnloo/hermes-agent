#!/usr/bin/env bash
# AI prepared by OpenAI Codex; evidence-only replay, no production fix.
set -u
: "${HERMES_PYTHON:?Supply an official PM-managed Python 3.14 interpreter}"
"$HERMES_PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 14), "Python 3.14 required"' || exit 2
packet_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(git -C "$packet_dir" rev-parse --show-toplevel) || exit 2
replay_root=$(mktemp -d "${TMPDIR:-/tmp}/hermes-b4-replay.XXXXXX") || exit 2
replay_source="$replay_root/source"
git -C "$repo_root" worktree add --detach "$replay_source" b30f95ac4a80d2f6dbe3aa01001b0524314f6d74 || exit 2
cp -- "$packet_dir/probe.py" "$replay_source/tests/tui_gateway/test_prompt_truncate_durable_scope.py" || exit 2
cd -- "$replay_source" || exit 2
HERMES_HOME="$replay_root/build-home" HERMES_RUNTIME_DIR="$replay_root/build-runtime"   "$HERMES_PYTHON" -m pm.build_env --source "$replay_source" --out "$replay_root/test-env" --group dev --group test || exit 2
HERMES_PYTHON="$replay_root/test-env/bin/python" HERMES_TEST_FILE_RETRIES=0   scripts/run_tests.sh -j 1 tests/tui_gateway/test_prompt_truncate_durable_scope.py -v -s
result=$?
printf 'Replay artifacts retained at %s; expected RED runner exit is 1, actual %s\n' "$replay_root" "$result"
exit "$result"
