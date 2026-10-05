# CUA status and ownership correction — 2026-10-05

This addendum updates dated observations in checkpoint `920533429b6b3dc5ccfe8b521a05d72d1cf357d5`. Historical local qualifications remain unchanged. It adds no delivery or independent fix.

## Image API workflow completed

[Run 37316142429](https://github.com/kvnloo/cua/actions/runs/37316142429) completed successfully at `e37d782bd732b3ea1de7fa088062db511f9d80bf` on October 5 at 13:38:40 UTC. Job `111783256479` reports every step successful.

This is **Image API workflow success only**. Its selected tests exclude `test_env_transport.py::test_files_listing_metadata`; it does not establish hosted execution of the directory consumer. The local one-test qualification and its causal controls remain separate. The original pending snapshot is retained as historical evidence.

## Version-fact work overlaps an active owner

[CUA PR #4665](https://github.com/trycua/cua/pull/4665), owned by **f-trycua**, was observed at `aa4b0777e6c44d386af0673f5dfa05cdb85a1056`, updated October 5 at 13:05 UTC. Its broad release/version synchronization, including release configuration, overlaps our generated version-fact subsets and composition:

- Sandbox `5d1dd8ec50dfdbf98d27adf98ecf641c7e0ff691`
- Python `4bd270be79fe7171442b65aaefc66d1d4734f3a8`
- TypeScript `127ddc0a9babcd484dea50203c1b7809a28c0db7`
- Partial composition `d1f6fc94217017d8d91b55725f9bc797621b7264`

These remain **qualified downstream evidence overlapping active owner work**, not unowned fixes to promote. The owner's SDK index contains both previously missing pip/npm 0.4.1 facts. The owner reports canonical generation and three passing version tests; those reports are not independent local validation of that owner head. No authentic SDK/Spaces metadata dumps or equivalent generator prerequisites were supplied in this review.

The next gate is the owner's review and evidence disposition. Our composition still has its recorded three passing generator checks and **one failed, two passed** version-fact suite. Neither its historical partial qualification nor the owner's reported success should be relabeled as the other's result. Do not duplicate the release synchronization or hand-edit generated SDK output.

Provenance: nonbundled local receipts `/workspace/receipts/cua-env-directory/hosted-terminal/README.md`, `/workspace/receipts/cua-doc-consumer-intake/4665-pr.json`, `4665-sdk-index.diff`, and `4665-index-assessment.json`. No tests, workflow reruns, upstream messages, or source changes were performed for this addendum.
