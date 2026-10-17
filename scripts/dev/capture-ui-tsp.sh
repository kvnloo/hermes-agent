#!/bin/sh
# Run ui-tsp in an authenticated Tern pane and save one shot.
# By default use a private headless client; an owner-checked relay may reuse an existing client.
set -eu

root=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
iso=${TSP_ISO_DIR:-/tmp/ui-tsp-capture}
sway_bin=${SWAY_BIN:-/home/kvn/.local/opt/sway-nested/bin/sway}
sway_lib=${SWAY_LIB:-/home/kvn/.local/opt/sway-nested/lib}
swaymsg=${SWAYMSG:-/home/kvn/.local/opt/sway-nested/bin/swaymsg}
python=${HERMES_PYTHON:-/workspace/hermes-home/hermes-agent/venv/bin/python}
ready_timeout=${TSP_READY_TIMEOUT:-10}
owner_helper=$root/scripts/dev/capture-ui-tsp-owner.py
reuse_tern_pid=${TSP_REUSE_TERN_PID:-}
reuse_control_port=${TSP_REUSE_TERN_CONTROL_PORT:-}
reuse_daemon_socket=${TSP_REUSE_TERN_DAEMON_SOCKET:-}
reuse_runtime_dir=${TSP_REUSE_TERN_RUNTIME_DIR:-}
expected_pane_id=${TSP_EXPECTED_PANE_ID:-}
control_mode=isolated
if [ -n "$reuse_tern_pid$reuse_control_port$reuse_daemon_socket$reuse_runtime_dir" ]; then
  if [ -z "$reuse_tern_pid" ] || [ -z "$reuse_control_port" ] || [ -z "$reuse_daemon_socket" ] || [ -z "$reuse_runtime_dir" ] || [ -z "$expected_pane_id" ]; then
    echo "reused Tern control requires PID, local TCP port, daemon socket, runtime directory and expected pane ID" >&2
    exit 1
  fi
  case "$reuse_tern_pid:$reuse_control_port:$expected_pane_id" in
    *[!0-9:]*|:*|*::*|*:) echo "reused Tern PID, port and pane ID must be integers" >&2; exit 1 ;;
  esac
  control_mode=relay
fi
if [ "$control_mode" = isolated ] && [ ! -x "$sway_bin" ]; then
  echo "missing sway at $sway_bin" >&2
  exit 1
fi
if [ ! -x "$python" ]; then
  echo "missing HERMES_PYTHON at $python" >&2
  exit 1
fi
if [ ! -f "$owner_helper" ]; then
  echo "missing control owner helper at $owner_helper" >&2
  exit 1
fi
case "$ready_timeout" in
  ''|*[!0-9]*)
    echo "TSP_READY_TIMEOUT must be an integer from 1 to 60 seconds" >&2
    exit 1
    ;;
esac
if [ "$ready_timeout" -lt 1 ] || [ "$ready_timeout" -gt 60 ]; then
  echo "TSP_READY_TIMEOUT must be an integer from 1 to 60 seconds" >&2
  exit 1
fi

mkdir -p "$iso"
iso=$(CDPATH= cd -- "$iso" && pwd -P)
out=${TSP_SHOT_DIR:-"$iso/shots"}
tsp_dist=$root/ui-tsp/dist

read_tsp_freshness() {
  node "$root/scripts/build/freshness.mjs" \
    --source "$root" --product tsp --out "$tsp_dist"
}

if ! current=$(read_tsp_freshness); then
  echo "unable to read the ui-tsp build receipt" >&2
  exit 1
fi
if [ "$current" != true ]; then
  echo "building stale ui-tsp product" >&2
  node "$root/scripts/build/tsp.mjs"
  if ! current=$(read_tsp_freshness); then
    echo "unable to verify the rebuilt ui-tsp product" >&2
    exit 1
  fi
  if [ "$current" != true ]; then
    echo "rebuilt ui-tsp product is not current" >&2
    exit 1
  fi
fi

sock=$iso/ctl.sock
owner_record=$iso/run/control-owner.json
if [ -L "$iso/run" ] || { [ -e "$iso/run" ] && [ ! -d "$iso/run" ]; }; then
  echo "refusing a non-directory or symlinked private runtime directory" >&2
  exit 1
