#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
variant=${1:-head}
zone=${2:-UTC}
case "$variant" in base|head) ;; *) exit 2;; esac
case "$zone" in UTC|America/New_York) ;; *) exit 2;; esac
home=$(mktemp -d "$root/home-$variant-${zone//\//_}-XXXXXX")
mkdir -p "$home"/{hermes,runtime,.cache}
cd "$root/$variant"
exec env -i HOME="$home" HERMES_HOME="$home/hermes" HERMES_RUNTIME_DIR="$home/runtime" XDG_CACHE_HOME="$home/.cache" TZ="$zone" LANG=C.UTF-8 npm_config_update_notifier=false npm_config_offline=true PATH=/workspace/shared/hermes-replay-qualification/home/hermes/tools/node-26.7.0-linux-x64/bin:/usr/bin:/bin NODE_OPTIONS="--require=$root/offline-guard.cjs" npm run test --prefix ui-tui -- src/__tests__/gatewayTimestampContinuity.test.tsx --reporter=verbose
