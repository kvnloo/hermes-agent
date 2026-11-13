"""Profile-scoped voice-output encoding metadata, shared by tool and gateway TTS."""


def prefers_opus_voice_output(platform: str) -> bool:
    """Read only the destination registration, without constructing an adapter.

    Before plugin discovery, bundled declarations preserve the historical defaults
    without importing adapter SDKs. A registered entry, including False, wins.
    """
    from gateway.platform_registry import platform_registry

    name = (platform or "").strip().lower()
    entry = platform_registry.get(name)
    if entry is not None:
        return entry.voice_output_opus
    from gateway.platform_env import bundled_sibling
    declaration = bundled_sibling(name)
    return bool(getattr(declaration, "VOICE_OUTPUT_OPUS", False))
