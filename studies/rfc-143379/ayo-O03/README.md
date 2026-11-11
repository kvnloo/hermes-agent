# RFC 654 diagnostic replay

Evidence and the source-linked reconciliation are in `/mnt/zer0models/workspace/zer0/data/operations/intent-analyzer-20261104/ayo-runs/exec-O03/`.

`run_fixed_substrate.py`, `test_real_checkout.py`, `test_consent_nonce_invariance.py`, and the scenario JSON are unchanged archived inputs. `diagnose.py` calls the existing runner's `run_one` with the canonical candidate test wrapper. `test_heldout.py` adds identifier-family and orphan-token diagnostics.

The executed replay uses the corrected `candidate-source.tar` and `input-manifest.json` from the execution folder's `evidence/retry-input/`. Fleet job `20261105-030951-7db5` on the `omarchy-phone` Linux guest produced 36 passes and 25 failures, with no skips or collection errors. Its process exits 1. Results, package versions, and source hashes are in `evidence/phone-retry/`. This is not canonical lockfile qualification.

Earlier attempts are reconciled: MBP job `fleet-mbp-90d5521c42594c3d` was evicted for `DiskPressure` before container startup, and phone guest job `20261105-030659-09f8` exited 127 before tests. Neither contributes test results. Their retained stages must not be edited.

Run heavy work only through `fleet-build`, with `--wait 1800`. Use a fresh source snapshot for `bash run.sh`; the script refuses to reuse its output and home directories. Fetch `out`, `setup.log`, and `environment-freeze.txt`.

Check saved evidence without running tests:

```bash
python3 verify_evidence.py /mnt/zer0models/workspace/zer0/data/operations/intent-analyzer-20261104/ayo-runs/exec-O03
```

After an actual diagnostic execution, add `--diagnostic-dir` pointing to its fetched `out` directory. Collection-only errors do not count as executed diagnostics.
