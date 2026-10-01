#!/usr/bin/env bash
# HERMES_CUA_DRIVER_CMD for E23: run the container's pinned cua-driver as `pn` inside the desktop session, over
# `docker exec -i` stdio. `manifest` is passed through, but its mcp_invocation.command (a CONTAINER path such as
# /opt/cua-driver/cua-driver) is rewritten to this wrapper, so Hermes' production startup (runtime-contract check,
# manifest-discovered MCP invocation, --no-overlay probe) runs unchanged and every hop lands back in the container.
# E23_LOCAL_DRIVER=<binary> swaps docker for a local binary: used only to self-test this wrapper.
set -euo pipefail
SELF=$(readlink -f "$0")
run() {
  if [ -n "${E23_LOCAL_DRIVER:-}" ]; then
    CUA_DRIVER_RS_TELEMETRY_ENABLED=0 exec "$E23_LOCAL_DRIVER" "$@"
  fi
  exec docker exec -i -u pn "${E23_CONTAINER:-e23-desktop}" bash -c \
    'set -a; . /tmp/bd/env; set +a; export CUA_DRIVER_RS_TELEMETRY_ENABLED=0; exec cua-driver "$@"' _ "$@"
}
if [ "${1:-}" = "manifest" ]; then
  set +e
  out=$( (run "$@") ); rc=$?
  set -e
  [ "$rc" = 0 ] || { printf '%s\n' "$out"; exit "$rc"; }
  printf '%s' "$out" | E23_SELF="$SELF" /usr/bin/python3 -c '
import json, os, sys
m = json.load(sys.stdin)
inv = m.get("mcp_invocation")
if isinstance(inv, dict):
    inv["command"] = os.environ["E23_SELF"]
json.dump(m, sys.stdout)'
  exit 0
fi
run "$@"
