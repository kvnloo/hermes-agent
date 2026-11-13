---
name: southpaw-training-onboarding
description: Use when setting up Southpaw profiles or running its tiny-SLM gym.
version: 1
author: Hermes Agent
license: UNLICENSED
metadata:
  hermes:
    tags: [southpaw, evolutionary-training, onboarding]
    related_skills: [hermes-agent, oss-checkout-install]
---
# Southpaw training onboarding

## When to Use
Use when deploying Southpaw evolutionary-training with fresh trainer/evaluator profiles, canonical provider checkout, and gated onboarding, or when running its Darwin evolution on small models.

## Onboarding gates

- Recover owner's live factory thread; distinguish this install from chiefstaff migration and architecture work.
- Resolve kvnloo/evolutionary-training and SouthpawIN source by HEAD SHA; reuse pinned provider checkout unchanged.
- Read GYM-TRAINER.md and scripts before configuring. Preserve original instructions and adapt paths and publication targets explicitly.
- Keep fresh independent profile identities; don't clone credentials, memories or cron jobs.
- Compare documented hardware (24 GB GPU / 32 GB RAM) with live VRAM/RAM/free/PSI; don't silently shrink workload.
- Reuse Evolution Lab's preparation-only bridge; its tool-bearing refusal is intentional.
- Probe CMAES.tell with equal distinct Genome values; also inspect generation progress and benchmark envelope compatibility.
- Configure Bot Mode via `profiles.configure`, verify via `profiles.describe`; don't claim canonical chats created from metadata.
- Use `discover_gateway_endpoint` + `attachable`, then `connect_gateway(endpoint=...)`; GatewayClient uses `rpc(method, **params)`. Verify SDK imports and dependency-bearing environment.
- Model routing: gym profiles use provider `vllm-sr` + the `privacy-route` plugin (O18). Read `<profile>/logs/privacy-route.jsonl` before blaming a model: `queue` means the lane is not deployed, not a bug.
- Keep schedules/uploads unarmed until source, hardware, runtime, data and authorization gates pass; verify with `cron list`.

## Tiny-SLM gym (Southpaw method on sub-1B models)
Use when the owner wants Southpaw's evolution loop applied to tiny models, or combined with weight-space programming (z0intelligence `benchmarks/weight_space`).

Scope rule: the owner's intent is Southpaw's **profile scaffold** (tiny-trainer runs loops, tiny-evaluator gates) running the **blog's process** (a frontier editor reads and edits raw weights, Experiment-8 style) on tiny models trained at **z0intelligence decision work** (tool-family next_action, recovery_action, model/effort routing, verification-needed), not math. Darwin merges and SFT are baseline arms; math lanes only validate the harness. When asked "are you using method X", answer which mechanism actually runs, plainly. In every update, label each number with the mechanism that produced it (CMA-ES Darwin merge, frontier editor <model>, control) and say "no editor has touched the weights yet" when true: the owner reads a merge or baseline result as the blog method doing worse otherwise.

