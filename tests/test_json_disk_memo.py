"""Differential contract for the pre-memo JSON reader and versioned memo."""

from __future__ import annotations

import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import json_disk_memo as memo


@pytest.fixture(autouse=True)
def _fresh_memo():
    memo.clear_json_disk_memo()
    yield
    memo.clear_json_disk_memo()


def _old_disk_reader(path: Path):
    """Original per-call JSON parser (before the in-process memo)."""
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def _generated_payloads():
    windows_path = r"C:\Users\模型\folder_%\file_name.json"
    # JSON allows duplicate object keys; both readers must retain the last value.
    yield "{}"
    yield "[]"
    yield (
        '{"duplicate":1,"duplicate":2,"path":'
        + json.dumps(windows_path, ensure_ascii=True)
        + ',"like":'
        + json.dumps("%_\\", ensure_ascii=True)
        + "}"
    )
    special = ("", "%", "_", r"part\child", "λ", "東京", windows_path, "a%b_c")
    rng = random.Random(1107)
    for count in (1, 17, 257):
        rows = [
            {
                "id": i % 7,  # duplicate values
                "name": special[i % len(special)],
                "path": windows_path + f"\\item_{i}%",
                "nested": {"children": [special[rng.randrange(len(special))], i]},
            }
            for i in range(count)
        ]
        yield json.dumps({"rows": rows, "unicode": "模型 🌐", "empty": []}, ensure_ascii=True)


@pytest.mark.parametrize("payload", list(_generated_payloads()))
def test_same_generated_json_as_old_parser(tmp_path, payload):
    path = tmp_path / "catalog.json"
    path.write_text(payload, encoding="utf-8")
    expected = _old_disk_reader(path)

    first = memo.read_json_disk_memo(path)
    second = memo.read_json_disk_memo(path)

    assert first == expected
    assert second == expected
    assert memo.json_disk_memo_parse_count() == 1


def test_utf8_bom_is_identical_to_old_reader(tmp_path):
    path = tmp_path / "bom.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"paths": [r"C:\folder\_x%", "κ"]}).encode("utf-8"))
    assert memo.read_json_disk_memo(path) == _old_disk_reader(path)


def test_nested_caller_mutation_cannot_poison_next_read(tmp_path):
    path = tmp_path / "catalog.json"
    original = {"xai": {"models": [{"id": "a"}, {"id": "a"}]}, "removed": ["_%", "\\"]}
    path.write_text(json.dumps(original), encoding="utf-8")

    first = memo.read_json_disk_memo(path)
    first["xai"]["models"][0]["id"] = "changed"
    first["xai"]["models"].append({"id": "extra"})
    first["removed"].clear()

    assert memo.read_json_disk_memo(path) == original
    assert memo.json_disk_memo_parse_count() == 1


def test_rewrite_invalidates_file_version(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text('{"version":1,"rows":[1]}', encoding="utf-8")
    assert memo.read_json_disk_memo(path)["version"] == 1
    before = path.stat()

    path.write_text('{"version":2,"rows":[1,2]}', encoding="utf-8")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
    assert memo.read_json_disk_memo(path)["version"] == 2
    assert memo.json_disk_memo_parse_count() == 2


def test_failed_parse_is_not_negative_cached(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text('{"broken":', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        memo.read_json_disk_memo(path)
    path.write_text('{"repaired":true}', encoding="utf-8")
    assert memo.read_json_disk_memo(path) == {"repaired": True}


def test_concurrent_readers_parse_single_version_once(tmp_path):
    path = tmp_path / "catalog.json"
    original = {"rows": [{"id": i} for i in range(100)]}
    path.write_text(json.dumps(original), encoding="utf-8")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: memo.read_json_disk_memo(path), range(12)))
    assert all(result == original for result in results)
    assert memo.json_disk_memo_parse_count() == 1


def test_seeded_home_catalog_readers_in_fresh_process(tmp_path):
    """Real catalog entry points share disk parses without loader mocks or network."""
    import subprocess
    import sys
    import textwrap

    home = tmp_path / "hermes"
    home.mkdir()
    (home / "models_dev_cache.json").write_text(
        json.dumps({"xai": {"models": {"grok-memo-fixture": {}}}}), encoding="utf-8"
    )
    (home / "cache").mkdir()
    (home / "cache" / "plugin-catalog.json").write_text(
        json.dumps({
            "entries": [{
                "name": "memo-fixture", "repo": "https://example.invalid/memo-fixture",
                "sha": "a" * 40,
            }],
            "removed": [{"name": "revoked-fixture", "reason": "test"}],
        }), encoding="utf-8"
    )
    probe = textwrap.dedent("""
        from agent.models_dev import fetch_models_dev
        from hermes_cli.models_catalog_static import _xai_curated_models
        from hermes_cli.plugin_catalog import (
            fetch_live_catalog, get_live_catalog_entry, live_removed_list,
        )
        from json_disk_memo import clear_json_disk_memo, json_disk_memo_parse_count

        clear_json_disk_memo()
        assert "grok-memo-fixture" in fetch_models_dev(allow_network=False)["xai"]["models"]
        assert "grok-memo-fixture" in _xai_curated_models()
        assert get_live_catalog_entry("memo-fixture").sha == "a" * 40
        assert live_removed_list()[0].name == "revoked-fixture"
        first = fetch_live_catalog()
        first["entries"][0]["name"] = "mutated"
        first["removed"].clear()
        assert get_live_catalog_entry("memo-fixture").sha == "a" * 40
        assert live_removed_list()[0].name == "revoked-fixture"
        assert json_disk_memo_parse_count() == 2
        print("models.dev discovery and plugin lookup/removals: two disk parses")
    """)
    env = {k: v for k, v in os.environ.items() if not k.startswith("HERMES_")}
    env.update(HOME=str(tmp_path), HERMES_HOME=str(home))
    result = subprocess.run(
        [sys.executable, "-c", probe], cwd=Path(__file__).resolve().parents[1],
        env=env, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "two disk parses" in result.stdout
