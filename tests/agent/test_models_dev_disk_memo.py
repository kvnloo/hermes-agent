"""models.dev disk memo: shared reads, guarded consumers, rewrite and quarantine."""

from __future__ import annotations

import json
import os

import pytest

import json_disk_memo as memo


@pytest.fixture
def cache_env(monkeypatch, tmp_path):
    import agent.models_dev as md

    cache = tmp_path / "models_dev_cache.json"
    etag = tmp_path / "models_dev_cache.etag"
    previous = (md._models_dev_cache, md._models_dev_cache_time, md._models_dev_retry_after)
    monkeypatch.setattr(md, "_get_cache_path", lambda: cache)
    monkeypatch.setattr(md, "_get_etag_path", lambda: etag)
    md._models_dev_cache = {}
    md._models_dev_cache_time = 0
    md._models_dev_retry_after = 0
    memo.clear_json_disk_memo()
    yield md, cache, etag
    md._models_dev_cache, md._models_dev_cache_time, md._models_dev_retry_after = previous
    memo.clear_json_disk_memo()


def test_valid_registry_is_shared_and_guard_rejects_mutation(cache_env):
    md, cache, _etag = cache_env
    original = {"xai": {"models": {"grok-test": {"limit": {"context": 1000}}}}}
    cache.write_text(json.dumps(original), encoding="utf-8")
    first = md._load_disk_cache()
    assert md._load_disk_cache() is first
    assert memo.json_disk_memo_parse_count() == 1

    with memo.guard_json_disk_memo_mutations():
        guarded = md._load_disk_cache()
        assert guarded == original
        with pytest.raises(TypeError, match="read-only"):
            guarded["xai"]["models"]["grok-test"]["limit"]["context"] = 0
        assert md._load_disk_cache() is guarded
    assert md._load_disk_cache() == original


def test_disk_version_invalidation_on_rewrite(cache_env):
    md, cache, _etag = cache_env
    cache.write_text(json.dumps({"xai": {"models": {"old": {}}}}), encoding="utf-8")
    assert "old" in md._load_disk_cache()["xai"]["models"]
    before = cache.stat()

    cache.write_text(json.dumps({"xai": {"models": {"new": {}, "unicode_模型": {}}}}), encoding="utf-8")
    os.utime(cache, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
    assert "new" in md._load_disk_cache()["xai"]["models"]
    assert "old" not in md._load_disk_cache()["xai"]["models"]
    assert memo.json_disk_memo_parse_count() == 2


def test_fetch_registry_provider_and_xai_curated_are_readonly(cache_env):
    md, cache, _etag = cache_env
    registry = {"xai": {"models": {"grok-test": {"limit": {"context": 64000}}}}}
    cache.write_text(json.dumps(registry), encoding="utf-8")

    with memo.guard_json_disk_memo_mutations():
        assert md.fetch_models_dev(allow_network=False) == registry
        provider = md._registry_provider("xai", False)
        assert provider == registry["xai"]
        assert md._registry_models("xai", allow_network=False) is provider["models"]

        from hermes_cli.models_catalog_static import _xai_curated_models
        assert "grok-test" in _xai_curated_models()

        raw = md._registry_models("xai", allow_network=False)["grok-test"]
        patched = md._merge_catalog_entry_with_override(raw, {"context_window": 1024})
        assert patched["limit"]["context"] == 1024
        assert raw["limit"]["context"] == 64000
        assert md._load_disk_cache() == registry
        assert memo.json_disk_memo_parse_count() == 1


@pytest.mark.parametrize("bad_json", ["{", "{}", "[]"])
def test_corrupt_or_empty_cache_still_quarantined_and_etag_cleared(cache_env, bad_json):
    md, cache, etag = cache_env
    cache.write_text(bad_json, encoding="utf-8")
    etag.write_text('"old-etag"', encoding="utf-8")

    assert md._load_disk_cache() == {}
    assert not cache.exists()
    assert cache.with_suffix(".json.corrupt").read_text(encoding="utf-8") == bad_json
    assert not etag.exists()

    replacement = {"xai": {"models": {"repaired": {}}}}
    cache.write_text(json.dumps(replacement), encoding="utf-8")
    assert md._load_disk_cache() == replacement


def test_production_model_consumers_cannot_poison_cached_registry(cache_env):
    md, cache, _etag = cache_env
    registry = {"xai": {"models": {"grok-test": {"limit": {"context": 64000},
                                               "modalities": {"input": ["text"]}}}}}
    cache.write_text(json.dumps(registry), encoding="utf-8")
    fetched = md.fetch_models_dev(allow_network=False)
    models = md._registry_models("xai", allow_network=False)
    assert models is fetched["xai"]["models"]
    with pytest.raises(TypeError, match="read-only"):
        fetched["xai"]["models"]["grok-test"]["limit"]["context"] = 1
    with pytest.raises(TypeError, match="read-only"):
        models["grok-test"]["modalities"]["input"].append("image")
    patched = md._merge_catalog_entry_with_override(
        models["grok-test"], {"context_window": 1024, "supports_vision": True}
    )
    assert patched["limit"]["context"] == 1024
    assert "image" in patched["modalities"]["input"]
    assert models["grok-test"]["limit"]["context"] == 64000
    assert models["grok-test"]["modalities"]["input"] == ["text"]
    assert md._load_disk_cache() == registry
