"""Transport-free dispatch acceptance for the create-time guard in PR #135952.

The existing cron resolver deliberately passes native targets through when a
platform has no parser. A create/update check must retain that behavior while
rejecting syntax that a plugin's declared parser or validator refuses (#135942).
"""

import json

import pytest

from cron import jobs
from cron.scheduler_delivery import _resolve_single_delivery_target
from tools.cronjob_tools import registry


@pytest.fixture
def delivery_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    plugin = home / "plugins" / "target-contract"
    plugin.mkdir(parents=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [irc-platform, target-contract]\n", encoding="utf-8"
    )
    (plugin / "plugin.yaml").write_text(
        "name: target-contract\nversion: 0.1.0\n", encoding="utf-8"
    )
    (plugin / "__init__.py").write_text(
        "def parse_target(ref):\n"
        "    if ref.startswith('stream:') and '/' in ref:\n"
        "        channel, topic = ref[7:].split('/', 1)\n"
        "        if channel.isdigit() and topic:\n"
        "            return channel, topic\n"
        "    return None\n"
        "\n"
        "def no_transport(*args, **kwargs):\n"
        "    raise AssertionError('validation must not construct a transport')\n"
        "\n"
        "def register(ctx):\n"
        "    ctx.register_platform('strict-target', 'Strict target', no_transport,\n"
        "        lambda: False, parse_target_ref_fn=parse_target,\n"
        "        validate_target_ref_fn=lambda channel: channel != '13')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_DISABLE_LAZY_INSTALLS", "1")
    monkeypatch.setattr(
        "asyncio.open_connection", lambda *a, **kw: pytest.fail("no network")
    )
    with jobs.use_cron_store(home):
        yield home


def _dispatch(action, **args):
    return json.loads(registry.dispatch("cronjob_manage", {"action": action, **args}))


@pytest.mark.parametrize("action", ["create", "update"])
@pytest.mark.parametrize("lane", ["deliver", "failure_deliver"])
def test_deferred_irc_target_remains_schedulable(delivery_home, action, lane):
    target = "irc:#future-room"
    # The real cold plugin-discovery and fire-time paths accept this native channel
    # without a cached directory, connection, credentials or adapter construction.
    fire_target = _resolve_single_delivery_target({}, target)
    assert fire_target["chat_id"] == "#future-room"
    seed = _dispatch(
        "create",
        prompt="Check status",
        schedule="every hour",
        paused=True,
        deliver="local",
    )
    assert seed["success"] is True
    args = {lane: target, "name": "Native channel"}
    if action == "create":
        args.update(prompt="Check status", schedule="every hour", paused=True)
    else:
        args["job_id"] = seed["job_id"]
    result = _dispatch(action, **args)
    assert result["success"] is True, result
    stored = jobs.get_job(result["job_id"] if action == "create" else seed["job_id"])
    assert stored[lane] == target


@pytest.mark.parametrize("action", ["create", "update"])
@pytest.mark.parametrize("lane", ["deliver", "failure_deliver"])
@pytest.mark.parametrize("target_ref", ["stream:5:daily", "stream:13/daily"])
def test_strict_plugin_failure_is_atomic(delivery_home, action, lane, target_ref):
    seed = _dispatch(
        "create",
        prompt="Check status",
        schedule="every hour",
        paused=True,
        deliver="strict-target:stream:5/daily",
    )
    assert seed["success"] is True
    store = delivery_home / "cron" / "jobs.json"
    before = store.read_bytes()
    # The good first destination must not stage a partial create/update when the
    # second element violates the plugin parser or its post-resolution validator.
    bad_target = f"strict-target:{target_ref}"
    args = {
        lane: f"strict-target:stream:5/daily,{bad_target}",
        "name": "Must not persist",
    }
    if action == "create":
        args.update(prompt="Check status", schedule="every hour", paused=True)
    else:
        args["job_id"] = seed["job_id"]
    result = _dispatch(action, **args)
    assert result["success"] is False, result
    assert bad_target in result["error"]
    assert store.read_bytes() == before
