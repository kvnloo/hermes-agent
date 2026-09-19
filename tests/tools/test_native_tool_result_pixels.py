"""Two-axis native tool-result pixel routing (#115248 / Phase 8).

``supports_vision`` must NOT be generalized as tool-result media support.
Native pixels require both axes positively known:

    model_can_understand_images
    AND tool_result_transport_accepts_images
    AND NOT explicit_veto
    AND NOT explicit_aux_override

Unknown fails closed. vision_analyze and computer_use capture must share one resolver.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest


def _caps(supports_vision):
    if supports_vision is None:
        return None
    return SimpleNamespace(supports_vision=supports_vision)


class TestTwoAxisResolver:
    def test_native_requires_both_axes_positive(self):
        from tools.vision_tools import resolve_native_tool_result_pixels

        with patch(
            "agent.models_dev.get_model_capabilities", return_value=_caps(True)
        ):
            d = resolve_native_tool_result_pixels("anthropic", "claude-sonnet-4", {})
        assert d.model_can_understand_images is True
        assert d.transport_accepts_images_in_tool_results is True
        assert d.explicit_veto is False
        assert d.native is True

    def test_vision_capable_model_plus_rejecting_transport_fails_closed(self):
        """Counterexample: vision-capable model + provider rejecting image tool content."""
        from tools.vision_tools import resolve_native_tool_result_pixels

        with patch(
            "agent.models_dev.get_model_capabilities", return_value=_caps(True)
        ), patch(
            "tools.vision_tools._profile_rejects_tool_media", return_value=True
        ):
            d = resolve_native_tool_result_pixels("xiaomi", "mimo-v2.5", {})
        assert d.model_can_understand_images is True
        assert d.explicit_veto is True
        assert d.native is False

    def test_text_only_model_plus_media_capable_aggregator_fails_closed(self):
        """Counterexample: text-only model + media-capable aggregator."""
        from tools.vision_tools import resolve_native_tool_result_pixels

        with patch(
            "agent.models_dev.get_model_capabilities", return_value=_caps(False)
        ), patch(
            "agent.image_routing._lookup_supports_vision", return_value=False
        ):
            d = resolve_native_tool_result_pixels("openrouter", "openai/gpt-4o-mini-textish", {})
        assert d.transport_accepts_images_in_tool_results is True
        assert d.model_can_understand_images is False
        assert d.native is False

    def test_unknown_model_capability_fails_closed_even_on_whitelist(self):
        from tools.vision_tools import resolve_native_tool_result_pixels

        with patch(
            "agent.models_dev.get_model_capabilities", return_value=None
        ), patch(
            "agent.image_routing._lookup_supports_vision", return_value=None
        ):
            d = resolve_native_tool_result_pixels("anthropic", "mystery-model", {})
        assert d.model_can_understand_images is None
        assert d.native is False

    def test_unknown_transport_fails_closed_despite_catalog_vision(self):
        """Catalog vision must NOT be generalized as transport acceptance."""
        from tools.vision_tools import resolve_native_tool_result_pixels

        with patch(
            "agent.models_dev.get_model_capabilities", return_value=_caps(True)
        ), patch(
            "agent.image_routing._lookup_supports_vision", return_value=True
        ), patch(
            "providers.get_provider_profile", return_value=None
        ):
            d = resolve_native_tool_result_pixels("acme-unknown", "vision-vlm", {})
        assert d.model_can_understand_images is True
        assert d.transport_accepts_images_in_tool_results is not True
        assert d.native is False

    def test_deepseek_flash_native_via_positive_transport_not_catalog_conflation(self):
        """#115248: deepseek transport is positively attested; both axes True → native."""
        from tools.vision_tools import resolve_native_tool_result_pixels

        with patch(
            "agent.models_dev.get_model_capabilities", return_value=_caps(True)
        ), patch(
            "agent.image_routing._lookup_supports_vision", return_value=True
        ):
            d = resolve_native_tool_result_pixels("deepseek", "deepseek-flash", {})
        assert d.transport_accepts_images_in_tool_results is True
        assert d.model_can_understand_images is True
        assert d.native is True

    def test_explicit_aux_override_blocks_native(self):
        from tools.vision_tools import resolve_native_tool_result_pixels

        cfg = {"auxiliary": {"vision": {"provider": "openrouter", "model": "google/gemini-2.5-flash"}}}
        with patch(
            "agent.models_dev.get_model_capabilities", return_value=_caps(True)
        ), patch(
            "agent.image_routing._lookup_supports_vision", return_value=True
        ):
            d = resolve_native_tool_result_pixels("anthropic", "claude-sonnet-4", cfg)
        assert d.explicit_aux_override is True
        assert d.native is False


class TestSharedResolverAgreement:
    def test_capture_and_vision_analyze_agree_deepseek_flash(self):
        from agent.auxiliary_client import clear_runtime_main, set_runtime_main
        from tools.computer_use import vision_routing
        from tools.vision_tools import _should_use_native_vision_fast_path

        set_runtime_main("deepseek", "deepseek-flash")
        try:
            with patch(
                "agent.models_dev.get_model_capabilities", return_value=_caps(True)
            ), patch(
                "agent.image_routing._lookup_supports_vision", return_value=True
            ), patch(
                "agent.image_routing.decide_image_input_mode", return_value="native"
            ):
                capture_aux = vision_routing.should_route_capture_to_aux_vision(
                    "deepseek", "deepseek-flash", {}
                )
                fast = _should_use_native_vision_fast_path()
            assert capture_aux is False
            assert fast is True
        finally:
            clear_runtime_main()

    def test_capture_and_vision_analyze_agree_on_veto(self):
        from agent.auxiliary_client import clear_runtime_main, set_runtime_main
        from tools.computer_use import vision_routing
        from tools.vision_tools import _should_use_native_vision_fast_path

        set_runtime_main("xiaomi", "mimo-v2.5")
        try:
            with patch(
                "agent.models_dev.get_model_capabilities", return_value=_caps(True)
            ), patch(
                "tools.vision_tools._profile_rejects_tool_media", return_value=True
            ), patch(
                "agent.image_routing.decide_image_input_mode", return_value="native"
            ):
                capture_aux = vision_routing.should_route_capture_to_aux_vision(
                    "xiaomi", "mimo-v2.5", {}
                )
                fast = _should_use_native_vision_fast_path()
            assert capture_aux is True
            assert fast is False
        finally:
            clear_runtime_main()