fi
mkdir -p "$iso/run" "$iso/sway" "$iso/plugins" "$iso/hermes-home" "$out"
chmod 700 "$iso/run"
capture_lock=$iso/.ui-tsp-capture.lock
if ! mkdir "$capture_lock" 2>/dev/null; then
  echo "another ui-tsp capture already owns $iso" >&2
  exit 1
fi
trap 'rmdir "$capture_lock" 2>/dev/null || true' 0
cat > "$iso/sway/config" << EOF
output * resolution 984x713
exec tern --control "$sock" "$iso"
EOF

validate_control_owner() {
  if [ "$control_mode" = relay ]; then
    python3 "$owner_helper" validate \
      --socket "$sock" --record "$owner_record" --iso "$iso" --expected-mode relay \
      --native-pid "$reuse_tern_pid" --native-port "$reuse_control_port" \
      --native-daemon "$reuse_daemon_socket" --native-runtime "$reuse_runtime_dir"
  else
    python3 "$owner_helper" validate \
      --socket "$sock" --record "$owner_record" --iso "$iso" --expected-mode isolated \
      --runtime "$iso/run" --daemon "$iso/daemon.sock" --config "$iso/sway/config"
  fi
}

if [ -L "$sock" ]; then
  echo "refusing a symlinked Tern control socket" >&2
  exit 1
elif [ -e "$sock" ]; then
  if [ ! -S "$sock" ]; then
    echo "refusing a non-socket Tern control path" >&2
    exit 1
  fi
  if ! validate_control_owner; then
    echo "refusing an unverified or stale Tern control socket" >&2
    exit 1
  fi
else
  if [ -e "$owner_record" ] || [ -L "$owner_record" ]; then
    echo "refusing a stale Tern control owner record without its socket" >&2
    exit 1
  fi
  if [ "$control_mode" = relay ]; then
    python3 "$owner_helper" serve-relay \
      --socket "$sock" --record "$owner_record" --iso "$iso" \
      --native-pid "$reuse_tern_pid" --native-port "$reuse_control_port" \
      --native-daemon "$reuse_daemon_socket" --native-runtime "$reuse_runtime_dir" \
      > "$iso/control-relay.log" 2>&1 &
    relay_pid=$!
    i=0
    while { [ ! -S "$sock" ] || [ ! -f "$owner_record" ]; } && [ "$i" -lt 50 ]; do
      if ! kill -0 "$relay_pid" 2>/dev/null; then
        break
      fi
      i=$((i + 1))
      sleep 0.1
    done
    if [ ! -S "$sock" ] || [ ! -f "$owner_record" ]; then
      echo "unable to establish owned local Tern control relay" >&2
      cat "$iso/control-relay.log" >&2 || true
      exit 1
    fi
  else
    env -u WAYLAND_DISPLAY -u SWAYSOCK -u DISPLAY -u TERN_PANE -u TERN_PANE_SOCKET \
      -u TERN_WINDOW_KEY -u TERN_WINDOW_SOCKET -u TERN_IDENTITY \
      WLR_BACKENDS=headless WLR_RENDERER=gles2 WLR_HEADLESS_OUTPUTS=1 \
      XDG_RUNTIME_DIR="$iso/run" \
      LD_LIBRARY_PATH="$sway_lib" \
      TERN_CONFIG_DIR="$iso" \
      TERN_DAEMON_SOCKET="$iso/daemon.sock" \
      "$sway_bin" --config "$iso/sway/config" > "$iso/sway.log" 2>&1 &
    sway_pid=$!
    i=0
    while [ ! -S "$sock" ] && [ "$i" -lt 50 ]; do
      i=$((i + 1))
      sleep 0.1
    done
    if [ -L "$sock" ] || [ ! -S "$sock" ]; then
      echo "isolated tern did not open a real control socket at $sock" >&2
      tail -20 "$iso/sway.log" >&2 || true
      exit 1
    fi
    if ! python3 "$owner_helper" record \
      --socket "$sock" --record "$owner_record" --iso "$iso" \
      --runtime "$iso/run" --daemon "$iso/daemon.sock" --config "$iso/sway/config" \
      --supervisor-pid "$sway_pid"; then
      echo "unable to attest the isolated Tern control socket" >&2
      exit 1
    fi
  fi
fi
if ! validate_control_owner; then
  echo "Tern control socket owner changed before use" >&2
  exit 1
fi

