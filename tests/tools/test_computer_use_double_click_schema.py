"""Schema-compatibility tests for cua-driver double-click dispatch."""

from tools.computer_use.backend import ActionResult
from tools.computer_use.cua_backend_input import _InputMixin


class _Session:
    def __init__(self, *, double_click_button: bool):
        self.double_click_button = double_click_button

    def supports_input_property(self, action: str, prop: str) -> bool:
        return action == "double_click" and prop == "button" and self.double_click_button

    def _has_tool(self, name: str) -> bool:
        return False


class _Harness(_InputMixin):
    def __init__(self, *, double_click_button: bool):
        self._active_pid = 41
        self._active_window_id = 9
        self._session = _Session(double_click_button=double_click_button)
        self.sent = None

    def _run_input_action(self, action, args, delivery_mode, bring_to_front):
        self.sent = (action, dict(args), delivery_mode, bring_to_front)
        return ActionResult(ok=True, action=action, message="sent")


def test_double_click_omits_default_left_button_when_schema_rejects_field():
    backend = _Harness(double_click_button=False)

    result = backend.click(element=7, click_count=2)

    assert result.ok is True
    assert backend.sent is not None
    action, args, _, _ = backend.sent
    assert action == "double_click"
    assert args == {"pid": 41, "element_index": 7, "window_id": 9}


def test_double_click_preserves_button_when_live_schema_accepts_it():
    backend = _Harness(double_click_button=True)

    result = backend.click(element=7, click_count=2, button="middle")

    assert result.ok is True
    action, args, _, _ = backend.sent
    assert action == "double_click"
    assert args["button"] == "middle"


def test_double_click_refuses_nonleft_button_when_schema_cannot_encode_it():
    backend = _Harness(double_click_button=False)

    result = backend.click(element=7, click_count=2, button="right")

    assert result.ok is False
    assert result.action == "double_click"
    assert result.code == "button_unsupported"
    assert backend.sent is None
