---
name: blind-semantic-seed-validation
description: "Use when authoring blind semantic defect seeds."
---

# Blind semantic seed validation

1. Read the experiment's boundary brief before opening implementations. Treat permitted filenames as insufficient for blindness: obtain sanitized implementations with inline mutant catalogs, bug selectors, law labels and detector references removed. If such material is inadvertently exposed, record exactly where and label the cohort contaminated; never quietly claim strict blindness.
2. Keep each seed independent and describe one plausible implementation error. Pair exact-once old/new replacements across all required model representations. Review constructor fields and guard domains for identical affected inputs and outputs.
3. Execute a direct concrete reference-versus-patched behavior witness using the actual implementation runtime, never the experiment's detector, tests, law runner or proof battery. Preserve inputs, outputs, command arguments and return codes.
4. Materialize patched models and ports only in an authorized scratch location. Keep source worktrees clean. For flat state representations, decode constructor-relevant fields before comparing outputs so irrelevant fields do not masquerade as semantic differences.
5. Build each patched port with a short syntax/transpilation command; never call transpilation a static typecheck or proof. If a directory-output mode fails on the clean baseline, try an explicit output filename and record both the failure and the workaround.
6. Persist per-seed evidence incrementally. Serialize writers that update one shared sealed JSONL file. At completion, compute IDs, quotas, class counts, witness completeness and a seal checksum programmatically; verify source worktree cleanliness separately.
7. Keep the sealing artifact out of git and avoid repeating descriptions in the summary supplied to the mechanical-check orchestrator. State unexecuted validation and contamination limitations plainly.
