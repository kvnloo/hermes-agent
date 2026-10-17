#!/bin/sh
# Turn a raw take into the editing master and the two 60 FPS deliverables.
#
#   conform-60.sh TAKE.raw
#
#   TAKE_master_<fps>fps.mkv   lossless FFV1 at the capture rate (keep this)
#   TAKE_native_60fps.mp4      normal speed: every (fps/60)th frame, no blending
#   TAKE_<n>x_slowmo_60fps.mp4 every captured frame on the 60 FPS timeline
#
# Frames are placed by the compositor's timestamps: a refresh the recorder
# missed is filled with the frame before it, so timing stays true and nothing
# is interpolated. slowdown = capture_fps / 60.
set -eu
raw=${1:?usage: conform-60.sh TAKE.raw}
base=${raw%.raw}
eval "$(python3 - "$raw" << 'EOS'
import json, statistics, sys
path = sys.argv[1]
m = json.load(open(path + '.json'))
t = [float(l.split()[1]) for l in open(path + '.times')]
fps = m.get('capture_fps') or round(1 / statistics.median([b - a for a, b in zip(t, t[1:])]))
if fps % 60:
    sys.exit(f"capture rate {fps} is not a multiple of 60")
# Slot each frame on the capture-rate grid; repeat the previous frame into any slot left empty.
slots, last = [], -1
for i, ts in enumerate(t):
    slot = max(last + 1, round((ts - t[0]) * fps))
    slots.extend([max(i - 1, 0)] * (slot - last - 1))
    slots.append(i)
    last = slot
open(path + '.slots', 'w').write('\n'.join(map(str, slots)) + '\n')
print(f"fps={fps} w={m['width']} h={m['height']} stride={m['stride']} frames={m['frames']} slots={len(slots)}")
EOS
)"
mult=$((fps / 60))
size=$((stride * h))
echo "conform: ${w}x${h} at $fps fps, $frames frames in $slots slots ($((slots - frames)) filled), ${mult}x slow motion"

# The frames in slot order, straight from the raw file.
feed() {
  python3 - "$raw" "$size" << 'EOS'
import sys
path, size = sys.argv[1], int(sys.argv[2])
out = sys.stdout.buffer
with open(path, 'rb') as f:
    for line in open(path + '.slots'):
        f.seek(int(line) * size)
        out.write(f.read(size))
EOS
}
in_opts="-f rawvideo -pix_fmt bgr0 -video_size ${w}x${h}"
x264="-c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -movflags +faststart"

feed | ffmpeg -hide_banner -loglevel error -y $in_opts -framerate "$fps" -i - \
  -c:v ffv1 -level 3 -g 1 -slices 16 -threads 8 "${base}_master_${fps}fps.mkv"
# Native speed: keep every (fps/60)th frame at its own instant. No frame blending: UI stays crisp.
ffmpeg -hide_banner -loglevel error -y -i "${base}_master_${fps}fps.mkv" \
  -vf "select='not(mod(n\,$mult))',setpts=N/60/TB" -r 60 $x264 "${base}_native_60fps.mp4"
# Slow motion: the same frames, one per 1/60 s (setpts=${mult}*PTS, fps=60 without dropping or inventing any).
ffmpeg -hide_banner -loglevel error -y -i "${base}_master_${fps}fps.mkv" \
  -vf "setpts=${mult}*PTS" -r 60 $x264 "${base}_${mult}x_slowmo_60fps.mp4"

for f in "${base}_master_${fps}fps.mkv" "${base}_native_60fps.mp4" "${base}_${mult}x_slowmo_60fps.mp4"; do
  "$(dirname "$0")/verify-frames.py" "$f"
done
echo "conform: expect master $slots frames, native $(( (slots + mult - 1) / mult )), slow motion $slots"
