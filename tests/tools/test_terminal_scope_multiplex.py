"""Per-turn terminal scope isolation under profile multiplexing (#68559 class).

One multiplexed process serves several profiles, but terminal.* used to
resolve through the process-global ``TERMINAL_*`` env vars bridged once at
startup — so every routed profile inherited the launch profile's backend,
cwd, docker mounts and shared-container key (#68559, #94200, #101132,
#95470). ``tools.terminal_scope`` installs the routed profile's COMPLETE
terminal policy as a ContextVar at each profile boundary; readers resolve
ONLY from it (omitted key → defined default, never ``os.environ``) and an
unresolvable policy fails closed.
"""

import json
import os

import pytest

from tools.terminal_scope import (
    TerminalPolicyRefusal,
    TerminalPolicyUnavailable,
    get_terminal_scope,
    install_profile_terminal_scope,
    reset_terminal_scope,
    set_terminal_scope,
    terminal_env,
)
from tools import browser_session_cloud as bs_cloud

_LAUNCH_CWD = "/home/launch-user/private"
_LAUNCH_VOLUMES = '["/host/secret:/data:rw"]'


@pytest.fixture(autouse=True)
def _polluted_launch_env(monkeypatch, tmp_path):
    """Launch profile A bridged a docker backend with sensitive policy into
    the process env; every test proves a routed profile observes none of it."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.setenv("TERMINAL_ENV", "docker")
    monkeypatch.setenv("TERMINAL_CWD", _LAUNCH_CWD)
    monkeypatch.setenv("TERMINAL_DOCKER_VOLUMES", _LAUNCH_VOLUMES)
    monkeypatch.setenv("TERMINAL_DOCKER_SHARED_CONTAINER_KEY", "alpha-shared")
    monkeypatch.setenv("TERMINAL_SSH_HOST", "10.10.0.103")
    monkeypatch.setattr("agent.secret_scope.build_profile_secret_scope", lambda _h: {})
    monkeypatch.setattr("hermes_cli.env_loader.hydrate_profile_secret_sources", lambda _h: None)
    import tools.terminal_tool as tt

    monkeypatch.setattr(tt, "_terminal_config_bridge_attempted", True)
    yield


def _profile(tmp_path, name, config_yaml="", dotenv=""):
    home = tmp_path / "profiles" / name
    home.mkdir(parents=True)
    if config_yaml:
        (home / "config.yaml").write_text(config_yaml, encoding="utf-8")
    if dotenv:
        (home / ".env").write_text(dotenv, encoding="utf-8")
    return home


def test_no_scope_keeps_process_env_behavior():
    """Single-process CLI/TUI (no scope bound) is byte-identical to before."""
    assert terminal_env("TERMINAL_ENV") == "docker"
    assert terminal_env("TERMINAL_SSH_HOST") == "10.10.0.103"


def test_scoped_read_never_falls_through_to_process_env():
    """Omitted key under a scope → defined default, NOT the ambient value."""
    token = set_terminal_scope({"TERMINAL_ENV": "local"})
    try:
        assert terminal_env("TERMINAL_ENV") == "local"
        assert terminal_env("TERMINAL_SSH_HOST") == ""
        assert terminal_env("TERMINAL_DOCKER_VOLUMES", "[]") == "[]"
        assert os.environ["TERMINAL_ENV"] == "docker"  # never mutated
    finally:
        reset_terminal_scope(token)


@pytest.mark.parametrize(
    "config_yaml,dotenv",
    [
        pytest.param("terminal:\n  backend: local\n  cwd: {cwd}\n", "", id="config-yaml"),
        pytest.param("", "TERMINAL_ENV=local\nTERMINAL_CWD={cwd}\n", id="dotenv-only"),
    ],
)
def test_routed_turn_reads_every_terminal_consumer_from_profile(
    tmp_path, config_yaml, dotenv
):
    """Leak matrix through the REAL gateway boundary: a routed local profile
    with its own cwd must be seen as such by every terminal.* consumer —
    terminal_tool config, container key resolution, docker media translation,
    file_tools/runtime_cwd cwd anchors, and the browser/env_probe backend
    checks — with none of launch profile A's docker policy showing through."""
    import gateway.run as gw
    import tools.terminal_tool as tt
    from agent import runtime_cwd
    from gateway.platforms import base as gbase
    from gateway.platforms.docker_media_paths import _docker_sandbox_dir_candidates
    from tools import env_probe, file_tools_paths

    b_cwd = tmp_path / "b-work"
    b_cwd.mkdir()
    home = _profile(
        tmp_path, "bee",
        config_yaml.format(cwd=b_cwd), dotenv.format(cwd=b_cwd),
    )

    with gw._profile_runtime_scope(home):
        cfg = tt._get_env_config()
        assert cfg["env_type"] == "local"
        assert cfg["cwd"] == str(b_cwd)
        assert cfg["docker_volumes"] == []
        assert cfg["docker_shared_container_key"] == ""
        # Session-less (cron) work for routed B keys B's own environment, never the launch
        # profile's shared "default" one (which carries A's env and terminal policy).
        assert tt._resolve_container_task_id(None) == f"home:{os.path.realpath(home)}"
        assert gbase._parse_docker_volume_mounts() == []
        assert not any(
            "alpha-shared" in c for c in _docker_sandbox_dir_candidates("agent:bee:x")
        )
        assert file_tools_paths._configured_terminal_cwd() == str(b_cwd)
        assert runtime_cwd.resolve_agent_cwd() == b_cwd
        assert bs_cloud.is_local_backend() is True
        # env_probe bails out with "" for remote backends; a local profile
        # must not be treated as remote just because the launch env is docker.
        assert env_probe._resolve_terminal_backend() == "local"
    assert get_terminal_scope() is None
    # Process env untouched — the launch profile's own turns are unchanged.
    assert os.environ["TERMINAL_DOCKER_VOLUMES"] == _LAUNCH_VOLUMES


