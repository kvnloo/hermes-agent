"""``set_theme``: the model hears what the desktop applied, never a success it assumed."""

import json

from tools.registry import discover_builtin_tools, registry


def _dispatch(args: dict, callback) -> dict:
    discover_builtin_tools()
    result = registry.dispatch("set_theme", args, callback=callback)
    assert isinstance(result, str)
    return json.loads(result)


def test_unknown_values_return_the_available_ids_without_reaching_the_renderer():
    calls = []

    accent = _dispatch({"accent": "chartreuse"}, calls.append)
    mode = _dispatch({"mode": "dim"}, calls.append)

    assert accent["success"] is False and "violet" in accent["available"] and "theme" in accent["available"]
    assert mode["success"] is False and mode["available"] == ["light", "dark", "system"]
    assert calls == []


def test_the_renderer_answer_is_the_result_for_values_and_pickers():
    sent = []

    def renderer(payload):
        sent.append(payload)
        return ({"success": True, "picked": {"layout": "terminal-deck"}} if "picker" in payload
                else {"success": False, "error": "Unknown layout", "available": ["sidebar-left"]})

    applied = _dispatch({"layout": " cockpit ", "accent": "#8A2BE2"}, renderer)
    picked = _dispatch({"picker": "layout"}, renderer)

    assert sent == [{"layout": "cockpit", "accent": "#8A2BE2"}, {"picker": "layout"}]
    assert applied == {"success": False, "error": "Unknown layout", "available": ["sidebar-left"]}
    assert picked == {"success": True, "picked": {"layout": "terminal-deck"}}


def _write_skin(home, name, css):
    skins = home / "skins"
    skins.mkdir(parents=True, exist_ok=True)
    (skins / f"{name}.yaml").write_text(f"name: {name}\ncolors:\n  background: '#120a24'\n"
                                        f"customCSS: |\n  {css}\n", encoding="utf-8")


def test_a_skin_file_becomes_display_skin_without_reaching_the_renderer():
    import os
    from pathlib import Path

    import hermes_yaml as yaml

    home = Path(os.environ["HERMES_HOME"])
    _write_skin(home, "pixel-quest", "body { animation: drift 8s infinite; }")
    sent = []

    applied = _dispatch({"skin": " pixel-quest "}, sent.append)

    assert applied == {"success": True, "skin": "pixel-quest"} and sent == []
    assert yaml.safe_load((home / "config.yaml").read_text())["display"]["skin"] == "pixel-quest"


def test_an_unknown_skin_writes_nothing_and_names_the_file_to_create():
    import os
    from pathlib import Path

    home = Path(os.environ["HERMES_HOME"])
    sent = []

    missing = _dispatch({"skin": "nope", "accent": "pink"}, sent.append)

    assert missing["success"] is False and "skins/nope.yaml" in missing["error"]
    assert "default" in missing["available"]
    assert sent == [] and not (home / "config.yaml").exists()
