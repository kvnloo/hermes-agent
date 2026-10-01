"""Direct-call probe: each arm's tools/fuzzy_match.py loaded by path, no repo imports.

Prints (count, strategy, error-prefix) per case per arm as JSON. $0, no network.
"""
import importlib.util
import json
import sys
from pathlib import Path

ARMS_DIR = Path(sys.argv[1])
ARMS = sys.argv[2].split(",")

CASES = {
    # wrong-region cases (must refuse)
    "block_anchor_54572": (
        "def handler(request):\n    audit_log(request.user_id)\n    return process(request)\n",
        "def handler(request):\n    validate(request.token)\n    return process(request)",
        "def handler(request):\n    rate_limit(request)\n    return process(request)",
    ),
    "single_line_trim_125376": (
        "def f(v):\n    return value.strip()\n",
        "    return value.trim()",
        "    return value.fixed()",
    ),
    "missing_anchor_111127": (
        "def normalize(value):\n    return value.strip()\n",
        "return value.trim()",
        "return value",
    ),
    "trailing_newline_bypass": (
        "def f(v):\n    return value.strip()\n",
        "    return value.trim()\n",
        "    return value.fixed()\n",
    ),
    # extra observations (not contract cases)
    "obs_context_aware_half_block_54572": (
        "def transfer(amount, dst):\n    check_balance(amount)\n    ledger.debit(amount, dst)\n    return receipt(dst)\n",
        "def transfer(amount, dst):\n    # TODO add logging here\n    pass\n    return receipt(dst)",
        "x = 1",
    ),
    "obs_crlf_trailing_bypass": (
        "def f(v):\n    return value.strip()\n",
        "    return value.trim()\r\n",
        "    return value.fixed()\r\n",
    ),
    "obs_leading_newline_bypass": (
        "x = 1\n\n    return value.strip()\n",
        "\n    return value.trim()",
        "\n    return value.fixed()",
    ),
    "obs_two_line_wrong_token": (
        "def normalize(value):\n    return value.strip()\n",
        "def normalize(value):\n    return value.trim()",
        "def normalize(value):\n    return value",
    ),
    # legitimate near-miss (must apply)
    "legit_block_drift_54575": (
        "def foo():\n    x = 1\n    y = 2\n    return x + y\n",
        "def foo():\n  x = 1\n  y = 9\n  return x + y",
        "def foo():\n    return 0\n",
    ),
    "legit_smart_quote_single_line": (
        "msg = “hello”\n",
        'msg = "hello"',
        'msg = "goodbye"',
    ),
    "legit_indent_drift_111127": (
        "def retry_delay():\n    return 250\n",
        "\n  return 250\n",
        "\n  return 500\n",
    ),
}


def load(arm):
    spec = importlib.util.spec_from_file_location(f"fm_{arm.replace('-', '_')}", ARMS_DIR / arm / "fuzzy_match.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


out = {}
for arm in ARMS:
    mod = load(arm)
    out[arm] = {}
    for name, (content, old, new) in CASES.items():
        new_content, count, strategy, err = mod.fuzzy_find_and_replace(content, old, new)
        out[arm][name] = {
            "count": count,
            "strategy": strategy,
            "error": (err or "")[:40] or None,
            "file_changed": new_content != content,
        }
print(json.dumps(out, indent=1))
