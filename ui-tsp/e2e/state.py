"""Observe the isolated application's on-disk YAML using its existing Python runtime."""
import json
import os
import pathlib
import sys

import yaml

manifest = json.loads(pathlib.Path(sys.argv[1]).read_text())
home = pathlib.Path(manifest["home"]).resolve()
proof = pathlib.Path(manifest["proof"]).resolve()
if home.parent != proof or not (home / ".native-settings-e2e").is_file():
    raise SystemExit("Refusing to inspect a non-fixture profile")
os.environ["HERMES_HOME"] = str(home)
os.environ["HOME"] = str(proof / "host-home")
os.environ["XDG_CONFIG_HOME"] = str(proof / "host-home" / ".config")
os.environ["XDG_CACHE_HOME"] = str(proof / "host-home" / ".cache")
os.environ["HERMES_PYTHON_SRC_ROOT"] = manifest["root"]
sys.path.insert(0, manifest["root"])
config = yaml.safe_load((home / "config.yaml").read_text())
if not isinstance(config, dict):
    raise SystemExit("The real fixture config is not a mapping")
if sys.argv[2:] == ["schema"]:
    from hermes_cli.web_server_config import CONFIG_SCHEMA
    print(json.dumps(CONFIG_SCHEMA, ensure_ascii=False))
else:
    print(json.dumps(config, ensure_ascii=False))
