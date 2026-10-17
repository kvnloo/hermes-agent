"""Consumer-visible settings RPC contracts against isolated on-disk profiles.

No real provider approvals, network calls or account mutations. These tests enter the
public request dispatcher and inspect saved YAML plus subsequent RPC readback.
"""

from __future__ import annotations

import builtins
import copy
import json
from pathlib import Path

import pytest
import hermes_yaml as yaml

import tui_gateway.server as server
from hermes_cli import web_server_config


def rpc(method, **params):
    return server.handle_request({"id": "settings-test", "method": method, "params": params})


def result(response):
    assert "result" in response, response
    return response["result"]


def saved(home):
    return yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8")) or {}


def seed(home, value):
    (home / "config.yaml").write_text(yaml.safe_dump(value), encoding="utf-8")


def _prepare_settings_rpc_child(home):
    import os

    os.environ["HERMES_HOME"] = str(home)
    os.environ.pop("HERMES_TUI_TOOL_PROGRESS", None)
    server._hermes_home = Path(home)
    server._cfg_cache = None
    server._cfg_sig = None
    server._cfg_path = None
    server._served_profile_homes = set()
    server._sessions = {
        "launch": {"agent": None, "profile_home": str(home), "session_key": "launch-record"},
    }
    web_server_config._schema_with_dynamic_provider_options = lambda: web_server_config.CONFIG_SCHEMA
    return server


def _legacy_public_rpc_worker(home, started, raw_read, resume_read, outcomes):
    child_server = _prepare_settings_rpc_child(home)
    original_load = child_server._load_cfg_raw

    def pause_after_disk_read():
        raw = original_load()
        raw_read.set()
        if not resume_read.wait(15):
            raise TimeoutError("legacy RPC read was not released")
        return raw

    child_server._load_cfg_raw = pause_after_disk_read
    try:
        started.set()
        response = child_server.handle_request({
            "id": "legacy-cross-process",
            "method": "config.set",
            "params": {"session_id": "launch", "key": "display.in_app_tips", "value": False},
        })
        outcomes.put(("legacy", response))
    except Exception as exc:
        outcomes.put(("legacy-error", repr(exc)))


def _native_public_rpc_worker(home, started, lock_requested, done, outcomes):
    from contextlib import contextmanager

    child_server = _prepare_settings_rpc_child(home)
    from hermes_cli import config as config_module
    original_lock = config_module.config_mutation_lock

    @contextmanager
    def observe_lock_attempt(path=None):
        lock_requested.set()
        with original_lock(path):
            yield

    config_module.config_mutation_lock = observe_lock_attempt
    try:
        started.set()
        response = child_server.handle_request({
            "id": "native-cross-process",
            "method": "settings.set",
            "params": {"session_id": "launch", "key": "display.show_reasoning", "value": False},
        })
        outcomes.put(("native", response))
    except Exception as exc:
        outcomes.put(("native-error", repr(exc)))
    finally:
        done.set()


