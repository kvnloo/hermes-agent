"""Local Whisper cache-miss regression for pre-imported Hugging Face Hub settings."""

import os
import sys
from types import ModuleType
from unittest.mock import patch

from tools.transcription_local import _create_whisper_model


def test_cache_miss_applies_timeout_overrides_to_imported_hub(monkeypatch):
    """A Hub imported before STT must see explicit and fallback timeouts at retry."""
    hub = ModuleType("huggingface_hub")
    hub.__path__ = []
    constants = ModuleType("huggingface_hub.constants")
    constants.HF_HUB_ETAG_TIMEOUT = 10
    constants.HF_HUB_DOWNLOAD_TIMEOUT = 10
    errors = ModuleType("huggingface_hub.errors")

    class LocalEntryNotFoundError(OSError):
        pass

    errors.LocalEntryNotFoundError = LocalEntryNotFoundError
    hub.constants = constants
    hub.errors = errors

    monkeypatch.setenv("HF_HUB_ETAG_TIMEOUT", " 20 ")
    monkeypatch.setenv("HF_HUB_DOWNLOAD_TIMEOUT", "0")

    online_model = object()
    attempts = []

    def fake_model(name, *, local_files_only, device, compute_type):
        attempts.append(local_files_only)
        assert (name, device, compute_type) == ("base", "cpu", "int8")
        if local_files_only:
            raise LocalEntryNotFoundError("snapshot not cached")

        assert os.environ["HF_HUB_ETAG_TIMEOUT"] == "20"
        assert os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] == "45"
        assert constants.HF_HUB_ETAG_TIMEOUT == 20
        assert constants.HF_HUB_DOWNLOAD_TIMEOUT == 45
        return online_model

    whisper = ModuleType("faster_whisper")
    whisper.WhisperModel = fake_model

    with patch.dict(sys.modules, {
        "huggingface_hub": hub,
        "huggingface_hub.constants": constants,
        "huggingface_hub.errors": errors,
        "faster_whisper": whisper,
    }):
        assert _create_whisper_model("base", device="cpu", compute_type="int8") is online_model

    assert attempts == [True, False]
