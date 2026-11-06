"""Tests for the WeCom callback-mode adapter."""

import asyncio
import hmac
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.wecom import callback_adapter as _callback_mod
from plugins.platforms.wecom.callback_adapter import WecomCallbackAdapter
from plugins.platforms.wecom.wecom_crypto import WXBizMsgCrypt

# ``_build_event`` parses inbound XML with defusedxml, which ships with the
# ``wecom`` extra (and transitively with ``youtube``, hence ``[all]`` in CI). A
# dev venv without either extra cannot exercise the parser; the crypto,
# routing, token-refresh and body-size tests below do not touch it and run
# regardless. This is a dependency gate, not a host-OS gate.
requires_defusedxml = pytest.mark.skipif(
    not _callback_mod.DEFUSEDXML_AVAILABLE,
    reason="defusedxml not installed (uv sync --extra wecom)",
)


def _app(name="test-app", corp_id="ww1234567890", agent_id="1000002"):
    return {
        "name": name,
        "corp_id": corp_id,
        "corp_secret": "test-secret",
        "agent_id": agent_id,
        "token": "test-callback-token",
        "encoding_aes_key": "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG",
    }


def _config(apps=None):
    return PlatformConfig(
        enabled=True,
        extra={"mode": "callback", "host": "127.0.0.1", "port": 0, "apps": apps or [_app()]},
    )


class TestWecomCrypto:
    def test_roundtrip_encrypt_decrypt(self):
        app = _app()
        crypt = WXBizMsgCrypt(app["token"], app["encoding_aes_key"], app["corp_id"])
        encrypted_xml = crypt.encrypt(
            "<xml><Content>hello</Content></xml>", nonce="nonce123", timestamp="123456",
        )
        root = ET.fromstring(encrypted_xml)
        decrypted = crypt.decrypt(
            root.findtext("MsgSignature", default=""),
            root.findtext("TimeStamp", default=""),
            root.findtext("Nonce", default=""),
            root.findtext("Encrypt", default=""),
        )
        assert b"<Content>hello</Content>" in decrypted


class TestWecomSignatureVerification:
    """Signature verification uses ``hmac.compare_digest`` (constant-time).

    The inbound ``msg_signature`` is an attacker-controlled query parameter on
    a public, unauthenticated endpoint, so it must be compared with
    ``hmac.compare_digest`` rather than plain ``!=`` — the repo-wide convention
    for request-path signature verifiers.
    """

    @staticmethod
    def _encrypt_and_parse(crypt, plaintext="<xml><Content>hello</Content></xml>"):
        encrypted_xml = crypt.encrypt(plaintext, nonce="nonce123", timestamp="123456")
        root = ET.fromstring(encrypted_xml)
        return {
            "msg_signature": root.findtext("MsgSignature", default=""),
            "timestamp": root.findtext("TimeStamp", default=""),
            "nonce": root.findtext("Nonce", default=""),
            "encrypt": root.findtext("Encrypt", default=""),
        }

    def _crypt(self):
        app = _app()
        return WXBizMsgCrypt(app["token"], app["encoding_aes_key"], app["corp_id"])

    def test_valid_signature_requires_constant_time_bytes_comparison(self, monkeypatch):
        """Valid signatures must verify via ``hmac.compare_digest`` on encoded bytes.

        The inbound ``msg_signature`` is an attacker-controlled query parameter on
        a public, unauthenticated endpoint, so the verifier must compare the
        expected signature to it with ``hmac.compare_digest`` on ``bytes``
        operands — never a plain string ``!=`` (timing oracle). This is the
        security invariant: a successful verification has to route through
        ``hmac.compare_digest`` with two ``bytes`` arguments. On the insecure
        base (string ``!=``) ``hmac.compare_digest`` is never called, so the
        spy records zero calls and this assertion fails red.
        """
        crypt = self._crypt()
        parts = self._encrypt_and_parse(crypt)

        calls = []
        real_compare_digest = hmac.compare_digest

        def _spy(left, right):
            calls.append((left, right))
            return real_compare_digest(left, right)

        monkeypatch.setattr(hmac, "compare_digest", _spy)

        decrypted = crypt.decrypt(
            parts["msg_signature"], parts["timestamp"], parts["nonce"], parts["encrypt"]
        )

        assert b"<Content>hello</Content>" in decrypted
        assert len(calls) == 1, "verification must go through hmac.compare_digest"
        left, right = calls[0]
        assert isinstance(left, bytes) and isinstance(right, bytes), (
            "compare_digest must receive bytes operands, not str"
        )
        assert left == right, "a valid signature must compare equal"


