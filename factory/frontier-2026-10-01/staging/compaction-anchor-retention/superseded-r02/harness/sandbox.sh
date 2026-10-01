#!/usr/bin/env bash
# usage: sandbox.sh <workdir> <home> <egress_log> <cmd...>
# bwrap: read-only root, own network namespace (loopback only), systemd-resolved socket masked (so DNS
# fails inside), pid ns, cleared env, the given HOME/HERMES_HOME, the live Hermes install masked except
# its venv (re-bound read-only). harness/egress_sitecustomize.py logs every non-loopback DNS lookup and
# connect attempt to <egress_log>. Set VENV, HERMES_INSTALL and EGRESS_DIR (dir holding
# sitecustomize.py) for your machine.
set -u
: "${VENV:?}" "${HERMES_INSTALL:?}" "${EGRESS_DIR:?}"
wd=$1; home=$2; elog=$3; shift 3
mkdir -p "$home/.hermes" "$home/tmp"; : > "$elog"
exec bwrap --ro-bind / / --dev /dev --proc /proc \
  --tmpfs "$HERMES_INSTALL" \
  --ro-bind "$VENV" "$VENV" \
  --tmpfs "$HOME/.ssh" --tmpfs "$HOME/.config/gh" --tmpfs /run/systemd/resolve \
  --bind "$home" "$home" --bind "$home/tmp" /tmp \
  --bind "$wd" "$wd" --bind "$(dirname "$elog")" "$(dirname "$elog")" \
  --ro-bind "$EGRESS_DIR" "$EGRESS_DIR" \
  --unshare-net --unshare-pid --die-with-parent --clearenv \
  --setenv HOME "$home" --setenv HERMES_HOME "$home/.hermes" \
  --setenv PATH "$VENV/bin:/usr/bin:/bin" --setenv PYTHONDONTWRITEBYTECODE 1 \
  --setenv PYTHONPATH "$EGRESS_DIR" --setenv EGRESS_LOG "$elog" \
  --chdir "$wd" "$@"
