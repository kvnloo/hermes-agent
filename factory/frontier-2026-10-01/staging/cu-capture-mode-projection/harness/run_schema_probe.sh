#!/usr/bin/env bash
# X1 runner: one bwrap sandbox per driver version. No network namespace route, fresh HOME/HERMES_HOME,
# the live Hermes home masked except the test interpreter's venv (read-only), pid namespace, die-with-parent.
# Usage: HERMES_PYTHON=<venv python> LIVE_HERMES_ROOT=<live install root to mask> \
#        [CUA_RELEASES=<dir of cua-driver release dirs>] run_schema_probe.sh <worktree> <run_dir> <version>...
set -euo pipefail
WT=$1; RUN=$2; shift 2
PY=${HERMES_PYTHON:?set HERMES_PYTHON to the test venv python}
VENV=$(dirname "$(dirname "$PY")")
LIVE=${LIVE_HERMES_ROOT:?set LIVE_HERMES_ROOT to the live Hermes install root (masked in the sandbox)}
RELEASES=${CUA_RELEASES:-$HOME/.cua-driver/packages/releases}
HARNESS=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$RUN"
for v in "$@"; do
  BIN=$RELEASES/${v}-x86_64-unknown-linux-gnu/cua-driver
  H=$RUN/home-$v
  mkdir "$H"   # fails if it already exists (fresh home per run)
  mkdir -p "$H/.hermes"
  bwrap --ro-bind / / --dev /dev --proc /proc \
    --tmpfs "$LIVE" --ro-bind "$VENV" "$VENV" \
    --tmpfs "$HOME/.ssh" --tmpfs "$HOME/.config/gh" \
    --bind "$RUN" "$RUN" --tmpfs /tmp \
    --unshare-net --unshare-pid --die-with-parent --clearenv \
    --setenv HOME "$H" --setenv HERMES_HOME "$H/.hermes" \
    --setenv PATH /usr/bin:/bin --setenv PROBE_WORKTREE "$WT" --setenv PROBE_FORBIDDEN "$LIVE:$HOME/.hermes" \
    --setenv HERMES_CUA_DRIVER_CMD "$BIN" --setenv CUA_DRIVER_RS_TELEMETRY_ENABLED 0 \
    --setenv PYTHONDONTWRITEBYTECODE 1 --setenv PROBE_DISPATCH "${PROBE_DISPATCH:-0}" \
    --chdir "$WT" \
    timeout 90 "$PY" "$HARNESS/schema_probe.py" > "$RUN/probe-$v.json" 2> "$RUN/probe-$v.stderr" \
    || echo "{\"version\": \"$v\", \"runner_rc\": $?}" > "$RUN/probe-$v.rc.json"
done
