"""Voice-mode system playback must scrub credential env (sibling of #70342)."""

from unittest.mock import MagicMock, patch


def test_play_audio_file_scrubbed_env(tmp_path, monkeypatch):
    audio = tmp_path / "t.mp3"
    audio.write_bytes(b"ID3fake")

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["env"] = kwargs.get("env")
        proc = MagicMock()
        proc.wait.return_value = 0
        proc.returncode = 0
        return proc

    import tools.voice_mode as vm

    with patch.object(vm, "platform") as plat, patch.object(
        vm.shutil, "which", return_value="/usr/bin/ffplay"
    ), patch.object(vm.subprocess, "Popen", side_effect=fake_popen):
        plat.system.return_value = "Linux"
        ok = vm.play_audio_file(str(audio))

    assert ok is True
    assert captured.get("env") is not None
    assert "TELEGRAM_BOT_TOKEN" not in captured["env"]
    assert "OPENAI_API_KEY" not in captured["env"]


def test_duration_probe_and_player_share_scrubbed_environment(tmp_path, monkeypatch):
    """Both actual subprocess boundaries must use the same credential-scrubbed env."""
    import tools.voice_mode as vm
    from tools import transcription_audio as ta

    audio = tmp_path / "long.mp3"
    audio.write_bytes(b"ID3fake")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    seen = {}

    def fake_run(command, **kwargs):
        seen["probe_command"] = command
        seen["probe_env"] = kwargs.get("env")
        return MagicMock(stdout="420.0\n", returncode=0)

    def fake_popen(command, **kwargs):
        seen["player_env"] = kwargs.get("env")
        proc = MagicMock()
        proc.wait.side_effect = lambda timeout=None: seen.setdefault("timeout", timeout)
        proc.returncode = 0
        return proc

    with patch.object(vm, "_system_player_candidates", return_value=[["ffplay", str(audio)]]), \
         patch.object(vm.shutil, "which", return_value="/usr/bin/ffplay"), \
         patch.object(ta, "_find_ffprobe_binary", return_value="/usr/bin/ffprobe"), \
         patch.object(ta.subprocess, "run", side_effect=fake_run), \
         patch.object(vm.subprocess, "Popen", side_effect=fake_popen):
        assert vm.play_audio_file(str(audio)) is True

    assert seen["probe_command"][0] == "/usr/bin/ffprobe"
    assert seen["timeout"] == 450.0
    assert seen["probe_env"] == seen["player_env"]
    assert seen["probe_env"] is not None
    assert "OPENAI_API_KEY" not in seen["probe_env"]
    assert "TELEGRAM_BOT_TOKEN" not in seen["probe_env"]
