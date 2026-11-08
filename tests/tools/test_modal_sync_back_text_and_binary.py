"""Regression for #125280: Modal sync-back must preserve binary assets and adjacent text.

Adapted from Liuzikaii's end-to-end reproducer in PR #125281 for oppih's PR #151183.
"""

import shlex
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from tools.environments.file_sync import FileSyncManager, iter_sync_files
from tools.environments.modal import ModalEnvironment, _AsyncWorker


@pytest.mark.platforms("posix")
def test_modal_sync_back_preserves_binary_and_neighboring_text(tmp_path, monkeypatch):
    home = tmp_path / "home"
    skill_dir = home / "skills" / "example"
    skill_dir.mkdir(parents=True)
    skill_text = skill_dir / "SKILL.md"
    skill_text.write_text("original instructions", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr("tools.environments.file_sync._sleep", lambda _delay: None)

    remote = tmp_path / "sandbox"
    (remote / "root/.hermes").mkdir(parents=True)
    worker = _AsyncWorker()
    worker.start()
    try:
        env = object.__new__(ModalEnvironment)
        env._worker = worker

        async def sandbox_exec(*argv):
            # Run the production tar/base64 pipeline locally. Only Modal's network transport
            # is replaced; its text-mode stdout contract is preserved.
            script = argv[-1].replace(
                "-C / root/.hermes", f"-C {shlex.quote(str(remote))} root/.hermes"
            )
            result = subprocess.run([*argv[:-1], script], capture_output=True, check=False)

            async def stdout_read():
                return result.stdout.decode("utf-8")

            async def stderr_read():
                return result.stderr.decode("utf-8", errors="replace")

            async def wait():
                return result.returncode

            return SimpleNamespace(
                stdout=SimpleNamespace(read=SimpleNamespace(aio=stdout_read)),
                stderr=SimpleNamespace(read=SimpleNamespace(aio=stderr_read)),
                wait=SimpleNamespace(aio=wait),
            )

        env._sandbox = SimpleNamespace(exec=SimpleNamespace(aio=sandbox_exec))

        def upload(host_path, remote_path):
            target = remote / remote_path.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(host_path, target)

        manager = FileSyncManager(
            iter_sync_files,
            upload,
            lambda _paths: None,
            bulk_download_fn=env._modal_bulk_download,
        )
        manager.sync(force=True)

        remote_text = remote / "root/.hermes/skills/example/SKILL.md"
        assert remote_text.is_file()
        remote_text.write_text("updated instructions", encoding="utf-8")
        binary = bytes(range(256))
        (remote_text.parent / "asset.bin").write_bytes(binary)

        manager.sync_back(hermes_home=home)

        assert skill_text.read_text(encoding="utf-8") == "updated instructions"
        assert (skill_dir / "asset.bin").read_bytes() == binary
    finally:
        worker.stop()
