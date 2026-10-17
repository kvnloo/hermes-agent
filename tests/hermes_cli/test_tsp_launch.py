from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hermes_cli import main_tui_launch
from scripts.build.agent import plant_surfaces


def _product(root: Path) -> Path:
    product = root / "tsp product"
    dist = product / "dist"
    dist.mkdir(parents=True)
    (product / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
    (dist / "entry.js").write_text(
        'import { message } from "./runtime.mjs"; console.log(message);\n', encoding="utf-8")
    (dist / "runtime.mjs").write_text('export const message = "staged TSP product";\n', encoding="utf-8")
    (dist / "hermes-build.json").write_text(json.dumps({"product": "tsp"}), encoding="utf-8")
    return product


@pytest.mark.platforms("posix")
def test_sealed_payload_launches_complete_staged_tsp_product(tmp_path, monkeypatch):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required to execute the staged TSP product")
    product = _product(tmp_path)
    sealed_root = tmp_path / "sealed" / "hermes-agent"
    cli = sealed_root / "hermes_cli"
    cli.mkdir(parents=True)
    (cli / "main_tui_launch.py").write_text("", encoding="utf-8")
    plant_surfaces(sealed_root, {"tsp": product})

    monkeypatch.setattr(main_tui_launch, "__file__", str(cli / "main_tui_launch.py"))
    monkeypatch.setattr(main_tui_launch, "_tui_node_bin", lambda _name: node)
    monkeypatch.delenv("HERMES_TSP_DIR", raising=False)
    argv, cwd = main_tui_launch._make_tsp_argv(sealed_root)

    staged = cli / "tsp_dist"
    assert cwd == staged
    assert Path(argv[-1]) == staged / "entry.js"
    assert json.loads((staged / "package.json").read_text()) == {"type": "module"}
    assert (staged / "runtime.mjs").is_file()
    assert (staged / "hermes-build.json").is_file()
    assert not (sealed_root / "ui-tsp").exists()
    run = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=True, timeout=10)
    assert run.stdout.strip() == "staged TSP product"


def test_incomplete_sealed_source_snapshot_fails_without_source_compilation(tmp_path, monkeypatch):
    source_root = tmp_path / "sealed"
    (source_root / "ui-tsp").mkdir(parents=True)
    (source_root / "ui-tsp/package.json").write_text('{"type":"module"}\n', encoding="utf-8")
    monkeypatch.setattr(main_tui_launch, "__file__", str(source_root / "hermes_cli/main_tui_launch.py"))
    monkeypatch.delenv("HERMES_TSP_DIR", raising=False)
    monkeypatch.setattr(main_tui_launch, "_tui_node_bin", lambda _name: pytest.fail("no TSP product"))

    with pytest.raises(FileNotFoundError, match="no complete TSP product or source build graph"):
        main_tui_launch._make_tsp_argv(source_root)


def test_incomplete_explicit_tsp_override_fails_without_fallback(tmp_path, monkeypatch):
    product = tmp_path / "caller product"
    product.mkdir()
    monkeypatch.setenv("HERMES_TSP_DIR", str(product))
    monkeypatch.setattr(
        main_tui_launch, "_tui_node_bin", lambda _name: pytest.fail("invalid override fell back"))

    with pytest.raises(FileNotFoundError, match="configured TSP product is incomplete"):
        main_tui_launch._make_tsp_argv(tmp_path / "source")


def test_referenced_tsp_product_uses_its_complete_product_root(tmp_path, monkeypatch):
    product = _product(tmp_path)
    monkeypatch.setattr(main_tui_launch, "__file__", str(tmp_path / "hermes_cli/main_tui_launch.py"))
    monkeypatch.setenv("HERMES_TSP_DIR", str(product))
    monkeypatch.setattr(main_tui_launch, "_tui_node_bin", lambda _name: "node-test")

    argv, cwd = main_tui_launch._make_tsp_argv(tmp_path / "source")
    assert argv == ["node-test", str(product / "dist/entry.js")]
    assert cwd == product
