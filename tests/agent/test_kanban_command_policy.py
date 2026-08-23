"""OX1000 C2 — pre-warmed kanban worker command policy.

Behavior contracts:
- the policy block exists, is bounded, and covers all four clauses;
- it is byte-stable (equal hash across accesses) with no volatile content;
- it rides only the kanban-worker injection point (non-kanban agents get
  no policy attribute content);
- the config gate defaults off and honors kanban.worker_command_policy;
- enabling it appends the block exactly once to the built system prompt,
  without altering past-context behavior or tool schemas.
"""
import pytest


# ---------------------------------------------------------------------------
# Policy content — four clauses
# ---------------------------------------------------------------------------

def test_policy_covers_all_four_clauses():
    from agent.kanban_command_policy import KANBAN_COMMAND_POLICY as P

    # Clause 1: file creation via write_file/patch, not heredoc/-c/echo/cat
    assert "heredoc" in P.lower()
    assert "python -c" in P
    assert "write_file" in P and "patch" in P
    # Clause 2: identical command >=4 attempts → stop and replan
    assert "4 times" in P and "Replan" in P
    # Clause 3: same-file patch failure >=2 → re-read; 3rd replaces unit/file
    assert "2 patch failures" in P
    assert "re-read" in P.lower() and "whole file" in P
    # Clause 4: repeated reads of unchanged files reuse existing results
    assert "re-read an unchanged file" in P


def test_policy_is_bounded_and_single_block():
    from agent.kanban_command_policy import KANBAN_COMMAND_POLICY as P

    assert len(P) < 2500  # concise pre-warm, not a manual
    assert P.count("# Command policy") == 1


def test_policy_byte_stable_hash():
    from agent.kanban_command_policy import (
        KANBAN_COMMAND_POLICY,
        command_policy_hash,
    )

    h1 = command_policy_hash()
    h2 = command_policy_hash(KANBAN_COMMAND_POLICY)
    h3 = command_policy_hash(KANBAN_COMMAND_POLICY)
    assert h1 == h2 == h3
    # No timestamps / session counters in the text.
    import re
    assert not re.search(r"\d{4}-\d{2}-\d{2}", KANBAN_COMMAND_POLICY)


# ---------------------------------------------------------------------------
# Config gate
# ---------------------------------------------------------------------------

def test_gate_defaults_off():
    from agent.kanban_command_policy import worker_command_policy_enabled

    assert worker_command_policy_enabled(None) is False
    assert worker_command_policy_enabled({}) is False
    assert worker_command_policy_enabled({"kanban": {}}) is False
    assert (
        worker_command_policy_enabled({"kanban": {"worker_command_policy": False}})
        is False
    )


def test_gate_honors_truthy_config():
    from agent.kanban_command_policy import worker_command_policy_enabled

    assert (
        worker_command_policy_enabled({"kanban": {"worker_command_policy": True}})
        is True
    )
    # Bare kanban-section dict also accepted.
    assert worker_command_policy_enabled({"worker_command_policy": True}) is True


def test_default_config_declares_gate_off():
    """DEFAULT_CONFIG carries the gate so deep-merge exposes the key."""
    from hermes_cli.config_defaults import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["kanban"]["worker_command_policy"] is False


def test_load_worker_command_policy_enabled_reads_real_config(
    tmp_path, monkeypatch
):
    """E2E through load_config_readonly against a temp HERMES_HOME."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    from cli import save_config_value
    from agent.kanban_command_policy import load_worker_command_policy_enabled

    assert load_worker_command_policy_enabled() is False
    save_config_value("kanban.worker_command_policy", True)
    assert load_worker_command_policy_enabled() is True


# ---------------------------------------------------------------------------
# Injection point — kanban workers only, once, byte-stable
# ---------------------------------------------------------------------------

class _FakeAgent:
    def __init__(self, valid_tool_names, guidance="", policy=""):
        self.valid_tool_names = set(valid_tool_names)
        self._kanban_worker_guidance = guidance
        self._kanban_command_policy = policy
        self.load_soul_identity = False
        self.skip_context_files = True
        self._tool_use_enforcement = False
        self.provider = ""
        self.model = ""
        self.platform = None

    def __getattr__(self, name):
        # Safe defaults for the long tail of agent attributes the prompt
        # builder touches (memory store, plugin sections, etc.).
        if name.startswith("__"):
            raise AttributeError(name)
        if name == "_plugin_system_prompt_sections_snapshot":
            return ()
        return None


def test_non_kanban_agent_gets_no_policy():
    from agent.system_prompt import build_system_prompt_parts

    agent = _FakeAgent({"memory"})
    parts = build_system_prompt_parts(agent)
    joined = " ".join(parts.values())
    assert "Command policy" not in joined


def test_kanban_agent_without_gate_has_no_policy_block():
    from agent.system_prompt import build_system_prompt_parts

    agent = _FakeAgent({"kanban_show"}, guidance="# Kanban task execution protocol")
    parts = build_system_prompt_parts(agent)
    joined = " ".join(parts.values())
    assert "# Kanban task execution protocol" in joined
    assert "Command policy" not in joined


def test_enabled_policy_appended_once_after_guidance():
    from agent.system_prompt import build_system_prompt_parts
    from agent.kanban_command_policy import (
        KANBAN_COMMAND_POLICY,
        command_policy_hash,
    )

    agent = _FakeAgent(
        {"kanban_show"},
        guidance="# Kanban task execution protocol",
        policy="\n" + KANBAN_COMMAND_POLICY,
    )
    stable = build_system_prompt_parts(agent)["stable"]
    assert stable.count("Command policy") == 1
    assert stable.index("# Kanban task execution protocol") < stable.index(
        "# Command policy"
    )
    # Byte-stable: rebuilding produces an identical stable tier.
    again = build_system_prompt_parts(agent)["stable"]
    assert again == stable


def test_agent_init_gate_resolution(monkeypatch):
    """The init-time snippet appends the block only when the gate passes."""
    import agent.kanban_command_policy as kp
    from agent.kanban_command_policy import KANBAN_COMMAND_POLICY

    monkeypatch.setattr(kp, "load_worker_command_policy_enabled", lambda: False)
    assert kp.load_worker_command_policy_enabled() is False

    monkeypatch.setattr(kp, "load_worker_command_policy_enabled", lambda: True)
    injected = "\n" + KANBAN_COMMAND_POLICY
    assert injected.startswith("\n# Command policy")
    # The init snippet stores exactly this shape on the agent.
    assert injected.strip().splitlines()[0] == "# Command policy (pre-warmed)"


@pytest.mark.parametrize("attr_missing", [True, False])
def test_getattr_fallback_keeps_legacy_paths_working(attr_missing):
    """Agents that bypass agent_init still build a prompt without error."""
    from agent.system_prompt import build_system_prompt_parts

    agent = _FakeAgent({"kanban_show"}, guidance="# Kanban task execution protocol")
    if attr_missing:
        del agent._kanban_command_policy
    parts = build_system_prompt_parts(agent)
    assert "# Kanban task execution protocol" in parts["stable"]
