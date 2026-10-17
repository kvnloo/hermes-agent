# demo-capture

Record Hermes × Tern for a 60 FPS video, at the highest frame rate that survives capture,
and conform it to 60 FPS without inventing or discarding frames.

Everything runs on a private stage: a headless Hyprland output with an isolated Tern
window on it (own config, daemon and HOME). Your own Tern windows, panes, config and
monitors are not touched, and nothing needs root or a portal prompt.

## Workflow

```sh
cd scripts/demo-capture

# verify environment: build the recorder, bring the stage up
./build.sh
./stage.sh up 1080p120          # presets/: 1080p120, 720p120, 720p180, 720p240

# record: NAME SECONDS SCENARIO [ARG]
./capture.sh launch 6 launch kerykeion

# verify recording: delivered, unique, dropped and duplicate frames, from the compositor's timestamps
./verify-frames.py "$DEMO_OUT/launch.raw"

# generate the master, native-speed 60 fps and frame-perfect slow motion
./conform-60.sh "$DEMO_OUT/launch.raw"
#   launch_master_120fps.mkv      lossless FFV1, keep this
#   launch_native_60fps.mp4       normal speed
#   launch_2x_slowmo_60fps.mp4    every captured frame on the 60 FPS timeline

./stage.sh down
```

`./takes.sh` records and conforms the whole standard set in one go. `DEMO_OUT` is where takes
are written (default `out/` here, git-ignored; raw frames are about 1 GB
per second at 1080p120, so point it at a real disk).

## What was measured (and why the answer is not 540)

Machine: RTX 3080 Ti, Hyprland 0.56 on Wayland, DP-1 at 1920x1080 @ 540.16 Hz.

| Question | Measured |
| --- | --- |
| Display | 540.16 Hz (`hyprctl monitors`) |
| Tern presentation during native motion | median frame gap 1.86 ms, i.e. 540 Hz, on a 540 Hz output (`tern ctl perf`, pane transitions) |
| Tern while eased-scrolling | 2.6 ms median gap (about 390 Hz), every frame an animation frame |
| Tern spinners and shimmer | about 70 unique frames a second: these effects step, they are not continuous |
| The launch splash | 25 fps by default; 45 to 110 unique fps with the recording switch (see below) |
| Capture, every frame, 1080p | 120 FPS: 0.2% of refreshes missed |
| Capture, every frame, 720p | 180 FPS: 0.7% missed. 240 FPS: 1.5 to 5% missed |
| Capture at 360 and 540 Hz | 5% missed at 960x540 @ 360; at 540 it gets every second or third frame |
| Capture overhead on Tern | median gap unchanged (1.86 ms), p95 3.5 → 4.0 ms |

So Tern's own motion does reach 540 Hz, but it does not survive this capture path. The
recorder uses `wlr-screencopy`, where each frame is one request and one GPU-to-CPU readback
by the compositor: about 6 ms at 1080p and 3.5 to 4 ms at 720p on this machine. That caps
clean capture at 120 FPS for 1080p and 180 FPS for 720p.

**Recommended master: 1080p @ 120 FPS (2x slow motion). For more slowdown, 720p @ 180 FPS (3x).**

Getting to 540 would need capture that never leaves the GPU. The candidate is
`gpu-screen-recorder` (KMS capture into NVENC). It is in the Arch repos but not installed,
needs root to install and grant its capability, and KMS can only capture a physical
connector, so it would have to record the real 540 Hz monitor rather than the private stage.
It has not been tried. `wl-screenrec` is VAAPI-only (no use on NVIDIA), `wf-recorder` did not
build against FFmpeg 8, and OBS/PipeWire needs an interactive portal pick.

These numbers moved a lot with the machine's performance mode: with it off, 720p topped out
near 120 FPS. Re-run the check below before trusting them on another day.

```sh
# every-frame ceiling at the current preset: a few seconds of an idle stage
./capture.sh ceiling 4 && ./verify-frames.py "$DEMO_OUT/ceiling.raw"
```

## The launch splash is program-driven

Hermes computes each splash frame and sends it to Tern, 25 times a second, so a 120 FPS
capture of it holds about 25 unique frames a second. The designs are pure functions of time,
and there is a recording-only switch to draw them more often:

```sh
HERMES_TUI_SPLASH_FPS=120 hermes        # unset, the splash is unchanged
```

