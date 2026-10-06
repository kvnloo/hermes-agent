#!/bin/sh
# The stage: a private Hyprland output and an isolated Tern window on it.
#
#   stage.sh up [PRESET]   create the output, start Tern there, size the window
#   stage.sh fit PRESET    re-size the window and set the output's refresh rate
#   stage.sh theme NAME    switch the stage's Tern theme (default: hermes)
#   stage.sh down          close Tern and remove the output
#
# Nothing here touches your own Tern windows, config, panes or monitors: the
# stage Tern has its own config dir, daemon socket and HOME (so its own omp
# agent dir, where themes/hermes.json is installed for it).
set -eu
. "$(dirname "$0")/lib.sh"

# The output is taller than any preset, so the window sits clear of a status
# bar and nothing but the window is in the capture region.
OUT_W=1920
OUT_H=1200

fit() {
  CAP_STREAM=0
  load_preset "$1"
  focus_save
  set -- $(output_xy)
  hyprctl keyword monitor "$DEMO_OUTPUT,${OUT_W}x${OUT_H}@$CAP_FPS,${1}x${2},1" > /dev/null
  sleep 1
  addr=$(stage_window)
  rx=$(( (OUT_W - CAP_W) / 2 ))
  ry=$(( (OUT_H - CAP_H) / 2 ))
  hyprctl dispatch setfloating "address:$addr" > /dev/null
  hyprctl dispatch resizewindowpixel "exact $CAP_W $CAP_H,address:$addr" > /dev/null
  hyprctl dispatch movewindowpixel "exact $(( $1 + rx )) $(( $2 + ry )),address:$addr" > /dev/null
  # Never take the keyboard: the stage is driven through its control socket.
  hyprctl dispatch setprop "address:$addr" no_focus 1 > /dev/null 2>&1 \
    || hyprctl dispatch setprop "address:$addr" nofocus 1 > /dev/null 2>&1 || true
  echo "$rx,$ry,$CAP_W,$CAP_H" > "$DEMO_STATE/region"
  echo "$CAP_FPS" > "$DEMO_STATE/fps"
  echo "${CAP_STREAM:-0}" > "$DEMO_STATE/stream"
  focus_restore
  sleep 1
  echo "stage: ${CAP_W}x${CAP_H} window on $DEMO_OUTPUT at $CAP_FPS Hz"
}

