#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "${1:?Pass an exact-head checkout with the evidence test overlaid}" && pwd)
packet=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
node_dir=$(dirname "$(command -v node)")
home=$(mktemp -d "${TMPDIR:-/tmp}/hermes-timestamp-evidence.XXXXXX")
mkdir -p "$home/hermes" "$home/runtime" "$home/.cache"
printf 'Disposable test home: %s\n' "$home"
cd "$repo"
exec env -i HOME="$home" HERMES_HOME="$home/hermes" HERMES_RUNTIME_DIR="$home/runtime" \
  XDG_CACHE_HOME="$home/.cache" TZ=UTC LANG=C.UTF-8 PATH="$node_dir:/usr/bin:/bin" \
  NODE_OPTIONS="--require=$packet/offline-guard.cjs" \
  npm run test --prefix ui-tui -- \
  src/__tests__/streamingTimestampContinuity.test.tsx \
  src/__tests__/streamingTimestamps.test.tsx \
  src/__tests__/messages.test.ts \
  src/__tests__/turnControllerNotice.test.ts \
  src/__tests__/turnControllerTodos.test.ts \
  --reporter=verbose
