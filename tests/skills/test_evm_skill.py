from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "optional-skills"
    / "blockchain"
    / "evm"
    / "scripts"
    / "evm_client.py"
)

_FAIL = object()  # eth_gasPrice raises -> _fetch_chain_stats records gas_price_gwei=None


def load_module():
    spec = importlib.util.spec_from_file_location("evm_skill", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _compare(mod, capsys, gas_gwei_by_chain):
    """Run ``cmd_compare`` against mocked RPC/price calls and return its JSON output."""

    def rpc_call(chain, method, params, req_id=1):
        value = gas_gwei_by_chain[chain]
        if value is _FAIL:
            raise RuntimeError("eth_gasPrice failed after retries")
        return hex(int(value * 1e9))

    with patch.object(mod, "rpc_call", side_effect=rpc_call), \
         patch.object(mod, "cg_price_by_id", return_value=10.0):
        mod.cmd_compare(argparse.Namespace())
    return json.loads(capsys.readouterr().out)


def _prices(mod, **overrides):
    prices = {chain: 1.0 + i for i, chain in enumerate(mod.CHAINS)}
    prices.update(overrides)
    return prices


def test_compare_headlines_ignore_chains_whose_gas_fetch_failed(capsys):
    mod = load_module()
    failed, priciest = list(mod.CHAINS)[:2]
    out = _compare(mod, capsys, _prices(mod, **{failed: _FAIL, priciest: 999.0}))

    assert out["most_expensive_gas"] == priciest
    assert out["cheapest_gas"] not in (None, failed)
    # The failed chain stays visible (null gas) instead of being dropped.
    assert next(e for e in out["comparison"] if e["chain"] == failed)["gas_price_gwei"] is None


def test_compare_zero_gas_chain_is_cheapest_not_most_expensive(capsys):
    mod = load_module()
    free = list(mod.CHAINS)[0]
    out = _compare(mod, capsys, _prices(mod, **{free: 0.0}))

    assert out["cheapest_gas"] == free
    assert out["most_expensive_gas"] != free
    assert out["comparison"][0]["chain"] == free
