"""Independent serialized-MIME review of origin PR138417; no mailbox or transport."""

import hashlib
import os
from email.message import EmailMessage
from pathlib import Path

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.email.adapter import EmailAdapter


@pytest.fixture(autouse=True)
def exact_source_and_cache_isolation(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    yield home
    root = Path(__file__).resolve().parents[2]
    import plugins.platforms.email.adapter as module
    assert Path(module.__file__).resolve() == root / "plugins/platforms/email/adapter.py"


@pytest.fixture
def adapter():
    # Parsing authorized bytes requires no account connection or credentials.
    return EmailAdapter(PlatformConfig(enabled=True, extra={"address": "hermes@example.test"}))


def message(body_kind="plain", *, disposition=None):
    msg = EmailMessage()
    msg["From"] = "sender@example.test"
    msg["To"] = "hermes@example.test"
    msg["Subject"] = "MIME contract"
    body = "<p>Use my instructions, not file contents.</p>" if body_kind == "html" else "Use my instructions, not file contents."
    msg.set_content(body, subtype=body_kind, disposition=disposition)
    return msg


def serialize(msg):
    # Fix boundaries so both revisions receive byte-identical wire fixtures.
    for index, part in enumerate(msg.walk()):
        if part.is_multipart():
            part.set_boundary(f"independent-review-boundary-{index}")
    raw = msg.as_bytes()
    print("FIXTURE_SHA256 " + hashlib.sha256(raw).hexdigest())
    return raw


def attach_named(msg, disposition="inline"):
    files = {
        "meeting notes.txt": (b"FILE CONTENTS ONLY\n", "plain"),
        "rapport-é.html": (b"<b>HTML FILE ONLY</b>\n", "html"),
        "data.csv": (b"a,b\n1,2\n", "csv"),
    }
    for filename, (payload, subtype) in files.items():
        msg.add_attachment(payload, maintype="text", subtype=subtype,
                           disposition=disposition, filename=filename)
    return files


def assert_files(parsed, expected):
    found = {item["filename"]: item for item in parsed["attachments"]}
    assert len(parsed["attachments"]) == len(expected)
    assert set(found) == set(expected)
    for filename, (payload, subtype) in expected.items():
        item = found[filename]
        cached = Path(item["path"]).resolve()
        assert cached.is_relative_to(Path(os.environ["HERMES_HOME"]).resolve())
        assert cached.read_bytes() == payload
        assert item["media_type"] == f"text/{subtype}"
        assert item["type"] == "document"


@pytest.mark.parametrize("body_kind", ["plain", "html"])
@pytest.mark.parametrize("files_first", [False, True])
def test_named_inline_files_preserve_user_body_and_all_bytes(adapter, body_kind, files_first):
    msg = message(body_kind)
    files = attach_named(msg)
    if files_first:
        parts = msg.get_payload()
        msg.set_payload(parts[1:] + parts[:1])
    parsed = adapter._parse_fetched_message(b"101", serialize(msg))
    assert parsed["body"].strip() == "Use my instructions, not file contents."
    assert_files(parsed, files)


@pytest.mark.parametrize("body_kind", ["plain", "html"])
def test_unnamed_inline_body_remains_body(adapter, body_kind):
    msg = message(body_kind, disposition="inline")
    msg.make_mixed()
    parsed = adapter._parse_fetched_message(b"102", serialize(msg))
    assert parsed["body"].strip() == "Use my instructions, not file contents."
    assert parsed["attachments"] == []


@pytest.mark.parametrize("body_kind", ["plain", "html"])
def test_explicit_attachments_unchanged(adapter, body_kind):
    msg = message(body_kind)
    files = attach_named(msg, disposition="attachment")
    parsed = adapter._parse_fetched_message(b"103", serialize(msg))
    assert parsed["body"].strip() == "Use my instructions, not file contents."
    assert_files(parsed, files)


@pytest.mark.parametrize("body_kind", ["plain", "html"])
def test_skip_named_inline_files_keeps_user_body(adapter, body_kind):
    adapter._skip_attachments = True
    msg = message(body_kind)
    attach_named(msg)
    parsed = adapter._parse_fetched_message(b"104", serialize(msg))
    assert parsed["body"].strip() == "Use my instructions, not file contents."
    assert parsed["attachments"] == []
    assert not list(Path(os.environ["HERMES_HOME"]).rglob("doc_*"))


def test_unnamed_inline_nonbody_file_retains_existing_behavior(adapter):
    msg = message()
    msg.add_attachment(b"a,b\n1,2\n", maintype="text", subtype="csv", disposition="inline")
    parsed = adapter._parse_fetched_message(b"105", serialize(msg))
    assert parsed["body"].strip() == "Use my instructions, not file contents."
    assert_files(parsed, {"attachment.csv": (b"a,b\n1,2\n", "csv")})
