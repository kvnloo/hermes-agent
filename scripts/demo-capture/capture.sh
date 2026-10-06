#!/bin/sh
# Record one take from the stage.
#
#   capture.sh NAME [SECONDS] [SCENARIO] [ARG]
#
# NAME      the take's name: writes $DEMO_OUT/NAME.raw (+ .times, .json)
# SECONDS   how long to record (default 4). Frames are held in RAM for the
#           burst: 1080p120 is ~1 GB/s, 720p180 ~0.65 GB/s.
# SCENARIO  a scenarios/*.scn file driven through Tern's control endpoint
#           while recording; {arg} in it is ARG (a splash design, say)
#
# Run `stage.sh up PRESET` first; the preset there sets size and rate.
set -eu
. "$(dirname "$0")/lib.sh"

name=${1:?usage: capture.sh NAME [SECONDS] [SCENARIO] [ARG]}
seconds=${2:-4}
scenario=${3:-}
arg=${4:-}
[ -S "$sock" ] || { echo "capture: no stage (run stage.sh up)" >&2; exit 1; }
[ -x "$here/build/burstcap" ] || "$here/build.sh" > /dev/null
fps=$(cat "$DEMO_STATE/fps")
region=$(cat "$DEMO_STATE/region")
frames=$(python3 -c "print(int($fps * $seconds * 1.03) + 8)")
mkdir -p "$DEMO_OUT"

# The burst lives in RAM until it ends: refuse one that would not fit.
[ "$(cat "$DEMO_STATE/stream" 2> /dev/null)" = 1 ] || python3 - "$region" "$frames" << 'EOS' || exit 1
import sys
w, h = (int(v) for v in sys.argv[1].split(',')[2:])
need = w * h * 4 * int(sys.argv[2])
avail = next(int(l.split()[1]) * 1024 for l in open('/proc/meminfo') if l.startswith('MemAvailable'))
if need > avail * 0.6:
    sys.exit(f"capture: this take needs {need / 2**30:.1f} GiB of RAM and {avail / 2**30:.1f} GiB is free; "
             "record fewer seconds or use a smaller preset")
EOS

# Clear the stage: every take gets a fresh tab, and so a fresh shell. (Reusing
# one is fragile: a program stopped mid-frame can leave half a protocol
# message in the shell's input, and the next command is swallowed by it.)
tabs() { ctl state | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["tabs"]))'; }
if [ -f "$DEMO_STATE/app.pid" ]; then
  kill "$(cat "$DEMO_STATE/app.pid")" 2> /dev/null || true
  rm -f "$DEMO_STATE/app.pid"
fi
ctl tab new > /dev/null
sleep 0.4
while [ "$(tabs)" -gt 1 ]; do
  ctl tab 1 > /dev/null
  ctl tab close > /dev/null
  sleep 0.3
done
ctl theme dark "$DEMO_THEME" > /dev/null
# Let the pane settle at its final size: a program reads it once, as it starts.
sleep 1.5

if [ -n "$scenario" ]; then
  [ -f "$scenario" ] || scenario=$here/scenarios/$scenario.scn
  # {repo} and {state} in a scenario are this checkout and the stage's state dir.
  sed -e "s#{repo}#$repo#g" -e "s#{state}#$DEMO_STATE#g" -e "s#{arg}#$arg#g" "$scenario" > "$DEMO_STATE/take.scn"
  ( tern ctl --control "$sock" --file "$DEMO_STATE/take.scn" > "$DEMO_STATE/take.log" 2>&1 & )
fi

if [ "$(cat "$DEMO_STATE/stream" 2> /dev/null)" = 1 ]; then
  # A streaming preset: frames go straight to the encoder, so the take can be any length.
  size=$(echo "$region" | awk -F, '{print $3 "x" $4}')
  if ffmpeg -hide_banner -encoders 2> /dev/null | grep -q h264_nvenc; then
    codec="-c:v h264_nvenc -preset p6 -tune hq -rc constqp -qp 14"
  else
    codec="-c:v libx264 -preset veryfast -crf 12"
  fi
  "$here/build/burstcap" -o "$DEMO_OUTPUT" -g "$region" -n "$frames" -t "$seconds" -a -s -f "$DEMO_OUT/$name.raw" \
    | ffmpeg -hide_banner -loglevel error -y -f rawvideo -pix_fmt bgr0 -video_size "$size" -framerate "$fps" -i - \
      $codec -pix_fmt yuv420p -movflags +faststart "$DEMO_OUT/${name}_native_${fps}fps.mp4"
  echo "capture: $DEMO_OUT/${name}_native_${fps}fps.mp4"
  "$here/verify-frames.py" "$DEMO_OUT/${name}_native_${fps}fps.mp4"
  exit 0
fi

"$here/build/burstcap" -o "$DEMO_OUTPUT" -g "$region" -n "$frames" -t "$seconds" -a -f "$DEMO_OUT/$name.raw"
python3 - "$DEMO_OUT/$name.raw" "$fps" << 'EOS'
import json, sys
path, fps = sys.argv[1], int(sys.argv[2])
meta = json.load(open(path + '.json'))
meta['capture_fps'] = fps
json.dump(meta, open(path + '.json', 'w'))
EOS
echo "capture: $DEMO_OUT/$name.raw"
echo "next:    $here/verify-frames.py $DEMO_OUT/$name.raw && $here/conform-60.sh $DEMO_OUT/$name.raw"
