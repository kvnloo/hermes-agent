#!/usr/bin/env bash
# Reproduce source-backed exploratory probes on EXACT upstream PR HEADs.
# Nothing is pushed or posted, and NO tracked source file is changed.
# A temporary detached worktree is used per PR, with an untracked test file.
# Some tests are intentionally expected to FAIL because they probe privacy/
# consistency properties not yet guaranteed by the PRs.
set -euo pipefail
if (( $# < 1 || $# > 3 )); then
  echo "Usage: $0 /absolute/hermes-checkout [output-dir] [PR-number-or-all]" >&2
  exit 2
fi
source_repo="$(cd "$1" && pwd)"
study_root="$(cd "$(dirname "$0")/.." && pwd)"
output_dir="${2:-$PWD/rfc-143379-exact-head-results}"
selected="${3:-all}"
mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"
[[ -f "$source_repo/scripts/run_tests.sh" ]] || { echo "Missing Hermes checkout" >&2; exit 2; }

pr_numbers=(141876 116673 139606 140008 116834 116846)
sha_by_pr=(
 af16e3ab16eed2492552c325ad1777533a8b7004
 2c1941aac46efac3b35605d99a8628e75a91c670
 5b31ccb7d56ad614da63588ef876584b9f95dd3f
 e543544aca215bf7ea838444b6df58bdbbd3e38c
 f678f4c7e5d994f03d8759fe0e950d3407ccca7e
 96dc75192a82b6c5645a89c2eb894fba97ad2bbd
)
# To compare a subsequently rebased chain-document head while retaining
# the original six frozen SHAs, set RFC_116673_SHA to an exact 40-digit SHA.
# The manifest records the override; no branch-name/head substitution occurs.
if [[ -n "${RFC_116673_SHA:-}" ]]; then
  if [[ ! "${RFC_116673_SHA}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "RFC_116673_SHA must be an exact 40-character lowercase SHA" >&2
    exit 2
  fi
  sha_by_pr[1]="${RFC_116673_SHA}"
fi
selector_by_pr=(
 'read_dispatch_contract or read_concurrency_snapshot'
 'read_dispatch_contract or read_concurrency_snapshot or chain_doc_reference_race or chain_doc_read_response_budget_candidate'
 'read_dispatch_contract'
 '__no_extra_probes__'
 'no_save_never_lands_in_memory_or_pending'
 'no_save_never_lands_in_memory_or_pending'
)
work_root="$(mktemp -d "${TMPDIR:-/tmp}/hermes-rfc143379.XXXXXXXX")"
cleanup() {
  for worktree in "$work_root"/head-*; do
    [[ -e "$worktree/.git" ]] && git -C "$source_repo" worktree remove --force "$worktree" >/dev/null 2>&1 || true
  done
  rm -rf "$work_root"
}
trap cleanup EXIT

printf 'pr\tsha\texit_code\tlog\n' > "$output_dir/manifest.tsv"
for index in "${!pr_numbers[@]}"; do
  pr="${pr_numbers[$index]}"
  sha="${sha_by_pr[$index]}"
  if [[ "$selected" != all && "$selected" != "$pr" ]]; then continue; fi
  log="$output_dir/pr-$pr.log"
  printf 'PR %s head %s\n' "$pr" "$sha" | tee "$log"
  if ! git -C "$source_repo" cat-file -e "$sha^{commit}" 2>/dev/null; then
    # GitHub exposes the exact submitted PR head, even for contributors' forks.
    if ! git -C "$source_repo" fetch --no-tags https://github.com/NousResearch/hermes-agent.git \
      "refs/pull/$pr/head" >> "$log" 2>&1; then
      printf 'fetch failed for PR %s; no substitution was made\n' "$pr" | tee -a "$log"
      printf '%s\t%s\tFETCH_FAILED\t%s\n' "$pr" "$sha" "$log" >> "$output_dir/manifest.tsv"
      continue
    fi
  fi
  worktree="$work_root/head-$pr"
  git -C "$source_repo" worktree add --detach "$worktree" "$sha" >> "$log" 2>&1
  actual="$(git -C "$worktree" rev-parse HEAD)"
  if [[ "$actual" != "$sha" ]]; then
    echo "Incorrect checkout SHA ($actual != $sha). Refusing substitution." | tee -a "$log"
    printf '%s\t%s\tSHA_MISMATCH\t%s\n' "$pr" "$sha" "$log" >> "$output_dir/manifest.tsv"
    continue
  fi
  mkdir -p "$worktree/tests/tools"
  cp "$study_root/checkout/test_real_checkout.py" "$worktree/tests/tools/test_rfc_homework.py"
  cp "$study_root/checkout/consent_scenarios.json" "$worktree/tests/tools/rfc_consent_scenarios.json"
  selector="${selector_by_pr[$index]}"
  extras=()
  if [[ "$pr" == 140008 ]]; then
    extras=(tests/tools/test_dream_cycle.py)
    if [[ ! -f "$worktree/${extras[0]}" ]]; then
      printf 'Dreaming tests missing at pinned SHA\n' >> "$log"
      printf '%s\t%s\tNO_DREAM_TESTS\t%s\n' "$pr" "$sha" "$log" >> "$output_dir/manifest.tsv"
      continue
    fi
  else
    extras=(tests/tools/test_rfc_homework.py)
  fi
  set +e
  if [[ "$pr" == 140008 ]]; then
    (cd "$worktree" && scripts/run_tests.sh "${extras[@]}" --file-retries 0 -- -q) >> "$log" 2>&1
  else
    (cd "$worktree" && scripts/run_tests.sh "${extras[@]}" --file-retries 0 -- -q -k "$selector") >> "$log" 2>&1
  fi
  status=$?
  set -e
  printf '%s\t%s\t%s\t%s\n' "$pr" "$sha" "$status" "$log" >> "$output_dir/manifest.tsv"
  printf 'PR %s diagnostic exit=%s (see %s)\n' "$pr" "$status" "$log"
done
printf '\nExact-head diagnostics written to: %s\n' "$output_dir"
printf 'Nonzero probe status is a finding, not an assertion about production frequency.\n'
