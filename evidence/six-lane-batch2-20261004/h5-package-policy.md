# Batch 2 H5 — dependency-group exact-pin policy gap

Base main: `24b9f0f8c5df5ec6d3d5c10ad9b27c3346bbc925`. Worktree `/workspace/lanes/h5`.
No production edit, commit, push, hosted CI, upstream communication, installation, or package-index requests.

## Finding

Fresh issue https://github.com/NousResearch/hermes-agent/issues/132558 has no claim comments or exact-number PR, but the defect class is owned:
- Adolanium PR130838, head `01b82ccf5b4574d27658e913d222528c266dbe1f`.
- Sahilvishnaliya PR132300, head `0a26e9141c6bcd0043affd973b031b9feb5c8c63`.
- Individual overlaps: pilk PR124115 and resvg-py PR123492.

Both comprehensive owner policies add seven exemptions and their invariant guards enumerate project.dependencies, project.optional-dependencies, and build-system.requires. Both omit dependency-groups. Current `pyproject.toml:554` declares `distlib==0.4.3; sys_platform == 'win32'` under dependency-groups.test; it is not exempt.

Current missing unique names: distlib, pilk, playwright, pyopen-wakeword, pypinyin, resvg-py, tomli-w, truststore. The two owner's seven-entry policies leave precisely distlib missing. This is additive current-source drift in already-owned work, not grounds to replace their implementations.

Intent: current pyproject.toml lines669-679 explicitly promise exemption for every exact pin and cite the missing invariant guard. Originating commit `1f713dce385991c5dd74c107da46f65cba80f5f7`, walker, "test(packaging): exempt every exact pin from exclude-newer — release-day brick class". distlib was introduced by ethernet commit `1c8fae61808f8ad721c5efed71996659d9d5aa5a`, "fix(pm): preserve runtime and user state across failure paths".

## Synthetic local consumer proof

Untracked review probe: `/workspace/lanes/h5/tests/pm/test_exact_pin_quarantine_consumer_probe.py`.
Log: `/workspace/receipts/batch2-h5-quarantine-probe.log`.

The probe parses actual current TOML with packaging.Requirement, canonicalizes package names, includes all dependency-group tables without evaluating the current host marker, and calls actual `pm.workspace._core_release_quarantine` against the current lock. Three in-memory policy scenarios: current main, seven additions shared by both owners, eight additions including distlib. No source policy mutated on disk. Existing dated reviewed overrides remain accepted.

Initial run: **2 expected failures, 1 pass**. Main reports eight unique missing package names mapped to generated '14 days'; owner-seven reports only distlib at '14 days'; group-inclusive control passes. Independent H4 review requested direct generated policy assertions, because initial criterion only checked declared membership. Added comparison of generated values to explicit reviewed values (or required false for undeclared exact pins), then reran. Final strengthened run: **2 expected failures, 1 pass** in 1.6s runner wall; owner-seven explicitly reports distlib generated value `14 days`, expected `False`.

Canonical command: `HERMES_PYTHON=/workspace/.onboarding/hermes-tests/bin/python scripts/run_tests.sh -j 2 tests/pm/test_exact_pin_quarantine_consumer_probe.py -q`, with exec write grant `/var/tmp`. No bare pytest or dependency installation.

This proves the manifest/generated-workspace omission only. It does not reproduce uv resolution against a mirror missing upload-time; that behavior remains the reporter's evidence. The distlib marker is Windows-only, but uv's universal lock may consider it on another host; no native Windows resolution is claimed here.

## Disposition and independent review

Parent selected **evidence only**: no production follow-up without owner coordination. Preserve the existing owners' credit and send the following private review finding to the parent: both guards should include dependency-group requirements; current distlib is missing from each seven-entry policy, and source/uv.lock policy parity must remain coherent. No upstream message was sent.

H4 independent reviewer `/root/hermes_gateway` approved the final strengthened evidence: independently inspected both owner guard diffs, confirmed group omission and final2expected-fail/1pass proof. Qualification: only the seven-entry policy deltas were simulated on current main, not full owner commits or actual mirror resolution.

Portable probe copy: `/workspace/receipts/batch2-h5-quarantine-probe.py`. To reproduce, place this copy at `tests/pm/test_exact_pin_quarantine_consumer_probe.py` in a checkout of the base SHA and run the canonical command above. It deliberately yields two failures and one pass; do not add it to a permanent test suite unchanged. Parent may publish this receipt and probe in the downstream evidence packet. No generated lock, dependency, source, or existing test file was edited.
