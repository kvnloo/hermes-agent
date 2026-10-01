#!/usr/bin/env bash
# Sequential $0 receipt runs for staging/prefix-parity-journeys. Run INSIDE harness/sandbox.sh from the
# staging worktree root (loopback-only netns, live home masked). Each arm patch is applied to the clean
# branch tree, run, then reverted with `git checkout -- <files>` (never git stash).
# r02: RAW and MAIN_REF are inputs (MAIN_REF pins the main SHA the adjacent + LEAF runs use); adds the
# ungated RED run, ungated ACP arms, the E09 smoke and the candidate-leaf unit runs (LEAF).
# r03: no local paths in this file. The staging dir is found from this script's location; RAW (a
# directory under <staging>/private/, never published) and PROBE_TMP (the probes' scratch root, which
# appears in the prompt they record; r02 used <probe-tmp>) are required inputs. The as-run r02 copy
# (paths inline) is kept private in private/harness-r02/.
set -uo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW="${RAW:?set RAW to a private raw directory, e.g. <staging>/private/raw-rNN}"
MAIN_REF="${MAIN_REF:-main}"
H=$R/harness
mkdir -p "$RAW"
export HERMES_TEST_FILE_RETRIES=0 HERMES_TEST_FILE_TIMEOUT=900 PROBE_TMP="${PROBE_TMP:?set PROBE_TMP}"
C17=tests/e2e/core/history/test_prefix_stability.py
LEAF_TESTS="tests/acp_adapter/test_server.py tests/acp_adapter/test_acp_commands.py"
PY="$HERMES_PYTHON"
ONLY="${ONLY:-}"

want() { [ -z "$ONLY" ] || [[ ",$ONLY," == *",$1,"* ]]; }

meta() {  # name rc start end
  printf '{"run":"%s","rc":%s,"started":"%s","ended":"%s","wall_s":%s,"head":"%s","dirty":"%s","load1_end":"%s"}\n' \
    "$1" "$2" "$(date -u -d @"$3" +%FT%TZ)" "$(date -u -d @"$4" +%FT%TZ)" "$(( $4 - $3 ))" \
    "$(git rev-parse HEAD)" "$(git status --porcelain --untracked-files=no | tr '\n' ' ')" \
    "$(cut -d' ' -f1 /proc/loadavg)" >> "$RAW/runs.jsonl"
}

pyt() {  # name files... [extra pytest args]
  local name=$1; shift
  local t0; t0=$(date +%s)
  bash scripts/run_tests.sh -j 2 --include-integration "$@" -q -rxX --tb=line \
    --junitxml="$RAW/$name.junit.xml" > "$RAW/$name.log" 2>&1
  local rc=$?
  meta "$name" "$rc" "$t0" "$(date +%s)"
}

c17() {  # name [extra pytest args...]
  local name=$1; shift
  pyt "$name" "$C17" "$@"
}

probe() {  # name [probe args...]
  local name=$1; shift
  local t0; t0=$(date +%s)
  "$PY" "$H/journey_probe.py" --label "$name" --out "$RAW/$name.json" "$@" > "$RAW/$name.log" 2>&1
  local rc=$?
  meta "$name" "$rc" "$t0" "$(date +%s)"
}

arm() {  # name patch[+patch...] command...
  local name=$1 patches=$2 p; shift 2
  for p in ${patches//+/ }; do
    git apply "$R/arms/$p" || { echo "{\"run\":\"$name\",\"error\":\"$p did not apply\"}" >> "$RAW/runs.jsonl"; git checkout -- .; return; }
  done
  sha256sum $(git diff --name-only) > "$RAW/$name.arm-files.sha256"
  git diff > "$RAW/$name.arm.diff"
  "$@"
  git checkout -- $(git diff --name-only)
}

leaf() {  # name [git apply --include glob]  (candidate leaf at unit level, on the MAIN_REF checkout)
  local name=$1 inc=${2:-}
  if [ -n "$inc" ]; then
    git apply --include="$inc" "$R/arms/candidate-acp-compress-no-nesting.patch" \
      || { echo "{\"run\":\"$name\",\"error\":\"leaf patch did not apply\"}" >> "$RAW/runs.jsonl"; return; }
    git diff > "$RAW/$name.arm.diff"
  fi
  pyt "$name" $LEAF_TESTS --tb=short
  if [ -n "$inc" ]; then git checkout -- $(git diff --name-only); fi
}

# Egress canary from inside this sandbox: must be blocked; loopback must work.
"$PY" - > "$RAW/egress_canary.json" <<'EOF'
import json, socket
def probe(h, p):
    s = socket.socket(); s.settimeout(3)
    try:
        s.connect((h, p)); return "CONNECTED"
    except OSError as e:
        return f"blocked errno={e.errno}"
    finally:
        s.close()
srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
print(json.dumps({"egress_1.1.1.1:443": probe("1.1.1.1", 443), "loopback": probe("127.0.0.1", srv.getsockname()[1])}))
EOF

want slice_full && c17 slice_full
want red_ungated && arm red_ungated red-ungate-known.patch c17 red_ungated -k acp_restarts
want e07_probe && probe e07_probe
want e08_probe && probe e08_probe --identity
want nc1_full && arm nc1_full nc1-per-request-timestamp.patch c17 nc1_full
want nc2_full && arm nc2_full nc2-restart-rebuild-nonce.patch c17 nc2_full
for a in fixA:acp-fixA-no-cached-system-message.patch hp76224:acp-hp76224-in-place-compaction.patch both:acp-both.patch; do
  n=${a%%:*}; p=${a#*:}
  want "acp_$n" && arm "acp_${n}_c17" "$p" c17 "acp_${n}_c17" -k acp_restarts
  want "acp_$n" && arm "acp_${n}_ungated" "$p+red-ungate-known.patch" c17 "acp_${n}_ungated" -k acp_restarts
  want "acp_$n" && arm "acp_${n}_probe" "$p" probe "acp_${n}_probe" --journeys acp_restarts
done
if want e09_smoke; then
  t0=$(date +%s)
  "$PY" "$H/e09_first_delta.py" --surfaces gw,api,acp --reps 5 --warmup 1 --delay 0.05 --order AB \
    --label e09_smoke --out "$RAW/e09_smoke.json" > "$RAW/e09_smoke.log" 2>&1
  meta e09_smoke $? "$t0" "$(date +%s)"
fi
if want adjacent || want leaf; then
  BR=$(git rev-parse HEAD)
  if want adjacent; then
    for f in tests/e2e/core/parity/test_entrypoint_parity.py tests/e2e/core/history/test_transcript_ledger.py; do
      pyt "adjacent_branch_$(basename "$f" .py)" "$f"
    done
  fi
  git checkout -q --detach "$MAIN_REF"
  if want adjacent; then
    for f in tests/e2e/core/parity/test_entrypoint_parity.py tests/e2e/core/history/test_transcript_ledger.py $C17; do
      pyt "adjacent_main_$(basename "$f" .py)" "$f"
    done
  fi
  if want leaf; then
    leaf leaf_base                                   # main as is
    leaf leaf_test_only 'tests/*'                    # RED: updated unit test, unchanged production line
    leaf leaf_full '*'                               # GREEN: fix + updated test
    leaf leaf_fix_old_test 'acp_adapter/*'           # the current unit test pins the buggy argument
  fi
  git checkout -q --detach "$BR"
fi
echo done