launch_nonce_file=$(mktemp "$iso/.ui-tsp-launch.XXXXXXXX")
launch_nonce=${launch_nonce_file##*.}
run_script=$iso/run-ui-tsp-$launch_nonce.sh
entry_owner=$iso/tsp-entry-$launch_nonce.js
if [ -e "$run_script" ] || [ -e "$entry_owner" ]; then
  echo "refusing to reuse an existing ui-tsp launch identity" >&2
  exit 1
fi

state=
cwd=
running=
label=
focus_id=
busy=
gate_open=
state_field() {
  printf '%s' "$state" | python3 -c '
import json
import sys

state = json.load(sys.stdin)
if not isinstance(state, dict) or state.get("ok") is not True:
    raise SystemExit(2)
focused = state.get("focused")
if not isinstance(focused, dict):
    raise SystemExit(2)
name = sys.argv[1]
if name == "gate_open":
    gate = state.get("gate")
    if not isinstance(gate, dict):
        print("false")
        raise SystemExit(0)
    applies = gate.get("applies")
    open_gate = (
        "error" in gate
        and gate.get("phase") == "off"
        and gate.get("error") is None
        and (
            applies is False
            or (applies is True and gate.get("signed_in") is True)
        )
    )
    print("true" if open_gate else "false")
    raise SystemExit(0)
value = focused.get(name)
if name == "busy":
    if not isinstance(value, bool):
        raise SystemExit(2)
    print("true" if value else "false")
elif name == "running":
    if name not in focused:
        raise SystemExit(2)
    if value is None:
        print("null")
    elif isinstance(value, str) and value.strip():
        print(value)
    else:
        raise SystemExit(2)
elif name == "id":
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise SystemExit(2)
    print(value)
elif isinstance(value, str):
    print(value)
else:
    raise SystemExit(2)
' "$1"
}
read_focused_state() {
  validate_control_owner || return 1
  state=$(tern ctl --control "$sock" state 2>/dev/null) || return 1
  cwd=$(state_field cwd 2>/dev/null) || return 1
  running=$(state_field running 2>/dev/null) || return 1
  label=$(state_field label 2>/dev/null) || return 1
  focus_id=$(state_field id 2>/dev/null) || return 1
  busy=$(state_field busy 2>/dev/null) || return 1
  gate_open=$(state_field gate_open 2>/dev/null) || return 1
}
assert_ok() {
  printf '%s' "$1" | python3 -c '
import json
import sys
try:
    result = json.load(sys.stdin)
except (json.JSONDecodeError, TypeError):
    raise SystemExit(2)
raise SystemExit(0 if isinstance(result, dict) and result.get("ok") is True else 1)
'
}

if ! read_focused_state; then
  echo "unable to read isolated Tern target state before launch" >&2
  exit 1
fi
if [ "$gate_open" != true ]; then
  echo "refusing ui-tsp launch because the native account gate is not confirmed open" >&2
  exit 1
fi
if [ "$label" != hermes ] || [ "$cwd" != "$root" ] || [ -z "$focus_id" ]; then
  echo "refusing ui-tsp launch in an unowned Tern target: label=$label cwd=$cwd id=$focus_id" >&2
  exit 1
fi
if [ -n "$expected_pane_id" ] && [ "$focus_id" != "$expected_pane_id" ]; then
  echo "refusing ui-tsp launch because focused Tern pane $focus_id is not the expected pane $expected_pane_id" >&2
  exit 1
fi
if [ "$busy" != false ] || [ "$running" != null ]; then
  echo "refusing ui-tsp launch because the isolated Tern target is busy: $running" >&2
  exit 1
fi
target_id=$focus_id

ln -s "$tsp_dist/entry.js" "$entry_owner"
cat > "$run_script" << EOF
#!/bin/sh
cd "$root"
export HERMES_TERN=1
export HERMES_PYTHON='$python'
export HERMES_PYTHON_SRC_ROOT='$root'
export HERMES_HOME='$iso/hermes-home'
export HERMES_TSP_CAPTURE_NONCE='$launch_nonce'
export TERM_PROGRAM=tern
unset TMUX STY ZELLIJ
mkdir -p "\$HERMES_HOME"
exec node '$entry_owner'
EOF
chmod +x "$run_script"
if ! validate_control_owner; then
  echo "refusing ui-tsp run because the Tern control socket owner changed" >&2
  exit 1
fi

if ! run_result=$(tern ctl --control "$sock" run "$run_script"); then
  echo "Tern rejected the ui-tsp launch command" >&2
  exit 1
fi
if ! assert_ok "$run_result"; then
  echo "Tern did not confirm the ui-tsp launch with .ok=true" >&2
  printf '%s\n' "$run_result" >&2
  exit 1
fi

ready_attempts=$((ready_timeout * 10))
i=0
ready=0
owner_running=
while [ "$i" -lt "$ready_attempts" ]; do
  if read_focused_state; then
    if [ "$gate_open" != true ]; then
      echo "native account gate closed while ui-tsp was starting" >&2
      exit 1
    fi
    if [ "$focus_id" != "$target_id" ] || [ "$label" != hermes ] || [ "$cwd" != "$root" ]; then
      echo "ui-tsp launch lost its isolated Tern owner: id=$focus_id label=$label cwd=$cwd" >&2
      exit 1
    fi
    if [ "$busy" = true ]; then
      case "$running" in
        *"$launch_nonce"*)
          owner_running=$running
          ready=1
          break
          ;;
        *)
          echo "ui-tsp target is busy under a different command: $running" >&2
          exit 1
          ;;
      esac
    elif [ "$running" != null ] && [ -n "$running" ]; then
      echo "ui-tsp target reports a command without foreground ownership: $running" >&2
      exit 1
    fi
  fi
  i=$((i + 1))
  sleep 0.1