def test_profile_omitting_keys_gets_defaults_not_launch_values(tmp_path):
    """#101132/#95470: a docker profile that does NOT set docker_volumes or
    docker_shared_container_key must not inherit the launch profile's."""
    import gateway.run as gw
    import tools.terminal_tool as tt

    home = _profile(tmp_path, "bee", "terminal:\n  backend: docker\n")
    with gw._profile_runtime_scope(home):
        cfg = tt._get_env_config()
        assert cfg["env_type"] == "docker"
        assert cfg["docker_volumes"] == []
        assert cfg["docker_shared_container_key"] == ""
        assert cfg["ssh_host"] == ""
        assert cfg["cwd"] != _LAUNCH_CWD
    assert json.loads(os.environ["TERMINAL_DOCKER_VOLUMES"])  # A unchanged


def test_persistent_docker_routed_profile_keeps_one_container(tmp_path):
    """Persistent Docker is profile-scoped: a routed profile's session-less (cron) work must key the
    SAME container as its session-bound work, and never another profile's."""
    import gateway.run as gw
    import tools.terminal_tool as tt
    from gateway.session_context import clear_session_vars, reset_session_vars, set_session_vars

    docker = "terminal:\n  backend: docker\n  container_persistent: true\n"
    keys = {}
    for name in ("bee", "wasp"):
        home = _profile(tmp_path, name, docker)
        with gw._profile_runtime_scope(home):
            cron_key = tt._resolve_container_task_id(None)
            tokens = set_session_vars(session_key=f"agent:{name}:chat", profile=name)
            try:
                session_key = tt._resolve_container_task_id(None)
            finally:
                clear_session_vars(tokens)
                reset_session_vars()
        assert cron_key == session_key == f"profile:{name}"
        keys[name] = cron_key
    assert keys["bee"] != keys["wasp"]


def test_malformed_profile_config_refuses_execution(tmp_path):
    """Unresolvable policy → refusal scope; terminal_tool refuses instead of
    running under the launch process's ambient policy (fail closed)."""
    from tools.terminal_tool import terminal_tool

    home = _profile(tmp_path, "broken", "terminal: [unclosed\n")
    token = install_profile_terminal_scope(home)
    try:
        assert isinstance(get_terminal_scope(), TerminalPolicyRefusal)
        with pytest.raises(TerminalPolicyUnavailable):
            terminal_env("TERMINAL_ENV")
        result = terminal_tool(command="whoami")
        assert "terminal policy unavailable" in result
    finally:
        reset_terminal_scope(token)


def test_gateway_runtime_scope_resets_on_error(tmp_path):
    import gateway.run as gw

    home = _profile(tmp_path, "qa", "terminal:\n  backend: local\n")
    with pytest.raises(RuntimeError):
        with gw._profile_runtime_scope(home):
            assert terminal_env("TERMINAL_ENV") == "local"
            raise RuntimeError("turn blew up")
    assert get_terminal_scope() is None


