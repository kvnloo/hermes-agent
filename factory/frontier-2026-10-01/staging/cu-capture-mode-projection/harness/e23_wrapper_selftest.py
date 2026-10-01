"""Self-test of e23_driver_wrapper.sh with E23_LOCAL_DRIVER (no docker, no display): Hermes' production startup
must accept the wrapper (runtime contract, manifest-discovered invocation, session start, capability gate)."""
import json, os
from tools.computer_use import cua_backend_driver as d
from tools.computer_use.cua_backend import CuaDriverBackend
out = {}
st = d.cua_driver_runtime_contract_status()
out["contract"] = {k: st[k] for k in ("ready", "version", "reason")}
cmd, args = d._resolve_mcp_invocation(os.environ["HERMES_CUA_DRIVER_CMD"])
out["mcp_invocation"] = {"command_is_wrapper": os.path.realpath(cmd) == os.path.realpath(os.environ["HERMES_CUA_DRIVER_CMD"]), "args": args}
b = CuaDriverBackend()
b.start()
out["started"] = True
out["supports_include_accessibility_tree"] = b._session.supports_input_property("get_window_state", "include_accessibility_tree")
out["supports_include_screenshot"] = b._session.supports_input_property("get_window_state", "include_screenshot")
out["list_windows_count_no_display"] = len(b.list_windows())
b.stop()
print(json.dumps(out, sort_keys=True))
