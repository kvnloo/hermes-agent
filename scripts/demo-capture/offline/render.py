#!/usr/bin/env python3
"""Render a recorded Hermes session to video with Tern's own offscreen renderer, a frame at a time.

    render.py TAKE [--theme dark|light] [--fps 60] [--scale 2] [--start S] [--seconds S]
              [--max-gap MS] [--events FILE] [--title TEXT] [--out DIR] [--keep-frames]

TAKE is a recording made by record.py ($DEMO_REC/TAKE.jsonl). A headless Tern replays it into a
pane at the recorded pace on its virtual clock (`surface-play ... paced`), and every frame is one
`wait` of exactly 1/fps and one `shot`: no screen capture, so no dropped or repeated frames at any
size or rate, and Tern-native motion (carets, spinners, eased scrolling, fades) is sampled exactly.

    --theme     the Hermes Tern theme, as themes/hermes-{dark,light}.css over Tern's own
                (headless Tern does not load user themes; see theme-probe.py)
    --scale     device pixels per logical pixel: 2 renders a 1280x720 window at 2560x1440
    --start     skip this many seconds of the session before the first frame
    --max-gap   shorten every pause between Hermes's messages to at most this long (default: off,
                real time). The video is then not real time; say so wherever it is shown.
    --focus     which pane holds the focus in a take recorded with --beside (default: right, where
                the shell's output is printed)
    --events    lines of `SECONDS COMMAND...`: Tern control commands run at those video times
                (split right, focus left, feed "file", theme dark "name", ...)
"""
import argparse
import base64
import json
import os
import shutil
import signal
import subprocess
import sys
import time

here = os.path.dirname(os.path.abspath(__file__))
state = os.environ.get("DEMO_STATE", "/tmp/hermes-demo-capture")
rec = os.environ.get("DEMO_REC", os.path.join(state, "rec"))

parser = argparse.ArgumentParser()
parser.add_argument("take")
parser.add_argument("--theme", default="dark", choices=["dark", "light"])
parser.add_argument("--fps", type=int, default=60)
parser.add_argument("--scale", type=float, default=2)
parser.add_argument("--start", type=float, default=0)
parser.add_argument("--seconds", type=float)
parser.add_argument("--max-gap", type=float)
parser.add_argument("--events")
parser.add_argument("--focus", default="right", choices=["left", "right"])
parser.add_argument("--title", default="hermes")
parser.add_argument("--out", default=os.environ.get("DEMO_OUT", os.path.join(here, "../out")))
parser.add_argument("--name")
parser.add_argument("--keep-frames", action="store_true")
parser.add_argument("--crf", default="12")
args = parser.parse_args()

source = args.take if args.take.endswith(".jsonl") else os.path.join(rec, args.take + ".jsonl")
meta = json.load(open(source[:-6] + ".meta.json"))
name = args.name or f"{os.path.basename(source)[:-6]}-{args.theme}"
out = os.path.abspath(args.out)
work = os.path.join(state, "render", name)
shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
os.makedirs(out, exist_ok=True)
sock = os.path.join(work, "r.sock")

# The stream, re-timed if asked: only the gaps between what Hermes sent are shortened.
lines = [json.loads(line) for line in open(source)]
first = lines[0]["t"]
shift = 0
previous = first
shortened = 0.0
shifts = []  # (original time, how much earlier everything from then on plays)
for line in lines:
    gap = line["t"] - previous
    previous = line["t"]
    if args.max_gap is not None and line["dir"] == "out" and gap > args.max_gap:
        shift += gap - args.max_gap
        shortened += gap - args.max_gap
        shifts.append((line["t"], shift))
    line["t"] = line["t"] - shift


def retimed(t):
    """A wall-clock time of the take on the re-timed stream's clock."""
    moved = 0
    for at, by in shifts:
        if t >= at:
            moved = by
    return t - moved


# A shell recorded beside the session: its output, in chunks, on the same clock.
beside = meta.get("beside")
chunks = []
if beside:
    for row in open(source[:-6] + ".shell.jsonl"):
        row = json.loads(row)
        chunks.append(((retimed(row["t"]) - first) / 1000, base64.b64decode(row["d"])))
length = (lines[-1]["t"] - first) / 1000
stream = os.path.join(work, "stream.jsonl")
with open(stream, "w") as handle:
    for line in lines:
        handle.write(json.dumps(line, separators=(",", ":")) + "\n")

seconds = args.seconds if args.seconds is not None else max(0.5, length - args.start + 0.5)
frames = round(seconds * args.fps)
events = []
if args.events:
    for row in open(args.events):
        row = row.strip()
        if row and not row.startswith("#"):
            at, command = row.split(None, 1)
            events.append((float(at), command.replace("{state}", state).replace("{here}", here)))
    events.sort(key=lambda event: event[0])

clean = {k: v for k, v in os.environ.items() if not k.startswith("TERN_")}
clean.update(HOME=os.path.join(state, "home"), TERN_CONFIG_DIR=state, TERN_DAEMON_SOCKET=os.path.join(work, "daemon.sock"))
serve = subprocess.Popen(
    ["tern", "serve", "--control", sock, "--out", work], env=clean,
    stdout=open(os.path.join(work, "tern.log"), "w"), stderr=subprocess.STDOUT, start_new_session=True,
)


