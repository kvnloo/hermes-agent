# Current Z09 qualification checks

These checks extend `qualify_token_thrift.py` without changing a live plugin, profile, or service. The command experiment measures required source facts, saved output tokens, and terminal-plus-transform latency. It does not measure model answers or provider usage. See `qualify_token_thrift_current.py:83-150`.

The input directory `fixtures/z09-current/` freezes the installed RTK hook on 2026-11-11. `bench.py` and `catalog.yaml` come from the original `fixtures/z09/` snapshot. The source hooks are not executed as benchmark commands, except for importing the frozen RTK callback. The private historical corpus is not an input. See `fixtures/z09/README.md:5-13`, `fixtures/z09-current/tasks.json`, and `qualify_token_thrift_current.py:44-50,81-106`.

## Replay the command experiment

Use the exact fleet command in the operation folder's `logs/COMMANDS-20261111.md`. Select only the two runner files and current fixture directory. Stage the installed RTK and uv binaries and the previously verified `o200k_base.tiktoken` vocabulary. Install `headroom-ai==0.42.0` and `tiktoken==0.14.0` in the worker's isolated venv. The fetched `dependencies.txt` records transitive versions.

The runner rotates arm order across three repetitions. Both Headroom arms use `protect_recent=0` and disable ML. The default-no-ML arm is not unrestricted Headroom default behavior. The agent arm selects `mode="agent"`. Python socket connections are denied during the experiment, and RTK telemetry is disabled under a temporary HOME. See `qualify_token_thrift_current.py:52-106`.

A process exit of 0 means the raw arm passed. Treatment failures remain in `records.jsonl`; inspect the summary rather than treating process success as qualification. See `qualify_token_thrift_current.py:137-150`.

## Validate retained evidence

Run `check_qualify_current.py` with the fetched artifact directory, current fixture directory, runner path, installed hook path, RTK binary path, and fleet terminal receipt. This metadata check does not replay tasks. It verifies that the saved evidence still matches the installed hook and RTK binary. See `check_qualify_current.py:13-24`.

The recorded negative control supplies the older hook and must fail with `Installed hook has drifted`. The same check against the current installed hook must pass. The experiment runner's `--self-check` rejects missing facts, changed exits, and transform errors. See `check_qualify_current.py:22`, `qualify_token_thrift_current.py:23-29`, and operation log `logs/drift-negative-control-20261111.log`.

## Replay the Serena catalog smoke check

Use the separate fleet command in `logs/COMMANDS-20261111.md`. It installs `serena-agent==2.1.0` in an isolated worker venv, then runs `qualify_serena_catalog.py`. The script starts a temporary stdio MCP process, initializes it, lists its tools, and closes the session. Native display variables are removed, browser launch is disabled, and dashboard and GUI-log flags are false. It does not activate a project, run semantic queries, enable a production client, or call a model. See `qualify_serena_catalog.py:16-51`.

The operation evidence folder is `/mnt/zer0models/workspace/zer0/data/operations/intent-analyzer-20261104/ayo-runs/exec-Z09`. The owner-facing result is `../QUALIFICATION-Z09-20261111.md` relative to this worktree's root.