done
if [ "$ready" -ne 1 ]; then
  echo "isolated ui-tsp frontend did not become ready within ${ready_timeout}s" >&2
  printf 'last state: %s\n' "${state:-unavailable}" >&2
  exit 1
fi

validate_owner() {
  read_focused_state || return 1
  [ "$gate_open" = true ] &&
    [ "$focus_id" = "$target_id" ] &&
    [ "$label" = hermes ] &&
    [ "$cwd" = "$root" ] &&
    [ "$busy" = true ] &&
    [ "$running" = "$owner_running" ]
}
if ! validate_owner; then
  echo "ui-tsp owner or native account gate changed before screenshot capture" >&2
  exit 1
fi

shot_nonce_file=$(mktemp "$iso/.ui-tsp-capture.XXXXXXXX")
shot_name=ui-tsp-hello-${shot_nonce_file##*.}
shot_target=$iso/target/shots/tern/live/$shot_name.png
if [ -e "$shot_target" ]; then
  echo "refusing to reuse an existing Tern screenshot: $shot_target" >&2
  exit 1
fi
shot_result=
shot_status=0
if ! validate_control_owner; then
  echo "refusing ui-tsp screenshot because the Tern control socket owner changed" >&2
  exit 1
fi
if ! shot_result=$(tern ctl --control "$sock" shot "$shot_name"); then
  shot_status=1
fi
if ! validate_owner; then
  echo "ui-tsp owner or native account gate changed during screenshot capture" >&2
  exit 1
fi
if [ "$shot_status" -ne 0 ]; then
  echo "Tern failed to capture the requested screenshot" >&2
  exit 1
fi
if ! assert_ok "$shot_result"; then
  echo "Tern did not confirm the screenshot with .ok=true" >&2
  printf '%s\n' "$shot_result" >&2
  exit 1
fi
if [ ! -s "$shot_target" ]; then
  echo "Tern did not produce the requested screenshot: $shot_target" >&2
  exit 1
fi
if ! python3 - "$shot_target" <<'PY'
import pathlib
import struct
import sys
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
         (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))


def invalid():
    raise ValueError("invalid PNG")


