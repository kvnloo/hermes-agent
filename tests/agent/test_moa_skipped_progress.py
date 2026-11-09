"""Regression for #71243: a guarded MoA slot still finishes its progress step."""

from agent import moa_loop


def test_skipped_moa_reference_emits_terminal_progress(monkeypatch):
    slots = [
        {"provider": "synthetic", "model": "a"},
        {"provider": "moa", "model": "nested"},
        {"provider": "synthetic", "model": "b"},
    ]

    def fake_reference(slot, *_args, **_kwargs):
        return (f"{slot['provider']}:{slot['model']}", "advice", None)

    monkeypatch.setattr(moa_loop, "_run_reference", fake_reference)
    progress = []
    heartbeats = []

    outputs = moa_loop._run_references_parallel(
        slots,
        [{"role": "user", "content": "plan"}],
        progress_callback=lambda done, total, label: progress.append(
            (done, total, label)
        ),
        heartbeat_callback=lambda done, total, pending, elapsed: heartbeats.append(
            (done, total, pending)
        ),
    )

    assert [done for done, _, _ in progress] == [1, 2, 3]
    assert all(total == len(slots) for _, total, _ in progress)
    assert progress[0][2] == "moa:nested"
    assert {label for _, _, label in progress} == {
        "synthetic:a", "moa:nested", "synthetic:b"
    }
    assert heartbeats and heartbeats[0][:2] == (1, 3)
    assert [label for label, _, _ in outputs] == [
        "synthetic:a", "moa:nested", "synthetic:b"
    ]
    assert outputs[1][1].startswith("[skipped:")
