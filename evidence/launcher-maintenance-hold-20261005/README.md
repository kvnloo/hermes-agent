# HOLD: adjacent launcher maintenance compatibility

This branch is **evidence only, not a ready fix**. Its single regression test intentionally fails on the included owner proposal. It is neither skipped nor marked `xfail`.

- Current-source control: `7157422022ff06f3e632d1dd394ee1253b17ad37` — **1 passed**.
- Owner proposal: [#129976](https://github.com/NousResearch/hermes-agent/pull/129976), Yuan Li (@dskwe), original `94551490e2d91850b9ad905cc2e25d6736f2a894`, preserved as `e89214945165df6c3b61badc05ba17b57b87a146` — **1 expected assertion failure**.

The same synthetic consumer generates and executes an inert launcher for its own temporary checkout, creates an inert durable target, and invokes `_publish_conveniences(..., create=False)`. Current code updates the launcher: subsequent execution prints the durable marker. The owner proposal still executes correctly before maintenance, but maintenance skips it and subsequent execution prints the old marker. The failing assertion observes `(False, 'fixture launched\n')` instead of `(True, 'durable fixture launched\n')`.

The owner moves bootstrap text from the wrapper into an adjacent script; the current ownership reader no longer recognizes that generator output. The remaining decision is a trusted association representation for legitimate same-installation maintenance. Do not broaden recognition, treat comments as ownership markers, or trust arbitrary adjacent files to make this test pass.

Run the single consumer with the repository's existing test interpreter:

```sh
HERMES_TEST_FILE_RETRIES=0 HERMES_PYTHON=/path/to/test/python \
  bash scripts/run_tests.sh -j 2 tests/hermes_cli/test_launcher_generated_identity.py
```

Linux was exercised; macOS was not. No foreign-file scenarios, real launchers, configuration changes, network calls, dependency installs or guard edits were used. No unrelated owner-reported failure is explained by this evidence. Independent review approved the evidence and retained the integration HOLD.

Static checks and hosted CI are separate from the deliberately failing behavioral result. This branch must not be presented as green or promoted as a product fix.