def test_tui_and_cron_boundaries_bind_and_reset(tmp_path):
    from tui_gateway import server
    from tools.terminal_scope import install_and_reset_profile_terminal_scope

    home = _profile(tmp_path, "dash", "terminal:\n  backend: local\n")
    with server._session_profile_runtime_scope({"profile_home": str(home)}):
        assert terminal_env("TERMINAL_ENV") == "local"
        assert terminal_env("TERMINAL_SSH_HOST") == ""
    assert get_terminal_scope() is None
    with install_and_reset_profile_terminal_scope(home):  # cron fire helper
        assert terminal_env("TERMINAL_ENV") == "local"
    assert get_terminal_scope() is None


def test_config_list_and_dict_values_are_json_not_repr(tmp_path):
    """config.yaml list/dict terminal keys must be JSON so terminal_tool's
    json.loads path succeeds. str() produces Python repr and drops the tool."""
    from tools.terminal_scope import build_profile_terminal_scope

    home = _profile(
        tmp_path,
        "docker-lists",
        "\n".join(
            [
                "terminal:",
                "  backend: docker",
                "  docker_forward_env:",
                "    - EMAIL_HOME_ADDRESS",
                "  docker_volumes:",
                "    - /tmp/a:/data",
                "  docker_env:",
                "    FOO: bar",
                "  docker_extra_args:",
                "    - --network=host",
                "",
            ]
        ),
    )
    scope = build_profile_terminal_scope(home)
    assert json.loads(scope["TERMINAL_DOCKER_FORWARD_ENV"]) == ["EMAIL_HOME_ADDRESS"]
    assert json.loads(scope["TERMINAL_DOCKER_VOLUMES"]) == ["/tmp/a:/data"]
    assert json.loads(scope["TERMINAL_DOCKER_ENV"]) == {"FOO": "bar"}
    assert json.loads(scope["TERMINAL_DOCKER_EXTRA_ARGS"]) == ["--network=host"]

    import gateway.run as gw
    import tools.terminal_tool as tt

    with gw._profile_runtime_scope(home):
        cfg = tt._get_env_config()
        assert cfg["docker_forward_env"] == ["EMAIL_HOME_ADDRESS"]
        assert cfg["docker_volumes"] == ["/tmp/a:/data"]
        assert cfg["docker_env"] == {"FOO": "bar"}
        assert cfg["docker_extra_args"] == ["--network=host"]


def test_dotenv_json_strings_stay_json_strings(tmp_path):
    """The .env path already stores JSON text; str() must keep that payload."""
    from tools.terminal_scope import build_profile_terminal_scope

    home = _profile(
        tmp_path,
        "dotenv-json",
        "terminal:\n  backend: docker\n",
        'TERMINAL_DOCKER_FORWARD_ENV=["EMAIL_HOME_ADDRESS"]\n'
        'TERMINAL_DOCKER_VOLUMES=["/tmp/a:/data"]\n',
    )
    scope = build_profile_terminal_scope(home)
    assert json.loads(scope["TERMINAL_DOCKER_FORWARD_ENV"]) == ["EMAIL_HOME_ADDRESS"]
    assert json.loads(scope["TERMINAL_DOCKER_VOLUMES"]) == ["/tmp/a:/data"]


def test_launch_turn_binds_terminal_scope_once_multiplexing_is_active(
    tmp_path, monkeypatch
):
    """#107422: after multiplexing starts, launch turns bind the launch home's
    own terminal policy (mirrors ``prompt_turn._prepare_turn_input``'s
    ``elif _served_profile_homes`` branch) so poisoned ambient os.environ is
    never the authority."""
    from tools.terminal_scope import (
        get_terminal_scope,
        install_profile_terminal_scope,
        reset_terminal_scope,
    )

    launch_home = tmp_path / ".hermes"
    launch_home.mkdir()
    (launch_home / "config.yaml").write_text(
        "terminal:\n  backend: local\n", encoding="utf-8"
    )
    monkeypatch.setenv("HERMES_HOME", str(launch_home))
    # Poison ambient the way the pre-fix latch did — launch scope must win.
    monkeypatch.setenv("TERMINAL_ENV", "docker")
    monkeypatch.setenv("TERMINAL_DOCKER_IMAGE", "bee/img:1")

    token = install_profile_terminal_scope(launch_home)
    try:
        assert get_terminal_scope() is not None
        assert terminal_env("TERMINAL_ENV") == "local"
        # DEFAULT_CONFIG may backfill docker_image; the poisoned bee image must not win.
        assert terminal_env("TERMINAL_DOCKER_IMAGE", "") != "bee/img:1"
        assert os.environ["TERMINAL_ENV"] == "docker"
        assert os.environ["TERMINAL_DOCKER_IMAGE"] == "bee/img:1"
    finally:
        reset_terminal_scope(token)
    assert get_terminal_scope() is None


