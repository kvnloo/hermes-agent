# Serena source-retrieval qualification

This experiment runs three inspected tasks on one real RTK hook file. It compares full-file reads, targeted shell reads, and Serena 2.1.0 LSP retrieval. It does not measure held-out model answers, provider usage, or a live agent integration. See `qualify_serena_semantic.py:91-139` and `fixtures/z09-semantic/tasks.json`.

The fixture is a byte-for-byte copy of the installed clean-profile hook, SHA256 `0b39e5a4281b16bf405d3230caee2295907aa7fdcb8859ef60dbc552280ab70a`. No historical conversation or corpus is an input. The targeted shell baseline has preselected line ranges and search context. It measures retrieval with known locations, not discovery effort. See `fixtures/z09-semantic/tasks.json:6-28` and the operation's `logs/freeze-semantic-20261112.log`.

## Run the experiment

Use the complete `fleet-build` command in the operation's `logs/COMMANDS-20261112.md`. Ship only the runner and fixture directory. Stage `uv` and the verified `o200k_base.tiktoken` vocabulary. Provision Python 3.13 in the job directory before starting Serena. Serena's pinned Pyright launcher requires that interpreter even when the server runs on Python 3.14. See the retained failure's `server-stderr.log:51-56` and successful `python-install.log`.

Install `serena-agent==2.1.0` with `tiktoken==0.12.0`. Serena requires that tokenizer version; the previous Headroom experiment's `0.14.0` pin conflicts. The worker's `dependencies.txt` records transitive versions. The operation's first failed fleet log records the resolver conflict.

Run `qualify_serena_semantic.py --self-check`, then the runner without that flag. Select a fresh `--out` directory for every replay. The runner refuses an existing records file. Failures remain in its saved records, and any failed evidence check produces a nonzero exit. See `qualify_serena_semantic.py:50-52,139`.

The server uses stdio, a temporary HOME, no display/session environment, and disabled dashboard/browser/GUI flags. Only `initial_instructions`, `find_symbol`, and `find_referencing_symbols` are called. No editing, memory, shell-execution, or model tool is called through Serena. See `qualify_serena_semantic.py:64-108`.

## Audit saved receipts

Run `check_serena_semantic.py` with `--artifacts`, `--inputs`, `--runner`, `--hook`, and `--receipt`. The full command is in the operation's `logs/check-and-negative-control-20261112.log`. This small local metadata audit checks source hashes, all 27 records, MCP errors/text, exact Python AST body spans, the real caller, summary arithmetic, and fleet exit 0. It does not independently retokenize saved text. See `check_serena_semantic.py:11-72`.

The retained negative control corrupts a returned source body while preserving required substrings. The checker must exit 1. The original artifact must exit 0. See the same negative-control log.

## Interpret the measurements

Token counts cover returned text, including Serena's JSON text formatting, not provider or billed usage. The instruction-text count and tools-catalog JSON count are separate overhead estimates, not an actual client prompt measurement. Call latency excludes installs, staging, admission, and server bootstrap. First semantic calls can include remaining LSP initialization. See `qualify_serena_semantic.py:81-134`.

The owner-facing result is `../../../QUALIFICATION-Z09-20261112.md` relative to this worktree root. Operation evidence is in `/mnt/zer0models/workspace/zer0/data/operations/intent-analyzer-20261104/ayo-runs/exec-Z09/`. This run neither installs Serena durably on the owner host nor changes production enablement. See the operation's commands and scoped wiring log.
