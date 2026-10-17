# Shared settings for the demo-capture scripts. Source, don't run.
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
repo=$(CDPATH= cd -- "$here/../.." && pwd)

# Short on purpose: Unix socket paths are limited to ~100 bytes.
DEMO_STATE=${DEMO_STATE:-/tmp/hermes-demo-capture}
# Where takes are written. Raw frames are large (1080p120: ~1 GB per second): use a real disk.
DEMO_OUT=${DEMO_OUT:-$here/out}
DEMO_OUTPUT=${DEMO_OUTPUT:-DEMOCAP}
DEMO_THEME=${DEMO_THEME:-hermes}
sock=$DEMO_STATE/ctl.sock

ctl() { tern ctl --control "$sock" "$@"; }

# Hyprland's socket name, for shells (agents, ssh) that don't carry it.
if [ -z "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
  HYPRLAND_INSTANCE_SIGNATURE=$(ls -t "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/hypr" 2>/dev/null | head -1)
  export HYPRLAND_INSTANCE_SIGNATURE
fi

load_preset() {
  preset=$1
  [ -f "$preset" ] || preset=$here/presets/$1.env
  [ -f "$preset" ] || { echo "no preset $1 (see $here/presets)" >&2; exit 2; }
  . "$preset"
}

# The capture output's origin in the global layout, and the stage window's address.
output_xy() { hyprctl monitors -j | python3 -c "
import json,sys
for m in json.load(sys.stdin):
    if m['name']=='$DEMO_OUTPUT': print(m['x'], m['y'])"; }
stage_window() { hyprctl clients -j | python3 -c "
import json,sys
pid=int(open('$DEMO_STATE/tern.pid').read())
for c in json.load(sys.stdin):
    if c['pid']==pid: print(c['address'])"; }

# Likewise the Wayland socket: a shell that outlived a compositor restart still names the old one.
runtime=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
if [ ! -S "$runtime/${WAYLAND_DISPLAY:-none}" ]; then
  WAYLAND_DISPLAY=$(ls -t "$runtime" 2>/dev/null | grep -E '^wayland-[0-9]+$' | head -1)
  export WAYLAND_DISPLAY
fi

# Changing outputs or windows can warp the pointer onto the stage, and with
# focus-follows-mouse that hands it your keyboard. Remember where you were
# and put you back; the stage window itself is made unfocusable.
focus_save() {
  saved_cursor=$(hyprctl cursorpos | tr -d ',')
  saved_window=$(hyprctl activewindow -j | python3 -c "import json,sys; print(json.load(sys.stdin).get('address',''))")
}
focus_restore() {
  [ -z "${saved_cursor:-}" ] || hyprctl dispatch movecursor $saved_cursor > /dev/null
  [ -z "${saved_window:-}" ] || hyprctl dispatch focuswindow "address:$saved_window" > /dev/null
}