def ctl(*words):
    reply = subprocess.run(["tern", "ctl", "--control", sock, *words], capture_output=True, text=True).stdout
    if '"ok":true' not in reply:
        raise SystemExit(f"render: `{' '.join(words)}` failed: {reply.strip()[:300]}")
    return json.loads(reply)


try:
    deadline = time.time() + 15
    while not os.path.exists(sock):
        if time.time() > deadline:
            raise SystemExit("render: the headless Tern did not start")
        time.sleep(0.1)
    time.sleep(0.5)

    ctl("size", str(meta["width"]), str(meta["height"]), str(args.scale))
    ctl("appearance", args.theme)
    # The Hermes theme is the base theme's tokens replaced: titanium under the dark one, `light` under the light.
    ctl("theme", args.theme, '"titanium"' if args.theme == "dark" else '"light"')
    ctl("css", "zz-hermes", os.path.join(here, "../themes", f"hermes-{args.theme}.css"))
    ctl("update", "idle")
    ctl("rename", json.dumps(args.title, ensure_ascii=False))
    pane = ctl("state")["panes"][0]
    if not meta.get("beside") and (pane["cols"], pane["rows"]) != (meta["cols"], meta["rows"]):
        print(f"render: the pane is {pane['cols']}x{pane['rows']} but the take was {meta['cols']}x{meta['rows']}", file=sys.stderr)

    # One frame is a shot, then exactly 1/fps on Tern's clock. Waits are whole milliseconds, so the
    # remainder is carried: frame n is taken at round(n * 1000 / fps) ms, never more than half a millisecond off.
    script = []
    if beside:
        # Both panes start as idle shells; the session replays in the left one, the recorded shell's
        # output is printed into the right one (cleared first, so only the recording shows).
        script += ["split right", "ready", "focus left"]
    script.append(f'surface-play "{stream}" paced')
    if args.start > 0:
        script.append(f"wait {round(args.start * 1000)}")
    feeds = os.path.join(work, "feed")
    os.makedirs(feeds)
    pending = b"\x1b[2J\x1b[3J\x1b[H" if beside else b""
    if beside and args.focus == "right":
        script.append("focus right")
    clock = 0
    for frame in range(frames):
        while events and events[0][0] <= frame / args.fps + 1e-9:
            script.append(events.pop(0)[1])
        while chunks and chunks[0][0] <= args.start + frame / args.fps + 1e-9:
            pending += chunks.pop(0)[1]
        if pending:
            path = os.path.join(feeds, f"{frame:06d}.txt")
            open(path, "wb").write(pending)
            pending = b""
            # `focus` waits for a pane to settle, which one playing a recording never does: a press moves the
            # focus at once. The shell's pane is pressed for the print, then Hermes's composer again.
            there = f"click {round(meta['width'] * 0.75)} {round(meta['height'] * 0.5)}"
            back = f"click {round(meta['width'] * 0.25)} {meta['height'] - 30}"
            script += ([there] if args.focus == "left" else []) + [f'feed "{path}"'] + ([back] if args.focus == "left" else [])
        script.append(f'shot "f{frame:06d}"')
        target = round((frame + 1) * 1000 / args.fps)
        script.append(f"wait {target - clock}")
        clock = target
    scenario = os.path.join(work, "frames.scn")
    open(scenario, "w").write("\n".join(script) + "\n")

    started = time.time()
    run = subprocess.run(["tern", "ctl", "--control", sock, "--file", scenario], capture_output=True, text=True)
    failed = [line for line in run.stdout.splitlines() if line.startswith("< ") and '"ok":false' in line]
    if failed:
        raise SystemExit(f"render: {len(failed)} commands failed, first: {failed[0][:300]}")
    took = time.time() - started
finally:
    subprocess.run(["tern", "ctl", "--control", sock, "quit"], capture_output=True)
    try:
        serve.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(serve.pid, signal.SIGTERM)

shots = os.path.join(work, "serve")
made = sorted(f for f in os.listdir(shots) if f.endswith(".png"))
if len(made) != frames:
    raise SystemExit(f"render: {len(made)} frames written, {frames} expected")
for extra in os.listdir(shots):
    if extra.endswith(".json"):
        os.remove(os.path.join(shots, extra))

video = os.path.join(out, f"{name}_{args.fps}fps.mp4")
subprocess.run(
    ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(args.fps), "-i", os.path.join(shots, "f%06d.png"),
     "-c:v", "libx264", "-preset", "slow", "-crf", args.crf, "-pix_fmt", "yuv420p", "-movflags", "+faststart", video],
    check=True,
)
if args.keep_frames:
    kept = os.path.join(out, f"{name}_frames")
    shutil.rmtree(kept, ignore_errors=True)
    shutil.move(shots, kept)
shutil.rmtree(work, ignore_errors=True)

real = "real time" if not shortened else f"pauses shortened by {shortened / 1000:.1f} s of {length + shortened / 1000:.1f} s"
print(f"render: {video}")
print(f"render: {frames} frames at {args.fps} fps, {round(meta['width'] * args.scale)}x{round(meta['height'] * args.scale)}, "
      f"{args.theme}, {real}; {took:.0f} s ({frames / took:.1f} frames/s)")
