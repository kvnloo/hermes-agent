#!/bin/sh
# Record and conform the standard set of takes, one after another.
#
#   takes.sh [--keep-raw]
#
# launch (real frontend, real gateway), the seven splash designs, the theme
# sweep, and Tern-native motion. Raw frames are deleted after each conform
# unless --keep-raw is given: the lossless master holds the same frames.
set -eu
. "$(dirname "$0")/lib.sh"
keep=${1:-}

take() { # NAME SECONDS SCENARIO [ARG]
  "$here/capture.sh" "$@" > "$DEMO_STATE/capture.log" 2>&1 || { cat "$DEMO_STATE/capture.log" >&2; exit 1; }
  "$here/verify-frames.py" "$DEMO_OUT/$1.raw" --json > "$DEMO_OUT/$1.report.json"
  "$here/verify-frames.py" "$DEMO_OUT/$1.raw"
  "$here/conform-60.sh" "$DEMO_OUT/$1.raw" | grep '^conform:'
  [ "$keep" = --keep-raw ] || rm -f "${DEMO_OUT:?}/$1.raw" "${DEMO_OUT:?}/$1.raw.slots"
  echo
}

"$here/stage.sh" up 1080p120
take launch 6 launch kerykeion
for design in kerykeion sigil velocity atlas windows unleash soul; do
  take "design-$design" 4 design "$design"
done

"$here/stage.sh" fit 720p120
take themes 9 themes

"$here/stage.sh" fit 720p180
take native-motion 5 native-motion

"$here/stage.sh" fit 1080p120
echo "takes: done, in $DEMO_OUT"
