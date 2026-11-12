#!/usr/bin/env bash
set -euo pipefail

log() { printf '[electron-e2e-display] %s\n' "$*" >&2; }

cleanup_pid=""
cleanup() {
  if [[ -n "$cleanup_pid" ]]; then
    kill "$cleanup_pid" 2>/dev/null || true
    wait "$cleanup_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
  log "using configured display (DISPLAY=${DISPLAY:-unset}, WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset})"
elif [[ -n "${XDG_RUNTIME_DIR:-}" ]]; then
  shopt -s nullglob
  sockets=("$XDG_RUNTIME_DIR"/wayland-*)
  shopt -u nullglob
  for socket in "${sockets[@]}"; do
    [[ "$socket" == *.lock ]] && continue
    if [[ -S "$socket" ]]; then
      export WAYLAND_DISPLAY="${socket##*/}"
      log "using detected Wayland session $WAYLAND_DISPLAY"
      break
    fi
  done
fi

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  if command -v Xvfb >/dev/null 2>&1; then
    display_number="${HERMES_E2E_XVFB_DISPLAY:-99}"
    export DISPLAY=":$display_number"
    log "starting Xvfb on $DISPLAY"
    Xvfb "$DISPLAY" -screen 0 1440x1000x24 -nolisten tcp >"${TMPDIR:-/tmp}/hermes-electron-xvfb.log" 2>&1 &
    cleanup_pid=$!
    for _ in {1..100}; do
      [[ -S "/tmp/.X11-unix/X$display_number" ]] && break
      kill -0 "$cleanup_pid" 2>/dev/null || { log "Xvfb exited; see ${TMPDIR:-/tmp}/hermes-electron-xvfb.log"; exit 1; }
      sleep 0.05
    done
    [[ -S "/tmp/.X11-unix/X$display_number" ]] || { log 'Xvfb did not become ready'; exit 1; }
  elif command -v xvfb-run >/dev/null 2>&1; then
    log 'using xvfb-run fallback'
    exec xvfb-run -a -s '-screen 0 1440x1000x24 -nolisten tcp' "$@"
  else
    log 'no graphical session or Xvfb found; install Xvfb for headless CI'
    exit 2
  fi
fi

"$@"
