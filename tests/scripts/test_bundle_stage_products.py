from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.bundles import native


ROOT = Path(__file__).resolve().parents[2]


def _git(source: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=source, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _frontend_fixture(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required to check frontend receipts")
    source = tmp_path / "source"
    build = source / "scripts/build"
    build.mkdir(parents=True)
    for name in ("freshness.mjs", "frontend-common.mjs", "tui.mjs", "tsp.mjs", "web.mjs"):
        shutil.copy2(ROOT / "scripts/build" / name, build / name)
    (source / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
    (source / "package-lock.json").write_text('{"lockfileVersion":3}\n', encoding="utf-8")
    (source / "ui-tui/src").mkdir(parents=True)
    (source / "ui-tui/src/entry.tsx").write_text("export const build = 'A'\n", encoding="utf-8")
    (source / "ui-tsp/src").mkdir(parents=True)
    (source / "ui-tsp/src/entry.ts").write_text("export const build = 'A'\n", encoding="utf-8")
    (source / "web/src").mkdir(parents=True)
    (source / "web/src/main.ts").write_text("export const build = 'A'\n", encoding="utf-8")
    _git(source, "init")
    _git(source, "config", "user.name", "Fixture")
    _git(source, "config", "user.email", "fixture@example.test")
    _git(source, "add", ".")
    _git(source, "commit", "-m", "frontend source A")
    revision = _git(source, "rev-parse", "HEAD")

    products = {name: tmp_path / f"{name}-product" for name in ("tui", "tsp", "web")}
    for name in ("tui", "tsp"):
        (products[name] / "dist").mkdir(parents=True)
        (products[name] / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
        (products[name] / "dist/entry.js").write_text(f"console.log('{name} product A')\n", encoding="utf-8")
    products["web"].mkdir()
    (products["web"] / "index.html").write_text("web product A\n", encoding="utf-8")
    recorder = (
        "import { join } from 'node:path';\n"
        "import { buildInputs, recordProduct } from './scripts/build/freshness.mjs';\n"
        "const [source, products] = process.argv.slice(1);\n"
        "for (const [name, root] of Object.entries(JSON.parse(products))) {\n"
        " const out = name === 'web' ? root : join(root, 'dist');\n"
        " recordProduct({source, product:name, out, inputs:buildInputs(source,name)});\n"
        "}\n"
    )
    subprocess.run(
        [node, "--input-type=module", "-e", recorder, str(source),
         json.dumps({name: str(path) for name, path in products.items()})],
        cwd=source, check=True, capture_output=True, text=True,
    )
    return source, revision, products


def _native_cli_args(source: Path, products: dict[str, Path], out: Path, ref: str):
    return [
        "native", "--out", str(out), "--source", str(source), "--ref", ref,
        "--tui", str(products["tui"]), "--tsp", str(products["tsp"]),
        "--web", str(products["web"]),
    ]


@pytest.mark.parametrize("damage", ["unreceipted", "metadata", "source-ref"])
def test_native_public_cli_rejects_unreceipted_or_stale_complete_products(
    tmp_path, monkeypatch, damage,
):
    source, _revision, products = _frontend_fixture(tmp_path)
    if damage == "unreceipted":
        (products["web"] / "hermes-build.json").unlink()
    elif damage == "metadata":
        (products["tui"] / "package.json").write_text('{"type":"commonjs"}\n', encoding="utf-8")
    else:
        (source / "web/src/main.ts").write_text("export const build = 'B'\n", encoding="utf-8")
        _git(source, "add", "web/src/main.ts")
        _git(source, "commit", "-m", "frontend source B")

    monkeypatch.setattr(native.sys, "argv", _native_cli_args(source, products, tmp_path / "out", "HEAD"))
    monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(
        native, "prepare_native",
        lambda **kwargs: pytest.fail("stale frontend products reached native preparation"),
    )
    with pytest.raises(ValueError):
        native.main()


def test_native_public_cli_pins_ref_and_uses_product_snapshot_during_preparation(
    tmp_path, monkeypatch,
):
    source, revision, products = _frontend_fixture(tmp_path)
    _git(source, "branch", "-m", "moving")
    out = tmp_path / "out"
    monkeypatch.setattr(native.sys, "argv", _native_cli_args(source, products, out, "moving"))
    monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "cache"))

    def prepare(*, ref, source, **kwargs):
        assert ref == revision
        (products["web"] / "index.html").write_text("caller mutation\n", encoding="utf-8")
        (source / "web/src/main.ts").write_text("export const build = 'B'\n", encoding="utf-8")
        _git(source, "add", "web/src/main.ts")
        _git(source, "commit", "-m", "frontend source B")
        return tmp_path / "fixture.prepared.json"

    observed = {}

    def assemble(prepared, frontends, *, frontends_are_frozen=False):
        observed["frontends_are_frozen"] = frontends_are_frozen
        observed["web"] = (frontends["web"] / "index.html").read_text(encoding="utf-8")
        observed["tui"] = (frontends["tui"] / "dist/entry.js").read_text(encoding="utf-8")
        return 0

    monkeypatch.setattr(native, "prepare_native", prepare)
    monkeypatch.setattr(native, "_finish_native", assemble)
    assert native.main() == 0
    assert observed == {
        "frontends_are_frozen": True,
        "web": "web product A\n",
        "tui": "console.log('tui product A')\n",
    }
    assert _git(source, "rev-parse", "moving") != revision
