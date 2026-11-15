"""Code-health fix instructions follow the language of the file being measured."""

import pytest

from scripts.code_health.model import MODULE_SCOPE, Finding
from scripts.code_health.report import format_findings


@pytest.mark.parametrize("path", [
    "ui-tui/src/oversized.ts",
    "apps/desktop/src/components/oversized.tsx",
])
def test_file_lines_remedy_for_typescript_uses_typescript_modules(path):
    ts_finding = Finding(path, "FILE_LINES", MODULE_SCOPE, 1, "2001 > 2000")
    ts_output = format_findings([ts_finding])
    py_finding = Finding("agent/oversized.py", "FILE_LINES", MODULE_SCOPE, 1, "2001 > 2000")
    py_output = format_findings([py_finding])

    assert "TypeScript module" in ts_output
    assert "`__init__.py`" not in ts_output
    assert "`__init__.py`" in py_output
