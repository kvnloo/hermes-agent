"""Playwright/Chromium backend for web-fixture computer_use benchmarks (#113850).

Loads static HTML fixtures and exposes numbered interactive elements through the
same ``ComputerUseBackend`` surface cua-driver uses for AX trees. Intended for
live browser timing runs (headless Chromium via Playwright — Puppeteer-equivalent
CDP stack) without touching approval or safety paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.computer_use.backend import ActionResult, CaptureResult, ComputerUseBackend, UIElement


class BrowserBackend(ComputerUseBackend):
    """Headless Chromium session over materialized web fixtures."""

    def __init__(self, html_path: Path, *, app_name: str = "browser") -> None:
        self._html_path = Path(html_path).resolve()
        self._app_name = app_name
        self._playwright = None
        self._browser = None
        self._page = None
        self._elements: list[UIElement] = []
        self._last_app = app_name
        self._last_target: dict[str, Any] = {"pid": 0, "window_id": 0}

    def start(self) -> None:
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._page = self._browser.new_page(viewport={"width": 1024, "height": 768})
        self._page.goto(self._html_path.as_uri(), wait_until="domcontentloaded")
        self._refresh_elements()

    def stop(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        self._page = None
        self._elements = []

    def is_available(self) -> bool:
        return True

    def _refresh_elements(self) -> list[dict[str, Any]]:
        assert self._page is not None
        raw = self._page.evaluate(
            """() => {
                const page = window.__fixturePage || document.body.dataset.page || '';
                const section = document.querySelector(`section[data-page="${page}"]`)
                    || document.body;
                const nodes = section.querySelectorAll(
                    'button, input, select, textarea, a[href], [data-label][role="button"]'
                );
                return Array.from(nodes).map((el, i) => ({
                    index: i + 1,
                    role: (el.getAttribute('role') || el.tagName || '').toLowerCase(),
                    label: (el.dataset.label || el.getAttribute('aria-label')
                        || el.value || el.textContent || '').trim().slice(0, 120),
                    enabled: !el.disabled,
                }));
            }"""
        )
        elements: list[UIElement] = []
        for row in raw or []:
            elements.append(
                UIElement(
                    index=int(row["index"]),
                    role=str(row.get("role") or "button"),
                    label=str(row.get("label") or ""),
                    app=self._app_name,
                    pid=1,
                    window_id=1,
                )
            )
        self._elements = elements
        return raw or []

    def capture(
        self,
        mode: str = "som",
        app: Optional[str] = None,
        pid: Optional[int] = None,
        window_id: Optional[int] = None,
    ) -> CaptureResult:
        del app, pid, window_id
        rows = self._refresh_elements()
        title = ""
        if self._page is not None:
            title = self._page.title() or ""
        return CaptureResult(
            mode=mode,
            width=1024,
            height=768,
            elements=list(self._elements),
            app=self._app_name,
            window_title=title,
            note=json.dumps({"fixture_page": rows[0] if rows else None, "pages": "browser"}),
        )

    def click(
        self,
        *,
        element: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        click_count: int = 1,
        modifiers: Optional[List[str]] = None,
        delivery_mode: Optional[str] = None,
        bring_to_front: bool = False,
    ) -> ActionResult:
        del x, y, button, click_count, modifiers, delivery_mode, bring_to_front
        if element is None or element < 1 or element > len(self._elements):
            return ActionResult(ok=False, action="click", message=f"invalid element {element!r}")
        assert self._page is not None
        try:
            clicked = self._page.evaluate(
                """(idx) => {
                    const page = window.__fixturePage || document.body.dataset.page || '';
                    const section = document.querySelector(`section[data-page="${page}"]`)
                        || document.body;
                    const nodes = section.querySelectorAll(
                        'button, input, select, textarea, a[href], [data-label][role="button"]'
                    );
                    const el = nodes[idx - 1];
                    if (!el) return false;
                    el.click();
                    return true;
                }""",
                element,
            )
            if not clicked:
                return ActionResult(ok=False, action="click", message=f"element #{element} not found")
        except Exception as exc:
            return ActionResult(ok=False, action="click", message=str(exc))
        self._page.wait_for_timeout(150)
        self._refresh_elements()
        return ActionResult(ok=True, action="click", message=f"clicked element #{element}")

    def drag(self, **kwargs: Any) -> ActionResult:
        del kwargs
        return ActionResult(ok=False, action="drag", message="drag not supported in browser fixtures")

    def scroll(self, **kwargs: Any) -> ActionResult:
        del kwargs
        return ActionResult(ok=False, action="scroll", message="scroll not supported in browser fixtures")

    def type_text(self, text: str, **kwargs: Any) -> ActionResult:
        del kwargs
        return ActionResult(ok=False, action="type", message=f"type not implemented ({len(text)} chars)")

    def key(self, keys: str, **kwargs: Any) -> ActionResult:
        del kwargs
        return ActionResult(ok=False, action="key", message=f"key not implemented ({keys!r})")

    def list_apps(self) -> List[Dict[str, Any]]:
        return [{"name": self._app_name, "pid": 1, "windows": 1}]

    def list_windows(self) -> List[Dict[str, Any]]:
        title = self._page.title() if self._page else self._html_path.stem
        return [{"title": title, "pid": 1, "window_id": 1, "app": self._app_name}]

    def focus_app(self, app: str, raise_window: bool = False) -> ActionResult:
        del raise_window
        self._last_app = app or self._app_name
        return ActionResult(ok=True, action="focus_app", message=f"focused {self._last_app}")

    def set_value(self, value: str, element: Optional[int] = None) -> ActionResult:
        del value, element
        return ActionResult(ok=False, action="set_value", message="set_value not supported")

    def is_done(self) -> bool:
        if self._page is None:
            return False
        return bool(
            self._page.evaluate(
                "() => Boolean(window.__fixtureDone || document.body.dataset.done === 'true')"
            )
        )


def install_browser_backend(
    html_path: Path,
    *,
    app_name: str = "browser",
    session_id: str = "",
) -> BrowserBackend:
    """Inject a browser backend for the active Hermes profile session key."""
    import tools.computer_use.tool as cu_tool

    backend = BrowserBackend(html_path, app_name=app_name)
    backend.start()
    bare_sid = str(session_id or "")
    sid = cu_tool._scoped_sid(session_id)
    permission_mode = cu_tool._cua_permission_mode(bare_sid)
    with cu_tool._backend_lock:
        cu_tool._install_backend(sid, backend, permission_mode)
    return backend


def release_browser_backend() -> None:
    from tools.computer_use.tool import reset_backend_for_tests

    reset_backend_for_tests()
