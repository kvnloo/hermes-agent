"""Private snapshots and receipt checks for frontend products consumed by assembly."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from scripts.bundles.payload import snapshot


def _validate_products(source_snapshot: Path, revision: str | None, products: dict[str, Path]) -> None:
    node = shutil.which("node")
    if node is None:
        raise FileNotFoundError("Node is required to validate frontend products")
    identity = f"source commit {revision}" if revision else "source tree"
    freshness = source_snapshot / "scripts/build/freshness.mjs"
    for name, product in products.items():
        output = product / "dist" if name in {"tui", "tsp"} else product
        result = subprocess.run(
            [node, str(freshness), "--source", str(source_snapshot),
             "--product", name, "--out", str(output)],
            cwd=source_snapshot, capture_output=True, text=True,
        )
        if result.returncode or result.stdout.strip() != "true":
            detail = result.stderr.strip() or result.stdout.strip()
            suffix = f": {detail}" if detail else ""
            raise ValueError(f"{name} product is stale or unreceipted for {identity}{suffix}")


def copy_frontends(source: Path, revision: str | None, frontends: dict[str, Path],
                   staging: Path, *, source_tree: bool = False) -> dict[str, Path]:
    """Copy, then validate, products under an already-private staging directory."""
    if not frontends:
        return {}
    if frontends.keys() - {"tui", "tsp", "web"}:
        raise ValueError("unknown frontend products")
    if not source_tree and (
        revision is None or not re.fullmatch(r"[a-f0-9]{40}", revision)
    ):
        raise ValueError("frontend products require a resolved 40-character source commit")
    staging = Path(staging)
    products_root = staging / "products"
    products_root.mkdir(mode=0o700)
    frozen = {}
    for name, product in frontends.items():
        destination = products_root / name
        shutil.copytree(Path(product), destination, symlinks=False)
        frozen[name] = destination

    source = Path(source).resolve()
    if source_tree:
        _validate_products(source, revision, frozen)
    else:
        with tempfile.TemporaryDirectory(prefix="hermes-frontend-source-") as source_temp:
            source_snapshot = Path(source_temp) / "source"
            snapshot(source, revision, source_snapshot)
            _validate_products(source_snapshot, revision, frozen)
    return frozen


@contextmanager
def snapshot_frontends(source: Path, revision: str | None, frontends: dict[str, Path], *,
                       source_tree: bool = False):
    """Yield receipt-checked private products for a pinned commit or immutable tree."""
    if not frontends:
        yield {}
        return
    with tempfile.TemporaryDirectory(prefix="hermes-frontend-products-") as temp:
        yield copy_frontends(
            source, revision, frontends, Path(temp), source_tree=source_tree,
        )
