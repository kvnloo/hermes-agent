"""Record bionic tools and assemble the prepared fixed-prefix agent."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def write_facts(payload: Path, lock_path: Path, build_set: Path, tui: Path,
                source: Path, ref: str) -> None:
    from pm.lock import Lockfile
    from pm.registry import get_package
    from scripts.bundles.frontend_products import snapshot_frontends
    from scripts.bundles.payload import record_tools, resolve_revision
    from scripts.build.agent import assemble
    from scripts.build.inputs import AgentInputs, RESOURCE_ENV, dependency_site

    source = Path(source).resolve()
    revision = resolve_revision(source, ref)

    payload = payload.resolve()
    target = "linux-arm64-bionic"
    record_tools(payload, lock_path, target, {name: name for name in ("python", "node", "uv", "npm", "ffmpeg", "ripgrep")})
    natives = [line.strip() for line in build_set.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    (payload / "native-wheels.json").write_text(json.dumps(natives) + "\n", encoding="utf-8")
    # This is the target pin, never the host's sys.version_info or sysconfig.
    version = Lockfile(lock_path).version("python")
    python = get_package("python").binary(payload / "tools/python", target)
    if version is None or python is None:
        raise ValueError("bionic Python pin/executable missing")
    repo = payload / "app"
    inputs = AgentInputs(
        project=repo / "pyproject.toml", code=repo, repo="app", placement="fixed", target=target,
        python=python,
        site_packages=dependency_site(payload / "venv", version, target),
        environment=payload / "venv", tools=payload / "tools", pm_runtime=payload / "pm-runtime",
        resources={name: repo / name for name in RESOURCE_ENV}, stamp=repo / "install-stamp.json",
    )
    with snapshot_frontends(source, revision, {"tui": tui}) as frozen:
        assemble(replace(inputs, frontends=frozen), payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path)
    parser.add_argument("build_set", type=Path)
    parser.add_argument("--tui-product", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ref", required=True)
    args = parser.parse_args()
    write_facts(
        args.payload, args.payload / "app/pm/lock.json", args.build_set, args.tui_product,
        args.source, args.ref,
    )