case "${1:-}" in
up)
  mkdir -p "$DEMO_STATE/home/.omp/agent/themes" "$DEMO_STATE/hermes-home" "$DEMO_OUT"
  chmod 700 "$DEMO_STATE"
  cp "$here/themes/"*.json "$DEMO_STATE/home/.omp/agent/themes/"
  printf 'theme:\n  dark: %s\n  light: light\n' "$DEMO_THEME" > "$DEMO_STATE/home/.omp/agent/config.yml"
  [ -f "$DEMO_STATE/settings.json" ] || echo '{"theme":"Dark","material":"Solid"}' > "$DEMO_STATE/settings.json"

  focus_save
  hyprctl monitors -j | grep -q "\"name\": \"$DEMO_OUTPUT\"" || hyprctl output create headless "$DEMO_OUTPUT" > /dev/null
  ws=$(hyprctl monitors -j | python3 -c "
import json,sys
for m in json.load(sys.stdin):
    if m['name']=='$DEMO_OUTPUT': print(m['activeWorkspace']['id'])")

  # A socket file can outlive its Tern: ask it, don't just look.
  ctl state > /dev/null 2>&1 || rm -f "$sock"
  if [ ! -S "$sock" ]; then
    cat > "$DEMO_STATE/tern.sh" << EOS
#!/bin/sh
echo \$\$ > "$DEMO_STATE/tern.pid"
exec env -u TERN_PANE -u TERN_PANE_SOCKET -u TERN_WINDOW_KEY -u TERN_WINDOW_SOCKET -u TERN_IDENTITY \\
  HOME="$DEMO_STATE/home" TERN_CONFIG_DIR="$DEMO_STATE" TERN_DAEMON_SOCKET="$DEMO_STATE/daemon.sock" \\
  tern --control "$sock" "$DEMO_STATE" > "$DEMO_STATE/tern.log" 2>&1
EOS
    chmod +x "$DEMO_STATE/tern.sh"
    hyprctl dispatch exec "[workspace $ws silent] $DEMO_STATE/tern.sh" > /dev/null
    i=0
    while [ ! -S "$sock" ] && [ "$i" -lt 60 ]; do i=$((i + 1)); sleep 0.25; done
    [ -S "$sock" ] || { echo "stage: Tern did not start (see $DEMO_STATE/tern.log)" >&2; exit 1; }
    sleep 2
  fi
  focus_restore
  ctl appearance dark > /dev/null
  ctl style solid > /dev/null

  # What the scenarios run. Each records its pid so the next take can clear the stage.
  #   hermes.sh [DESIGN] [SPLASH_FPS]   the real frontend on a real gateway
  #   splash.sh [DESIGN] [SPLASH_FPS]   the splash gallery, held on one design
  # DEMO_HERMES_HOME names the Hermes home to use; the default is an empty one
  # under the stage, which has no model provider: fine for the launch, not for a prompt.
  # DEMO_HERMES_MODEL / DEMO_HERMES_PROVIDER pick the model for the take's
  # session only, the way `hermes --model --provider` does; no config is written.
  # DEMO_HERMES_CWD is the directory the session works in (keep the agent out of real repos).
  cat > "$DEMO_STATE/hermes.sh" << EOS
#!/bin/sh
echo \$\$ > "$DEMO_STATE/app.pid"
cd "$repo"
export HERMES_TERN=1 TERM_PROGRAM=tern HERMES_PYTHON_SRC_ROOT="$repo"
export HERMES_PYTHON="\${HERMES_PYTHON:-${HERMES_PYTHON:-/workspace/hermes-home/hermes-agent/venv/bin/python}}"
export HERMES_HOME="${DEMO_HERMES_HOME:-$DEMO_STATE/hermes-home}"
export HERMES_TUI_SPLASH="\${1:-kerykeion}" HERMES_TUI_SPLASH_FPS="\${2:-}"
[ -z "${DEMO_HERMES_MODEL:-}" ] || export HERMES_MODEL="${DEMO_HERMES_MODEL:-}" HERMES_INFERENCE_MODEL="${DEMO_HERMES_MODEL:-}"
[ -z "${DEMO_HERMES_PROVIDER:-}" ] || export HERMES_TUI_PROVIDER="${DEMO_HERMES_PROVIDER:-}" HERMES_INFERENCE_PROVIDER="${DEMO_HERMES_PROVIDER:-}"
[ -z "${DEMO_HERMES_CWD:-}" ] || export HERMES_TUI_CWD="${DEMO_HERMES_CWD:-}"
unset TMUX STY ZELLIJ
exec node "$repo/ui-tsp/dist/entry.js" 2> "$DEMO_STATE/hermes.err"
EOS
  cat > "$DEMO_STATE/splash.sh" << EOS
#!/bin/sh
echo \$\$ > "$DEMO_STATE/app.pid"
cd "$repo/ui-tsp"
export TERM_PROGRAM=tern HERMES_TUI_SPLASH_FPS="\${2:-}"
unset TMUX STY ZELLIJ
exec "$repo/node_modules/.bin/tsx" scripts/splash-demo.ts --design "\${1:-kerykeion}" 2> "$DEMO_STATE/splash.err"
EOS
  chmod +x "$DEMO_STATE/hermes.sh" "$DEMO_STATE/splash.sh"
  [ -f "$repo/ui-tsp/dist/entry.js" ] || (cd "$repo/ui-tsp" && npm run bundle > /dev/null)
  fit "${2:-1080p120}"
  echo "stage: up. control socket $sock, theme $(ctl state | python3 -c 'import json,sys; print(json.load(sys.stdin).get("theme_dark"))')"
  ;;
fit) fit "$2" ;;
theme)
  ctl theme dark "$2" | grep -q '"ok":true' || { echo "stage: Tern has no theme called $2" >&2; exit 1; }
  echo "stage: theme $2"
  ;;
down)
  focus_save
  [ -S "$sock" ] && ctl quit > /dev/null 2>&1 || true
  sleep 1
  rm -f "$sock"
  hyprctl output remove "$DEMO_OUTPUT" > /dev/null 2>&1 || true
  focus_restore
  echo "stage: down"
  ;;
*)
  sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
  exit 2
  ;;
esac
