"""The -m gateway entry point retains one module identity (alt-glitch, #152713)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


# Execute the real module using runpy's -m semantics, but intercept main()
# before gateway startup. The canonical import happens inside that process.
_PROBE = r"""
import importlib
import runpy
import sys


class ReachedGatewayMain(Exception):
    pass


def trace_gateway_main(frame, event, arg):
    if (event == "call"
            and frame.f_code.co_name == "main"
            and frame.f_globals.get("__name__") == "__main__"
            and frame.f_globals.get("__package__") == "gateway"):
        running = sys.modules["__main__"]
        imported = importlib.import_module("gateway.run")
        assert imported is running, (
            "gateway.run import created a second module instead of using __main__"
        )
        raise ReachedGatewayMain
    return None


sys.settrace(trace_gateway_main)
try:
    runpy.run_module("gateway.run", run_name="__main__", alter_sys=True)
except ReachedGatewayMain:
    pass
else:
    raise AssertionError("gateway.run did not invoke its main()")
finally:
    sys.settrace(None)
"""


def test_module_entrypoint_reuses_gateway_run():
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, (
        f"gateway module identity probe exited {result.returncode}:\n"
        f"{result.stdout}\n{result.stderr}"
    )
