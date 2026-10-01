#!/usr/bin/env bash
# E23 (QUEUED, NOT RUN by the builder): Linux desktop capture timing, main vs NousResearch#126447, on the
# sandbox-desktop image that pins cua-driver 0.28.2 (Xvnc + Xfce + AT-SPI). Lane: docker, local, $0 cash.
# Preconditions: OD-6 (CU design hold allows E23), host quiet (load1 < 4, cpu-quiet lane), no Quackles window.
# Pre-registered: >=40 timed captures per (target, mode, arm); blocks ABBA; A/A arm for the noise floor;
# primary metric = capture wall ms median + p95 and timeout count, ax and vision; som is the control.
# Kill/falsifier: no ax/vision median delta beyond the A/A floor on either target -> record the null, defer.
#
# Usage: SCRATCH=<dir holding h.git> E23_WORKTREES=<dir for the two arm worktrees> HERMES_PYTHON=<venv python> \
#        [CUA_DRIVER_VERSION=0.28.2] e23_run.sh <main sha> <out dir>
set -euo pipefail
MAIN=${1:?main sha}; OUT=${2:?out dir}
S=${SCRATCH:?set SCRATCH to the directory holding the h.git mirror}
R=$S/h.git
WTB=${E23_WORKTREES:?set E23_WORKTREES to a directory for the two arm worktrees}
HARNESS=$(cd "$(dirname "$0")" && pwd)
PY=${HERMES_PYTHON:?set HERMES_PYTHON to the test venv python}
export E23_CONTAINER=e23-desktop
mkdir -p "$OUT"

# 1. Arms: base = main, candidate = main + #126447 head 8891ff469a (merge-tree, must be clean).
git -C "$R" worktree add --detach "$WTB/e23-main" "$MAIN"
git -C "$R" worktree add --detach "$WTB/e23-c126447" "$MAIN"
git -C "$R" diff 105568c155 8891ff469a -- tools/ | git -C "$WTB/e23-c126447" apply --3way
git -C "$WTB/e23-c126447" reset -q
git -C "$WTB/e23-c126447" diff --stat > "$OUT/c126447.diffstat"

# 2. Image: build from the pinned main tree (or pull nousresearch/hermes-sandbox:desktop and record its digest).
# CUA_DRIVER_VERSION=0.21.0 reproduces the pm/lock.json pin (only include_screenshot advertised: ax lane only).
docker build -f "$WTB/e23-main/docker/sandbox-desktop.Dockerfile" --build-arg CUA_DRIVER_VERSION="${CUA_DRIVER_VERSION:-0.28.2}" \
  -t hermes-sandbox:e23 "$WTB/e23-main"
docker image inspect hermes-sandbox:e23 --format '{{.Id}}' > "$OUT/image.id"

# 3. Desktop: no network inside; the launcher publishes DISPLAY/XAUTHORITY/DBUS env to /tmp/bd/env.
docker run -d --name "$E23_CONTAINER" --network none --memory=4g --cpus=4 hermes-sandbox:e23
docker cp "$WTB/e23-main/tools/bot_desktop/launcher.sh" "$E23_CONTAINER:/tmp/launcher.sh"
docker cp "$WTB/e23-main/tools/bot_desktop/wallpaper.png" "$E23_CONTAINER:/tmp/wallpaper.png"
docker exec -u pn -d "$E23_CONTAINER" bash -c 'mkdir -p /tmp/bd && HERMES_BD_PROFILE=e23 HERMES_BD_DISPLAY_NUM=20 \
  HERMES_BD_SOCKET=/tmp/bd/rfb.sock HERMES_BD_XAUTH=/tmp/bd/Xauthority HERMES_BD_ENV_FILE=/tmp/bd/env \
  HERMES_BD_CONFIG_HOME=/tmp/bd/xdg HERMES_BD_WALLPAPER=/tmp/wallpaper.png bash /tmp/launcher.sh >/tmp/bd/launcher.log 2>&1'
until docker exec -u pn "$E23_CONTAINER" test -f /tmp/bd/env; do sleep 0.5; done
docker exec -u pn "$E23_CONTAINER" bash -c 'set -a; . /tmp/bd/env; set +a; cua-driver --version; cua-driver doctor || true' > "$OUT/driver.txt" 2>&1

# 4. Targets: a small GTK tree (xfce4-terminal) and a large one (headed Chromium, ~1500 controls, a11y forced).
"$PY" - > "$OUT/heavy.html" <<'PY'
print("<!doctype html><title>E23 heavy</title><body>" + "".join(f"<button>b{i}</button><a href='#{i}'>l{i}</a>" for i in range(750)) + "</body>")
PY
docker cp "$OUT/heavy.html" "$E23_CONTAINER:/tmp/heavy.html"
docker exec -u pn -d "$E23_CONTAINER" bash -c 'set -a; . /tmp/bd/env; set +a; xfce4-terminal --title=Terminal'
docker exec -u pn -d "$E23_CONTAINER" bash -c 'set -a; . /tmp/bd/env; set +a; \
  $(ls -d /opt/playwright/chromium-*/chrome-linux*/chrome | head -1) --force-renderer-accessibility --no-first-run \
  --user-data-dir=/tmp/e23-chrome file:///tmp/heavy.html'
sleep 10

# 5. Blocks: A=main, B=c126447, A'=main again (A/A). 4 blocks x n=10 = 40 per (target, mode, arm).
run_block() {  # arm-label worktree block
  local H; H=$(mktemp -d "$OUT/home.XXXX"); mkdir -p "$H/.hermes"
  env -i PATH=/usr/bin:/bin HOME="$H" HERMES_HOME="$H/.hermes" PYTHONPATH="$2" E23_CONTAINER="$E23_CONTAINER" \
    HERMES_CUA_DRIVER_CMD="$HARNESS/e23_driver_wrapper.sh" \
    "$PY" "$HARNESS/e23_capture_timing.py" --arm "$1" --block "$3" --n 10 --warmup 3 \
      --targets Terminal,E23 --out "$OUT/rows.jsonl"
}
uptime > "$OUT/load_start"
for blk in 1 2 3 4; do
  if [ $((blk % 2)) = 1 ]; then order="A B Aa"; else order="Aa B A"; fi
  for arm in $order; do
    case $arm in
      A)  run_block main "$WTB/e23-main" "$blk" ;;
      Aa) run_block main-aa "$WTB/e23-main" "$blk" ;;
      B)  run_block c126447 "$WTB/e23-c126447" "$blk" ;;
    esac
  done
done
uptime > "$OUT/load_end"
"$PY" "$HARNESS/e23_summarize.py" "$OUT/rows.jsonl" --base main --aa main-aa --candidates c126447 > "$OUT/summary.json"

# 6. Cleanup.
docker rm -f "$E23_CONTAINER"
git -C "$R" worktree remove --force "$WTB/e23-main"
git -C "$R" worktree remove --force "$WTB/e23-c126447"