class TestWecomCallbackEventConstruction:
    @requires_defusedxml
    def test_build_event_extracts_text_message(self):
        adapter = WecomCallbackAdapter(_config())
        xml_text = """
        <xml>
          <ToUserName>ww1234567890</ToUserName>
          <FromUserName>zhangsan</FromUserName>
          <CreateTime>1710000000</CreateTime>
          <MsgType>text</MsgType>
          <Content>\u4f60\u597d</Content>
          <MsgId>123456789</MsgId>
        </xml>
        """
        event = adapter._build_event(_app(), xml_text)
        assert event is not None
        assert event.source is not None
        assert event.source.user_id == "zhangsan"
        assert event.source.chat_id == "ww1234567890:zhangsan"
        assert event.message_id == "123456789"
        assert event.text == "\u4f60\u597d"


class TestWecomCallbackRouting:

    @pytest.mark.asyncio
    async def test_send_selects_correct_app_for_scoped_chat_id(self):
        apps = [
            _app(name="corp-a", corp_id="corpA", agent_id="1001"),
            _app(name="corp-b", corp_id="corpB", agent_id="2002"),
        ]
        adapter = WecomCallbackAdapter(_config(apps=apps))
        adapter._user_app_map["corpB:alice"] = "corp-b"
        adapter._access_tokens["corp-b"] = {"token": "tok-b", "expires_at": 9999999999}

        calls = {}

        class FakeResponse:
            def json(self):
                return {"errcode": 0, "msgid": "ok1"}

        class FakeClient:
            async def post(self, url, json):
                calls["url"] = url
                calls["json"] = json
                return FakeResponse()

        adapter._http_client = FakeClient()
        result = await adapter.send("corpB:alice", "hello")

        assert result.success is True
        assert calls["json"]["touser"] == "alice"
        assert calls["json"]["agentid"] == 2002
        assert "tok-b" in calls["url"]


class TestWecomCallbackSendTokenRefresh:
    @pytest.mark.asyncio
    async def test_send_retries_with_fresh_token_on_errcode_40001(self):
        """errcode=40001 must evict the cached token, refresh, and retry once."""
        adapter = WecomCallbackAdapter(_config())
        adapter._access_tokens["test-app"] = {"token": "stale", "expires_at": 9999999999}
        adapter._user_app_map["ww1234567890:alice"] = "test-app"

        responses = [
            {"errcode": 40001, "errmsg": "invalid credential"},
            {"errcode": 0, "msgid": "msg-ok"},
        ]
        post_calls = []

        class FakeClient:
            async def post(self, url, json=None, **kw):
                post_calls.append(url)

                class R:
                    def json(inner):
                        return responses[len(post_calls) - 1]
                return R()

            async def get(self, url, params=None, **kw):
                class R:
                    def json(inner):
                        return {"errcode": 0, "access_token": "fresh", "expires_in": 7200}
                return R()

        adapter._http_client = FakeClient()
        result = await adapter.send("ww1234567890:alice", "hello")

        assert result.success is True
        assert result.message_id == "msg-ok"
        assert len(post_calls) == 2
        assert "fresh" in post_calls[1]
        assert adapter._access_tokens["test-app"]["token"] == "fresh"


class TestWecomCallbackPollLoop:
    @requires_defusedxml
    @pytest.mark.asyncio
    async def test_poll_loop_dispatches_handle_message(self, monkeypatch):
        adapter = WecomCallbackAdapter(_config())
        calls = []

        async def fake_handle_message(event):
            calls.append(event.text)

        monkeypatch.setattr(adapter, "handle_message", fake_handle_message)
        event = adapter._build_event(
            _app(),
            """
            <xml>
              <ToUserName>ww1234567890</ToUserName>
              <FromUserName>lisi</FromUserName>
              <CreateTime>1710000000</CreateTime>
              <MsgType>text</MsgType>
              <Content>test</Content>
              <MsgId>m2</MsgId>
            </xml>
            """,
        )
        task = asyncio.create_task(adapter._poll_loop())
        await adapter._message_queue.put(event)
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert calls == ["test"]


class TestWecomCallbackBodySizeLimit:
    """Pre-auth oversized-body rejection (DoS hardening, PR #10192)."""

    def _request(self, body_bytes):
        from unittest.mock import Mock

        from aiohttp import StreamReader
        from aiohttp.test_utils import make_mocked_request

        protocol = Mock(_reading_paused=False)
        reader = StreamReader(protocol=protocol, limit=2 ** 20)
        reader.feed_data(body_bytes)
        reader.feed_eof()
        return make_mocked_request(
            "POST", "/wecom/callback?msg_signature=s&timestamp=1&nonce=n",
            payload=reader,
        )

    @pytest.mark.asyncio
    async def test_oversized_body_rejected_with_413(self):
        from plugins.platforms.wecom.callback_adapter import _MAX_BODY

        adapter = WecomCallbackAdapter(_config())
        oversized = b"<xml>" + b"A" * (_MAX_BODY + 1) + b"</xml>"
        response = await adapter._handle_callback(self._request(oversized))
        assert response.status == 413


