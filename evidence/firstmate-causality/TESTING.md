# Firstmate causality metadata verification

Run from the repository root with the canonical hermetic wrapper. Bootstrap the repository-approved locked development environment once if the worktree has no pytest-capable `.venv`:

```text
uv sync --extra dev
scripts/run_tests.sh tests/tools/test_kanban_tools.py tests/hermes_cli/test_kanban_worker_spawn_toolsets.py -q
```

Expected baseline: **35 passed**. `uv sync` consumes the committed lockfile; the runner validates that the selected environment imports pytest and otherwise fails closed. Run the metadata contract separately:

```text
scripts/run_tests.sh tests/evidence/test_firstmate_causality_metadata.py -q
```

The metadata test executes the real selector, verifies current v3 artifact hashes and matrix, keeps the old six-run artifact superseded, rejects missing/ambiguous current pointers, and keeps artifact authenticity confidence distinct from conditional causal/effect and historical-primary-cause confidence.