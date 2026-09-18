from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import load_workbook

from autopo.config import DATE_COLUMNS
from autopo.core.excel_writer import append_rows, ensure_workbook

ROW = {
    "Upload": "Y",
    "Sold-to Party": "10001",
    "Customer Reference": "242445",
    "Customer Material": "C460-3373",
    "Order Quantity": "40",
    "Unit Price": "1234.56",
    "CRD": "2025/04/07",
}


@pytest.fixture()
def workbook_path(tmp_path: Path) -> Path:
    return tmp_path / "open_order.xlsx"


def headers_of(path: Path, sheet: str = "OpenOrder") -> list[str]:
    ws = load_workbook(path)[sheet]
    return [c.value for c in ws[1] if c.value]


class TestEnsureWorkbook:
    def test_creates_a_sheet_with_headers(self, workbook_path: Path):
        wb = ensure_workbook(workbook_path)
        ws = wb["OpenOrder"]
        assert ws["A1"].value == "Upload"
        assert ws.freeze_panes == "A2"

    def test_reuses_an_existing_workbook(self, workbook_path: Path):
        append_rows(workbook_path, [ROW])
        wb = ensure_workbook(workbook_path)
        assert wb["OpenOrder"].max_row == 2

    def test_adds_a_missing_sheet_to_an_existing_workbook(self, workbook_path: Path):
        append_rows(workbook_path, [ROW])
        wb = ensure_workbook(workbook_path, sheet_name="EU")
        assert "EU" in wb.sheetnames


class TestAppendRows:
    def test_creates_the_output_directory(self, tmp_path: Path):
        path = tmp_path / "nested" / "dir" / "open_order.xlsx"
        append_rows(path, [ROW])
        assert path.exists()

    def test_returns_the_number_of_rows_written(self, workbook_path: Path):
        assert append_rows(workbook_path, [ROW, ROW, ROW]) == 3

    def test_writes_values_under_the_matching_header(self, workbook_path: Path):
        append_rows(workbook_path, [ROW])
        ws = load_workbook(workbook_path)["OpenOrder"]
        by_header = dict(zip(headers_of(workbook_path), [c.value for c in ws[2]]))
        assert by_header["Sold-to Party"] == "10001"
        assert by_header["Order Quantity"] == "40"
        assert by_header["CRD"] == "2025/04/07"

    def test_columns_the_row_does_not_fill_are_left_blank(self, workbook_path: Path):
        append_rows(workbook_path, [ROW])
        ws = load_workbook(workbook_path)["OpenOrder"]
        by_header = dict(zip(headers_of(workbook_path), [c.value for c in ws[2]]))
        assert by_header["Remark"] is None

    def test_appending_twice_accumulates_instead_of_overwriting(self, workbook_path: Path):
        # A day's run appends several POs to the same tracker.
        append_rows(workbook_path, [ROW, ROW])
        append_rows(workbook_path, [ROW])
        ws = load_workbook(workbook_path)["OpenOrder"]
        assert ws.max_row == 4  # 1 header + 3 data rows

    def test_the_header_row_is_written_once(self, workbook_path: Path):
        append_rows(workbook_path, [ROW])
        append_rows(workbook_path, [ROW])
        ws = load_workbook(workbook_path)["OpenOrder"]
        assert [c.value for c in ws[2]] != [c.value for c in ws[1]]
        assert ws["A1"].value == "Upload"

    def test_date_columns_get_a_date_number_format(self, workbook_path: Path):
        append_rows(workbook_path, [ROW])
        ws = load_workbook(workbook_path)["OpenOrder"]
        crd = next(c for c in ws[2] if ws.cell(row=1, column=c.column).value == "CRD")
        assert crd.number_format == "YYYY/MM/DD"

    def test_non_date_columns_keep_the_general_format(self, workbook_path: Path):
        append_rows(workbook_path, [ROW])
        ws = load_workbook(workbook_path)["OpenOrder"]
        qty = next(
            c for c in ws[2] if ws.cell(row=1, column=c.column).value == "Order Quantity"
        )
        assert qty.number_format == "General"

    def test_every_date_column_is_a_real_header(self, workbook_path: Path):
        # Guards against a rename in config.py silently disabling date formatting.
        append_rows(workbook_path, [ROW])
        present = set(headers_of(workbook_path))
        assert set(DATE_COLUMNS) - {"ETA"} <= present

    def test_writes_to_the_requested_sheet(self, workbook_path: Path):
        append_rows(workbook_path, [ROW], sheet_name="EU")
        assert "EU" in load_workbook(workbook_path).sheetnames

    def test_a_second_sheet_gets_its_own_headers(self, workbook_path: Path):
        append_rows(workbook_path, [ROW])
        append_rows(workbook_path, [ROW], sheet_name="EU")
        assert headers_of(workbook_path, "EU") == headers_of(workbook_path, "OpenOrder")

    def test_writing_no_rows_leaves_a_headers_only_workbook(self, workbook_path: Path):
        assert append_rows(workbook_path, []) == 0
        assert load_workbook(workbook_path)["OpenOrder"].max_row == 1
