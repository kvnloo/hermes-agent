#!/bin/sh
# Run ui-tsp inside a private headless Tern and save one shot.
# Does not touch the user desktop or the user Tern daemon.
set -eu

root=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
iso=${TSP_ISO_DIR:-/tmp/ui-tsp-capture}
sway_bin=${SWAY_BIN:-/home/kvn/.local/opt/sway-nested/bin/sway}
sway_lib=${SWAY_LIB:-/home/kvn/.local/opt/sway-nested/lib}
swaymsg=${SWAYMSG:-/home/kvn/.local/opt/sway-nested/bin/swaymsg}
python=${HERMES_PYTHON:-/workspace/hermes-home/hermes-agent/venv/bin/python}
out=${TSP_SHOT_DIR:-"$iso/shots"}
sock=$iso/ctl.sock

if [ ! -x "$sway_bin" ]; then
  echo "missing sway at $sway_bin" >&2
  exit 1
fi
if [ ! -x "$python" ]; then
  echo "missing HERMES_PYTHON at $python" >&2
  exit 1
fi

if [ ! -f "$root/ui-tsp/dist/entry.js" ]; then
  echo "building ui-tsp/dist/entry.js" >&2
  (cd "$root/ui-tsp" && npm run bundle)
fi

mkdir -p "$iso/run" "$iso/sway" "$iso/plugins" "$out"
chmod 700 "$iso/run"
cat > "$iso/sway/config" << EOF
output * resolution 984x713
exec tern --control $sock $iso
EOF

if [ ! -S "$sock" ]; then
  env -u WAYLAND_DISPLAY -u SWAYSOCK -u DISPLAY -u TERN_PANE -u TERN_PANE_SOCKET \
    -u TERN_WINDOW_KEY -u TERN_WINDOW_SOCKET -u TERN_IDENTITY \
    WLR_BACKENDS=headless WLR_RENDERER=gles2 WLR_HEADLESS_OUTPUTS=1 \
    XDG_RUNTIME_DIR="$iso/run" \
    LD_LIBRARY_PATH="$sway_lib" \
    TERN_CONFIG_DIR="$iso" \
    TERN_DAEMON_SOCKET="$iso/daemon.sock" \
    "$sway_bin" --config "$iso/sway/config" > "$iso/sway.log" 2>&1 &
  echo $! > "$iso/sway.pid"
  i=0
  while [ ! -S "$sock" ] && [ "$i" -lt 50 ]; do
    i=$((i + 1))
    sleep 0.1
  done
fi
if [ ! -S "$sock" ]; then
  echo "isolated tern did not open $sock" >&2
  tail -20 "$iso/sway.log" >&2 || true
  exit 1
fi

cat > "$iso/run-ui-tsp.sh" << EOF
#!/bin/sh
cd "$root"
export HERMES_TERN=1
export HERMES_PYTHON='$python'
export HERMES_PYTHON_SRC_ROOT='$root'
export HERMES_HOME='$iso/hermes-home'
export TERM_PROGRAM=tern
unset TMUX STY ZELLIJ
mkdir -p "\$HERMES_HOME"
exec node '$root/ui-tsp/dist/entry.js'
EOF
chmod +x "$iso/run-ui-tsp.sh"
mkdir -p "$iso/hermes-home"

tern ctl --control "$sock" run "$iso/run-ui-tsp.sh" >/dev/null
sleep 2
state=$(tern ctl --control "$sock" state)
cwd=$(printf '%s' "$state" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("focused",{}).get("cwd"))')
if [ "$cwd" != "$iso" ]; then
  echo "refusing to shot a pane whose cwd is $cwd" >&2
  exit 1
fi
running=$(printf '%s' "$state" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("focused",{}).get("running"))')
label=$(printf '%s' "$state" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("focused",{}).get("label"))')
tern ctl --control "$sock" shot ui-tsp-hello >/dev/null
shot=$(find "$iso" "$root" /tmp -path '*/target/shots/tern/live/ui-tsp-hello.png' -print -quit 2>/dev/null || true)
if [ -n "$shot" ]; then
  cp "$shot" "$out/ui-tsp-hello.png"
fi
printf 'label=%s\nrunning=%s\nshot=%s\n' "$label" "$running" "${shot:-missing}"
