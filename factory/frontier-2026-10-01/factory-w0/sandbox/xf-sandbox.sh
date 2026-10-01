#!/usr/bin/env bash
# xf-sandbox.sh: kernel sandbox (bubblewrap) for factory cells. FACTORY.md section 6, layers 1, 4 and 5.
#
#   xf-sandbox.sh <run-dir> <worktree> [--] <command> [args...]
#
# Inside the sandbox:
#   * own network namespace (loopback only), own PID namespace, new session, dies with the caller;
#   * / is read-only; only <run-dir> and <worktree> are writable (plus /tmp = <run-dir>/tmp and
#     /var/tmp = <run-dir>/vartmp, both stored in the run dir);
#   * the real home is a tmpfs, so ~/.hermes, ~/.config/gh, ~/.ssh and every credential file
#     are invisible; HOME=<run-dir>/home, HERMES_HOME=<run-dir>/home/.hermes;
#   * /run is a tmpfs (no user bus, no service manager sockets);
#   * the live install is a tmpfs with only its venv re-bound read-only; every Hermes console
#     script in that venv is over-bound by a stub that logs to <run-dir>/blocked-exec.log and
#     exits 126;
#   * the environment is cleared; PATH puts the venv's bin first, so `hermes` resolves to the stub.
# Before exec, the wrapper refuses denylisted test selections (exit 97).
#
# Exit codes: 64 usage, 65 refused path, 97 denylisted selection, 126 stub hit (from inside),
# otherwise the command's own status.
# Each guard line carries an XF-GUARD tag: the F15 canary removes one tag at a time to prove that
# the probe escapes without it. Do not put two guards on one line.
set -euo pipefail

BWRAP=/usr/bin/bwrap
LIVE_INSTALL="${XF_LIVE_INSTALL:-<hermes-home>}"
VENV="$LIVE_INSTALL/hermes-agent/venv"
REAL_HOME="$(getent passwd "$(id -u)" | cut -d: -f6)"
DENY_RC=97