def check_png(path):
    data = pathlib.Path(path).read_bytes()
    if len(data) < len(SIGNATURE) or data[:len(SIGNATURE)] != SIGNATURE:
        invalid()

    position = len(SIGNATURE)
    chunk_index = 0
    width = height = bit_depth = color_type = interlace = None
    seen_palette = seen_idat = idat_ended = seen_iend = False
    decoder = None
    expected_data = decoded_data = 0
    next_filter = None
    filter_offsets = None

    def row_starts(layout):
        offset = 0
        for rows, row_bytes in layout:
            for _ in range(rows):
                yield offset
                offset += row_bytes + 1

    def consume_output(output):
        nonlocal decoded_data, next_filter
        end = decoded_data + len(output)
        if end > expected_data:
            invalid()
        while next_filter is not None and next_filter < end:
            if output[next_filter - decoded_data] > 4:
                invalid()
            next_filter = next(filter_offsets, None)
        decoded_data = end

    def consume_idat(payload):
        pending = payload
        while True:
            output = decoder.decompress(pending, 65536)
            consume_output(output)
            if decoder.unused_data:
                invalid()
            pending = decoder.unconsumed_tail
            if pending:
                continue
            if len(output) == 65536 and not decoder.eof:
                pending = b""
                continue
            break

    while position < len(data):
        if len(data) - position < 12:
            invalid()
        length = struct.unpack_from(">I", data, position)[0]
        type_start = position + 4
        payload_start = position + 8
        payload_end = payload_start + length
        if payload_end + 4 > len(data):
            invalid()
        chunk_type = data[type_start:type_start + 4]
        payload = data[payload_start:payload_end]
        stored_crc = struct.unpack_from(">I", data, payload_end)[0]
        if (any(not (65 <= byte <= 90 or 97 <= byte <= 122) for byte in chunk_type)
                or chunk_type[2] & 0x20
                or zlib.crc32(payload, zlib.crc32(chunk_type)) & 0xffffffff != stored_crc):
            invalid()
        position = payload_end + 4

        if chunk_index == 0 and chunk_type != b"IHDR":
            invalid()
        if seen_idat and chunk_type != b"IDAT":
            idat_ended = True
        if chunk_type == b"IDAT" and idat_ended:
            invalid()

        if chunk_type == b"IHDR":
            if chunk_index != 0 or width is not None or length != 13:
                invalid()
            width, height, bit_depth, color_type, compression, filtering, interlace = (
                struct.unpack(">IIBBBBB", payload))
            valid_depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8),
                            4: (8, 16), 6: (8, 16)}
            if (not 0 < width <= 0x7fffffff or not 0 < height <= 0x7fffffff
                    or bit_depth not in valid_depths.get(color_type, ())
                    or compression != 0 or filtering != 0 or interlace not in (0, 1)):
                invalid()
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
            bits_per_pixel = channels * bit_depth
            passes = ((0, 0, 1, 1),) if interlace == 0 else ADAM7
            layout = []
            for x_start, y_start, x_step, y_step in passes:
                pass_width = max(0, (width - x_start + x_step - 1) // x_step)
                pass_height = max(0, (height - y_start + y_step - 1) // y_step)
                if pass_width and pass_height:
                    row_bytes = (pass_width * bits_per_pixel + 7) // 8
                    layout.append((pass_height, row_bytes))
                    expected_data += pass_height * (row_bytes + 1)
            filter_offsets = row_starts(layout)
            next_filter = next(filter_offsets, None)
            decoder = zlib.decompressobj()
        elif chunk_type == b"PLTE":
            if (width is None or seen_palette or seen_idat or color_type in (0, 4)
                    or not 0 < length <= 768 or length % 3):
                invalid()
            entries = length // 3
            if color_type == 3 and entries > 1 << bit_depth:
                invalid()
            seen_palette = True
        elif chunk_type == b"IDAT":
            if width is None or (color_type == 3 and not seen_palette):
                invalid()
            seen_idat = True
            consume_idat(payload)
        elif chunk_type == b"IEND":
            if length != 0 or not seen_idat or position != len(data):
                invalid()
            seen_iend = True
            break
        elif chunk_type in (b"IHDR", b"PLTE", b"IDAT", b"IEND"):
            invalid()
        elif not chunk_type[0] & 0x20:
            invalid()
        chunk_index += 1

    if not seen_iend or decoder is None:
        invalid()
    consume_output(decoder.flush())
    if (not decoder.eof or decoder.unused_data or decoded_data != expected_data
            or next_filter is not None):
        invalid()


try:
    check_png(sys.argv[1])
except (OSError, ValueError, OverflowError, struct.error, zlib.error):
    sys.exit(1)
PY
then
  echo "Tern screenshot is not a complete, decodable PNG image: $shot_target" >&2
  exit 1
fi
if ! validate_owner; then
  echo "ui-tsp owner or native account gate changed during screenshot capture" >&2
  exit 1
fi
cp "$shot_target" "$out/ui-tsp-hello.png"
printf 'label=%s\nrunning=%s\nshot=%s\n' "$label" "$owner_running" "$shot_target"
