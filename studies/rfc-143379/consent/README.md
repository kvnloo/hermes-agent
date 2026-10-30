# Hermes consent lab (offline, synthetic)

A reproducible, no-GitHub-write experiment for Hermes [#116788](https://github.com/NousResearch/hermes-agent/issues/116788) comparing `main`, PR #116834, PR #116846, and a **hypothetical local combination**. Tests source-aligned gate implementations with a synthetic forbidden marker, not real personal information.

- `FINDINGS.md`: outcomes, source pins, recommended regressions, limitations.
- `runtime.py`: temporary-home memory/pending persistence harness and CSV writer.
- `snapshots/main.py`, `snapshots/pr_116834.py`, `snapshots/pr_116846.py`: production gate excerpts with standalone import adapters.
- `snapshots/local_combination.py`: proposed union, not upstream code.
- `test_consent.py`: 116 deterministic parameterized tests (many assert reproduced vulnerabilities rather than safety).
- `results.csv`: observed decisions and marker locations.

Re-run with Python 3.10+ and pytest:

```sh
python -m pytest -q test_consent.py
python runtime.py
```

No full Hermes repository or live model is required or used; the GitHub checkout integration run remains to be done.