def test_scope_projects_home_mode_into_policy(tmp_path):
    """The canonical TERMINAL_CONFIG_ENV_MAP must include ``home_mode`` so that
    ``build_profile_terminal_scope`` projects the profile's ``home_mode`` into
    the scope. Without the mapping ``TERMINAL_HOME_MODE`` is silently dropped
    while peer keys (backend/ssh_host) project, violating the scope's
    "total policy" contract (#101242).
    """
    from tools.terminal_scope import (
        build_profile_terminal_scope,
        set_terminal_scope,
        reset_terminal_scope,
    )

    home = _profile(
        tmp_path,
        "hmode",
        "terminal:\n  backend: docker\n  home_mode: profile\n"
        "  ssh_host: example.com\n  ssh_port: 2222\n",
    )
    scope = build_profile_terminal_scope(home)
    assert "TERMINAL_HOME_MODE" in scope, (
        "home_mode was dropped from the per-profile scope — "
        "TERMINAL_CONFIG_ENV_MAP is missing the home_mode mapping"
    )
    token = set_terminal_scope(scope)
    try:
        assert terminal_env("TERMINAL_HOME_MODE", "auto") == "profile"
        assert terminal_env("TERMINAL_ENV") == "docker"
        assert terminal_env("TERMINAL_SSH_HOST") == "example.com"
        assert terminal_env("TERMINAL_SSH_PORT", "22") == "2222"
    finally:
        reset_terminal_scope(token)


def test_scope_defaults_home_mode_to_auto_when_profile_omits_it(tmp_path):
    """A profile that omits ``home_mode`` gets the defined default ``auto`` via
    the scope, not the launch process's ambient value."""
    from tools.terminal_scope import (
        build_profile_terminal_scope,
        set_terminal_scope,
        reset_terminal_scope,
    )

    home = _profile(tmp_path, "automode", "terminal:\n  backend: local\n")
    scope = build_profile_terminal_scope(home)
    assert scope.get("TERMINAL_HOME_MODE") == "auto"
    token = set_terminal_scope(scope)
    try:
        assert terminal_env("TERMINAL_HOME_MODE", "profile") == "auto"
    finally:
        reset_terminal_scope(token)


def test_routed_profile_home_mode_profile_drives_subprocess_home(tmp_path, monkeypatch):
    """End-to-end through the gateway boundary.

    A routed profile configured with ``home_mode: profile``, served from a
    launch process whose ambient ``TERMINAL_HOME_MODE=auto``, must resolve
    subprocess ``HOME`` to ``{HERMES_HOME}/home`` via ``get_subprocess_home`` —
    honoring the routed profile's policy, not the launch process's ambient
    value. Both defects (scope projection + consumer scope-read) are required
    for this to pass (#101242).
    """
    import gateway.run as gw
    import hermes_constants

    monkeypatch.setenv("TERMINAL_HOME_MODE", "auto")
    monkeypatch.setattr(hermes_constants, "is_container", lambda: False)

    home = _profile(
        tmp_path, "coder", "terminal:\n  backend: local\n  home_mode: profile\n"
    )
    (home / "home").mkdir()
    real_home = tmp_path / "real-home"
    real_home.mkdir()
    monkeypatch.setenv("HOME", str(real_home))
    monkeypatch.setenv("HERMES_HOME", str(home))

    with gw._profile_runtime_scope(home):
        from hermes_constants import get_subprocess_home

        assert terminal_env("TERMINAL_HOME_MODE", "auto") == "profile"
        assert get_subprocess_home() == str(home / "home")
    from hermes_constants import get_subprocess_home

    assert get_subprocess_home() is None


