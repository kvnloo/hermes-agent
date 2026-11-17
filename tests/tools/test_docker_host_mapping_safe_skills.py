"""Regression for #50798: a sibling Docker sandbox must see symlink-safe skills."""

from pathlib import Path

import pytest

from tools import credential_files, docker_host_mapping
from tools.environments import docker as docker_env


@pytest.mark.platforms("posix")
def test_symlink_safe_skills_staged_for_host_socket(monkeypatch, tmp_path):
    gateway_home = tmp_path / "opt-data"
    skills = gateway_home / "skills"
    scripts = skills / "demo" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "hello.py").write_text("print('hello')\n", encoding="utf-8")
    secret = tmp_path / "secret"
    secret.write_text("must not reach sandbox", encoding="utf-8")
    (skills / "demo" / "secret-link").symlink_to(secret)

    monkeypatch.setenv("TERMINAL_SANDBOX_DIR", str(gateway_home / "sandboxes"))
    monkeypatch.setattr(
        docker_host_mapping, "resolve_host_mapping",
        lambda: {str(gateway_home): "/daemon/hermes"},
    )
    monkeypatch.setattr(
        credential_files, "_skill_dir_roots",
        lambda container_base: iter([(skills, f"{container_base}/skills")]),
    )
    monkeypatch.setattr(credential_files, "get_credential_file_mounts", lambda: [])
    monkeypatch.setattr(credential_files, "get_cache_directory_mounts", lambda: [])

    args = docker_env._readonly_skill_mount_args()
    assert len(args) == 2 and args[0] == "-v"
    source, destination, mode = args[1].split(":")
    assert (destination, mode) == ("/root/.hermes/skills", "ro")
    assert source.startswith("/daemon/hermes/sandboxes/docker/safe-skills-")

    staged = gateway_home / Path(source).relative_to("/daemon/hermes")
    assert (staged / "demo" / "scripts" / "hello.py").read_text(encoding="utf-8") == "print('hello')\n"
    assert not (staged / "demo" / "secret-link").exists()
