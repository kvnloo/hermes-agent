"""GET /api/config must encode YAML surrogate escapes without corrupting text."""

import hermes_yaml as yaml
import pytest


def test_get_config_repairs_yaml_surrogates_for_json(monkeypatch, _isolate_hermes_home):
    """Escaped emoji pairs survive; unmatched halves (including keys) become U+FFFD."""
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    from hermes_cli import web_server
    from hermes_cli.web_routers import config_env

    # PyYAML expands \u escapes into surrogate code units, not valid UTF-8 text.
    parsed = yaml.safe_load(r'''
agent:
  personalities:
    surfer: "Cowabunga! \uD83E\uDD19"
    orphan: "Oops \uD800"
    "\uD800": "bad key"
''')

    async def scoped_config(_profile, _reader):
        return parsed

    monkeypatch.setattr(config_env, "scoped_to_thread", scoped_config)
    client = TestClient(web_server.app)
    client.headers[web_server._SESSION_HEADER_NAME] = web_server._SESSION_TOKEN

    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json() == {
        "agent": {
            "personalities": {
                "surfer": "Cowabunga! \U0001f919",
                "orphan": "Oops \ufffd",
                "\ufffd": "bad key",
            }
        }
    }
