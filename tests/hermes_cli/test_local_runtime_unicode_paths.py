"""Regression for #156692: narrow argv decoding must not corrupt paths under Unicode homes."""

from types import SimpleNamespace

from hermes_cli.local_runtime import presets, supervisor


def test_unicode_home_server_spawn_passes_ascii_preset_and_key_paths(tmp_path, monkeypatch):
    home = tmp_path / "Bąrt"
    executable = home / "engine" / "llama-server"
    model_dir = home / "models"
    model_dir.mkdir(parents=True)
    preset_path = home / "runtimes" / "llamacpp" / "presets.ini"
    preset_path.parent.mkdir(parents=True)
    preset_path.write_text("[example]\nmodel = example.gguf\n", encoding="utf-8")

    monkeypatch.setattr(supervisor, "runtimes_root", lambda: preset_path.parent)
    monkeypatch.setattr(supervisor, "_direct_io_args", lambda exe: ())
    monkeypatch.setattr(supervisor, "_api_key_file_supported", lambda exe: True)
    spawns = []
    monkeypatch.setattr(supervisor, "spawn_server", lambda cmd, **kw: (
        spawns.append((cmd, kw)) or SimpleNamespace(pid=123), None))
    sup = supervisor.LlamaServerSupervisor(executable, model_dir, port=19001,
                                           preset_path=preset_path)
    monkeypatch.setattr(sup, "_write_state", lambda: None)
    try:
        sup._spawn()
    finally:
        sup._log_handle.close()

    cmd, options = spawns[0]
    assert options["cwd"] == str(executable.parent)
    for flag, expected in (("--models-preset", preset_path),
                           ("--api-key-file", supervisor.api_key_path())):
        argument = cmd[cmd.index(flag) + 1]
        assert argument.isascii()
        assert (executable.parent / argument).resolve() == expected.resolve()


def test_unicode_home_preset_paths_are_ascii_relative_to_engine(tmp_path):
    home = tmp_path / "Bąrt"
    cwd = home / "engine"
    values = {
        "model": home / "models" / "example.gguf",
        "mmproj": home / "models" / "assets" / "vision.gguf",
        "model-draft": home / "models" / "assets" / "draft.gguf",
    }
    entry = presets.PresetEntry("example", window=8192, spilled=False,
                                keys={key: str(path) for key, path in values.items()})
    text = presets.render_presets([entry], server_cwd=cwd)
    for key, expected in values.items():
        line = next(line for line in text.splitlines() if line.startswith(f"{key} = "))
        argument = line.split(" = ", 1)[1]
        assert argument.isascii()
        assert (cwd / argument).resolve() == expected.resolve()
