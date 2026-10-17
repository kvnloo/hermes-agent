#!/bin/sh
# Builds burstcap into ./build (needs gcc, wayland-scanner and wayland-client; no root).
set -eu
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
mkdir -p "$here/build"
xml=$here/src/wlr-screencopy-unstable-v1.xml
wayland-scanner client-header "$xml" "$here/build/wlr-screencopy-unstable-v1-client-protocol.h"
wayland-scanner private-code "$xml" "$here/build/wlr-screencopy-unstable-v1-protocol.c"
cc -O2 -Wall -o "$here/build/burstcap" -I"$here/build" "$here/src/burstcap.c" \
  "$here/build/wlr-screencopy-unstable-v1-protocol.c" $(pkg-config --cflags --libs wayland-client)
echo "built $here/build/burstcap"
