"""Names reserved for native built-in TTS handlers.

The single owner shared by :mod:`agent.tts_registry` (rejects colliding plugin
names) and :mod:`tools.tts_command_provider` (never treats these as
``tts.providers.<name>`` entries). Kept dependency-free so the registry can
import it without pulling in the TTS tool, which would be a circular import.
"""

BUILTIN_TTS_PROVIDERS = frozenset({
    "edge", "elevenlabs", "openai", "minimax", "xai", "mistral", "gemini",
    "neutts", "kittentts", "piper", "deepinfra"})