usage() { echo "usage: xf-sandbox.sh <run-dir> <worktree> [--] <command> [args...]" >&2; exit 64; }
refuse() { echo "xf-sandbox: refused: $*" >&2; exit 65; }
[ $# -ge 3 ] || usage
RUN_IN="$1"; WT_IN="$2"; shift 2
[ "${1:-}" = "--" ] && shift
[ $# -ge 1 ] || usage

# ── Path layer: run dir and worktree must be real dirs outside the live install and home ──
mkdir -p "$RUN_IN"
RUN="$(realpath -e "$RUN_IN")"; WT="$(realpath -e "$WT_IN")"
[ -d "$WT" ] && [ -e "$WT/.git" ] || refuse "worktree is not a git checkout: $WT_IN"
for p in "$RUN" "$WT"; do
  case "$p/" in
    /|/tmp/*|/dev/shm/*) refuse "$p is on a tmpfs or is /" ;;
    "$LIVE_INSTALL"/*|"$REAL_HOME"/*) refuse "$p is under the live install or the real home" ;;
  esac
done
case "$RUN/" in "$WT"/*) refuse "run dir inside the worktree" ;; esac

# ── Selection layer (H1 denylist): never run updater, self-update, re-exec, fleet, service or
#    credential-copying tests. Fail closed: a directory that contains one denylisted file is refused. ──
DENY_GLOBS=(
  'tests/e2e/core/upgrade/*' 'tests/e2e/core/windows_update/*' 'tests/e2e/core/live/*'
  'tests/computer_use/live_*' 'tests/install/*' 'tests/scripts/desktop_update/*'
  'tests/*update*' 'tests/*upgrade*' 'tests/*updater*' 'tests/*fleet*' 'tests/*relaunch*'
  'tests/*systemd*' 'tests/*launchd*' 'tests/*service*' 'tests/*_live.py' 'tests/*_live_*'
  'tests/*windows_live*'
  'evals/update_*' 'evals/*/update_*' 'evals/tool_search/tool_search_livetest*' 'evals/postmortem/live_ab/*'
  'evals/*live_e2e*' 'evals/*livetest*'
)
EXEC_RE='os\.execv|os\.execl|execvpe?\(|_reexec'
is_denied_file() {  # $1: path relative to the worktree
  local rel="$1" g
  for g in "${DENY_GLOBS[@]}"; do [[ "$rel" == $g ]] && return 0; done
  case "$rel" in
    tests/*.py|evals/*.py) grep -qE "$EXEC_RE" "$WT/$rel" 2>/dev/null && return 0 ;;
  esac
  return 1
}
deny_check() {
  local tok word rel abs selected=0 runner=0 f
  set -f  # tokens are matched, never globbed on the host
  for tok in "$@"; do
    for word in $tok; do  # split shell text handed as one argument (bash -c '...') on whitespace
      word="${word#*=}"; word="${word%%::*}"
      case "$word" in */run_tests.sh|run_tests.sh|pytest|*/pytest|py.test) runner=1 ;; esac
      [ -n "$word" ] || continue
      case "$word" in /*) abs="$word" ;; *) abs="$WT/$word" ;; esac
      abs="$(realpath -m "$abs")"
      case "$abs/" in "$WT"/*) ;; *) continue ;; esac
      [ -e "$abs" ] || continue
      rel="${abs#"$WT"/}"
      case "$rel" in tests|tests/*|evals|evals/*) selected=1 ;; *) continue ;; esac
      if [ -d "$abs" ]; then
        while IFS= read -r f; do
          is_denied_file "$f" && { echo "xf-sandbox: denylisted selection: $rel contains $f" >&2; exit $DENY_RC; }
        done < <(git -C "$WT" ls-files -- "$rel")
      elif is_denied_file "$rel"; then
        echo "xf-sandbox: denylisted selection: $rel" >&2; exit $DENY_RC
      fi
    done
  done
  # A test runner with no tests/ or evals/ path collects the whole suite, which contains denylisted files.
  if [ "$runner" = 1 ] && [ "$selected" = 0 ]; then
    echo "xf-sandbox: denylisted selection: a test runner with no explicit path selects the whole suite" >&2; exit $DENY_RC
  fi
  set +f
  return 0
}
deny_check "$@"  # XF-GUARD:denylist

# ── Run dir layout and the exec stub ──
mkdir -p "$RUN/home/.hermes" "$RUN/tmp" "$RUN/vartmp" "$RUN/.xf"
STUB="$RUN/.xf/hermes-stub"
rm -f "$STUB"
cat > "$STUB" <<EOF
#!/bin/sh
# xf-sandbox exec stub: a Hermes console script was executed inside the sandbox.
printf '%s\t%s\t%s\n' "\$(date -u +%Y-%m-%dT%H:%M:%SZ)" "\$0" "\$*" >> '$RUN/blocked-exec.log'
echo "xf-sandbox: exec of \$0 blocked" >&2
exit 126
EOF
chmod 0555 "$STUB"
: >> "$RUN/blocked-exec.log"

# Console script names come from the worktree's pyproject, never from listing the venv.
mapfile -t SCRIPTS < <(sed -n '/^\[project\.scripts\]/,/^\[/{s/^\([A-Za-z0-9_.-]*\)[[:space:]]*=.*/\1/p}' "$WT/pyproject.toml")
SCRIPTS+=(hermes)
STUB_BINDS=()
for name in $(printf '%s\n' "${SCRIPTS[@]}" | sort -u); do
  [ -e "$VENV/bin/$name" ] || [ -L "$VENV/bin/$name" ] || continue
  STUB_BINDS+=(--ro-bind "$STUB" "$VENV/bin/$name")
done

EXTRA_RW=()  # XF-SABOTAGE-HOOK:write (empty: nothing else is writable)

ARGS=(--ro-bind / / --dev /dev --proc /proc)
ARGS+=(--tmpfs /run)
ARGS+=(--tmpfs "$REAL_HOME")  # XF-GUARD:home
ARGS+=(--tmpfs "$LIVE_INSTALL")  # XF-GUARD:hermes_home
ARGS+=(--ro-bind "$VENV" "$VENV")
ARGS+=("${STUB_BINDS[@]}")  # XF-GUARD:exec
ARGS+=(--bind "$RUN" "$RUN" --ro-bind "$RUN/.xf" "$RUN/.xf" --bind "$RUN/tmp" /tmp --bind "$RUN/vartmp" /var/tmp)
ARGS+=(--bind "$WT" "$WT")
ARGS+=("${EXTRA_RW[@]}")
ARGS+=(--unshare-net)  # XF-GUARD:net
ARGS+=(--unshare-pid --unshare-ipc --unshare-uts --die-with-parent --new-session)
ARGS+=(--clearenv --setenv HOME "$RUN/home" --setenv HERMES_HOME "$RUN/home/.hermes"
       --setenv HERMES_PYTHON "$VENV/bin/python" --setenv PATH "$VENV/bin:/usr/bin:/bin"
       --setenv TMPDIR /tmp --setenv LANG C.UTF-8 --setenv XF_RUN "$RUN" --setenv XF_SANDBOX 1
       --chdir "$WT")
exec "$BWRAP" "${ARGS[@]}" -- "$@"