0. Before proposing a plan, re-read the z0evals record on small models for z0's own decisions (posts `slm-router-v0`, `factory-intelligence-v0`, `local-offload-and-authority-v0`, `offload-and-loop-v0`, `next-action-baseline`, and the `math372` council lesson) and the `~/.z0int/episodes` manifests (labels, n, ridge/MB baselines). Sub-1B decoders lose to 3-8B models at free-form tool calling; their plausible niche is bounded scoring/classification with calibrated abstention. A plan that ignores these numbers repeats killed experiments.
0b. The Hermes episode datasets are the owner's own prompts and tool history ("local vault only"). Moving them, even as derived features, to Modal or any external service needs his explicit OK; offer redacted-derived / groot-only / public-stand-in options.
1. Work on a branch worktree of kvnloo/evolutionary-training (`git worktree add -b <branch> /mnt/zer0models/worktrees/evolutionary-training-<topic> origin/master`); the canonical provider checkout stays byte-clean. The existing gym code lives in `tiny/` on branch `feat/tiny-slm-gym` (`darwin.py`, `modal_gym.py`, `launch.py`, `collect.py`, README); extend it rather than rewriting.
2. Pairs are base × instruct of the same architecture, revisions pinned via `https://huggingface.co/api/models/<id>` `sha`. Check `/mnt/zer0models` (HF hub at `zer0-models/huggingface/hub`) for local copies first. "Both ends in parallel" = smallest (SmolLM2-135M, Gemma-3-270M) and largest under 1B (Qwen3.5-0.8B, Qwen3-0.6B) lanes at once, moving inward.
3. Run each lane end to end inside one Modal GPU container (parents, CMA-ES, best merge, held-out scoring) and spawn it detached; groot only launches and reads the results Volume. Smoke every new pair with `--gens 1 --pop 2` before the real run: architecture bugs show up at the parents or the first candidate.
4. Fitness from a train split only; held-out sets (GSM8K test, MATH-500, pinned dataset revisions) never feed fitness. Add a smooth tie-break term (gold-solution log-prob), since 135M models score ~0% and accuracy alone gives no gradient.
5. Profiles: `hermes profile create <name> --description ...` (no clone), then copy only the `model`/`providers` blocks from gym-trainer's config, symlink `plugins/privacy-route` to `~/.local/lib/z0-guard/privacy-route/current/adapter`, copy `privacy-route.json`, set `terminal.cwd` to the worktree, and replace the default SOUL.md stub (read it first; the write guard refuses otherwise). Trainer runs lanes; evaluator judges paired, per-item gains against the better parent.

6. Lever order for z0 decision tasks (four-seat council convergence): mandatory simple controls (majority, recency/last-family, bigram, ridge, MB) -> frozen SLM trunk + trained linear/logit head (Jev-style; no generated output, so no format failure) -> LoRA only if the head underfits -> blog weight editing only against a named, measured defect (looping, invalid-format/no-answer, majority collapse), at matched budget against calibration/logit-bias, a random rank-1 edit of equal norm and LoRA -> Darwin base x instruct merges last (no parent is skilled at z0 tasks). Promote only on frontier work removed (tokens/calls/latency at verified outcome), never on prediction accuracy alone.
7. next_action data recipe (study `z0evals studies/tiny-slm-gym-v0`, `scripts/nextaction.py split|parity|controls`): reuse `z0int/train.py` features (96-dim trigram hashes of user text and previous five families; `tool` is the label source, never a feature); split whole sessions by start time with a purge gap before each boundary; commit only counts/rates/sha256; seal the test file 0600 for tiny-evaluator.

Pitfalls:
- Run the trivial controls before calling any learned model a baseline: on next_action, "same family as last step" scores ~0.74 where the published ridge bar was 0.41. A plan built on the weak bar overstates every candidate.
- A few automated sessions (delegation loops, long EXECUTE runs) hold 20-70% of rows, so row-level accuracy measures those loops. Make session-macro (each row weighted 1/session length) the primary metric, report row-micro beside it, and use session-clustered bootstrap CIs.
- Split by session COUNT, not row fraction: with giant sessions a row-fraction boundary leaves a dev window of a dozen sessions. Purge only sessions *starting* within the gap; purging every session that spans a boundary drops whole giant sessions (tens of percent of rows).
- A merge chosen on a 64-item fitness set does not carry over: the best of 48 candidates is inflated by ~2 SE. Re-score winners on held-out data and compare with the better parent; a fitness gain alone is not a result.
- The source `CMAES.tell` sorts (fitness, Genome) tuples and crashes on tied fitness; rank on (fitness, index).
- Qwen3.5 checkpoints store `model.language_model.*` while `AutoModelForCausalLM` parameters are `model.*`. Map parameter names to checkpoint keys explicitly and assert >95% of parameters mapped, or the "merge" silently changes nothing.
- Qwen's 248k vocabulary: a batched fp32 `log_softmax` over full logits OOMs a 24 GB GPU. Keep logits bf16 and take per-sample `cross_entropy` on the completion slice, small batches.
- The source merge uses only `rho_b` and `tau` of the 14 genome dims; any use of the other dims is an extension. Say so in the README.
