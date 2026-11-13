---
name: gz-sensors-native-requalification
description: "Use when requalifying gz-sensors fork leaves natively."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [gazebo, cpp, testing, upstream]
    related_skills: [upstream-contribution, github]
---
# gz-sensors native requalification

## When to Use
Use for isolated native current-base validation of gz-sensors contributions, especially CameraInfo and DVL regressions.

## Procedure

- Read the exact upstream CONTRIBUTING and `.github/workflows/ci.yml`, `.github/ci/packages.apt`, and `.github/ci/after_make.sh` before choosing dependencies. Rotary main uses unversioned CMake package names and may have dropped older Ubuntu CI; do not substitute older release libraries.
- If host dependencies are absent, use an isolated container matching the current CI distribution, enable the official gzdev project repositories, and install the source-owned package list. Preserve image ID, package versions and build logs. Do not expose the host desktop or GPU implicitly.
- Pin both original fork commits and current upstream. Apply each original patch separately, retain author/signoff/disclosure bytes without minting human certifications, and compare `git merge-tree --write-tree BASE ORIGINAL_HEAD` with the tested overlay's `git write-tree`. Equal trees establish clean composition, not a newly published commit.
- Build native targets `INTEGRATION_wide_angle_camera`, `INTEGRATION_dvl`, `INTEGRATION_camera`, `UNIT_Sensor_TEST`, and `UNIT_Noise_TEST` as applicable. CMake emits executables under `BUILD/bin/`, not the corresponding source/test directories.
- Run with isolated Xvfb and `RENDER_ENGINE_VALUES=ogre2`, matching source-owned CI settings. Use separate build directories for baseline and each candidate. Save raw output and GoogleTest XML; repeated runs' XML may only represent one iteration, so reconcile repeat counts with execution log lines.
- Inspect source and log early returns even when GoogleTest reports OK. The wide-angle ImagesWithBuiltinSDF case can return early for Ogre2 without marking a skipped testcase; do not count that as exercised image-rendering coverage.
- For equidistant CameraInfo, revert the production PopulateWideAngleInfo call site while retaining the regression/fixture, rebuild, and require the model/coefficient assertions to fail. Restore bytes and rerun before assigning a final tree verdict.
- For deterministic DVL, restoring nonzero stddev while retaining strict tolerances is an omission control, not proof of a naturally occurring rare >4-sigma flake. Run the clean baseline too and disclose a passing bounded baseline. A changed expected water velocity is a separate sensitivity control. Supply `--gtest_filter=...`; a bare pattern is ignored by GoogleTest.
- `codecheck` can exit zero while emitting source diagnostics. Compare normalized diagnostic sets against the same clean base and report both the exit code and retained warnings; never call that warning-free.
- Review newly synthesized CameraInfo projection entries against authored SDF translations as well as the issue's centered mono fixture. A helper that derives focal lengths may silently zero `P[3]`/`P[7]` where the previous path preserved `LensProjectionTx/Ty`. Corroborate with the real custom-camera-info integration path using nonzero tx/ty, compare the unchanged candidate with the old call path, then restore source and fixtures; hold the supplied artifact rather than silently repairing its immutable SHA.
- Use the exact lens token `equisolid_angle` for equisolid fallback probes; `equisolid` can yield a green metadata test without exercising the intended dispatch. Assert the fallback distortion model, coefficient count, focal/principal entries and authored translations; label these as metadata probes, not image-geometry proof.
- Read each failed hosted job before treating red CI as a translation regression. Inspect the returned check states even when `gh pr checks --json` exits zero; command success does not mean CI success. An older CameraSensor raw-pointer Image constructor can fail both CMake/Resolute and Bazel before tests, while Noble's older Rotary packages still support that exact head. Pin the package versions, test the unchanged head on the supported distribution, and test current-upstream composition separately without rewriting the owner's branch. Compare the synthetic PR merge tree with the candidate tree before attributing hosted source evidence.
- Avoid repeated `xvfb-run` cleanup races in short mutation loops by keeping one private Xvfb process per isolated container, probing its UNIX socket for readiness and terminating it after the suite. Preserve failed attempts; an exit-5 cleanup failure after a real assertion is not a missing assertion, and a missing readiness utility is a harness failure rather than behavioral RED.
- Qualify an actual committed current-base replay when the handoff requires a commit, not only an exported composition tree. Preserve the original author/message/trailers verbatim, use a truthful agent committer, and explicitly record that replaying a patch does not retain original-head ancestry or authorize a force update. Verify the candidate bundle and its prerequisite base. Never turn an existing signoff into a new human certification.
- Separate DVL determinism from stochastic coverage: zero tracking noise keeps Gaussian construction/application but removes nonzero-noise and covariance execution. Generic Noise_TEST success is not DVL noise-integration coverage. Run the unchanged baseline, retain the noise-restoration omission control, and independently perturb expected water velocity to prove kinematics sensitivity; restore and verify the committed source afterward.
- If the shared assignment says existing ownership forbids mutation, keep the owner's carrier unchanged even when an API repair is obvious. Refresh both hosted failed-job logs, reproduce the exact-head compile failure with read-only source mounts, and stage the existing upstream API patch as attributed reference material, not an applied repair. Distinguish an expected-failure runner's zero exit from the nested build's nonzero result.
- Keep current-base native evidence, historical fork CI, fresh hosted CI, DCO/admission, authorization, platform/GPU coverage and full-suite acceptance separate. Shared CameraSensor files do not by themselves make a depth-projection PR a duplicate of a wide-angle metadata repair. Preserve downstream-only stacked evidence-adapter branches and sibling explicit holds.