class TestWecomCallbackHTTP:
    """GET (``_handle_verify``) and POST (``_handle_callback``) signature boundaries.

    The inbound ``msg_signature`` is an attacker-controlled query parameter on a
    public, unauthenticated endpoint. Both handlers must route signature failures
    through ``WXBizMsgCrypt.decrypt`` (constant-time compare) and return a clean
    4xx — 403 for GET verify, 400 for POST callback — never a 500 or an
    ``logger.exception`` traceback. The valid control proves the 4xx is the
    signature, not the request shape.
    """

    @staticmethod
    def _encrypted_parts(plaintext="<xml><Content>hello</Content></xml>"):
        app = _app()
        crypt = WXBizMsgCrypt(app["token"], app["encoding_aes_key"], app["corp_id"])
        xml = crypt.encrypt(plaintext, nonce="nonce123", timestamp="123456")
        root = ET.fromstring(xml)
        return {
            "msg_signature": root.findtext("MsgSignature", default=""),
            "timestamp": root.findtext("TimeStamp", default=""),
            "nonce": root.findtext("Nonce", default=""),
            "encrypt": root.findtext("Encrypt", default=""),
        }

    @staticmethod
    def _make_request(method, query, body=b""):
        from unittest.mock import Mock

        from aiohttp import StreamReader
        from aiohttp.test_utils import make_mocked_request

        protocol = Mock(_reading_paused=False)
        reader = StreamReader(protocol=protocol, limit=2 ** 20)
        if body:
            reader.feed_data(body)
        reader.feed_eof()
        path = "/wecom/callback?" + urlencode(query)
        return make_mocked_request(method, path, payload=reader)

    @staticmethod
    def _signature_for(kind, valid):
        if kind == "valid":
            return valid
        if kind == "tampered":
            return valid[:-1] + ("0" if valid[-1] != "0" else "1")
        # non_ascii: a hostile query value that decodes to non-ASCII str
        return "\u00e9" * 40

    @pytest.mark.parametrize(
        "method,kind,status",
        [
            ("GET", "valid", 200),
            ("GET", "tampered", 403),
            ("GET", "non_ascii", 403),
            ("POST", "valid", 200),
            ("POST", "tampered", 400),
            ("POST", "non_ascii", 400),
        ],
    )
    @requires_defusedxml
    @pytest.mark.asyncio
    async def test_signature_failure_at_get_and_post_boundaries(
        self, method, kind, status, caplog
    ):
        import logging

        parts = self._encrypted_parts()
        query = {
            "msg_signature": self._signature_for(kind, parts["msg_signature"]),
            "timestamp": parts["timestamp"],
            "nonce": parts["nonce"],
            "echostr": parts["encrypt"],
        }
        body = ("<xml><Encrypt>%s</Encrypt></xml>" % parts["encrypt"]).encode("utf-8")
        request = self._make_request(method, query, body if method == "POST" else b"")
        adapter = WecomCallbackAdapter(_config())

        with caplog.at_level(
            logging.ERROR, logger="plugins.platforms.wecom.callback_adapter"
        ):
            if method == "GET":
                response = await adapter._handle_verify(request)
            else:
                response = await adapter._handle_callback(request)

        assert response.status == status, (method, kind, response.status, response.text)
        # Signature failures must stay on the silent WeComCryptoError path — no
        # 500 and no exception traceback logged for tampered/non-ASCII values.
        if kind != "valid":
            assert not any(r.levelno >= logging.ERROR for r in caplog.records), (
                method,
                kind,
                [r.getMessage() for r in caplog.records],
            )


@pytest.mark.asyncio
async def test_oversized_cron_output_is_split_under_the_2048_byte_text_limit():
    """message/send keeps only the first 2048 BYTES of text.content; CJK output used to lose
    everything past ~680 characters. The router now hands over the full payload and send()
    splits it by UTF-8 bytes."""
    from gateway.config import GatewayConfig
    from gateway.delivery import DeliveryRouter

    adapter = WecomCallbackAdapter(_config())
    adapter._access_tokens["test-app"] = {"token": "tok", "expires_at": 9999999999}
    sent = []

    class _Client:
        async def post(self, url, json):
            sent.append(json["text"]["content"])
            return type("R", (), {"json": lambda self: {"errcode": 0, "msgid": "m"}})()

    adapter._http_client = _Client()
    content = "\n\n".join(f"第{i}段 " + "数据" * 100 for i in range(40))
    payload = DeliveryRouter(GatewayConfig())._cap_oversized_output(adapter, content, "job")
    result = await adapter.send("test-app:user1", payload)

    assert result.success
    assert len(sent) > 1 and max(len(s.encode()) for s in sent) <= 2048
    assert "第39段" in sent[-1]
