"""BTW live text delivery and cancellation fallback boundaries."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agent.side_question import answer_side_question


def test_fork_streams_actual_deltas_and_keeps_snapshot_untouched():
    history = [{"role": "user", "content": "Main"}, {"role": "assistant", "content": "Done"}]
    deltas = []
    def run(**kwargs):
        assert kwargs["conversation_history"] == history
        kwargs["stream_callback"]("Actual ")
        kwargs["stream_callback"]("answer")
        return {"final_response": "Actual answer"}
    fork = SimpleNamespace(run_conversation=run, shutdown_memory_provider=Mock(), close=Mock())
    with patch("agent.background_review.build_cache_parity_fork", return_value=(fork, {}, False)), \
         patch("agent.background_review._record_review_usage_to_parent"), \
         patch("agent.background_review._snapshot_review_usage", return_value={}):
        assert answer_side_question("Question", history, parent_agent=object(), stream_callback=deltas.append) == "Actual answer"
    assert deltas == ["Actual ", "answer"]
    assert history == [{"role": "user", "content": "Main"}, {"role": "assistant", "content": "Done"}]
    fork.close.assert_called_once()


def test_cancelled_fork_does_not_spawn_a_new_oneshot_call():
    for result in ("", RuntimeError("interrupted")):
        with patch("agent.side_question._answer_via_fork", side_effect=result if isinstance(result, Exception) else None,
                   return_value=result), patch("agent.side_question._answer_via_oneshot") as fallback:
            assert answer_side_question("Question", [], parent_agent=object(), cancelled=lambda: True) == ""
        fallback.assert_not_called()
