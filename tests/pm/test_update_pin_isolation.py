"""#125386: one failing pin must not zero out the whole `pm update` run.

`_apply_pins` let any `_pin_artifacts` exception propagate (a package's
resolution bug or one target's rolling-pool 404), so `lockfile.save()`
never ran and every unrelated package stayed un-updated. Pins are now
isolated per package: successes are pinned and saved, failures are
reported and summarized, exit stays non-zero.
"""

import pytest

from pm import cli, paths, registry
from pm.lock import Lockfile
from pm.package import Package
from pm.store import current_target
from pm.update import Resolved


class PinFixture(Package):
    def __init__(self, name, versions):
        self.name = name
        self.versions = versions
        self.version_style = "semver"

    def missing_reason(self, target):
        return None if target == current_target() else "not a fixture target"

    def latest_versions(self, target, locked=None):
        return self.versions

    def fetch_urls(self, version, target):
        return [f"https://fixture.example/{self.name}-{version}-{target}.tgz"]

    def known_sha256(self, version, url):
        return "0" * 64


def _decision(package, version):
    return Resolved(package.name, "1.0", package.version_style,
                    version=version, per_target={current_target(): version})


def prepare(tmp_path, monkeypatch):
    lock = Lockfile(tmp_path / "lock.json")
    broken = PinFixture("broken-pin", ["2.0"])
    healthy = PinFixture("healthy-pin", ["3.0"])
    for package in (broken, healthy):
        lock.set_pin(package.name, "1.0", {})
        monkeypatch.setitem(registry._packages, package.name, package)
    lock.save()
    monkeypatch.setattr(paths, "lockfile_path", lambda: lock.path)
    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HERMES_RUNTIME_DIR", str(tmp_path / "tools"))

    real_pin_artifacts = cli._pin_artifacts

    def pin_artifacts_or_raise(package, decision, current):
        if package.name == "broken-pin":
            raise ValueError("fixture pool skew: 404")
        return real_pin_artifacts(package, decision, current)

    monkeypatch.setattr(cli, "_pin_artifacts", pin_artifacts_or_raise)
    monkeypatch.setattr(cli, "_install_names", lambda names: None)
    monkeypatch.setattr(cli, "_sync_venv_step", lambda: True)
    return lock, broken, healthy


def test_one_failing_pin_does_not_block_the_rest(tmp_path, monkeypatch, capsys):
    lock, broken, healthy = prepare(tmp_path, monkeypatch)
    changed = [_decision(broken, "2.0"), _decision(healthy, "3.0")]
    assert cli._apply_pins(changed, lock) == 1
    out = capsys.readouterr().out
    assert "✗ broken-pin pin failed: fixture pool skew: 404" in out
    assert "✓ healthy-pin pinned 1.0 → 3.0" in out
    assert "pinned 1, failed 1: broken-pin" in out
    # The healthy pin survived to disk; the broken row kept its old version.
    assert lock.version("healthy-pin") == "3.0"
    assert lock.version("broken-pin") == "1.0"


def test_all_pins_failing_leaves_lockfile_untouched(tmp_path, monkeypatch, capsys):
    lock, broken, healthy = prepare(tmp_path, monkeypatch)
    before = lock.path.read_bytes()
    changed = [_decision(broken, "2.0")]
    assert cli._apply_pins(changed, lock) == 1
    out = capsys.readouterr().out
    assert "✗ broken-pin pin failed" in out
    assert "every pin failed; lockfile untouched" in out
    assert lock.path.read_bytes() == before


def test_clean_run_still_succeeds(tmp_path, monkeypatch, capsys):
    lock, broken, healthy = prepare(tmp_path, monkeypatch)
    changed = [_decision(healthy, "3.0")]
    assert cli._apply_pins(changed, lock) == 0
    out = capsys.readouterr().out
    assert "✓ healthy-pin pinned 1.0 → 3.0" in out
    assert "failed" not in out
    assert lock.version("healthy-pin") == "3.0"


@pytest.mark.parametrize("names,code,published", [
    (["broken-pin", "healthy-pin"], 1, True),
    (["healthy-pin", "broken-pin"], 1, True),
    (["broken-pin"], 1, False),
    (["healthy-pin"], 0, True),
], ids=["broken-first", "healthy-first", "all-failed", "clean"])
def test_update_publishes_before_installing_only_successful_pins(
        tmp_path, monkeypatch, capsys, record_property, names, code, published):
    """The command's installer consumes the saved pin, not the writer's in-memory view."""
    import argparse
    import json

    lock, _, _ = prepare(tmp_path, monkeypatch)
    before = lock.path.read_bytes()
    pin = cli._pin_artifacts
    attempts, installs, syncs = [], [], []

    def observed_pin(package, decision, current):
        attempts.append(package.name)
        return pin(package, decision, current)

    def observed_install(selected):
        fresh = Lockfile(lock.path)
        installs.append({"names": list(selected), "healthy": fresh.version("healthy-pin"),
                         "broken": fresh.version("broken-pin"),
                         "artifacts": fresh.artifacts("healthy-pin", current_target())})
        return None

    monkeypatch.setattr(cli, "_pin_artifacts", observed_pin)
    monkeypatch.setattr(cli, "_install_names", observed_install)
    monkeypatch.setattr(cli, "_sync_venv_step", lambda: syncs.append("sync") or True)
    args = argparse.Namespace(names=names, target=None, check=False, uv=False, npm=False, termux=False)
    result = cli.cmd_update(args)
    output = capsys.readouterr().out
    fresh = Lockfile(lock.path)
    observed = {"result": result, "attempts": attempts, "installs": installs, "syncs": syncs,
                "fresh_versions": {n: fresh.version(n) for n in ("healthy-pin", "broken-pin")},
                "lock_bytes_changed": lock.path.read_bytes() != before}
    record_property("pin_publication_observation", json.dumps(observed, sort_keys=True))

    assert result == code
    assert attempts == names  # No pin is retried or silently skipped.
    assert fresh.version("broken-pin") == "1.0"
    if published:
        assert installs == [{"names": ["healthy-pin"], "healthy": "3.0", "broken": "1.0",
                             "artifacts": [{"url": f"https://fixture.example/healthy-pin-3.0-{current_target()}.tgz",
                                            "sha256": "0" * 64}]}]
        assert fresh.version("healthy-pin") == "3.0"
        assert syncs == ["sync"]
    else:
        assert installs == syncs == []
        assert lock.path.read_bytes() == before
        assert "every pin failed; lockfile untouched" in output
    if "broken-pin" in names:
        assert "broken-pin pin failed: fixture pool skew: 404" in output
        if published:
            assert "pinned 1, failed 1: broken-pin" in output
    else:
        assert "failed" not in output
