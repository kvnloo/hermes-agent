#!/usr/bin/env bash
# F07P dry run (r03): repeat-key prevalence probe against the scripted fake model, on main and head,
# tool_search default and off. Outputs are sanitized (tree path -> <wt>) before they land in raw-r03/.
set -euo pipefail
MAIN=$1 HEAD=$2
S=$S
W=$ARTIFACTS/promotion-readiness-2026-10-01/wt/stfix/cu-repeat-input-dedup
ST=$ARTIFACTS/frontier-2026-10-01/staging/cu-repeat-input-dedup
TH=$S/testhome-sf-cu-repeat-input-dedup
PY=<hermes-home>/hermes-agent/venv/bin/python
OUT=$ST/receipts/raw-r03
TMP=$S/sf-cu/probe
mkdir -p "$TMP"
for arm in main head; do
  sha=$MAIN; [ "$arm" = head ] && sha=$HEAD
  git -C "$W" checkout -q -f --detach "$sha"; git -C "$W" clean -fdq
  for mode in default off; do
    T=$TH/probe-$arm-$mode; rm -rf "$T"; mkdir -p "$T/.hermes"
    env -i PATH=/usr/bin:/bin HOME="$T" HERMES_HOME="$T/.hermes" TZ=UTC LANG=C.UTF-8 "$PY" \
      "$ST/probes/repeat_key_prevalence.py" --tree "$W" --fake --trials 1 --tool-search "$mode" \
      --out "$TMP/probe-dryrun-$arm-$mode.json" > "$TMP/probe-dryrun-$arm-$mode.stdout" 2> "$TMP/probe-dryrun-$arm-$mode.stderr" || true
    for ext in json stderr; do
      sed -e "s#$W#<wt>#g" -e "s#$TH#\$TH#g" -e "s#$S#<scratchpad>#g" -e "s#$PY#\$HERMES_PYTHON#g" \
          -e "s#<hermes-home>#<live-install>#g" -e "s#~#~#g" \
          "$TMP/probe-dryrun-$arm-$mode.$ext" > "$OUT/probe-dryrun-$arm-$mode.$ext"
    done
    echo "$arm $mode $(cat "$TMP/probe-dryrun-$arm-$mode.stdout" | tail -1 | cut -c1-300)"
  done
done
git -C "$W" checkout -q -f --detach "$HEAD"; git -C "$W" clean -fdq
echo "restored $(git -C "$W" rev-parse HEAD)"
