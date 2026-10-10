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


def load_module():
    spec = importlib.util.spec_from_file_location("evm_skill", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# Sentinel instructing the rpc_call mock to raise (simulating eth_gasPrice
# failing after all retries), which _fetch_chain_stats swallows into
# gas_price_gwei = None.
_RAISE = object()


def _rpc_side_effect(gas_by_chain):
    """Build an rpc_call replacement driven by an intended gwei value per chain.

    A float (including 0.0) is turned into the hex of int(gwei * 1e9), so the
    real hex_to_int -> gwei_from_wei -> round(...) pipeline runs end-to-end.
    _RAISE makes the call raise, exercising the None (failed-fetch) path.
    """
    def _rpc_call(chain, method, params, req_id=1):
        if method != "eth_gasPrice":
            return "0x0"
        value = gas_by_chain[chain]
        if value is _RAISE:
            raise RuntimeError("eth_gasPrice failed after 5 retries")
        return hex(int(value * 1e9))
    return _rpc_call


def _run_compare(mod, gas_by_chain, native_price=10.0, capsys=None):
    """Patch the network layer and run cmd_compare, returning parsed stdout JSON."""
    with patch.object(mod, "rpc_call", side_effect=_rpc_side_effect(gas_by_chain)), \
         patch.object(mod, "cg_price_by_id", return_value=native_price):
        mod.cmd_compare(argparse.Namespace())
    captured = capsys.readouterr()
    return json.loads(captured.out)


# --------------------------------------------------------------------------- #
# Per-chain gas scenarios (gwei) for the headline-mislabel regression suite.
# --------------------------------------------------------------------------- #

_NONE_SCENARIO = {                      # polygon fails its eth_gasPrice fetch
    "ethereum":  12.5,
    "bsc":       3.2,
    "base":      0.001,
    "arbitrum":  0.01,
    "polygon":   _RAISE,
    "optimism":  0.002,
    "avalanche": 25.0,
    "zksync":    0.0452,
}

_ZERO_SCENARIO = {                      # base returns 0x0 (genuinely free gas)
    "ethereum":  12.5,
    "bsc":       3.2,
    "base":      0.0,
    "arbitrum":  0.01,
    "polygon":   80.0,
    "optimism":  0.002,
    "avalanche": 25.0,
    "zksync":    0.0452,
}

_HAPPY_SCENARIO = {                      # every chain reports a real positive price
    "ethereum":  12.5,
    "bsc":       3.2,
    "base":      0.5,
    "arbitrum":  0.01,
    "polygon":   80.0,
    "optimism":  0.002,
    "avalanche": 25.0,
    "zksync":    0.0452,
}


def test_compare_failed_fetch_chain_not_named_most_expensive(capsys):
    """A chain whose eth_gasPrice failed (gas_price_gwei=None) must not be
    labelled most_expensive_gas; the real most-expensive chain wins. Guards
    the post-retry RPC-failure path, which reproduces against live public RPCs."""
    mod = load_module()
    out = _run_compare(mod, _NONE_SCENARIO, capsys=capsys)

    assert out["most_expensive_gas"] == "avalanche"      # 25.0 gwei, the real max
    assert out["cheapest_gas"] == "base"                # 0.001 gwei, the real min

    chains_in_order = [e["chain"] for e in out["comparison"]]
    assert chains_in_order[-1] == "polygon"             # None sorts to the tail
    assert chains_in_order[0] == "base"

    polygon_entry = next(e for e in out["comparison"] if e["chain"] == "polygon")
    assert polygon_entry["gas_price_gwei"] is None      # failure still visible
    assert out["errors"] == {}                          # errors contract unchanged


def test_compare_zero_gas_chain_named_cheapest_not_most_expensive(capsys):
    """A chain returning 0x0 (gas_price_gwei=0.0, genuinely the cheapest) must
    be reported as cheapest_gas, not mislabelled most_expensive_gas. Guards
    the truthiness-vs-`is None` distinction at the heart of the bug."""
    mod = load_module()
    out = _run_compare(mod, _ZERO_SCENARIO, capsys=capsys)

    assert out["cheapest_gas"] == "base"                # 0.0 gwei, genuinely cheapest
    assert out["most_expensive_gas"] == "polygon"       # 80.0 gwei, genuinely priciest

    assert out["comparison"][0]["chain"] == "base"
    assert out["comparison"][0]["gas_price_gwei"] == 0.0
    assert out["comparison"][-1]["chain"] == "polygon"
    assert out["errors"] == {}


def test_compare_all_chains_fail_yields_null_headlines(capsys):
    """If every chain fails eth_gasPrice (all gas_price_gwei=None), headlines
    are None. Guards the empty `priced` branch (`if priced else None`)."""
    mod = load_module()
    all_failed = {chain: _RAISE for chain in mod.CHAINS}
    out = _run_compare(mod, all_failed, capsys=capsys)

    assert out["cheapest_gas"] is None
    assert out["most_expensive_gas"] is None
    assert len(out["comparison"]) == len(mod.CHAINS)
    assert all(e["gas_price_gwei"] is None for e in out["comparison"])
    assert out["errors"] == {}


def test_compare_happy_path_no_regression(capsys):
    """With real positive prices on every chain, headline derivation must match
    the expected min/max and the comparison array must be ascending by gas.
    Pins the public output contract that SKILL.md directs consumers to read."""
    mod = load_module()
    out = _run_compare(mod, _HAPPY_SCENARIO, capsys=capsys)

    assert out["cheapest_gas"] == "optimism"             # 0.002 gwei
    assert out["most_expensive_gas"] == "polygon"       # 80.0 gwei

    gas_values = [e["gas_price_gwei"] for e in out["comparison"]]
    assert gas_values == sorted(gas_values)             # ascending
    assert gas_values[0] == 0.002
    assert gas_values[-1] == 80.0
    assert out["errors"] == {}
