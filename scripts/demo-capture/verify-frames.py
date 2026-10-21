#!/usr/bin/env python3
"""Inspect a take: did the compositor's frames survive capture, and are they unique?

    verify-frames.py TAKE.raw [--json]
    verify-frames.py VIDEO.mkv|.mp4          (frame count, rate and duration only)

For a raw take it reads the compositor's own per-frame timestamps (TAKE.raw.times)
and hashes every frame, so nothing here is inferred from a container's metadata:

  delivered    frames the recorder got, per second
  missed       refresh intervals with no frame (a gap of 2+ intervals)
  duplicates   frames identical to the one before (the screen did not change)
  unique       delivered minus duplicates, per second
"""
import hashlib
import json
import statistics
import subprocess
import sys


def probe(path):
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
         'stream=nb_read_frames,r_frame_rate,avg_frame_rate,width,height,codec_name,pix_fmt:format=duration',
         '-of', 'json', path], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    s = data['streams'][0]
    num, den = (int(x) for x in s['avg_frame_rate'].split('/'))
    frames = int(s['nb_read_frames'])
    print(f"{path}")
    print(f"  {s['codec_name']} {s['pix_fmt']} {s['width']}x{s['height']}")
    print(f"  frames {frames}, avg rate {num / den:.3f} fps, duration {float(data['format']['duration']):.3f} s")
    return {'frames': frames, 'fps': num / den, 'duration': float(data['format']['duration'])}


def raw(path):
    meta = json.load(open(path + '.json'))
    size = meta['stride'] * meta['height']
    times = [float(line.split()[1]) for line in open(path + '.times')]
    hashes = []
    with open(path, 'rb') as f:
        for _ in range(meta['frames']):
            hashes.append(hashlib.blake2b(f.read(size), digest_size=8).digest())

    gaps = [b - a for a, b in zip(times, times[1:])]
    interval = statistics.median(gaps)
    span = times[-1] - times[0]
    missed = sum(round(g / interval) - 1 for g in gaps if g / interval >= 1.5)
    dup = sum(1 for a, b in zip(hashes, hashes[1:]) if a == b)
    ordered = sorted(gaps)
    requested = meta.get('capture_fps')
    report = {
        'take': path,
        'size': f"{meta['width']}x{meta['height']}",
        'capture_requested_fps': requested,
        'output_refresh_hz': round(1 / interval, 2),
        'frames': len(times),
        'seconds': round(span, 3),
        'capture_delivered_fps': round((len(times) - 1) / span, 2),
        'unique_fps': round((len(times) - 1 - dup) / span, 2),
        'missed_refreshes': missed,
        'missed_percent': round(100 * missed / (len(times) + missed), 2),
        'duplicate_frames': dup,
        'frame_time_ms': {
            'median': round(interval * 1000, 3),
            'p99': round(ordered[int(len(ordered) * 0.99)] * 1000, 3),
            'worst_1pct_mean': round(statistics.mean(ordered[int(len(ordered) * 0.99):]) * 1000, 3),
            'max': round(ordered[-1] * 1000, 3),
        },
        'slowdown_to_60': round((requested or round(1 / interval)) / 60, 3),
    }
    return report


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    if not path.endswith('.raw'):
        probe(path)
        return 0
    r = raw(path)
    if '--json' in sys.argv:
        print(json.dumps(r, indent=2))
        return 0
    t = r['frame_time_ms']
    print(f"Take:               {r['take']} ({r['size']})")
    print(f"Capture requested:  {r['capture_requested_fps']} FPS")
    print(f"Output refresh:     {r['output_refresh_hz']} Hz")
    print(f"Capture delivered:  {r['capture_delivered_fps']} FPS ({r['frames']} frames in {r['seconds']} s)")
    print(f"Unique-frame rate:  {r['unique_fps']} FPS")
    print(f"Dropped frames:     {r['missed_refreshes']} ({r['missed_percent']}%)")
    print(f"Duplicate frames:   {r['duplicate_frames']} (screen unchanged between them)")
    print(f"Frame time:         median {t['median']} ms, p99 {t['p99']} ms, worst 1% {t['worst_1pct_mean']} ms, max {t['max']} ms")
    print(f"Slowdown to 60:     {r['slowdown_to_60']}x")
    return 0


if __name__ == '__main__':
    sys.exit(main())
