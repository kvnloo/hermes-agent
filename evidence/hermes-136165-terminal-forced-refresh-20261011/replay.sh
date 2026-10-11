#!/usr/bin/env bash
# Creates a retained disposable checkout; does not alter the caller's install.
set -euo pipefail
if [ "$#" -ne 2 ]; then
  echo "usage: $0 <head|base> <absolute PM-built Python 3.14 interpreter>" >&2
  exit 2
fi
packet_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(git -C "$packet_dir" rev-parse --show-toplevel)"
case "$1" in
  head) revision=71e74e11bc389c0ee4a02b09f88dd42421d46bbe ;;
  base) revision=a62979dc3601c9eae455bff5b35ba8f9bed0df30 ;;
  *) echo "choose head or base" >&2; exit 2 ;;
esac
test_python="$2"
"$test_python" -c 'import sys, pytest, httpx; assert sys.version_info[:2] == (3, 14); print(sys.version); print("pytest", pytest.__version__, "httpx", httpx.__version__)'
run_root="$(mktemp -d "${TMPDIR:-/tmp}/hermes136165-replay-XXXXXX")"
git -C "$repo_root" worktree add --detach "$run_root/checkout" "$revision"
cp "$packet_dir/fixture.py" "$run_root/checkout/tests/hermes_cli/test_codex_terminal_pool_refresh.py"
mkdir -p "$run_root/home" "$run_root/hermes" "$run_root/codex"
echo "Retained replay directory: $run_root"
echo "Expected exit 1: head 14 PASS / 1 FAIL; base 11 PASS / 1 FAIL."
cd "$run_root/checkout"
HOME="$run_root/home" HERMES_HOME="$run_root/hermes" CODEX_HOME="$run_root/codex" \
HERMES_PYTHON="$test_python" scripts/run_tests.sh \
  tests/hermes_cli/test_codex_terminal_pool_refresh.py \
  tests/hermes_cli/test_auth_codex_provider.py --file-retries 0 -j 1
