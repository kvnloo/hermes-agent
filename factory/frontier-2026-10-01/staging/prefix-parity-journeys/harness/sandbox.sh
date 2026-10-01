#!/usr/bin/env bash
# Run a command from the staging worktree inside a loopback-only network namespace with the live
# Hermes home masked (only the interpreter venv is re-bound read-only). Usage: sandbox.sh <cmd...>
#
# r03: no local paths in this file. Required environment:
#   HERMES_VENV  the test venv (re-bound read-only; its python becomes HERMES_PYTHON)
#   LIVE_HOME    the live Hermes home to mask with a tmpfs
#   TH           a scratch test home (HOME=$TH, HERMES_HOME=$TH/.hermes)
# The environment is cleared inside, so pass run inputs explicitly, e.g.
#   sandbox.sh /usr/bin/env RAW=... PROBE_TMP=... MAIN_REF=... bash <staging>/harness/run_receipts.sh
# The as-run r02 copy (paths inline) is kept private in private/harness-r02/.
set -euo pipefail
V="${HERMES_VENV:?set HERMES_VENV to the test venv}"
L="${LIVE_HOME:?set LIVE_HOME to the live Hermes home to mask}"
TH="${TH:?set TH to a scratch test home}"
mkdir -p "$TH/.hermes"
exec bwrap --dev-bind / / --tmpfs "$L" --ro-bind "$V" "$V" \
  --unshare-net --unshare-pid --die-with-parent --proc /proc --clearenv \
  --setenv PATH "$V/bin:/usr/bin:/bin" --setenv USER "${USER:-nobody}" \
  --setenv HOME "$TH" --setenv HERMES_HOME "$TH/.hermes" --setenv HERMES_PYTHON "$V/bin/python" \
  --setenv TZ UTC --setenv LANG C.UTF-8 --setenv PYTHONHASHSEED 0 \
  --unsetenv __HERMES_ACTIVATED \
  "$@"