@pytest.fixture
def homes(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    launch = tmp_path / ".hermes"
    worker = launch / "profiles" / "worker"
    for home, model in ((launch, "launch-model"), (worker, "worker-model")):
        home.mkdir(parents=True)
        seed(home, {"model": {"default": model}, "display": {"show_reasoning": True}})
        (home / ".env").write_text("TEST_ROUTE_KEY=inert-local-key\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(launch))
    for name in ("HERMES_MODEL", "HERMES_INFERENCE_MODEL", "HERMES_MANAGED"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(server, "_hermes_home", launch)
    monkeypatch.setattr(server, "_cfg_cache", None)
    monkeypatch.setattr(server, "_cfg_sig", None)
    monkeypatch.setattr(server, "_cfg_path", None)
    monkeypatch.setattr(server, "_served_profile_homes", set())
    sessions = {
        "launch": {"agent": None, "profile_home": str(launch), "session_key": "launch-record",
                   "create_reasoning_override": {"enabled": True, "effort": "high"}},
        "worker": {"agent": None, "profile_home": str(worker), "session_key": "worker-record",
                   "create_reasoning_override": {"enabled": True, "effort": "low"}},
    }
    monkeypatch.setattr(server, "_sessions", sessions)
    return launch, worker


def test_sparse_save_and_reversion_preserve_unrelated_raw_values(homes):
    launch, _ = homes
    seed(launch, {"model": {"default": "fixture-model", "provider": "custom", "api_key": "${TEST_ROUTE_KEY}"},
                  "terminal": {"cwd": "${TEST_ROUTE_KEY}"},
                  "unrelated": {"user_owned": [1, 2]}, "display": {"show_reasoning": True}})
    env_before = (launch / ".env").read_bytes()
    for value in (False, True):
        response = result(rpc("settings.set", session_id="launch", key="display.show_reasoning", value=value))
        assert response["value"] is value
        assert response["confirm_required"] is False
        current = saved(launch)
        assert current["model"]["api_key"] == "${TEST_ROUTE_KEY}"
        assert current["terminal"]["cwd"] == "${TEST_ROUTE_KEY}"
        assert current["unrelated"] == {"user_owned": [1, 2]}
        assert "compression" not in current
        assert result(rpc("settings.get", session_id="launch"))["fields"]["display.show_reasoning"]["value"] is value
    assert (launch / ".env").read_bytes() == env_before


def test_profile_defaults_never_overwrite_live_reasoning_pin(homes):
    _, worker = homes
    original = copy.deepcopy(server._sessions["worker"])
    response = result(rpc("settings.set", session_id="worker", key="agent.reasoning_effort", value="medium"))
    assert response["value"] == "medium"
    assert saved(worker)["agent"]["reasoning_effort"] == "medium"
    assert server._sessions["worker"] == original
    assert result(rpc("config.get", session_id="worker", key="reasoning"))["value"] == "low"


def test_two_profile_reads_writes_and_explicit_scope_are_isolated(homes):
    launch, worker = homes
    launch_before = (launch / "config.yaml").read_bytes()
    response = result(rpc("settings.get", session_id="worker"))
    assert response["profile"] == "worker"
    assert response["fields"]["model"]["value"] == "worker-model"
    assert result(rpc("settings.get", profile="worker"))["fields"]["model"]["value"] == "worker-model"
    assert result(rpc("settings.get", session_id="launch"))["profile"] == "default"
    result(rpc("settings.set", session_id="worker", profile="worker", key="display.show_reasoning", value=False))
    assert saved(worker)["display"]["show_reasoning"] is False
    assert (launch / "config.yaml").read_bytes() == launch_before
    assert rpc("settings.set", session_id="worker", profile="default", key="display.show_reasoning", value=True)["error"]["code"] == 4001
    assert rpc("settings.get", session_id="worker", profile="default")["error"]["code"] == 4001
    assert saved(worker)["display"]["show_reasoning"] is False


@pytest.mark.parametrize("sid", ["closed", ""])
def test_unknown_or_missing_live_session_cannot_write(homes, sid):
    before = [(home / "config.yaml").read_bytes() for home in homes]
    assert rpc("settings.set", session_id=sid, key="display.show_reasoning", value=False)["error"]["code"] == 4001
    assert [(home / "config.yaml").read_bytes() for home in homes] == before


def test_unknown_profile_does_not_fall_back_to_launch(homes):
    launch, _ = homes
    before = (launch / "config.yaml").read_bytes()
    assert rpc("settings.set", session_id="launch", profile="missing", key="display.show_reasoning", value=False)["error"]["code"] == 4064
    assert (launch / "config.yaml").read_bytes() == before


@pytest.mark.parametrize("replacement", [None, {"agent": None, "profile_home": "other"}])
def test_session_retired_or_replaced_during_discovery_cannot_write(homes, monkeypatch, replacement):
    launch, _ = homes
    original_schema = web_server_config._schema_with_dynamic_provider_options

    def discover_after_retirement():
        schema = original_schema()
        if replacement is None:
            server._sessions.pop("launch", None)
        else:
            server._sessions["launch"] = replacement
        return schema

    monkeypatch.setattr(web_server_config, "_schema_with_dynamic_provider_options", discover_after_retirement)
    before = (launch / "config.yaml").read_bytes()
    assert rpc("settings.set", session_id="launch", key="display.show_reasoning", value=False)["error"]["code"] == 4001
    assert (launch / "config.yaml").read_bytes() == before


@pytest.mark.parametrize(("key", "value"), [
    ("display.show_reasoning", "false"), ("display.show_reasoning", None),
    ("agent.gateway_timeout", True), ("agent.gateway_timeout", "5"),
    ("approvals.mode", "invalid"), ("model", {"api_key": "not-a-model"}),
    ("toolsets", {}), ("providers", []), ("unrelated.secret", "new"),
    ("model_context_length", -1), ("model_context_length", 5.5),
    ("model_context_length", True), ("agent.gateway_timeout", float("inf")),
])
def test_invalid_fields_types_options_and_numbers_leave_bytes_unchanged(homes, key, value):
    launch, _ = homes
    before = (launch / "config.yaml").read_bytes()
    assert rpc("settings.set", session_id="launch", key=key, value=value)["error"]["code"] == 4002
    assert (launch / "config.yaml").read_bytes() == before


def test_confirmation_flag_requires_an_actual_boolean(homes):
    response = rpc("settings.set", session_id="launch", key="security.redact_secrets", value=False, confirmed="true")
    assert response["error"]["code"] == 4000


def test_dynamic_options_come_from_the_requested_profile(homes):
    launch, worker = homes
    for home, name in ((launch, "launch-voice"), (worker, "worker-voice")):
        seed(home, {"tts": {"provider": name, "providers": {name: {"command": "inert-fixture --voice"}}}})
    fields = result(rpc("settings.get", session_id="worker"))["fields"]
    assert "worker-voice" in fields["tts.provider"]["options"]
    assert "launch-voice" not in fields["tts.provider"]["options"]
    assert rpc("settings.set", session_id="worker", key="tts.provider", value="launch-voice")["error"]["code"] == 4002
    assert result(rpc("settings.get", session_id="launch"))["fields"]["tts.provider"]["value"] == "launch-voice"


def test_schema_getter_projects_defaults_nullable_objects_and_private_values(homes):
    launch, _ = homes
    seed(launch, {"model": {"default": "private-route", "api_key": "model-private"},
                  "delegation": {"api_key": "delegation-private"},
                  "providers": {"fixture": {"api_key": "provider-private", "base_url": "${TEST_ROUTE_KEY}"}},
                  "dashboard": {"basic_auth": {"password_hash": "hash-private"}},
                  "unrelated": {"hidden": "not-declared"}})
    fields = result(rpc("settings.get", session_id="launch"))["fields"]
    assert fields["model"]["value"] == "private-route"
    assert fields["delegation.api_key"]["sensitive"] is True
    assert fields["delegation.api_key"]["value"] is None
    assert fields["dashboard.basic_auth.password_hash"]["value"] is None
    assert fields["providers"]["type"] == "object"
    assert fields["providers"]["value"]["fixture"] == {"api_key": None, "base_url": "${TEST_ROUTE_KEY}"}
    assert fields["agent.run_budget_seconds"]["type"] == "number"
    assert fields["agent.run_budget_seconds"]["nullable"] is True
    assert fields["agent.run_budget_seconds"]["value"] is None
    assert fields["agent.run_budget_seconds"]["default"] is None
    assert "unrelated" not in fields
    wire = json.dumps(fields)
    for secret in ("model-private", "delegation-private", "provider-private", "hash-private", "not-declared", "inert-local-key"):
        assert secret not in wire


def test_nullable_number_and_structured_field_can_revert_without_unrelated_resets(homes):
    launch, _ = homes
    seed(launch, {"agent": {"gateway_timeout": 120}, "compression": {"model_thresholds": {"fixture": 0.4}}})
    for value in (45, None):
        response = result(rpc("settings.set", session_id="launch", key="agent.run_budget_seconds", value=value))
        assert response["value"] == value
        assert saved(launch)["agent"]["gateway_timeout"] == 120
    response = result(rpc("settings.set", session_id="launch", key="compression.model_thresholds", value={}))
    assert response["value"] == {}
    assert "fixture" not in saved(launch).get("compression", {}).get("model_thresholds", {})
    assert saved(launch)["agent"]["gateway_timeout"] == 120


def test_context_override_normalization_and_removal_preserve_route_credentials_and_siblings(homes):
    launch, _ = homes
    model = {"default": "fixture-model", "provider": "custom", "base_url": "http://127.0.0.1:9/v1",
             "api_key": "${TEST_ROUTE_KEY}", "api_mode": "chat_completions", "user_note": "keep"}
    seed(launch, {"model": model, "display": {"show_reasoning": True}, "other": {"keep": 1}})
    env_before = (launch / ".env").read_bytes()
    for value in (8192, 0):
        response = result(rpc("settings.set", session_id="launch", key="model_context_length", value=value))
        assert response["value"] == value
        assert result(rpc("settings.get", session_id="launch"))["fields"]["model_context_length"]["value"] == value
        raw = saved(launch)
        assert {key: raw["model"][key] for key in model} == model
        assert raw["other"] == {"keep": 1}
        assert raw["display"]["show_reasoning"] is True
        assert "model_context_length" not in raw
        if value:
            assert raw["model"]["context_length"] == value
        else:
            assert "context_length" not in raw["model"]
    assert (launch / ".env").read_bytes() == env_before


def test_bare_model_context_upgrade_does_not_invent_credentials(homes):
    launch, _ = homes
    seed(launch, {"model": "bare-fixture", "unrelated": "keep"})
    result(rpc("settings.set", session_id="launch", key="model_context_length", value=4096))
    assert saved(launch)["model"] == {"default": "bare-fixture", "context_length": 4096}
    result(rpc("settings.set", session_id="launch", key="model_context_length", value=0))
    assert saved(launch)["model"] == {"default": "bare-fixture"}
    assert saved(launch)["unrelated"] == "keep"


def test_model_route_change_keeps_canonical_deletions_and_unrelated_raw_settings(homes, monkeypatch):
    from hermes_cli.model_switch import ModelSwitchResult

    launch, _ = homes
    seed(launch, {
        "model": {
            "default": "old-fixture", "provider": "custom", "base_url": "http://127.0.0.1:9/v1",
            "api_key": "inert-fixture-key", "key_env": "INERT_FIXTURE_KEY", "context_length": 4096,
            "api_mode": "chat_completions",
        },
        "context_length": 8192,
        "model_context_length": 16384,
        "display": {"show_reasoning": True},
        "unrelated": {"preserve": ["raw", 1]},
    })
    selection = ModelSwitchResult(
        success=True, new_model="new-fixture", target_provider="openai",
        base_url="https://api.openai.com/v1", api_mode="chat_completions",
    )
    monkeypatch.setattr(web_server_config, "_infer_provider_on_model_change", lambda *_: ("openai", "new-fixture"))
    monkeypatch.setattr(web_server_config, "_normalize_main_model_assignment", lambda *_: ("openai", "new-fixture"))
    monkeypatch.setattr(web_server_config, "_validated_main_model_selection", lambda *_: selection)

    response = result(rpc("settings.set", session_id="launch", key="model", value="new-fixture", confirmed=True))
    assert response["value"] == "new-fixture"
    raw = saved(launch)
    assert raw["model"]["provider"] == "openai"
    assert raw["model"]["default"] == "new-fixture"
    assert not {"api_key", "key_env", "context_length"} & raw["model"].keys()
    assert "context_length" not in raw
    assert "model_context_length" not in raw
    assert raw["display"]["show_reasoning"] is True
    assert raw["unrelated"] == {"preserve": ["raw", 1]}
    from hermes_cli.auth import _model_level_key_env
    assert _model_level_key_env("openai") == ""


def test_slow_model_validation_does_not_hold_the_shared_config_writer_lock(homes, monkeypatch):
    import contextvars
    import threading
    from hermes_cli.model_switch import ModelSwitchResult

    launch, _ = homes
    seed(launch, {"model": {"default": "old-fixture", "provider": "custom",
                            "base_url": "http://127.0.0.1:9/v1"}})
    selection = ModelSwitchResult(
        success=True, new_model="new-fixture", target_provider="openai",
        base_url="https://api.openai.com/v1", api_mode="chat_completions",
    )
    validating = threading.Event()
    release_validation = threading.Event()
    legacy_done = threading.Event()
    model_done = threading.Event()
    results = {}
    failures = []
    monkeypatch.setattr(web_server_config, "_schema_with_dynamic_provider_options",
                        lambda: web_server_config.CONFIG_SCHEMA)
    monkeypatch.setattr(web_server_config, "_infer_provider_on_model_change",
                        lambda *_: ("openai", "new-fixture"))
    monkeypatch.setattr(web_server_config, "_normalize_main_model_assignment",
                        lambda *_: ("openai", "new-fixture"))

    def validate_without_provider_io(*_args):
        validating.set()
        if not release_validation.wait(5):
            raise TimeoutError("model validation was not released")
        return selection

    monkeypatch.setattr(web_server_config, "_validated_main_model_selection", validate_without_provider_io)

    def run_model():
        try:
            results["model"] = contextvars.copy_context().run(
                rpc, "settings.set", session_id="launch", key="model", value="new-fixture", confirmed=True)
        except Exception as exc:
            failures.append(exc)
        finally:
            model_done.set()

    def run_legacy():
        try:
            results["legacy"] = contextvars.copy_context().run(
                rpc, "config.set", session_id="launch", key="display.in_app_tips", value=False)
        except Exception as exc:
            failures.append(exc)
        finally:
            legacy_done.set()

    model_writer = threading.Thread(target=run_model, name="model-validation-writer", daemon=True)
    model_writer.start()
    assert validating.wait(2)
    legacy_writer = threading.Thread(target=run_legacy, name="legacy-config-writer", daemon=True)
    legacy_writer.start()
    legacy_completed_during_validation = legacy_done.wait(1.5)
    release_validation.set()
    model_writer.join(timeout=5)
    legacy_writer.join(timeout=5)

    assert not model_writer.is_alive() and not legacy_writer.is_alive()
    assert legacy_completed_during_validation
    assert model_done.is_set() and legacy_done.is_set()
    assert not failures
    assert "result" in results["model"] and "result" in results["legacy"]
    raw = saved(launch)
    assert raw["model"]["default"] == "new-fixture"
    assert raw["display"]["in_app_tips"] is False


def test_settings_accept_runtime_enum_and_union_domains(homes, monkeypatch):
    launch, _ = homes
    monkeypatch.delenv("HERMES_VERIFY_ON_STOP", raising=False)
    fields = result(rpc("settings.get", session_id="launch"))["fields"]
    assert fields["terminal.modal_mode"]["options"] == ["auto", "direct", "managed"]
    assert fields["agent.verify_on_stop"]["accepted_types"] == ["boolean", "string"]
    assert "auto" in fields["agent.verify_on_stop"]["accepted_values"]
    assert fields["agent.tool_use_enforcement"]["accepted_types"] == ["boolean", "string", "list"]

    for value in ("auto", "direct", "managed"):
        result(rpc("settings.set", session_id="launch", key="terminal.modal_mode", value=value, confirmed=True))
        assert saved(launch)["terminal"]["modal_mode"] == value
    for key, value in (
        ("context.engine", "compressor"),
        ("agent.verify_on_stop", "auto"),
        ("agent.tool_use_enforcement", False),
    ):
        response = result(rpc("settings.set", session_id="launch", key=key, value=value, confirmed=True))
        assert response["value"] == value
    raw = saved(launch)
    assert raw["context"]["engine"] == "compressor"
    assert raw["agent"]["verify_on_stop"] == "auto"
    assert raw["agent"]["tool_use_enforcement"] is False

    before = (launch / "config.yaml").read_bytes()
    assert rpc("settings.set", session_id="launch", key="terminal.modal_mode",
               value="sandbox", confirmed=True)["error"]["code"] == 4002
    assert (launch / "config.yaml").read_bytes() == before


def test_dotted_resource_attribute_setting_uses_its_literal_key(homes):
    launch, _ = homes
    key = "monitoring.gateway_health_export.resource_attributes.deployment.environment.name"
    seed(launch, {"monitoring": {"gateway_health_export": {
        "resource_attributes": {"deployment.environment.name": "before"},
    }}})
    fields = result(rpc("settings.get", session_id="launch"))["fields"]
    assert fields[key]["value"] == "before"
    response = result(rpc("settings.set", session_id="launch", key=key, value="after", confirmed=True))
    assert response["value"] == "after"

    raw = saved(launch)["monitoring"]["gateway_health_export"]["resource_attributes"]
    assert raw["deployment.environment.name"] == "after"
    assert "deployment" not in raw
    from agent.monitoring.otlp_exporter import _safe_resource_attributes
    assert _safe_resource_attributes(raw)["deployment.environment.name"] == "after"


def test_automatic_context_length_reset_clears_all_legacy_aliases(homes):
    launch, _ = homes
    seed(launch, {
        "model": {"default": "fixture-model", "context_length": 8192, "api_key": "inert-fixture-key"},
        "context_length": 4096,
        "model_context_length": 16384,
        "unrelated": {"preserve": True},
    })
    response = result(rpc("settings.set", session_id="launch", key="model_context_length", value=0))
    assert response["value"] == 0
    assert result(rpc("settings.get", session_id="launch"))["fields"]["model_context_length"]["value"] == 0
    raw = saved(launch)
    assert "context_length" not in raw
    assert "model_context_length" not in raw
    assert raw["model"] == {"default": "fixture-model", "api_key": "inert-fixture-key"}
    assert raw["unrelated"] == {"preserve": True}


@pytest.mark.parametrize("document", ["model: [unterminated", "- wrong-root\n"])
def test_malformed_config_cannot_be_read_or_replaced(homes, document):
    launch, _ = homes
    path = launch / "config.yaml"
    path.write_text(document, encoding="utf-8")
    before = path.read_bytes()
    assert rpc("settings.get", session_id="launch")["error"]["code"] == 5098
    assert rpc("settings.set", session_id="launch", key="display.show_reasoning", value=False)["error"]["code"] == 5098
    assert path.read_bytes() == before


def test_unreadable_config_is_not_replaced(homes, monkeypatch):
    launch, _ = homes
    path = launch / "config.yaml"
    before = path.read_bytes()
    original_open = builtins.open

    def denied_open(filename, *args, **kwargs):
        if Path(filename) == path:
            raise PermissionError("fixture read denial")
        return original_open(filename, *args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(builtins, "open", denied_open)
        assert rpc("settings.set", session_id="launch", key="display.show_reasoning", value=False)["error"]["code"] == 5098
    assert path.read_bytes() == before


def test_risk_and_collection_opt_in_require_exact_confirmation_without_a_write(homes):
    launch, _ = homes
    before = (launch / "config.yaml").read_bytes()
    for key, value in (("security.redact_secrets", False), ("telemetry.shared_metrics.send", True)):
        response = result(rpc("settings.set", session_id="launch", key=key, value=value))
        assert response["confirm_required"] is True
        assert key in response["confirm_message"]
        assert "default" in response["confirm_message"]
        assert (launch / "config.yaml").read_bytes() == before
    # Only an inert fixture's local security config changes. No provider approval is granted.
    response = result(rpc("settings.set", session_id="launch", key="security.redact_secrets", value=False, confirmed=True))
    assert response["value"] is False
    assert response["confirm_required"] is False


def test_withdraw_collection_uses_coupled_consent_writer(homes):
    launch, _ = homes
    seed(launch, {"telemetry": {"shared_metrics": {"enabled": True, "send": True}}, "unrelated": "keep"})
    response = result(rpc("settings.set", session_id="launch", key="telemetry.shared_metrics.enabled", value=False, confirmed=True))
    assert response["value"] is False
    raw = saved(launch)
    assert raw["telemetry"]["shared_metrics"]["enabled"] is False
    assert raw["telemetry"]["shared_metrics"]["send"] is False
    assert raw["unrelated"] == "keep"
    assert result(rpc("shared_metrics.status", profile="default"))["decided"] is True


def test_compound_secret_redaction_survives_rotation_and_sparse_edit(homes):
    launch, _ = homes
    seed(launch, {"providers": {"first": {"api_key": "old-private", "base_url": "http://127.0.0.1:9"},
                              "second": {"api_key": "untouched-private", "user_note": "keep"}}})
    projected = result(rpc("settings.get", session_id="launch"))["fields"]["providers"]["value"]
    projected["first"]["base_url"] = "http://127.0.0.1:10"
    projected.pop("second")
    seed(launch, {"providers": {"first": {"api_key": "rotated-private", "base_url": "http://127.0.0.1:9"},
                              "second": {"api_key": "untouched-private", "user_note": "keep"}}})
    response = result(rpc("settings.set", session_id="launch", key="providers", value=projected, confirmed=True))
    assert "rotated-private" not in json.dumps(response)
    assert saved(launch)["providers"]["first"]["api_key"] == "rotated-private"
    assert saved(launch)["providers"]["first"]["base_url"] == "http://127.0.0.1:10"
    assert saved(launch)["providers"]["second"] == {"api_key": "untouched-private", "user_note": "keep"}


@pytest.mark.parametrize("preview", ["***", "«redacted:old»", "abcd...wxyz"])
def test_redacted_preview_never_replaces_a_secret(homes, preview):
    launch, _ = homes
    seed(launch, {"delegation": {"api_key": "inert-private"}})
    before = (launch / "config.yaml").read_bytes()
    assert rpc("settings.set", session_id="launch", key="delegation.api_key", value=preview, confirmed=True)["error"]["code"] == 4002
    assert (launch / "config.yaml").read_bytes() == before


def test_sensitive_null_preserves_and_explicit_clear_is_confirmed(homes):
    launch, _ = homes
    seed(launch, {"delegation": {"api_key": "inert-private", "model": "keep"}})
    before = (launch / "config.yaml").read_bytes()
    assert result(rpc("settings.set", session_id="launch", key="delegation.api_key", value=None))["value"] is None
    assert (launch / "config.yaml").read_bytes() == before
    assert result(rpc("settings.set", session_id="launch", key="delegation.api_key", value=""))["confirm_required"] is True
    result(rpc("settings.set", session_id="launch", key="delegation.api_key", value="", confirmed=True))
    assert saved(launch)["delegation"]["api_key"] == ""
    assert saved(launch)["delegation"]["model"] == "keep"


def test_a_retired_profile_home_cannot_be_recreated_by_a_stale_write(homes):
    _, worker = homes
    before = (worker / "config.yaml").read_bytes()
    retired = worker.with_name("retired-worker")
    worker.rename(retired)
    response = rpc("settings.set", session_id="worker", key="display.show_reasoning", value=False)
    assert response["error"]["code"] == 4001
    assert not worker.exists()
    assert (retired / "config.yaml").read_bytes() == before


def test_an_unattached_transport_cannot_read_or_write_a_live_session(homes):
    launch, _ = homes
    owner, stranger = object(), object()
    server._sessions["launch"]["transport"] = owner
    before = (launch / "config.yaml").read_bytes()
    token = server.bind_transport(stranger)
    try:
        assert rpc("settings.get", session_id="launch")["error"]["code"] == 4001
        assert rpc("settings.set", session_id="launch", key="display.show_reasoning", value=False)["error"]["code"] == 4001
    finally:
        server.reset_transport(token)
    assert (launch / "config.yaml").read_bytes() == before
    token = server.bind_transport(owner)
    try:
        assert result(rpc("settings.get", session_id="launch"))["profile"] == "default"
    finally:
        server.reset_transport(token)


def test_managed_leaf_and_compound_ancestor_are_not_writable(homes, monkeypatch):
    from hermes_cli import managed_scope

    launch, _ = homes
    before = (launch / "config.yaml").read_bytes()
    monkeypatch.setattr(managed_scope, "managed_config_keys",
                        lambda: {"agent.gateway_timeout", "providers.fixture.api_key"})
    for key, value in (("agent.gateway_timeout", 42), ("providers", {})):
        response = rpc("settings.set", session_id="launch", key=key, value=value, confirmed=True)
        assert response["error"]["code"] == 4002
    assert (launch / "config.yaml").read_bytes() == before


def test_credential_list_reorder_matches_routes_not_positions(homes):
    launch, _ = homes
    seed(launch, {"fallback_providers": [
        {"provider": "custom", "model": "first", "base_url": "http://127.0.0.1:9", "api_key": "first-private"},
        {"provider": "custom", "model": "second", "base_url": "http://127.0.0.1:10", "api_key": "second-private"},
    ]})
    fields = result(rpc("settings.get", session_id="launch"))["fields"]
    reordered = list(reversed(fields["fallback_providers"]["value"]))
    response = result(rpc("settings.set", session_id="launch", key="fallback_providers",
                          value=reordered, confirmed=True))
    assert [row["model"] for row in response["value"]] == ["second", "first"]
    assert [row["api_key"] for row in response["value"]] == [None, None]
    assert [row["api_key"] for row in saved(launch)["fallback_providers"]] == ["second-private", "first-private"]


def test_repeated_identical_events_do_not_rewrite_a_file(homes):
    launch, _ = homes
    before = (launch / "config.yaml").read_bytes()
    for _ in range(2):
        response = result(rpc("settings.set", session_id="launch", key="display.show_reasoning", value=True))
        assert response["value"] is True
        assert response["confirm_required"] is False
    assert (launch / "config.yaml").read_bytes() == before


@pytest.mark.parametrize("method", ["settings.get", "settings.set"])
def test_settings_remain_available_when_discovery_updates_profile_config(homes, monkeypatch, method):
    import contextvars
    import threading
    from hermes_cli.config import save_config

    launch, _ = homes
    original_schema = web_server_config._schema_with_dynamic_provider_options
    writers = []
    failures = []

    def discover_after_concurrent_config_update():
        finished = threading.Event()
        scope = contextvars.copy_context()

        def update():
            try:
                scope.run(save_config, {"agent": {"gateway_timeout": 321}}, merge_existing=True)
            except Exception as exc:
                failures.append(exc)
            finally:
                finished.set()

        writer = threading.Thread(target=update, daemon=True)
        writers.append(writer)
        writer.start()
        if not finished.wait(2):
            raise TimeoutError("Plugin discovery could not read or update the profile configuration.")
        return original_schema()

    monkeypatch.setattr(web_server_config, "_schema_with_dynamic_provider_options", discover_after_concurrent_config_update)
    try:
        params = {"session_id": "launch"}
        if method == "settings.set":
            params.update(key="display.show_reasoning", value=False)
        response = rpc(method, **params)
    finally:
        for writer in writers:
            writer.join(timeout=5)
    assert not failures
    current = result(response)
    assert saved(launch)["agent"]["gateway_timeout"] == 321
    if method == "settings.get":
        assert current["fields"]["agent.gateway_timeout"]["value"] == 321
    else:
        assert current["value"] is False
        assert saved(launch)["display"]["show_reasoning"] is False


@pytest.mark.parametrize(("legacy_key", "legacy_value"), [
    ("display.in_app_tips", False),
    ("details_mode.tools", "expanded"),
    ("prompt", "inert legacy prompt"),
    ("personality", "concise"),
])
def test_legacy_and_native_config_writers_serialize_complete_rmw(homes, monkeypatch, legacy_key, legacy_value):
    import contextvars
    import threading

    import utils

    launch, _ = homes
    snapshot_ready = threading.Event()
    release_legacy = threading.Event()
    settings_started = threading.Event()
    settings_done = threading.Event()
    results = {}
    failures = []
    original_save = server._save_cfg
    original_roundtrip_dump = utils._roundtrip_dump
    monkeypatch.setattr(web_server_config, "_schema_with_dynamic_provider_options", lambda: web_server_config.CONFIG_SCHEMA)

    def paused_save(cfg):
        if threading.current_thread().name == "legacy-config-writer":
            snapshot_ready.set()
            if not release_legacy.wait(5):
                raise TimeoutError("legacy config writer was not released")
        return original_save(cfg)

    def paused_roundtrip_dump(*args, **kwargs):
        if threading.current_thread().name == "legacy-config-writer":
            snapshot_ready.set()
            if not release_legacy.wait(5):
                raise TimeoutError("legacy config writer was not released")
        return original_roundtrip_dump(*args, **kwargs)

    monkeypatch.setattr(server, "_save_cfg", paused_save)
    monkeypatch.setattr(utils, "_roundtrip_dump", paused_roundtrip_dump)

    def invoke(name, scope, method, **params):
        try:
            results[name] = scope.run(rpc, method, **params)
        except Exception as exc:
            failures.append(exc)

    legacy_scope = contextvars.copy_context()
    legacy = threading.Thread(
        name="legacy-config-writer",
        target=invoke,
        args=("legacy", legacy_scope, "config.set"),
        kwargs={"session_id": "launch", "key": legacy_key, "value": legacy_value},
        daemon=True,
    )

    def update_native():
        settings_started.set()
        try:
            results["settings"] = contextvars.copy_context().run(
                rpc, "settings.set", session_id="launch", key="display.show_reasoning", value=False)
        except Exception as exc:
            failures.append(exc)
        finally:
            settings_done.set()

    legacy.start()
    assert snapshot_ready.wait(2)
    settings = threading.Thread(target=update_native, name="native-settings-writer", daemon=True)
    settings.start()
    assert settings_started.wait(2)
    completed_before_legacy_commit = settings_done.wait(0.5)
    release_legacy.set()
    legacy.join(timeout=5)
    settings.join(timeout=5)

    assert not legacy.is_alive() and not settings.is_alive()
    assert not completed_before_legacy_commit
    assert not failures
    assert "result" in results["legacy"] and "result" in results["settings"]
    raw = saved(launch)
    assert raw["display"]["show_reasoning"] is False
    if legacy_key == "display.in_app_tips":
        assert raw["display"]["in_app_tips"] is False
    elif legacy_key == "details_mode.tools":
        assert raw["display"]["sections"]["tools"] == "expanded"
    elif legacy_key == "personality":
        assert raw["display"]["personality"] == "concise"
    else:
        assert raw["custom_prompt"] == "inert legacy prompt"



def test_legacy_and_native_public_config_rpcs_serialize_across_processes(homes):
    import multiprocessing

    launch, _ = homes
    seed(launch, {
        "model": {"default": "fixture-model", "provider": "custom", "api_key": "inert-provider-fixture"},
        "display": {"show_reasoning": True},
        "unrelated": {"nested": {"user_owned": [1, "preserve"]}},
    })
    env_before = (launch / ".env").read_bytes()
    context = multiprocessing.get_context("spawn")
    legacy_started, legacy_read, resume_legacy = context.Event(), context.Event(), context.Event()
    native_started, native_lock_requested, native_done = context.Event(), context.Event(), context.Event()
    outcomes = context.Queue()
    legacy = context.Process(
        target=_legacy_public_rpc_worker,
        args=(str(launch), legacy_started, legacy_read, resume_legacy, outcomes),
    )
    native = context.Process(
        target=_native_public_rpc_worker,
        args=(str(launch), native_started, native_lock_requested, native_done, outcomes),
    )
    started = []
    try:
        legacy.start()
        started.append(legacy)
        assert legacy_started.wait(10), "legacy RPC process did not start"
        assert legacy_read.wait(10), "legacy RPC did not reach its real raw-config read"
        native.start()
        started.append(native)
        assert native_started.wait(10), "native RPC process did not start"
        assert native_lock_requested.wait(10), "native settings RPC did not request the profile lock"
        assert not native_done.wait(0.5), "native settings RPC passed a legacy read-modify-write transaction"
    finally:
        resume_legacy.set()
        for process in started:
            process.join(timeout=15)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)

    assert legacy.exitcode == 0
    assert native.exitcode == 0
    responses = dict(outcomes.get(timeout=5) for _ in range(2))
    assert "legacy" in responses and "native" in responses
    assert "result" in responses["legacy"], responses["legacy"]
    assert "result" in responses["native"], responses["native"]
    current = saved(launch)
    assert current["display"]["in_app_tips"] is False
    assert current["display"]["show_reasoning"] is False
    assert current["model"] == {
        "default": "fixture-model", "provider": "custom", "api_key": "inert-provider-fixture"}
    assert current["unrelated"] == {"nested": {"user_owned": [1, "preserve"]}}
    assert (launch / ".env").read_bytes() == env_before


@pytest.mark.parametrize(("key", "value", "display", "first_value", "second_value", "final_display"), [
    ("battery", "toggle", {"battery": False}, "on", "off", {"battery": False}),
    ("verbose", "cycle", {"tool_progress": "all"}, "verbose", "off", {"tool_progress": "off"}),
    ("focus", "toggle", {"focus_view": False, "tool_progress": "verbose"},
     "on", "off", {"focus_view": False, "tool_progress": "verbose", "focus_saved_tool_progress": "verbose"}),
])
def test_concurrent_config_set_cycles_and_focus_are_profile_transactions(
        homes, monkeypatch, key, value, display, first_value, second_value, final_display):
    import contextvars
    import threading

    launch, _ = homes
    monkeypatch.delenv("HERMES_TUI_TOOL_PROGRESS", raising=False)
    seed(launch, {
        "model": {"default": "fixture-model", "provider": "custom", "api_key": "inert-provider-fixture"},
        "display": {"show_reasoning": True, **display},
        "unrelated": {"nested": {"user_owned": [2, "preserve"]}},
    })
    env_before = (launch / ".env").read_bytes()
    original_display_cfg = server._display_cfg
    first_read, release_first = threading.Event(), threading.Event()
    second_read, second_started = threading.Event(), threading.Event()
    done = {"first": threading.Event(), "second": threading.Event()}
    results, failures = {}, []

    def pause_after_first_snapshot():
        current = original_display_cfg()
        name = threading.current_thread().name
        if name == "derived-config-first" and not first_read.is_set():
            first_read.set()
            if not release_first.wait(5):
                raise TimeoutError("first derived config read was not released")
        elif name == "derived-config-second":
            second_read.set()
        return current

    monkeypatch.setattr(server, "_display_cfg", pause_after_first_snapshot)

    def invoke(name, scope):
        if name == "second":
            second_started.set()
        try:
            results[name] = scope.run(rpc, "config.set", session_id="launch", key=key, value=value)
        except Exception as exc:
            failures.append(exc)
        finally:
            done[name].set()

    first = threading.Thread(
        name="derived-config-first", target=invoke, args=("first", contextvars.copy_context()), daemon=True)
    second = threading.Thread(
        name="derived-config-second", target=invoke, args=("second", contextvars.copy_context()), daemon=True)
    first.start()
    try:
        assert first_read.wait(5), "first RPC did not read its derived display state"
        second.start()
        assert second_started.wait(5), "second RPC did not start"
        assert not second_read.wait(0.5), "second RPC derived its decision before the first commit"
        assert not done["second"].is_set()
    finally:
        release_first.set()
        first.join(timeout=5)
        if second.ident is not None:
            second.join(timeout=5)

    assert not first.is_alive() and not second.is_alive()
    assert not failures
    assert result(results["first"])["value"] == first_value
    assert result(results["second"])["value"] == second_value
    current = saved(launch)
    for field, expected in final_display.items():
        assert current["display"][field] == expected
    assert current["display"]["show_reasoning"] is True
    assert current["model"] == {
        "default": "fixture-model", "provider": "custom", "api_key": "inert-provider-fixture"}
    assert current["unrelated"] == {"nested": {"user_owned": [2, "preserve"]}}
    assert (launch / ".env").read_bytes() == env_before

def test_global_model_rpc_keeps_later_settings_context_pin(homes, monkeypatch):
    import contextvars
    import threading
    from types import SimpleNamespace

    import utils

    launch, _ = homes
    seed(launch, {
        "model": {
            "default": "old-model",
            "provider": "custom",
            "base_url": "http://localhost:1234/v1",
            "context_length": 32000,
        },
        "display": {"show_reasoning": True},
    })
    switch_result = SimpleNamespace(
        success=True, new_model="claude-haiku", target_provider="anthropic", provider_changed=True,
        api_key="", base_url="https://api.anthropic.com", api_mode="anthropic_messages",
        warning_message="", is_global=True)
    monkeypatch.setattr("hermes_cli.model_switch.switch_model", lambda **_kwargs: switch_result)
    monkeypatch.setattr(web_server_config, "_schema_with_dynamic_provider_options",
                        lambda: web_server_config.CONFIG_SCHEMA)
    monkeypatch.setattr(
        "hermes_cli.observability.shared_metrics_events.record_model_switch", lambda **_kwargs: None)

    original_atomic_update = utils.atomic_roundtrip_yaml_update
    model_write_waiting = threading.Event()
    release_model_write = threading.Event()
    settings_started = threading.Event()
    settings_done = threading.Event()
    responses = {}
    failures = []

    def pause_model_write(path, key, value):
        if threading.current_thread().name == "global-model-writer" and not model_write_waiting.is_set():
            model_write_waiting.set()
            if not release_model_write.wait(5):
                raise TimeoutError("global model commit was not released")
        return original_atomic_update(path, key, value)

    monkeypatch.setattr(utils, "atomic_roundtrip_yaml_update", pause_model_write)

    global_context = contextvars.copy_context()
    settings_context = contextvars.copy_context()

    def persist_global_model():
        try:
            responses["model"] = global_context.run(
                rpc, "config.set", session_id="launch", key="model",
                value="claude-haiku --provider anthropic --global", confirm_expensive_model=True)
        except Exception as exc:
            failures.append(exc)

    def set_context_pin():
        settings_started.set()
        try:
            responses["settings"] = settings_context.run(
                rpc, "settings.set", session_id="launch", key="model_context_length",
                value=8192, confirmed=True)
        except Exception as exc:
            failures.append(exc)
        finally:
            settings_done.set()

    model_writer = threading.Thread(name="global-model-writer", target=persist_global_model, daemon=True)
    settings_writer = threading.Thread(name="native-settings-writer", target=set_context_pin, daemon=True)
    model_writer.start()
    try:
        assert model_write_waiting.wait(2)
        settings_writer.start()
        assert settings_started.wait(2)
        settings_completed_before_model_commit = settings_done.wait(0.5)
    finally:
        release_model_write.set()
        model_writer.join(timeout=5)
        if settings_writer.ident is not None:
            settings_writer.join(timeout=5)

    assert not model_writer.is_alive() and not settings_writer.is_alive()
    assert not settings_completed_before_model_commit
    assert not failures
    assert "result" in responses["model"] and "result" in responses["settings"]
    final = saved(launch)
    assert final["model"]["default"] == "claude-haiku"
    assert final["model"]["provider"] == "anthropic"
    assert final["model"]["context_length"] == 8192


@pytest.mark.parametrize(("key", "value"), [
    ("quick_commands", {"inert": {"exec": "printf native-settings-fixture"}}),
    ("skills.inline_shell", True),
    ("browser.dialog_policy", "auto_accept"),
])
def test_execution_and_dialog_policy_changes_require_confirmation(homes, key, value):
    launch, _ = homes
    before = (launch / "config.yaml").read_bytes()
    response = result(rpc("settings.set", session_id="launch", key=key, value=value))
    assert response["confirm_required"] is True
    assert key in response["confirm_message"]
    assert (launch / "config.yaml").read_bytes() == before


def test_submitted_duplicate_credential_routes_are_rejected_before_save(homes):
    launch, _ = homes
    seed(launch, {"fallback_providers": [
        {"provider": "custom", "model": "fixture", "api_key": "inert-private"},
    ]})
    row = result(rpc("settings.get", session_id="launch"))["fields"]["fallback_providers"]["value"][0]
    before = (launch / "config.yaml").read_bytes()
    response = rpc("settings.set", session_id="launch", key="fallback_providers",
                   value=[row, copy.deepcopy(row)], confirmed=True)
    assert response["error"]["code"] == 4002
    assert (launch / "config.yaml").read_bytes() == before


@pytest.mark.parametrize("key", ["tts.provider", "stt.provider", "memory.provider"])
def test_dynamic_choices_preserve_environment_templates_without_exposing_their_expansion(homes, key):
    launch, _ = homes
    section = key.split(".")[0]
    seed(launch, {section: {"provider": "${TEST_ROUTE_KEY}"}})
    field = result(rpc("settings.get", session_id="launch"))["fields"][key]
    assert field["value"] == "${TEST_ROUTE_KEY}"
    assert "${TEST_ROUTE_KEY}" in field["options"]
    assert "inert-local-key" not in json.dumps(field)
    before = (launch / "config.yaml").read_bytes()
    response = result(rpc("settings.set", session_id="launch", key=key, value=field["value"]))
    assert response["value"] == "${TEST_ROUTE_KEY}"
    assert response["confirm_required"] is False
    assert (launch / "config.yaml").read_bytes() == before


@pytest.mark.parametrize(("managed", "key", "value"), [
    ("model.context_length", "model_context_length", 0),
    ("model.context_length", "model_context_length", 8192),
    ("telemetry.shared_metrics.send", "telemetry.shared_metrics.enabled", False),
    ("telemetry.shared_metrics.enabled", "telemetry.shared_metrics.send", False),
])
def test_virtual_and_coupled_settings_cannot_mutate_managed_paths(homes, monkeypatch, managed, key, value):
    from hermes_cli import managed_scope
    launch, _ = homes
    seed(launch, {"model": {"default": "fixture", "context_length": 4096},
                  "telemetry": {"shared_metrics": {"enabled": True, "send": True}}})
    monkeypatch.setattr(managed_scope, "managed_config_keys", lambda: {managed})
    before = (launch / "config.yaml").read_bytes()
    response = rpc("settings.set", session_id="launch", key=key, value=value, confirmed=True)
    assert response["error"]["code"] == 4002
    assert (launch / "config.yaml").read_bytes() == before


@pytest.mark.parametrize("params", [
    {"value": False}, {"key": "display.show_reasoning"}, {"key": 42, "value": False},
])
def test_missing_or_mistyped_required_settings_parameters_return_invalid_params(homes, params):
    launch, _ = homes
    before = (launch / "config.yaml").read_bytes()
    response = rpc("settings.set", session_id="launch", **params)
    assert response["error"]["code"] == 4000
    assert (launch / "config.yaml").read_bytes() == before


def test_setting_templates_follow_the_winning_managed_layer(homes, tmp_path, monkeypatch):
    launch, _ = homes
    seed(launch, {"terminal": {"cwd": "${TEST_ROUTE_KEY}"},
                  "agent": {"gateway_timeout": "${TEST_ROUTE_KEY}"},
                  "tts": {"provider": "${TEST_ROUTE_KEY}"}})
    managed = tmp_path / "managed-policy"
    managed.mkdir()
    seed(managed, {"terminal": {"cwd": "/approved-fixture"},
                   "agent": {"gateway_timeout": 321},
                   "tts": {"provider": "${ADMIN_ROUTE_FIXTURE}"}})
    monkeypatch.setenv("HERMES_MANAGED_DIR", str(managed))
    monkeypatch.setenv("ADMIN_ROUTE_FIXTURE", "inert-admin-route")
    fields = result(rpc("settings.get", session_id="launch"))["fields"]
    assert fields["terminal.cwd"]["value"] == "/approved-fixture"
    assert fields["agent.gateway_timeout"]["value"] == 321
    assert fields["tts.provider"]["value"] == "${ADMIN_ROUTE_FIXTURE}"
    assert "${ADMIN_ROUTE_FIXTURE}" in fields["tts.provider"]["options"]
    assert "inert-admin-route" not in json.dumps(fields["tts.provider"])
    assert "inert-local-key" not in json.dumps(fields)


def test_optional_speech_provider_reset_restores_autodetection(homes):
    launch, _ = homes
    key, initial = "stt.provider", "local"
    branch = initial
    for part in reversed(key.split(".")):
        branch = {part: branch}
    seed(launch, {**branch, "unrelated": {"preserved": True}})
    fields = result(rpc("settings.get", session_id="launch"))["fields"]
    assert fields[key]["value"] == initial
    assert fields[key]["nullable"] is True
    result(rpc("settings.set", session_id="launch", key=key, value=None, confirmed=True))
    node = saved(launch)
    for part in key.split(".")[:-1]:
        node = node[part]
    assert key.split(".")[-1] not in node
    assert saved(launch)["unrelated"] == {"preserved": True}
    assert result(rpc("settings.get", session_id="launch"))["fields"][key]["value"] is None


@pytest.mark.parametrize(("stored", "kind", "shown"), [
    (False, "select", "none"),
    (True, "select", None),
    ({"enabled": True, "effort": "high"}, "select", "high"),
    ({"enabled": True, "effort": "fast"}, "object", {"enabled": True, "effort": "fast"}),
])
def test_legacy_and_custom_reasoning_forms_remain_editable_without_changing_live_pins(homes, stored, kind, shown):
    launch, _ = homes
    seed(launch, {"agent": {"reasoning_effort": stored}})
    before = (launch / "config.yaml").read_bytes()
    field = result(rpc("settings.get", session_id="launch"))["fields"]["agent.reasoning_effort"]
    assert field["type"] == kind
    assert field["value"] == shown
    assert (launch / "config.yaml").read_bytes() == before
    replacement = {"enabled": True, "effort": "thinking"} if kind == "object" else "low"
    response = result(rpc("settings.set", session_id="launch", key="agent.reasoning_effort", value=replacement))
    assert response["value"] == replacement
    assert saved(launch)["agent"]["reasoning_effort"] == replacement
    assert result(rpc("config.get", session_id="launch", key="reasoning"))["value"] == "high"
