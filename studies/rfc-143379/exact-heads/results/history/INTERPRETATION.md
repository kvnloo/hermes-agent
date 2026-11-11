# Initial runs and corrected interpretation

The fleet logs in this directory retain setup failures and an invalid initial long-session fixture.

- `20261023-014926-8dfc`: read, chain and three individual consent heads executed successfully. Its first combination attempt failed because the local fetch did not update shallow roots. Its long-session fixture used tool results above the actual production pruning floor of 200 characters. The summarizer received zero identifiers. The two `long-*.json` files in this history directory are **invalid as retention-policy comparisons**. They remain evidence of that fixture defect only.
- `20261023-015238-291c`: the shallow update flag fixed the first setup failure. The resolver then lacked the detector commit during the first merge phase. No combination measurement ran.
- `20261023-015406-c312`: the shortened fixture stayed below 200 characters and every cycle delivered identifiers to the deterministic summarizer. Its corrected long-session JSON is in the parent `results/` directory. This run's unrelated combination setup still failed before measurements.
- `20261023-015557-b5eb`: prefetching both PRs through successive local shallow transports failed with `fatal: shallow file has changed since we read it`. No combination measurement ran. The runner now initializes a separate repository and fetches the three exact remote commits together.

These are harness/setup corrections, not upstream Hermes defects. Successful read, chain, and individual consent measurements were not rerun during these retries. Expected RED acceptance findings are distinct from setup errors.

The final long-session harness also returns nonzero for an invalid fixture and the runner returns nonzero for setup/measurement errors. The long-session exit-status-only correction occurred after its successful numerical run. It does not alter the recorded retention algorithms or measurements.
