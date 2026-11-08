import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hermes_cli.json_safety import dumps_utf8_safe
from hermes_cli.web_server import UTF8SafeJSONResponse


def test_dumps_utf8_safe_repairs_keys_and_values_without_mutating_input():
    payload = {"key\udfff": ["value\ud800", "中文"]}

    serialized = dumps_utf8_safe(payload, ensure_ascii=False)

    serialized.encode("utf-8")
    assert json.loads(serialized) == {"key�": ["value�", "中文"]}
    assert next(iter(payload)) == "key\udfff"


def test_dumps_utf8_safe_leaves_valid_unicode_serialization_unchanged():
    payload = {"message": "Hello, 世界 👋"}

    assert dumps_utf8_safe(payload, ensure_ascii=False) == json.dumps(
        payload, ensure_ascii=False
    )


def test_fastapi_default_response_survives_lone_surrogate():
    app = FastAPI(default_response_class=UTF8SafeJSONResponse)

    @app.get("/payload")
    def payload():
        return {"message": "Hello \ud83d 世界"}

    response = TestClient(app).get("/payload")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello � 世界"}
    assert "世界".encode() in response.content


def test_config_endpoint_preserves_yaml_escaped_surrogate_pair():
    """Regression for NousResearch/hermes-agent#150918."""
    from hermes_cli.config import get_config_path
    from hermes_cli.web_server import _SESSION_HEADER_NAME, _SESSION_TOKEN, app

    config_path = get_config_path()
    config_path.write_text(
        "agent:\n"
        "  personalities:\n"
        '    surfer: "Cowabunga! \\uD83E\\uDD19"\n'
        '    hype: "Oops \\uD83E"\n',
        encoding="utf-8",
    )
    response = TestClient(app).get(
        "/api/config",
        headers={_SESSION_HEADER_NAME: _SESSION_TOKEN},
    )
    assert response.status_code == 200
    personalities = response.json()["agent"]["personalities"]
    assert personalities["surfer"] == "Cowabunga! 🤙"
    assert personalities["hype"] == "Oops �"
