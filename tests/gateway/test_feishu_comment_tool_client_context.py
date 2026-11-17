"""A Feishu document-comment agent's Lark client must reach tool workers without leaking between comments.

The public comment agent binds the client before entering AIAgent, but tools execute on
other threads through propagate_context_to_thread. Exercise the real entry point and
feishu_doc_read handler with in-memory Lark replies; no model or Feishu network needed.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import json
from types import SimpleNamespace

import hermes_bootstrap


def test_concurrent_feishu_comments_keep_their_lark_client_on_tool_workers(monkeypatch):
    from plugins.platforms.feishu import feishu_comment
    from tools import feishu_doc_tool
    from tools.feishu_lark import get_client
    from tools.thread_context import propagate_context_to_thread

    both_comments_running = Barrier(2)

    class FakeLarkClient:
        def __init__(self, document_text):
            self.document_text = document_text

        def request(self, _request):
            return SimpleNamespace(
                code=0,
                raw=SimpleNamespace(
                    content=json.dumps({"data": {"content": self.document_text}})
                ),
            )

    class CommentAgent:
        def __init__(self, **_kwargs):
            pass

        def run_conversation(self, prompt, conversation_history=None):
            # Hold both comment contexts live before either dispatches a tool.
            both_comments_running.wait()
            with ThreadPoolExecutor(max_workers=1) as workers:
                reply = workers.submit(
                    propagate_context_to_thread(
                        lambda: feishu_doc_tool._handle_feishu_doc_read(
                            {"doc_token": prompt}
                        )
                    )
                ).result()
            return {"final_response": reply, "messages": [], "api_calls": 1}

        def close(self):
            pass

    monkeypatch.setattr("run_agent.AIAgent", CommentAgent)
    monkeypatch.setattr(feishu_comment, "_resolve_model_and_runtime", lambda: ("m", {}))
    monkeypatch.setattr(feishu_doc_tool, "build_request", lambda *_a, **_kw: object())

    def answer_comment(prompt, document_text):
        answer = feishu_comment._run_comment_agent(
            prompt, FakeLarkClient(document_text), session_key=""
        )
        return answer, get_client()

    with ThreadPoolExecutor(max_workers=2) as events:
        first = events.submit(answer_comment, "first-doc", "document-A")
        second = events.submit(answer_comment, "second-doc", "document-B")
        first_answer, first_client_after = first.result()
        second_answer, second_client_after = second.result()

    assert "document-A" in first_answer
    assert "document-B" in second_answer
    assert "document-B" not in first_answer
    assert "document-A" not in second_answer
    assert first_client_after is None
    assert second_client_after is None
    assert get_client() is None
