"""Static HTML web fixtures for Jev-speed decide-loop benchmarks (RFC #112639).

These fixtures run without a live browser in CI: each page is a small state machine
with numbered interactable elements, mirroring ``semantic_fixtures`` for desktop AX
trees. A real browser session can load the same HTML files for E2E timing runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

_FIXTURES_ROOT = Path(__file__).resolve().parent.parent.parent / "tests" / "computer_use" / "fixtures" / "web"


@dataclass
class WebElement:
    index: int
    tag: str
    label: str
    action: str = "click"
    enabled: bool = True


@dataclass
class WebPage:
    name: str
    elements: list[WebElement] = field(default_factory=list)
    done: bool = False


class _FixtureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._buttons: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        if tag in {"button", "a", "input"}:
            label = attr.get("data-label") or attr.get("value") or attr.get("id") or tag
            action = attr.get("data-action") or "click"
            self._buttons.append((tag, label, action))


def parse_html_fixture(path: Path) -> list[tuple[str, str, str]]:
    parser = _FixtureParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser._buttons


@dataclass
class WebFixtureFlow:
    """Multi-page wizard loaded from static HTML files."""

    name: str
    pages: list[WebPage]
    transitions: dict[tuple[str, int], str]
    _page_idx: int = field(default=0, repr=False)

    def capture(self) -> dict[str, Any]:
        page = self.pages[self._page_idx]
        return {
            "ok": True,
            "total_elements": len(page.elements),
            "elements": [
                {
                    "index": el.index,
                    "role": el.tag,
                    "label": el.label,
                    "enabled": el.enabled,
                }
                for el in page.elements
            ],
            "page": page.name,
            "done": page.done,
        }

    def click(self, element: int) -> dict[str, Any]:
        page = self.pages[self._page_idx]
        if element < 1 or element > len(page.elements):
            return {"error": f"invalid element {element}"}
        key = (page.name, element)
        nxt = self.transitions.get(key)
        if nxt is None:
            return {"error": f"no transition for {key}"}
        for i, p in enumerate(self.pages):
            if p.name == nxt:
                self._page_idx = i
                break
        return {"ok": True, "page": nxt}

    def is_done(self) -> bool:
        return bool(self.pages[self._page_idx].done)

    def make_handle(self, decide_script: list[dict] | None = None) -> Callable[[dict[str, Any]], str]:
        script = list(decide_script or [])
        script_idx = {"i": 0}

        def handle(args: dict[str, Any]) -> str:
            action = args.get("action")
            if action == "capture":
                return json.dumps(self.capture())
            if action == "decide":
                if not script:
                    return json.dumps({"ok": False, "error": "no decide script"})
                payload = script[script_idx["i"]]
                script_idx["i"] = min(script_idx["i"] + 1, len(script) - 1)
                return json.dumps(payload)
            if action == "click":
                return json.dumps(self.click(int(args.get("element") or 0)))
            if action == "key":
                return json.dumps({"ok": True})
            return json.dumps({"error": f"unsupported {action}"})

        return handle


def two_step_wizard_fixture() -> WebFixtureFlow:
    """Two-dialog flow matching the zenity multistep E2E shape."""
    pages = [
        WebPage(
            name="intro",
            elements=[
                WebElement(1, "button", "Continue"),
                WebElement(2, "button", "Cancel"),
            ],
        ),
        WebPage(
            name="confirm",
            elements=[
                WebElement(1, "button", "Submit"),
                WebElement(2, "button", "Back"),
            ],
        ),
        WebPage(name="complete", elements=[], done=True),
    ]
    transitions = {
        ("intro", 1): "confirm",
        ("intro", 2): "complete",
        ("confirm", 1): "complete",
        ("confirm", 2): "intro",
    }
    return WebFixtureFlow(name="two_step_wizard", pages=pages, transitions=transitions)


def flights_search_fixture() -> WebFixtureFlow:
    """Minimal flights-search shape inspired by jev-ultrafast demos."""
    pages = [
        WebPage(
            name="search",
            elements=[
                WebElement(1, "input", "From"),
                WebElement(2, "input", "To"),
                WebElement(3, "button", "Search flights"),
            ],
        ),
        WebPage(
            name="results",
            elements=[
                WebElement(1, "button", "Select cheapest"),
                WebElement(2, "button", "Change search"),
            ],
        ),
        WebPage(name="booked", elements=[], done=True),
    ]
    transitions = {
        ("search", 3): "results",
        ("results", 1): "booked",
        ("results", 2): "search",
    }
    return WebFixtureFlow(name="flights_search", pages=pages, transitions=transitions)


def all_web_fixtures() -> list[WebFixtureFlow]:
    return [two_step_wizard_fixture(), flights_search_fixture()]


def _flow_transitions_js(flow: WebFixtureFlow) -> str:
    mapping: dict[str, str] = {}
    for (page, element), nxt in flow.transitions.items():
        mapping[f"{page}:{element}"] = nxt
    return json.dumps(mapping)


def write_flow_html(flow: WebFixtureFlow, path: Path) -> Path:
    """Materialize one navigable HTML fixture for live browser benchmarks."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    transitions = _flow_transitions_js(flow)
    done_pages = {p.name for p in flow.pages if p.done}
    sections: list[str] = []
    for page in flow.pages:
        if page.done:
            sections.append(
                f'<section data-page="{page.name}" hidden><p>Done</p></section>'
            )
            continue
        buttons: list[str] = []
        for el in page.elements:
            buttons.append(
                f'<button data-fixture-index="{el.index}" data-label="{el.label}">{el.label}</button>'
            )
        sections.append(
            f'<section data-page="{page.name}" hidden>{"".join(buttons)}</section>'
        )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{flow.name}</title>
<style>
  body {{ font-family: system-ui, sans-serif; padding: 2rem; }}
  section[hidden] {{ display: none; }}
  button {{ margin: 0.5rem; padding: 0.6rem 1rem; }}
</style></head>
<body data-page="{flow.pages[0].name}">
<script>
const transitions = {transitions};
const donePages = new Set({json.dumps(sorted(done_pages))});
window.__fixturePage = document.body.dataset.page;
window.__fixtureDone = false;
function showPage(name) {{
  window.__fixturePage = name;
  document.body.dataset.page = name;
  document.querySelectorAll('section[data-page]').forEach((sec) => {{
    sec.hidden = sec.dataset.page !== name;
  }});
  if (donePages.has(name)) {{
    window.__fixtureDone = true;
    document.body.dataset.done = 'true';
  }}
}}
document.addEventListener('click', (ev) => {{
  const btn = ev.target.closest('button[data-fixture-index]');
  if (!btn) return;
  const page = window.__fixturePage;
  const idx = btn.dataset.fixtureIndex;
  const key = page + ':' + idx;
  const nxt = transitions[key];
  if (nxt) showPage(nxt);
}});
showPage(window.__fixturePage);
</script>
{"".join(sections)}
</body></html>"""
    path.write_text(html, encoding="utf-8")
    return path


def write_default_html_fixtures(root: Path | None = None) -> list[Path]:
    """Materialize HTML files for browser-backed E2E (optional)."""
    root = root or _FIXTURES_ROOT
    root.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for flow in all_web_fixtures():
        files.append(write_flow_html(flow, root / f"{flow.name}.html"))
    return files