def test_routed_profile_home_mode_auto_does_not_inherit_launch_profile(tmp_path, monkeypatch):
    """The inverse leak: a routed profile with ``home_mode: auto`` must NOT
    inherit the launch process's ambient ``profile`` mode through the stale
    ``os.environ`` read path. Subprocess ``HOME`` stays the real account HOME.
    """
    import gateway.run as gw
    import hermes_constants

    monkeypatch.setenv("TERMINAL_HOME_MODE", "profile")
    monkeypatch.setattr(hermes_constants, "is_container", lambda: False)

    home = _profile(
        tmp_path, "autohost", "terminal:\n  backend: local\n  home_mode: auto\n"
    )
    (home / "home").mkdir()
    real_home = tmp_path / "real-home"
    real_home.mkdir()
    monkeypatch.setenv("HOME", str(real_home))
    monkeypatch.setenv("HERMES_HOME", str(home))

    with gw._profile_runtime_scope(home):
        from hermes_constants import get_subprocess_home

        assert terminal_env("TERMINAL_HOME_MODE", "profile") == "auto"
        assert get_subprocess_home() is None
    from hermes_constants import get_subprocess_home

    assert get_subprocess_home() == str(home / "home")


def test_routed_a_b_a_build_subprocess_env_respects_home_mode_and_restores_launch_env(
    tmp_path, monkeypatch
):
    """Real-path A->B->A regression through the production child-env builder.

    The launch profile A runs at ``home_mode=auto`` (real HOME preserved). Routed profile B
    declares ``home_mode: profile``; while B's scope is bound, ``build_subprocess_env`` must
    resolve the child ``HOME`` to B's profile home, and after the scope is released the same
    builder must restore A's launch behavior (real HOME) -- neither the scope nor B's policy
    leaks back into the launch env (#101242, root AGENTS.md real-import E2E requirement)."""
    import hermes_constants
    from tools.environments.local import build_subprocess_env

    monkeypatch.setattr(hermes_constants, "is_container", lambda: False)
    real_home = tmp_path / "real-home"
    real_home.mkdir()
    monkeypatch.setenv("HOME", str(real_home))

    # Launch profile A: ambient home_mode=auto, HOME stays real.
    launch_home = tmp_path / "profiles" / "launch"
    launch_home.mkdir(parents=True)
    (launch_home / "config.yaml").write_text("terminal:\n  backend: local\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(launch_home))
    monkeypatch.setenv("TERMINAL_HOME_MODE", "auto")

    def _child_home():
        return build_subprocess_env().get("HOME")

    # A: no scope bound, ambient auto -- real HOME is preserved.
    assert _child_home() == str(real_home)

    # B: routed profile with home_mode=profile (scope + hermes_home override, the real
    # gateway multiplex path installed by _profile_runtime_scope).
    b_home = tmp_path / "profiles" / "routed"
    b_home.mkdir(parents=True)
    (b_home / "home").mkdir()
    (b_home / "config.yaml").write_text(
        "terminal:\n  backend: local\n  home_mode: profile\n", encoding="utf-8"
    )
    import gateway.run as gw

    with gw._profile_runtime_scope(b_home):
        assert terminal_env("TERMINAL_HOME_MODE", "auto") == "profile"
        assert _child_home() == str(b_home / "home")

    # A again: scope released, launch policy restored -- no leak of B's profile home.
    assert get_terminal_scope() is None
    assert _child_home() == str(real_home)


def test_routed_home_mode_from_dotenv_and_yaml_precedence(tmp_path):
    """``terminal.home_mode`` is projected from both the profile ``.env``
    (``TERMINAL_HOME_MODE``) and ``config.yaml`` (``terminal.home_mode``), and
    YAML wins over ``.env`` -- the same precedence every other terminal key uses
    in ``build_profile_terminal_scope`` (#101242)."""
    from tools.terminal_scope import build_profile_terminal_scope

    # .env sets profile, YAML omits home_mode -> .env value projects.
    env_only = _profile(
        tmp_path, "envonly", "terminal:\n  backend: local\n",
        dotenv="TERMINAL_HOME_MODE=profile\n",
    )
    (env_only / "home").mkdir()
    scope_env = build_profile_terminal_scope(env_only)
    assert scope_env.get("TERMINAL_HOME_MODE") == "profile"

    # YAML sets real, .env sets profile -> YAML wins.
    both = _profile(
        tmp_path, "both",
        "terminal:\n  backend: local\n  home_mode: real\n",
        dotenv="TERMINAL_HOME_MODE=profile\n",
    )
    (both / "home").mkdir()
    scope_both = build_profile_terminal_scope(both)
    assert scope_both.get("TERMINAL_HOME_MODE") == "real"

    # YAML sets profile, .env omits -> YAML value projects.
    yaml_only = _profile(
        tmp_path, "yamlonly", "terminal:\n  backend: local\n  home_mode: profile\n"
    )
    (yaml_only / "home").mkdir()
    scope_yaml = build_profile_terminal_scope(yaml_only)
    assert scope_yaml.get("TERMINAL_HOME_MODE") == "profile"
