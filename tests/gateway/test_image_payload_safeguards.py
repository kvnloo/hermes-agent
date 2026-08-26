import pytest

from agent.image_routing import (
    content_has_native_images,
    is_explicit_image_save_only_request,
    strip_historical_native_images,
)


def test_explicit_save_only_request_is_detected_without_matching_normal_analysis():
    assert is_explicit_image_save_only_request("Save these only — do not analyze them.")
    assert is_explicit_image_save_only_request("just save, don't inspect the images")
    assert not is_explicit_image_save_only_request("save these and analyze the screenshots")
    assert not is_explicit_image_save_only_request("what is shown here?")


@pytest.mark.parametrize(
    "instruction",
    [
        "Save these images to the archive and identify the defect on the drive.",
        "Save these images to the folder and tell me what is shown on the drive.",
        "Archive these photos to the folder and analyze the storage.",
        "Store these screenshots to the evidence and inspect the archive.",
        "Save this only for the record, then identify the defect in the image.",
        "No review needed; analyze the image for defects.",
        "Don't inspect the metadata; analyze the actual image.",
    ],
)
def test_mixed_or_unknown_save_wording_fails_open(instruction):
    assert not is_explicit_image_save_only_request(instruction)


def test_native_inline_content_is_recognized_for_attachment_deduplication():
    native = [
        {"type": "text", "text": "keep this"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
    ]
    assert content_has_native_images(native)
    assert not content_has_native_images([{"type": "text", "text": "plain"}])


def test_historical_image_payloads_are_replaced_without_mutating_history():
    payload = "data:image/png;base64," + ("A" * 100_000)
    history = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "first turn"},
                {"type": "image_url", "image_url": {"url": payload}},
            ],
        },
        {"role": "assistant", "content": "saved"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "current turn"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,CURRENT"}},
            ],
        },
    ]

    outbound = strip_historical_native_images(history, current_turn_user_idx=2)

    assert payload in history[0]["content"][1]["image_url"]["url"]
    assert outbound[0]["content"] == "first turn\n[Image attachment omitted after its original turn.]"
    assert outbound[2]["content"] == history[2]["content"]
    assert payload not in repr(outbound)