With 120 requested, the recorded takes hold 45 to 110 unique frames a second depending on the
design (the default design is the heaviest to compute): building and diffing a full-pane
frame in Node is the limit, not Tern, which acknowledged each frame in about 5 ms. That is
enough for 2x slow motion of the splash; it is not interpolation, every frame is a real frame
of the same motion. The stage's `hermes.sh` and `splash.sh` take the rate as their second
argument, and the scenarios pass 120.

## Slow motion is exact

`conform-60.sh` places frames by the compositor's timestamps. A refresh the recorder missed
is filled with the frame before it, so timing stays true; nothing is blended or interpolated.

```
slowdown = capture_fps / 60        120 → 2x   180 → 3x   240 → 4x
native   : every (capture_fps / 60)th frame, at 60 FPS
slow     : every frame, one per 1/60 s   (the equivalent of setpts=N*PTS, fps=60)
```

It then reads the three files back with `ffprobe -count_frames` and prints the counts next to
the counts it expects.

## The Hermes theme for Tern

`themes/hermes.json` is the Hermes website palette as a Tern theme (omp's theme format):
paper `#0000f2`, ink `#f2f2f2`, shade `#000082`, accent `#f2f200`, dim `#a6a6f6`,
ray `#6e6ef7`. The stage installs and selects it. To use it in your own Tern:

```sh
mkdir -p ~/.omp/agent/themes && cp themes/hermes.json ~/.omp/agent/themes/
# then pick "hermes" in Tern's theme picker, or set theme.dark: hermes in ~/.omp/agent/config.yml
```

Tern reads user themes from the omp agent directory in a real window; the headless
`tern serve` does not load them.

`./stage.sh theme NAME` switches the stage to any of Tern's themes. The splash and the chrome
follow, because they draw in theme tokens.

## Scenarios

A scenario is a file of Tern control commands (`tern help dev`), run through the stage's
control endpoint while recording. `{state}` is the stage's state directory and `{arg}` is the
fourth argument of `capture.sh`.

| Scenario | What it records |
| --- | --- |
| `launch` | The real frontend on a real gateway: splash, hand-off, session chrome. `ARG` is the design. |
| `design` | One splash design from its first frame. `ARG` is the design. |
| `themes` | One design held while Tern's themes change under it, ending on `hermes`. |
| `native-motion` | Tern-native motion only: eased scrolling, splits, zoom. |
| `agent-turn` | A real launch and a real prompt: splash, hand-off, tool cards, streamed answer. `ARG` is the prompt. |
| `beside-shell` | Hermes answering in one pane while a shell runs beside it. `ARG` is the prompt. |
| `chrome-themes` | A finished turn, then Tern's themes changing under the chrome. `ARG` is the prompt. |

The stage's Hermes home is empty, so `launch` shows the real launch but has no model
provider. The three scenarios above need a real one. Name it when the stage comes up, with
the model for the take's session only (nothing is written to the config) and a throwaway
directory for the agent to work in:

```sh
DEMO_HERMES_HOME=~/.hermes DEMO_HERMES_MODEL=openrouter/free DEMO_HERMES_PROVIDER=openrouter \
DEMO_HERMES_CWD=/tmp/hermes-demo-capture/project ./stage.sh up 1080p60
./capture.sh agent-turn 75 agent-turn "What does this project do? Read the code and answer in two sentences."
```

A turn runs far longer than a burst fits in RAM, so these use the streaming presets
(`1080p60`, `720p60`): frames go straight to an encoder and the take can be any length, at
normal speed only. In testing a 75-second 1080p60 take missed 1.8% of frames.

## Files

| Path | What |
| --- | --- |
| `build.sh`, `src/burstcap.c` | The recorder: a burst of frames with the compositor's timestamp for each |
| `stage.sh` | The private output and isolated Tern window |
| `capture.sh` | One take |
| `verify-frames.py` | Frame integrity of a take, or frame count and rate of a video |
| `conform-60.sh` | Master, native-speed 60 FPS and slow-motion 60 FPS |
| `takes.sh` | The standard set of takes |
| `presets/`, `scenarios/`, `themes/` | Sizes and rates, scripted takes, the Hermes Tern theme |

## Known limits

- A burst is held in RAM until it ends; `capture.sh` refuses one that will not fit.
- Every take starts in a fresh tab: a program stopped mid-frame can leave half a protocol
  message in a reused shell's input.
- The stage window is unfocusable and every stage operation puts your pointer and focus back.
  Without that, creating the output can warp the pointer onto it and hand it your keyboard.
- The stage Tern shows a "Restart to update" button in its title bar when an update is pending.
- The splash is inset a few cells from the pane edge, and tall box-drawing strokes show
  hairline gaps between rows.
