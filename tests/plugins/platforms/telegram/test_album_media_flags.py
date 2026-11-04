"""Album batching preserves per-attachment text-inlining semantics at admission."""
from types import SimpleNamespace

import pytest

from gateway.platforms.event import MessageEvent
from gateway.session_envelope import _media_clause
from plugins.platforms.telegram.adapter import TelegramAdapter


def test_six_document_album_passes_native_media_validation(tmp_path):
    adapter = SimpleNamespace(_merge_caption=TelegramAdapter._merge_caption)
    pending = {}
    for index in range(6):
        event = MessageEvent(text="", media_urls=[str(tmp_path / f"invoice-{index}.pdf")],
                             media_types=["application/pdf"], media_text_inlined=[False])
        TelegramAdapter._merge_into_pending(adapter, pending, "album", event)
    album = pending["album"]
    assert _media_clause(album) is None
    assert album.media_text_inlined == [False] * 6
    assert album.media_urls == [str(tmp_path / f"invoice-{index}.pdf") for index in range(6)]


@pytest.mark.parametrize("flags", [([], [True]), ([False], []), ([True], [False]), ([False], [True]), ([], [])])
def test_album_preserves_legacy_and_explicit_inlining_flags(flags, tmp_path):
    adapter = SimpleNamespace(_merge_caption=TelegramAdapter._merge_caption)
    pending = {}
    for index, inlined in enumerate(flags):
        event = MessageEvent(text=f"caption-{index}", media_urls=[str(tmp_path / f"file-{index}")],
                             media_types=["text/plain"], media_text_inlined=inlined,
                             media_filenames=[f"file-{index}"])
        TelegramAdapter._merge_into_pending(adapter, pending, "album", event)
    album = pending["album"]
    assert _media_clause(album) is None
    assert album.media_text_inlined == [value for flag in flags for value in (flag or [None])]
    assert album.media_filenames == ["file-0", "file-1"]
    assert album.text == "caption-0\n\ncaption-1"


def test_zip_and_two_inlined_markdown_documents_keep_their_flags(tmp_path):
    adapter = SimpleNamespace(_merge_caption=TelegramAdapter._merge_caption)
    pending = {}
    names = ["archive.zip", "first.md", "second.md"]
    paths = [str(tmp_path / name) for name in names]
    types = ["application/zip", "text/markdown", "text/markdown"]
    for path, name, mime, inlined in zip(paths, names, types, [False, True, True]):
        event = MessageEvent(text="", media_urls=[path], media_types=[mime],
                             media_filenames=[name], media_text_inlined=[inlined])
        TelegramAdapter._merge_into_pending(adapter, pending, "album", event)
    album = pending["album"]
    assert _media_clause(album) is None
    assert album.media_urls == paths
    assert album.media_types == types
    assert album.media_filenames == names
    assert album.media_text_inlined == [False, True, True]


def test_photo_then_named_document_keeps_parallel_metadata(tmp_path):
    """A nameless photo must not shift a following document's per-file metadata."""
    adapter = SimpleNamespace(_merge_caption=TelegramAdapter._merge_caption)
    pending = {}
    photo_path = str(tmp_path / "photo.jpg")
    document_path = str(tmp_path / "report.pdf")
    photo = MessageEvent(text="", media_urls=[photo_path], media_types=["image/jpeg"])
    document = MessageEvent(text="", media_urls=[document_path],
                            media_types=["application/pdf"], media_text_inlined=[False],
                            media_filenames=["report.pdf"])

    TelegramAdapter._merge_into_pending(adapter, pending, "album", photo)
    TelegramAdapter._merge_into_pending(adapter, pending, "album", document)

    album = pending["album"]
    assert album.media_urls == [photo_path, document_path]
    assert album.media_types == ["image/jpeg", "application/pdf"]
    assert album.media_text_inlined == [None, False]
    assert album.media_filenames == ["", "report.pdf"]
    assert _media_clause(album) is None
