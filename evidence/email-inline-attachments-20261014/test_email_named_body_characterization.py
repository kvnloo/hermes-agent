"""Observation only: RFC2183 permits filename on a normally displayed inline part."""

import hashlib
import json
import os
from email.message import EmailMessage
from pathlib import Path

from gateway.config import PlatformConfig
from plugins.platforms.email.adapter import EmailAdapter


def test_record_named_inline_body(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    adapter = EmailAdapter(PlatformConfig(enabled=True, extra={"address": "hermes@example.test"}))
    msg = EmailMessage()
    msg["From"] = "sender@example.test"
    msg["Subject"] = "Named inline main text"
    msg.set_content("Please calculate the total from the attached data.\n", disposition="inline", filename="message.txt")
    msg.add_attachment(b"price\n12\n", maintype="text", subtype="csv", disposition="attachment", filename="data.csv")
    msg.set_boundary("named-inline-body-characterization")
    raw = msg.as_bytes()
    (Path(os.environ["HOME"]) / "named-inline-body.eml").write_bytes(raw)
    parsed = adapter._parse_fetched_message(b"106", raw)
    output = {
        "classification": "observation-only, no product-contract assertion",
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "body": parsed["body"],
        "attachments": [{"filename": item["filename"], "media_type": item["media_type"],
                         "payload": Path(item["path"]).read_text()} for item in parsed["attachments"]],
    }
    (Path(os.environ["HOME"]) / "named-inline-body-observation.json").write_text(json.dumps(output, indent=2) + "\n")
