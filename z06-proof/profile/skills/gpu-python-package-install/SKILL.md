---
name: gpu-python-package-install
description: "Use when installing GPU Python ML packages (unsloth, torch)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [python, uv, venv, cuda, torch, ml]
---
# GPU Python package install (unsloth, torch stacks)

## When to Use
Use for installing or qualifying GPU Python dependency stacks: unsloth, vllm, xformers, diffusion/training workers, or anything that pulls in CUDA torch. Honor an explicit target environment; runtime qualification requires more than a successful install.

## Procedure
1. Probe the host in one call: `nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv`, `free -m`, memory PSI from `/proc/pressure/memory`, `uv --version`, `uv python list --only-installed`, `uv cache dir`, and `df -h` for root, the data drive and the actual uv cache. Recheck RAM/PSI/VRAM immediately before model loading; an earlier snapshot is not admission.
2. Choose the explicit requested environment, or one standalone venv per tool under `/mnt/zer0models/venvs/<name>` and project envs under `/mnt/zer0models/project-envs`. For upgrade qualification, create a new isolated environment and preserve live venvs. Do not install into system/Hermes Python. Verify cache placement rather than assuming it; use `UV_CACHE_DIR` on the large data drive for large wheels when needed.
3. Pin the Python version the package supports, usually 3.12: `uv venv <dir> --python 3.12 -q && VIRTUAL_ENV=<dir> uv pip install <pkg>`. Torch with CUDA is several GB, so give the command a long timeout; a foreground timeout over 600s turns into a tracked background job. Do not re-run it while it is pending. End the turn and wait for the notification.
4. Verify before reporting success: `<dir>/bin/python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0)); import <pkg>"`, plus the package's main entry point (e.g. `from unsloth import FastLanguageModel`). Filter the zsh/gitstatus noise from output with `grep -vE 'gitstatus|zshrc|zle|monitor'`.
5. For worker upgrade qualification, run `uv pip check --python <dir>/bin/python`, import the worker's exact symbols, exercise a tiny CUDA operation, and load the existing offline tokenizer before attempting full model loading. Discover checkpoints through provider configuration/docs and reuse them without redownloading. Keep exact commands, exit codes, resolved versions (`uv pip freeze`), worker/source hashes, and admission snapshots outside the repository. Follow [worker qualification](references/worker-qualification.md) for host-memory accounting and real inference gates.
6. Report installation and runtime acceptance separately: versions, torch+CUDA build, GPU visibility, venv path, and fish activation line for installation requests. For qualification, return PASS only after the requested real workload and output inspection pass; otherwise return the specific blocker and exact report path, listing unexecuted gates. Never turn an exit-zero smoke skip or successful import into inference success.

## Pitfalls
- A wheel resolved by unsloth may be built for an older torch (xformers is the usual one) and then fail to load. It falls back to PyTorch SDPA, so it is a warning, not a failure. Offer `unsloth install-kernels xformers` (may compile; slow) or `pip uninstall xformers`; do not silently rebuild.
- `/mnt/zer0models/project-envs` holds per-project envs; `/mnt/zer0models/venvs` holds standalone tool envs. Use the matching one.
