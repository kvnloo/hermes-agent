# Can Bölük's Tern frontend: rebased five-slice stack

Source: can1357/hermes-agent:tern-frontend at 0f6fa6fd9534470b1c7d590fcecf9580305def37. Base: synced main 2038bd92d26d06ab3df622dd9155be7296ba5187.

The bundle preserves Can's author metadata and source-SHA provenance on all five derived commits. It requires the base commit in your checkout. Original mirror is unchanged.

1. Renderer-neutral extraction: 3484c1aa6177eeccf9fef45cecf64ed5198b56d3
2. TSP/build/launcher plumbing: 2f5f78fc0e272060cd152d8ec6fafefb19102e27
3. Minimal dogfood UI: 74e408ff62020e224089a114a7eaca447a3e0242
4. Interaction parity: 57e6ef799c357c489c084ff59a82655fface84e0
5. Native polish: 20e93ec1f1dbaec3d40b38568537de853ae0b66e

Final tree 51aeaed1edd3f252b034fb72132da60bb6c88746 equals the local full rebase 8a9a8920db2e6de02e04dd397c48e5bf75fccbdf and published integration commit44117a03d6e3c1bf2063f438d96b288bce2d931c. Independent review verified linear ancestry, author metadata, source provenance and tree equality.

Validation:46 TSP tests;44 Python launcher/source-build tests;33 build-JS tests;20 renderer-extraction tests passed. TSP lint/typecheck/receipted build, extraction typecheck, App lifecycle smoke and non-TSP exit75 passed. Slice3/4 intermediate checks also passed; overlapping tests are not additional unique coverage. Native Tern/live-provider end-to-end acceptance was not established.

The aggregate health check still reports15 feature findings;10 other script guards passed. Not merge-ready. Hosted CI not qualified by these local results.

Import without changing main:

```sh
git fetch origin main
git bundle verify hermes-tern-authored-stack.bundle
git fetch ./hermes-tern-authored-stack.bundle 'refs/heads/tern-stack-*:refs/heads/tern-stack-*'
```

The remotely published integration branch retains Can's exact original commits as second-parent history; its merge topology differs from the linear authored stack in this bundle. No upstream PR or deployment was created.
