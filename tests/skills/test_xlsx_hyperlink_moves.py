"""Regression for NousResearch/hermes-agent#150852 (costa-marcello)."""

import os
import subprocess
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter


SCRIPTS = (Path(__file__).resolve().parents[2]
           / "skills/productivity/microsoft-office/scripts")


def test_hyperlinks_follow_structural_edits(tmp_path):
    for script in ("xlsx_edit.py", "xlsx_restructure.py"):
        for axis in ("rows", "cols"):
            for operation in ("insert", "delete"):
                book_path = tmp_path / f"{script}-{axis}-{operation}.xlsx"
                wb = Workbook()
                ws = wb.active
                for original in range(1, 6):
                    coord = (f"A{original}" if axis == "rows"
                             else f"{get_column_letter(original)}1")
                    cell = ws[coord]
                    cell.value = f"site{original}.example"
                    cell.hyperlink = f"https://site{original}.example/"
                    cell.hyperlink.tooltip = f"tip-{original}"
                wb.save(book_path)

                command = [sys.executable, str(SCRIPTS / script),
                           str(book_path), f"--{operation}-{axis}", "2"]
                result = subprocess.run(
                    command, capture_output=True, text=True, encoding="utf-8",
                    env={**os.environ, "LC_ALL": "C", "LANG": "C"},
                    check=False)
                assert result.returncode == 0, result.stderr

                ws = load_workbook(book_path).active
                for original in range(1, 6):
                    if operation == "delete" and original == 2:
                        continue
                    dest = (original if original < 2 else
                            original + (1 if operation == "insert" else -1))
                    coord = (f"A{dest}" if axis == "rows"
                             else f"{get_column_letter(dest)}1")
                    cell = ws[coord]
                    assert cell.value == f"site{original}.example"
                    assert cell.hyperlink is not None
                    assert cell.hyperlink.ref == coord
                    assert cell.hyperlink.target == f"https://site{original}.example/"
                    assert cell.hyperlink.tooltip == f"tip-{original}"

                empty = 2 if operation == "insert" else 5
                coord = (f"A{empty}" if axis == "rows"
                         else f"{get_column_letter(empty)}1")
                assert ws[coord].value is None
                assert ws[coord].hyperlink is None
