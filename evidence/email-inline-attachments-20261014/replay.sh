#!/usr/bin/env bash
set -euo pipefail
CHECKOUT="$(cd "$1" && pwd)"
PYTHON="$2"
if [[ "$PYTHON" != /* ]] || [ ! -x "$PYTHON" ]; then
  echo "TEST_PYTHON must be an absolute executable path." >&2
  exit 2
fi
if [ -e "$3" ]; then
  echo "Refusing to overwrite existing output: $3" >&2
  exit 2
fi
mkdir -p "$3"
OUT="$(cd "$3" && pwd)"
mkdir -p "$OUT/runtime-check"
env -i PATH="$PATH" HOME="$OUT/runtime-check" "$PYTHON" -c 'import pytest' || {
  echo "TEST_PYTHON must already provide pytest; refusing provisioning." >&2
  exit 2
}
PACKET="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
git -C "$CHECKOUT" diff --quiet
git -C "$CHECKOUT" diff --cached --quiet
copy_if_safe() {
  if [ -e "$2" ]; then
    cmp "$1" "$2" || { echo "Refusing to overwrite differing file: $2" >&2; exit 2; }
  else
    cp "$1" "$2"
  fi
}
copy_if_safe "$PACKET/test_email_inline_attachment_contract.py" "$CHECKOUT/tests/gateway/test_email_inline_attachment_contract.py"
copy_if_safe "$PACKET/origin_test_email_inline_text_attachment.py" "$CHECKOUT/tests/gateway/test_email_inline_origin_contract.py"
copy_if_safe "$PACKET/test_email_named_body_characterization.py" "$CHECKOUT/tests/gateway/test_email_named_body_characterization.py"
copy_if_safe "$PACKET/review_provenance.py" "$CHECKOUT/review_provenance.py"
cd "$CHECKOUT"
for rev in base head; do
  if [ "$rev" = base ]; then
    sha=0e427d788d253630d38a3a51cd76849e73cd6925
  else
    sha=126a18a9fe75e1e2e94a6cb090a1bcf37b68b381
  fi
  git checkout --detach "$sha"
  mkdir -p "$OUT/home-$rev"
  set +e
  env -i PATH="$PATH" HOME="$OUT/home-$rev" HERMES_PYTHON="$PYTHON" HERMES_TEST_FILE_RETRIES=0 __HERMES_TESTS_REEXEC=1 \
    scripts/run_tests.sh tests/gateway/test_email.py tests/gateway/test_email_charset_fallback.py \
    tests/gateway/test_email_imap_id_protocol.py tests/gateway/test_email_robustness.py \
    tests/gateway/test_email_secret_scope.py tests/gateway/test_email_inline_origin_contract.py \
    tests/gateway/test_email_inline_attachment_contract.py -j 2 -v --tb=short -p review_provenance \
    > "$OUT/$rev-focused.log" 2>&1
  echo "$?" > "$OUT/$rev-focused.exit"
  env -i PATH="$PATH" HOME="$OUT/home-$rev" HERMES_PYTHON="$PYTHON" HERMES_TEST_FILE_RETRIES=0 __HERMES_TESTS_REEXEC=1 \
    scripts/run_tests.sh tests/gateway/test_email_named_body_characterization.py \
    -j 1 -v --tb=short -p review_provenance > "$OUT/$rev-characterization.log" 2>&1
  echo "$?" > "$OUT/$rev-characterization.exit"
  set -e
done
