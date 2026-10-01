#!/usr/bin/env bash
set -uo pipefail
export S WT HERMES_PYTHON
P=$S/st-edit-fuzzy; R="bash $P/run_arm_v4.sh"
C=tests/tools/test_fuzzy_match_wrong_region.py
CT="$C tests/tools/test_fuzzy_match.py tests/tools/test_file_tools_live.py"
ADJ="tests/acp_adapter/test_edit_approval.py tests/hermes_cli/test_shared_metrics_harness.py tests/tools/test_file_operations.py tests/tools/test_file_operations_delete.py tests/tools/test_file_operations_edge_cases.py tests/tools/test_file_tools.py tests/tools/test_file_tools_live.py tests/tools/test_fuzzy_match.py tests/tools/test_patch_already_applied.py tests/tools/test_patch_multimatch_locations.py tests/tools/test_patch_parser.py tests/tools/test_patch_v4a_gate.py tests/tools/test_patch_ws_diagnosis.py"
echo "### start $(date -u +%FT%TZ)"
CARRIER_TESTS=0 $R base 1 commit-only $C
for rep in 1 2 3; do
  for arm in base c54575 c125376-leaf both leaf+fold both+fold; do echo "## $arm rep$rep"; $R $arm $rep proof $CT; done
  for arm in c126502 c126502+leaf+fold; do echo "## $arm rep$rep"; CARRIER_TESTS=0 $R $arm $rep proof $C; done
done
for s in floor single_line foldin; do echo "## sabotage $s"; SABOTAGE=$s $R both+fold 1 sabotage-$s $CT; done
for arm in base c54575 c125376-leaf both+fold c126502; do echo "## adjacent $arm"; CARRIER_TESTS=0 $R $arm 1 adjacent $ADJ; done
echo "### end $(date -u +%FT%TZ)"
