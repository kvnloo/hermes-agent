#!/usr/bin/env bash
set -euo pipefail
mkdir -p z06-results
exec > >(tee z06-results/transcript.log) 2>&1
set -x
hostname
python3 -m pm.build_env --source . --out .venv-z06 --group dev --group test
export HERMES_PYTHON="$PWD/.venv-z06/bin/python"
export HERMES_TEST_FILE_RETRIES=0
cp z06-proof/test_routes.py tests/plugins/test_z06_routes_replay.py
scripts/run_tests.sh tests/tools/test_tool_search.py tests/agent/test_tool_search_oauth_recall.py tests/agent/test_anthropic_mcp_prefix_strip.py tests/plugins/test_transform_tool_result_hook.py tests/plugins/test_z06_routes_replay.py -j 2 -s --file-retries 0 | tee z06-results/green-all.log
"$HERMES_PYTHON" -m ruff check tools/tool_search.py tools/tool_search_catalog.py tools/tool_search_validation.py tests/agent/test_tool_search_oauth_recall.py | tee z06-results/lint.log
sha256sum tools/tool_search.py tools/tool_search_catalog.py tools/tool_search_validation.py tests/agent/test_tool_search_oauth_recall.py > z06-results/tested-hashes.txt
printf 'all_checks_exit=0\n'
