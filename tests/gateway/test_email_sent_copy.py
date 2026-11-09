"""Sent-folder regression for iam-kristie's NousResearch/hermes-agent#151663."""

import os
from email import message_from_bytes
from unittest.mock import MagicMock, patch

from gateway.config import PlatformConfig
from plugins.platforms.email.adapter import EmailAdapter


def _adapter(**extra):
    with patch.dict(os.environ, {
        "EMAIL_ADDRESS": "hermes@test.com",
        "EMAIL_PASSWORD": "secret",
        "EMAIL_IMAP_HOST": "imap.test.com",
        "EMAIL_SMTP_HOST": "smtp.test.com",
    }):
        return EmailAdapter(PlatformConfig(enabled=True, extra=extra))


def _servers():
    smtp, imap = MagicMock(), MagicMock()
    imap.capabilities = ()
    imap.list.return_value = ("OK", [b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Sent Mail"'])
    imap.select.return_value = ("OK", [b"0"])
    imap.search.return_value = ("OK", [b""])
    imap.append.return_value = ("OK", [b"saved"])
    return smtp, imap


def test_sent_copy_after_smtp():
    adapter = _adapter()
    smtp, imap = _servers()
    order = []
    smtp.send_message.side_effect = lambda msg: order.append("smtp")
    imap.append.side_effect = lambda *args: (order.append("append") or ("OK", [b"saved"]))
    with patch.object(adapter, "_connect_smtp", return_value=smtp), \
         patch.object(adapter, "_connect_imap", return_value=imap):
        message_id = adapter._send_email("reader@test.com", "hello")
    assert order == ["smtp", "append"]
    imap.select.assert_called_once_with('"[Gmail]/Sent Mail"', readonly=True)
    imap.search.assert_called_once_with(None, "HEADER", "Message-ID", message_id)
    mailbox, flags, internal_date, raw = imap.append.call_args.args
    assert mailbox == '"[Gmail]/Sent Mail"'
    assert flags == r"(\Seen)"
    assert internal_date is None
    sent = message_from_bytes(raw)
    assert sent["Message-ID"] == message_id
    assert sent["To"] == "reader@test.com"
    assert sent.get_payload(0).get_payload(decode=True).decode("utf-8") == "hello"


def test_sent_copy_skips_provider_autofile():
    adapter = _adapter()
    smtp, imap = _servers()
    imap.search.return_value = ("OK", [b"123"])
    with patch.object(adapter, "_connect_smtp", return_value=smtp), \
         patch.object(adapter, "_connect_imap", return_value=imap):
        adapter._send_email("reader@test.com", "hello")
    smtp.send_message.assert_called_once()
    imap.append.assert_not_called()


def test_sent_append_failure_never_retries_smtp(caplog):
    adapter = _adapter()
    smtp, imap = _servers()
    imap.append.return_value = ("NO", [b"read only"])
    with patch.object(adapter, "_connect_smtp", return_value=smtp), \
         patch.object(adapter, "_connect_imap", return_value=imap):
        assert adapter._send_email("reader@test.com", "hello").startswith("<hermes-")
    smtp.send_message.assert_called_once()
    assert "SMTP delivered, but Sent copy" in caplog.text


def test_no_copy_on_smtp_failure_or_opt_out():
    adapter = _adapter()
    smtp, imap = _servers()
    smtp.send_message.side_effect = RuntimeError("SMTP refused")
    with patch.object(adapter, "_connect_smtp", return_value=smtp), \
         patch.object(adapter, "_connect_imap", return_value=imap):
        try:
            adapter._send_email("reader@test.com", "hello")
        except RuntimeError:
            pass
        else:
            assert False, "SMTP failure must propagate"
    imap.append.assert_not_called()

    adapter = _adapter(save_sent=False)
    smtp, imap = _servers()
    with patch.object(adapter, "_connect_smtp", return_value=smtp), \
         patch.object(adapter, "_connect_imap", return_value=imap):
        adapter._send_email("reader@test.com", "hello")
    smtp.send_message.assert_called_once()
    imap.append.assert_not_called()


def test_attachment_uses_same_sent_copy_path(tmp_path):
    attachment = tmp_path / "note.txt"
    attachment.write_text("attached")
    adapter = _adapter()
    smtp, imap = _servers()
    with patch.object(adapter, "_connect_smtp", return_value=smtp), \
         patch.object(adapter, "_connect_imap", return_value=imap):
        adapter._send_email_with_attachment("reader@test.com", "file", str(attachment))
    raw = imap.append.call_args.args[3]
    saved = message_from_bytes(raw)
    assert any(part.get_filename() == "note.txt" for part in saved.walk())
