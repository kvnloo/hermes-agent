"""The normal cache wrapper retains the owner's image filename contract."""

from pathlib import Path
import re

import pytest

from gateway.platforms import base


@pytest.mark.parametrize("filename", ["Screenshot 2026-09-15 at 11.12.26.png", ""])
def test_cache_media_bytes_preserves_image_filename(tmp_path, monkeypatch, filename):
    monkeypatch.setattr(base, "IMAGE_CACHE_DIR", tmp_path)
    image = b"\x89PNG\r\n\x1a\n" + b"x" * 64

    cached = base.cache_media_bytes(image, filename=filename, mime_type="image/png")

    assert cached is not None
    assert cached.kind == "image"
    assert cached.media_type == "image/png"
    path = Path(cached.path)
    assert path.read_bytes() == image
    suffix = "_Screenshot-2026-09-15-at-11.12.26" if filename else ""
    assert re.fullmatch(r"img_[0-9a-f]{12}" + re.escape(suffix) + r"\.png", path.name)
