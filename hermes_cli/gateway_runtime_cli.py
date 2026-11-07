"""Machine-readable ensure boundary. No bootstrap credentials leave this command."""
from dataclasses import asdict
import json
import math
import sys
import traceback
from contextlib import redirect_stdout


def ensure_exit_code(result) -> int:
    if result.reason_code == "deadline":
        return 5
    if result.reason_code in {"authorization", "profile_mismatch", "gateway_elevated", "gateway_other_session"}:
        return 4
    return {"ready": 0, "incompatible": 3, "draining": 6,
            "inaccessible": 7, "conflict": 7, "starting": 5, "absent": 5}[result.state]


def cmd_gateway_ensure(args) -> None:
    from hermes_constants import get_hermes_home
    from hermes_cli.gateway_runtime import ensure_gateway_runtime

    # Only caller-controlled timeout syntax/range is an invalid invocation.
    # A ValueError raised after dispatch is a launch failure, not a bad CLI argument.
    try:
        timeout = float(args.timeout)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
    except (ValueError, TypeError):
        print(json.dumps({"state": "inaccessible", "reason_code": "invalid_invocation", "endpoint": None},
                         separators=(",", ":"), sort_keys=True))
        raise SystemExit(2)

    try:
        # Legacy imported utilities can print; protocol stdout belongs only to us.
        with redirect_stdout(sys.stderr):
            result = ensure_gateway_runtime(get_hermes_home(), timeout=timeout)
        payload = asdict(result)
        if result.endpoint:
            payload["endpoint"]["capabilities"] = sorted(result.endpoint.capabilities)
        # The code THIS client (and any gateway it starts) runs, resolved exactly like the owner's
        # ``endpoint.code_sha``: a client that sees them differ is attached to a gateway that
        # outlived ``hermes update`` and must restart it rather than re-attach.
        from hermes_cli.version_info import get_code_identity
        payload["client_code_sha"] = get_code_identity().get("sha")
        code = ensure_exit_code(result)
    except (ValueError, TypeError):
        traceback.print_exc(file=sys.stderr)
        payload, code = {"state": "inaccessible", "reason_code": "launch_failed", "endpoint": None}, 7
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    raise SystemExit(code)
