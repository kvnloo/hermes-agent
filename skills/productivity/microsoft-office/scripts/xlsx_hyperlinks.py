"""Keep hyperlinks attached to their cells across openpyxl structural moves."""

from copy import copy

from openpyxl.utils import get_column_letter


def move_cells_with_hyperlinks(ws, axis, index, count, delete):
    """Move cells and update link refs, dropping links from deleted cells."""
    links = []
    for cell in ws._cells.values():
        hyperlink = getattr(cell, "hyperlink", None)
        if hyperlink is None:
            continue
        pos = cell.row if axis == "rows" else cell.column
        if delete and index <= pos < index + count:
            continue
        if delete:
            delta = -count if pos >= index + count else 0
        else:
            delta = count if pos >= index else 0
        row = cell.row + (delta if axis == "rows" else 0)
        col = cell.column + (delta if axis == "cols" else 0)
        links.append((f"{get_column_letter(col)}{row}", copy(hyperlink)))

    getattr(ws, f"{'delete' if delete else 'insert'}_{axis}")(index, count)

    # openpyxl moves cell objects but leaves hyperlink.ref on the old address.
    # Clear orphan links before restoring only the surviving destinations.
    for cell in ws._cells.values():
        if getattr(cell, "hyperlink", None) is not None:
            cell.hyperlink = None
    for coord, hyperlink in links:
        hyperlink.ref = coord
        ws[coord].hyperlink = hyperlink
