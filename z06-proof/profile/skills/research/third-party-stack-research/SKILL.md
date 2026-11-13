---
name: third-party-stack-research
description: "Use when researching or vetting third-party software."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [reverse-engineering, tech-stack, rust, ui-frameworks, research, github, x]
    related_skills: [agent-reach, github]
---

# third-party-stack-research

Use when researching a third-party software stack, selecting an OSS base, vetting a library or system modification, or evaluating a published model checkpoint.

## Rules

1. Recover the owner's original links, existing research issue, branches, forks and prior receipts before broad discovery. Treat worker briefs as pointers and remembered matches as candidates. Resolve a linked post before assuming it names the requested tool; report mismatched identities and inspect the actual host OS and filesystem.
2. Fingerprint the real installed closed build before describing its dependencies. Follow references/closed-binary-stack-fingerprinting.md, dump strings once and read every relevant matching line to reject substring false positives. Keep binary evidence, public documentation, author rationale and runtime behavior separately labeled; stars and sibling projects are weak dependency evidence.
3. Read current first-party README, package metadata and LICENSE bytes before ranking. Follow rename and successor chains through their current lifecycle notices. Pin revisions and hash captured bytes; label moving-branch captures honestly. Scope negative findings to searched revisions and files, and investigate redirects, default branches and truncated trees before interpreting missing paths.
4. Search product names, competitors and domain nouns across several vocabularies. Use paginated REST for large owner inventories and bare blob-less clones for 7/30/90-day commits, active days and human-author counts. Follow references/cross-forge-ecosystem-sweep.md for multi-forge landscapes and forge policy; separate closed services from OSS and stalled mirrors from the actual development forge.
5. Compare matching layers: product, library/SDK, engine, CLI/agent and hosted infrastructure. Record fit, runtime, interactive versus offline behavior, license obligations, maintenance and always-on services. Prefer fitting active communities and no-new-service tools; widen once when none fits. Recommend one stock or forked tool mapped to existing artifacts, while preserving the host's state, orchestration and acceptance ownership.
6. Review build.rs, install hooks, postinstall and unpacked payloads statically before building. Isolate probes from the product checkout, pin versions and inspect telemetry, hosted endpoints and permissions. Follow references/oss-library-adoption-vetting.md to measure real code and matched baselines on the owner's hardware before an adopt, embed, borrow or skip verdict. Obtain selection before forking or installing a product-base candidate.
7. Keep source triage, executable compatibility, adoption benchmark and product integration as separate stages. For generative UI, run the isolated stock-package smoke recipe before host changes. Test rejected types, chunking, interrupted streams, continuation and replay; preserve completion/error state and existing artifact contracts. Compare the actual advertised mechanism with equivalent output, full prompt cost, repairs and real timing.
8. Match the requested visual deliverable to its client. Use references/visual-candidate-gallery.md for verified candidate identities, curated screenshots and license flags. Use the adoption reference for on-device split replay and normal-conversation dogfood: verify exact package/version, authorized device window, original human turns, actual provider deltas and semantic fidelity. Label fixture pacing, WebView labs, desktop previews and sequential composites accurately.
9. Follow references/layerfs-workspace-benchmarks.md for workspace tools. Map capabilities to source-owned seams before timing. Measure checkout, dependencies, prepared-template reuse, teardown, isolation and real agent episodes on the owner's filesystem. Verify Docker ownership and actual limits, preserve shared stores and daemons, bound inode churn, and separate fast mounts from throughput, durability or containment.
10. Follow references/local-model-checkpoint-evals.md for model cards and checkpoints. Read manifests and score provenance before downloads, reuse the author's harness, check cached weights, register the experiment and keep shadow scope. Measure CPU/RAM/VRAM admission, preserve other jobs, use durable GPU runs, and qualify mixed harnesses, tiny validation sets and actual parameter dtypes before reporting gains.
11. Follow references/system-mod-install-vetting.md for privileged modifications: canonical upstream, pinned static review, exact PCI/device identity, failure reports, unprivileged per-kernel builds, mechanism-specific baseline and rollback. Route authorized root work through the owner's credential-safe prompt or polkit, never password text. Codify tracked /etc changes in .files and obtain the applicable maintenance window before disruptive installation or reboot.
12. Keep research separate from adoption, council deliberation, production activation and training authority. Inspect execution-library branch, mount, credential, permission and lifecycle defaults; require isolated ownership and independent exact-head acceptance. Preserve private histories, signing material and credentials outside public inputs and artifacts. Leave user checkout remotes untouched, disclose untested gates, and save research notes only within requested scope.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
