#!/bin/sh
set -eu
: "${BUN_BIN:?BUN_BIN is required}"
: "${BEND_PATCHED_MAIN:?BEND_PATCHED_MAIN is required}"
exec "$BUN_BIN" "$BEND_PATCHED_MAIN" "$@"
