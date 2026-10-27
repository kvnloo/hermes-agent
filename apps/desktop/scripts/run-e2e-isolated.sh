#!/usr/bin/env bash
set -euo pipefail

# Run Electron/Playwright inside a Wayland-native compositor whose backend has
# no host output or physical input devices. Never fall back to the live desktop:
# a missing compositor is safer than stealing the user's focus or pointer.
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ACCOUNT_HOME=$(getent passwd "$(id -u)" | cut -d: -f6)
LOCAL_CAGE_ROOT=${HERMES_TEST_CAGE_ROOT:-"$ACCOUNT_HOME/.local/opt/hermes-test-compositor"}

if [[ -n ${HERMES_TEST_CAGE:-} ]]; then
  CAGE=$HERMES_TEST_CAGE
elif command -v cage >/dev/null 2>&1; then
  CAGE=$(command -v cage)
elif [[ -x "$LOCAL_CAGE_ROOT/usr/bin/cage" ]]; then
  CAGE="$LOCAL_CAGE_ROOT/usr/bin/cage"
  export LD_LIBRARY_PATH="$LOCAL_CAGE_ROOT/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
else
  printf '%s\n' \
    'Hermes GUI tests refused to use the live desktop.' \
    'Install cage (Wayland-native) or set HERMES_TEST_CAGE to its executable.' >&2
  exit 78
fi

RUNTIME_DIR=$(mktemp -d "${XDG_RUNTIME_DIR:-/tmp}/hermes-gui-test.XXXXXX")
chmod 700 "$RUNTIME_DIR"
cleanup() { rm -rf "$RUNTIME_DIR"; }
trap cleanup EXIT INT TERM

export XDG_RUNTIME_DIR=$RUNTIME_DIR
export WLR_BACKENDS=headless
export WLR_HEADLESS_OUTPUTS=1
export WLR_NO_HARDWARE_CURSORS=1
export HERMES_GUI_TEST_ISOLATED=1
unset DISPLAY WAYLAND_DISPLAY HYPRLAND_INSTANCE_SIGNATURE SWAYSOCK

if (($#)); then
  command=("$@")
else
  command=(npx playwright test e2e/ --reporter=list)
fi

cd "$ROOT"
exec "$CAGE" -- "${command[@]}"
