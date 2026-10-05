"""Original PR127650 upload and response-shape regressions."""

import asyncio
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from plugins.platforms.feishu.feishu_response import response_error_result


class TestUploadDiagnostics(unittest.TestCase):
    def test_document_upload_failure_keeps_api_code_and_msg_behind_headline(self):
        """Regression (#127639): the upload headline used to fully replace the API's
        code/msg, so an app missing the im:resource scope (code 99991672) surfaced
        only as "missing file_key" with no diagnosis in the operator log."""
        from gateway.config import PlatformConfig
        from plugins.platforms.feishu.adapter import FeishuAdapter

        adapter = FeishuAdapter(PlatformConfig())

        class _FileAPI:
            def create(self, request):
                return SimpleNamespace(
                    success=lambda: False,
                    code=99991672,
                    msg=(
                        "Access denied. One of the following scopes is required: "
                        "[im:resource:upload, im:resource]"
                    ),
                )

        adapter._client = SimpleNamespace(
            im=SimpleNamespace(v1=SimpleNamespace(file=_FileAPI()))
        )

        async def _direct(func, *args, **kwargs):
            return func(*args, **kwargs)

        with tempfile.NamedTemporaryFile("wb", suffix=".docx", delete=False) as tmp:
            tmp.write(b"docx test")
            file_path = tmp.name

        try:
            with patch("plugins.platforms.feishu.adapter.asyncio.to_thread", side_effect=_direct):
                result = asyncio.run(
                    adapter.send_document(chat_id="oc_chat", file_path=file_path)
                )
        finally:
            os.unlink(file_path)

        self.assertFalse(result.success)
        self.assertIn("Feishu file upload missing file_key", result.error)
        self.assertIn("[99991672]", result.error)
        self.assertIn("im:resource", result.error)

    def test_response_error_result_shapes(self):
        denied = SimpleNamespace(
            success=lambda: False, code=99991672, msg="Access denied: scope im:resource required"
        )

        override = response_error_result(
            denied, default_message="file upload failed",
            override_error="Feishu file upload missing file_key",
        )
        self.assertFalse(override.success)
        self.assertEqual(
            override.error,
            "Feishu file upload missing file_key [99991672] Access denied: scope im:resource required",
        )
        # The appended diagnosis must never read as a platform verdict downstream, so the
        # kind is pinned explicitly rather than left for substring classification to infer.
        self.assertEqual(override.error_kind, "unknown")

        plain = response_error_result(
            SimpleNamespace(success=lambda: False, code=230002, msg="chat not found"),
            default_message="send failed",
        )
        self.assertEqual(plain.error, "[230002] chat not found")
        self.assertEqual(plain.error_kind, "unknown")

        # lark BaseResponse.msg is Optional[str]: a present-but-None msg falls back to the
        # default instead of rendering the literal "None".
        none_msg = response_error_result(
            SimpleNamespace(success=lambda: False, code=230002, msg=None),
            default_message="send failed",
        )
        self.assertEqual(none_msg.error, "[230002] send failed")

        bare = response_error_result(
            SimpleNamespace(success=lambda: False), default_message="send failed"
        )
        self.assertEqual(bare.error, "[unknown] send failed")

        bare_override = response_error_result(
            SimpleNamespace(success=lambda: False), default_message="file upload failed",
            override_error="Feishu file upload missing file_key",
        )
        self.assertEqual(bare_override.error, "Feishu file upload missing file_key [unknown] file upload failed")
