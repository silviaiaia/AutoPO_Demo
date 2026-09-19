"""Writer for the Open Order workbook.

The workbook is not a report. It is the staging file for an ERP import, and
that importer rejects typed cells: a quantity written as a number, or a date
written as a date, is refused at upload. So every value goes in as text --
quantities, prices, and dates as YYYY/MM/DD strings -- and nothing here sets a
number format.

From inside Excel this looks broken: quantities will not sum and CRD will not
sort as a date. That is the trade the import requires. tests/test_excel_writer
locks it in, so a well-meaning change to "fix" the types cannot quietly break
the upload instead.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from autopo.config import STANDARD_COLUMNS


_HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
_HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)


def _default_headers() -> List[str]:
    order = [
        "upload", "sales_doc_item", "soldto_abbr", "shipto_abbr",
        "customer_ref_date", "soldto", "shipto", "customer_ref",
        "customer_po_item", "material", "module_material",
        "customer_material", "order_qty", "unit_price", "currency",
        "crd", "etd", "remark",
    ]
    return [STANDARD_COLUMNS[k] for k in order]


def ensure_workbook(path: str | Path, sheet_name: str = "OpenOrder") -> Workbook:
    """Load an existing workbook or create a fresh one with headers."""
    path = Path(path)
    if path.exists():
        wb = load_workbook(path)
        if sheet_name not in wb.sheetnames:
            wb.create_sheet(sheet_name)
        return wb

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    _write_header(ws)
    return wb


def _write_header(ws) -> None:
    headers = _default_headers()
    for idx, name in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=idx, value=name)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
    for idx, _ in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = 18
    ws.freeze_panes = "A2"


def append_rows(
    workbook_path: str | Path,
    rows: Iterable[dict],
    sheet_name: str = "OpenOrder",
) -> int:
    path = Path(workbook_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = ensure_workbook(path, sheet_name)
    ws = wb[sheet_name]
    headers = [c.value for c in ws[1] if c.value] or _default_headers()
    for idx, name in enumerate(_default_headers(), start=1):
        if ws.cell(row=1, column=idx).value is None:
            ws.cell(row=1, column=idx, value=name)
            ws.cell(row=1, column=idx).font = _HEADER_FONT
            ws.cell(row=1, column=idx).fill = _HEADER_FILL

    start_row = ws.max_row + 1
    written = 0
    for row in rows:
        for idx, header in enumerate(headers, start=1):
            value = row.get(header, "")
            # Text, always -- see the module docstring. Coercing here keeps the
            # guarantee at the boundary, whatever a parser hands over.
            if not isinstance(value, str):
                value = str(value)
            ws.cell(row=start_row + written, column=idx, value=value)
        written += 1

    wb.save(path)
    return written
