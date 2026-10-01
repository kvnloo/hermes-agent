#!/usr/bin/env bash
# usage: car_sandbox.sh <workdir> <cmd...>
# bwrap: read-only root, no network namespace (loopback only), pid ns, cleared env,
# isolated HOME/HERMES_HOME, live hermes home masked (only the venv re-bound read-only).
set -u
RUNH=$STAGING/raw/sbhome
VENV=$VENV
mkdir -p "$RUNH/.hermes" "$RUNH/tmp"
wd=$1; shift
exec bwrap --ro-bind / / --dev /dev --proc /proc \
  --tmpfs $HERMES_INSTALL \
  --ro-bind "$VENV" "$VENV" \
  --tmpfs $HOME/.ssh --tmpfs $HOME/.config/gh \
  --bind "$RUNH" "$RUNH" --bind "$RUNH/tmp" /tmp \
  --bind "$wd" "$wd" \
  --unshare-net --unshare-pid --die-with-parent --clearenv \
  --setenv HOME "$RUNH" --setenv HERMES_HOME "$RUNH/.hermes" \
  --setenv PATH "$VENV/bin:/usr/bin:/bin" --setenv PYTHONDONTWRITEBYTECODE 1 \
  --setenv HERMES_DISABLE_MODEL_METADATA_FETCH 1 \
  --chdir "$wd" "$@"
