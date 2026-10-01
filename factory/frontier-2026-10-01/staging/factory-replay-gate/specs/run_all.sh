#!/usr/bin/env bash
# Runs each pre-registered spec once through the gate runner at the staging commit. Serial; -j 2 per cell.
#
#   W=<runner-wt> XF_REPO=<repo.git> XF_PYTHON=<venv-python> HOME=<test-home> specs/run_all.sh <spec id>...
#
# Every machine-specific location comes from the environment, so nothing local is written down here:
#   W          a worktree checked out at the staging commit (the runner under test)
#   XF_REPO    a git dir that holds every SHA the specs pin
#   XF_PYTHON  the interpreter for the runner and its cells (read-only)
#   HOME       an isolated test home, never the real one; HERMES_HOME defaults to $HOME/.hermes
#   XF_SCRATCH where run directories go (default: $W/.xf-runs)
# Receipts are written next to the specs, to ../receipts/<id>.json.
set -u
: "${W:?set W to the runner worktree}" "${XF_REPO:?set XF_REPO to the git dir}" "${XF_PYTHON:?set XF_PYTHON}"
real_home=$(getent passwd "$(id -u)" | cut -d: -f6)
if [ "$(realpath -m "$HOME")" = "$(realpath -m "$real_home")" ]; then
  echo "refusing: HOME is the real home; point it at an isolated test home" >&2
  exit 2
fi
STAGE=$(cd "$(dirname "$0")/.." && pwd)
export HOME HERMES_HOME=${HERMES_HOME:-$HOME/.hermes}
cd "$W"
for id in "$@"; do
  echo "=== $id $(date -u +%FT%TZ) runner=$(git -C "$W" rev-parse --short=10 HEAD)"
  "$XF_PYTHON" -m evals._factory.gate_runner run --work-order "$STAGE/specs/$id.wo.json" \
     --repo "$XF_REPO" --scratch "${XF_SCRATCH:-$W/.xf-runs}" --python "$XF_PYTHON" --out "$STAGE/receipts/$id.json"
  echo "rc=$? $(date -u +%FT%TZ)"
done
