"""Probe (not a contract test): print the registered profile_id per launch/request case."""
import importlib.util, pathlib, pytest
_spec = importlib.util.spec_from_file_location(
    "w2reg", pathlib.Path(__file__).with_name("test_browser_controller_session_profile.py"))
w2 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(w2)
from gateway.browser_control_broker import get_browser_control_broker
from tui_gateway import server

@pytest.mark.parametrize("launch,req", [("default", None), ("default", "ops"), ("work", None), ("work", "default"), ("work", "ops")])
def test_probe(monkeypatch, tmp_path, launch, req):
    w2._serve_launch_profile(monkeypatch, tmp_path, launch)
    sid, reg = w2._create_and_register(w2._Transport(), req)
    try:
        home = server._sessions[sid].get("profile_home")
        out = reg.get("result", {}).get("scope", {}).get("profile_id") if "result" in reg else f"ERROR {reg['error']['code']}"
        import os
        root = str(w2.get_default_hermes_root())
        shown = None if home is None else str(home).replace(root, "<root>")
        with open("/tmp/claude-1000/-home-kvn-zer0/0c40e097-3138-4d4c-a137-74e0e9bc7d3d/scratchpad/w2-browser-memcfg/probe.out", "a") as fh:
            fh.write(f"PROBE launch={launch} request={req} profile_home={shown} root_basename={pathlib.Path(root).name} -> profile_id={out!r}\n")
    finally:
        get_browser_control_broker().reset(); server._sessions.pop(sid, None)
