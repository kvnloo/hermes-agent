"""MemoryManager strips slash-skill scaffolding for every provider.

When a user invokes a /skill or /bundle, Hermes expands the turn into a
model-facing message that embeds the full skill body. Feeding that verbatim to
memory providers pollutes their stores/embeddings with prompt scaffolding
instead of what the user actually asked. The strip lives once in MemoryManager
so it covers the whole provider fan-out — not per backend.

See: agent.skill_commands.extract_user_instruction_from_skill_message and
MemoryManager._strip_skill_scaffolding.
"""

from agent.memory_manager import MemoryManager
from agent.memory_provider import MemoryProvider
from agent.skill_commands import extract_user_instruction_from_skill_message, _SKILL_DIR_NOTE_END


_SINGLE_SKILL_TURN = (
    '[IMPORTANT: The user has invoked the "skill-creator" skill, indicating they want '
    "you to follow its instructions. The full skill content is loaded below.]\n\n"
    "# Skill Creator\n\n"
    "Large skill body that must not be searched or embedded.\n\n"
    "The user has provided the following instruction alongside the skill invocation: "
    "make a skill for release triage"
)

_BUNDLE_TURN = (
    '[IMPORTANT: The user has invoked the "backend-dev" skill bundle, '
    "loading 2 skills together. Treat every skill below as active guidance for this turn.]\n\n"
    "Bundle: backend-dev\n"
    "Skills loaded: test-driven-development, code-review\n\n"
    "User instruction: fix the failing retrieval test\n\n"
    '[Loaded as part of the "backend-dev" skill bundle.]\n\n'
    "Large bundled skill body that must not be searched or embedded."
)

_BARE_SKILL_TURN = (
    '[IMPORTANT: The user has invoked the "skill-creator" skill, indicating they want '
    "you to follow its instructions. The full skill content is loaded below.]\n\n"
    "# Skill Creator\n\n"
    "Large skill body, no user instruction."
)


class _RecordingProvider(MemoryProvider):
    """Captures exactly what user text each fan-out method received."""

    _name = "recording"

    def __init__(self):
        self.prefetched = []
        self.queued = []
        self.synced = []

    @property
    def name(self) -> str:
        return self._name

    def initialize(self, session_id: str = "", **kwargs) -> None:
        pass

    def is_available(self) -> bool:
        return True

    def system_prompt_block(self) -> str:
        return ""

    def prefetch(self, query, *, session_id: str = "") -> str:
        self.prefetched.append(query)
        return ""

    def queue_prefetch(self, query, *, session_id: str = "") -> None:
        self.queued.append(query)

    def sync_turn(self, user_content, assistant_content, *, session_id: str = "", messages=None) -> None:
        self.synced.append(user_content)

    def get_tool_schemas(self):
        return []


def _manager_with_recorder():
    mgr = MemoryManager()
    provider = _RecordingProvider()
    mgr.add_provider(provider)
    return mgr, provider


class TestExtractUserInstruction:
    def test_non_string_returns_none(self):
        assert extract_user_instruction_from_skill_message(None) is None
        assert extract_user_instruction_from_skill_message(123) is None
        assert extract_user_instruction_from_skill_message([{"text": "hi"}]) is None



    def test_bundle_with_instruction(self):
        assert (
            extract_user_instruction_from_skill_message(_BUNDLE_TURN)
            == "fix the failing retrieval test"
        )




class TestMemoryManagerStripsScaffolding:

    def test_prefetch_all_skips_bare_skill(self):
        mgr, provider = _manager_with_recorder()
        result = mgr.prefetch_all(_BARE_SKILL_TURN)
        assert result == ""
        assert provider.prefetched == []

    def test_queue_prefetch_all_strips_bundle(self):
        mgr, provider = _manager_with_recorder()
        mgr.queue_prefetch_all(_BUNDLE_TURN)
        mgr.flush_pending(timeout=5.0)
        assert provider.queued == ["fix the failing retrieval test"]

    def test_auto_loaded_skills_keep_only_typed_text(self):
        skill_footer = f"[Skill directory: /skills/example]\nResolve relative paths, {_SKILL_DIR_NOTE_END}"
        turn = (
            '[IMPORTANT: The "example" skill is auto-loaded. Follow its instructions for this session.]\n'
            "The skill body contains the terminal tool absolute path footer as quoted text.\n"
            + skill_footer + "\n\n"
            + '[IMPORTANT: The "another" skill is auto-loaded. Follow its instructions for this session.]\n'
            "Second skill body.\n[Skill directory: /skills/another]\nResolve paths, " + _SKILL_DIR_NOTE_END
            + "\n\nnot remember anything i tell you"
        )
        mgr, provider = _manager_with_recorder()
        mgr.prefetch_all(turn)
        mgr.queue_prefetch_all(turn)
        mgr.sync_all(turn, "I will investigate.")
        mgr.flush_pending(timeout=5.0)
        expected = ["not remember anything i tell you"]
        assert provider.prefetched == expected
        assert provider.queued == expected
        assert provider.synced == expected

    def test_gateway_auto_load_sync_preserves_user_text_and_skips_bare(self, tmp_path, monkeypatch):
        from types import SimpleNamespace

        from agent import skill_commands
        from gateway.run_turn_prepare import GatewayTurnPrepareMixin

        skill_dir = tmp_path / "example"
        skill_dir.mkdir()
        loaded = ({"name": "example", "content": "# Injected skill\nNot user speech."},
                  skill_dir, "example")
        monkeypatch.setattr(
            skill_commands, "_load_skill_payload",
            lambda name, task_id=None: loaded,
        )
        # The footer sentence can appear in ordinary user text, and whitespace
        # may be significant (e.g. pasted Markdown or code).
        for typed_text in (
            f"  keep this formatting:\n\n{_SKILL_DIR_NOTE_END}\n  second line  ",
            "",
        ):
            event = SimpleNamespace(text=typed_text)
            GatewayTurnPrepareMixin._hmwa_auto_load_skills(
                None, event, "example", "test-session", "test-session",
            )
            mgr, provider = _manager_with_recorder()
            mgr.prefetch_all(event.text)
            mgr.queue_prefetch_all(event.text)
            mgr.sync_all(event.text, "Done.")
            mgr.flush_pending(timeout=5.0)
            expected = [typed_text] if typed_text else []
            assert provider.prefetched == expected
            assert provider.queued == expected
            assert provider.synced == expected

        # A normal pasted quote may start like a scaffold without being one.
        quoted = '[IMPORTANT: The "note" is simply a quoted line'
        assert skill_commands.extract_user_instruction_from_skill_message(quoted) == quoted
        mgr, provider = _manager_with_recorder()
        mgr.sync_all(quoted, "Done.")
        mgr.flush_pending(timeout=5.0)
        assert provider.synced == [quoted]

    def test_sync_all_skips_bare_skill(self):
        mgr, provider = _manager_with_recorder()
        mgr.sync_all(_BARE_SKILL_TURN, "Done.")
        mgr.flush_pending(timeout=5.0)
        assert provider.synced == []

