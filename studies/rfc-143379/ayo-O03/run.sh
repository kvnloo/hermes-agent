#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir .compat-home
exec env -i PATH="$PATH" HOME="$PWD/.compat-home" TZ=UTC LANG=C.UTF-8 bash -c '
set -euo pipefail
{
  date -u
  uname -a
  python3 --version
  python3 -m venv .compat-venv
  .compat-venv/bin/python -m pip install pytest pytest-asyncio pytest-timeout pyyaml python-dotenv rich filelock httpx requests jinja2 pydantic packaging tomli-w openai ruamel.yaml
  .compat-venv/bin/python -m pip freeze > environment-freeze.txt
} 2>&1 | tee setup.log
export HERMES_PYTHON="$PWD/.compat-venv/bin/python"
exec "$HERMES_PYTHON" diagnose.py
'
