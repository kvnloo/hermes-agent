# Z09 offline RTK check

This snapshot supports an evidence-retention check, not a held-out model-answer accuracy claim. Five tasks inspect existing source files. Two explicitly synthetic controls check unsupported-command passthrough and ripgrep's no-match exit status. Required facts were frozen before execution in `tasks.json`.

## Source provenance

| Snapshot | Source | Relevant lines |
|---|---|---|
| `rtk_plugin.py` | `/home/kvn/.hermes/profiles/clean/plugins/rtk-rewrite/__init__.py` | 12-13, 23, 40-73 |
| `bench.py` | `/mnt/zer0models/workspace/zer0/data/operations/token-thrift-tools-20261104/bench.py` | 13-18, 66-83 |
| `catalog.yaml` | Hermes commit `84496839dad737f567cb885c34775410e26c8f6e`, `plugin-catalog/rtk-rewrite.yaml` | 3, 14, 22-24 |

The two Python snapshots are byte-for-byte copies, not newly implemented production integrations. Do not execute `bench.py` from this snapshot. It expects the owner's private corpus and overwrites its result path. The runner reads it only as task input.

## Run the check

From the Hermes worktree, use the existing fleet admission path. Replace the binary input with the installed, reviewed RTK binary and choose an output directory:

```sh
fleet-build --node mbp --local-data --src . \
  --src-include scripts/qualify_token_thrift.py \
  --src-include scripts/fixtures/z09 \
  --input /home/kvn/.local/bin/rtk:rtk \
  --mem 1G --cpus 1 --wait 1800 \
  --fetch qualification-results --out /path/to/results \
  -- bash -c 'chmod +x rtk && python3 scripts/qualify_token_thrift.py --rtk ./rtk --inputs scripts/fixtures/z09 --out qualification-results'
```

On exit 75, keep `--wait 1800`. Do not run the check on groot. The payload selects only this small snapshot and the runner. It does not include the historical terminal corpus, user configuration, credentials, or the installed profile's mutable state.

The runner registers the frozen hook with an isolated callback context. It times hook invocation plus terminal command execution, alternates raw/treatment ordering across three repetitions, and saves stdout, stderr, exits, missing facts, hashes, and per-command timing. It disables RTK telemetry under a temporary HOME before running commands. A failed raw evidence assertion exits 2. Treatment failures remain in the result file even if the runner exits 0, so inspect `summary.json` rather than treating process exit as a quality score.

`count_qualify_tokens.py` counts saved output text using an installed `tiktoken` package and a separately supplied, SHA256-verified `o200k_base.tiktoken` vocabulary. Network connections are denied during counting. For the small saved artifact this is a sub-second local metadata check, not a task replay. It counts stdout and stderr separately and refuses outputs that vary between repetitions.

## Interpretation limits

The isolated callback is not the full Hermes dispatcher, approval path, terminal backend, or model loop. Fact presence is not semantic answer correctness. No model, provider billing receipt, Headroom integration, Serena integration, or real user workload distribution is measured. The result cannot establish a production speedup, an agent-quality improvement, or permission to enable a new filter.

Raw JSONL output, fleet receipts, command logs, tokenizer provenance, and the owner-facing qualification document are retained under `/mnt/zer0models/workspace/zer0/data/operations/intent-analyzer-20261104/ayo-runs/exec-Z09/` and `/mnt/zer0models/workspace/zer0/data/operations/token-thrift-tools-20261104/QUALIFICATION-Z09.md`.
