#!/usr/bin/env bash
# From repo root with pin archives in ../pins and Python env in ../venv.
set -eu
run() { PYTHONPATH="../pins/$1" ../venv/bin/python evals/fb2/run.py "$2" "$3"; }
for pin in 268bb091 0f602c5f a9c65dc4 main; do
    for arm in one two; do run "$pin" stock "$arm"; done
done
for variant in no-lock cache-write both; do
    for arm in one two; do run a9c65dc4 "$variant" "$arm"; done
done
# Re-run the failed controls without changing the input or target.
run 0f602c5f stock one
run main stock one
