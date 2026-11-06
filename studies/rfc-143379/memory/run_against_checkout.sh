#!/usr/bin/env bash
# Runs EXISTING Hermes tests in an already-selected checkout/branch.
# It does not check out, push, create branches/PRs, or post any comments.
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo 'Usage: ./run_against_checkout.sh /path/to/hermes-checkout' >&2
  exit 2
fi
repo="$1"
if [[ ! -f "$repo/tools/memory_tool_store.py" ]]; then
  echo 'Not a Hermes checkout' >&2
  exit 2
fi
cd "$repo"
printf 'Repository: %s\n' "$(git rev-parse --show-toplevel)"
printf 'Revision: %s\n' "$(git rev-parse HEAD)"
printf 'Branch: %s\n' "$(git branch --show-current)"
files=(
  tests/tools/test_memory_tool.py
  tests/tools/test_memory_patch_action.py
  tests/tools/test_memory_target_contract.py
)
if [[ -f tests/tools/test_memory_chain_docs.py ]]; then
  files+=(tests/tools/test_memory_chain_docs.py)
fi
if [[ -f tests/tools/test_write_gate.py ]]; then
  files+=(tests/tools/test_write_gate.py)
fi
if [[ -x scripts/run_tests.sh ]]; then
  scripts/run_tests.sh "${files[@]}" --file-retries 0
else
  python -m pytest -q "${files[@]}"
fi
