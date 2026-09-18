from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from autopo.parsers import CustomerAParser, CustomerBParser, Dispatcher
from samples.generate_mock_pos import build_customer_a_pdf, build_customer_b_pdf
from tests.factories import ItemA, build_a_pdf, build_b_pdf

TODAY = datetime.now().strftime("%Y/%m/%d")


class TestCustomerA:
    """Free-text layout: fields are scraped line by line."""

    def test_extracts_one_row_per_item_line(self, customer_a_pdf: Path):
        rows = CustomerAParser().parse(str(customer_a_pdf))
        assert len(rows) == 2

    def test_header_fields_are_shared_by_every_row(self, customer_a_pdf: Path):
        rows = CustomerAParser().parse(str(customer_a_pdf))
        for row in rows:
            assert row["Sold-to Party"] == "10001"
            assert row["Ship-to Party"] == "10001"
            assert row["Sold-to Abbreviation"] == "CUST-A"
            assert row["Customer Reference"] == "242445"
            assert row["Customer Reference Date"] == TODAY
            assert row["Upload"] == "Y"
            assert row["ETD"] == "TBD"

    def test_line_item_fields(self, customer_a_pdf: Path):
        first, second = CustomerAParser().parse(str(customer_a_pdf))

        assert first["Customer PO Item No"] == "01"
        assert first["Customer Material"] == "C460-3373"
        assert first["Order Quantity"] == "40"
        assert first["Unit Price"] == "1234.56"

        assert second["Customer PO Item No"] == "02"
        assert second["Customer Material"] == "C650-7790"
        assert second["Order Quantity"] == "7"
        assert second["Unit Price"] == "99.00"

    def test_unit_price_starts_out_equal_to_the_original(self, customer_a_pdf: Path):
        for row in CustomerAParser().parse(str(customer_a_pdf)):
            assert row["Unit Price"] == row["Original Unit Price"]

    def test_sales_document_item_numbers_in_tens(self, customer_a_pdf: Path):
        rows = CustomerAParser().parse(str(customer_a_pdf))
        assert [r["Sales Document Item"] for r in rows] == ["10", "20"]

    def test_crd_is_the_monday_a_week_before_the_delivery_date(self, customer_a_pdf: Path):
        # 2025/04/19 is a Saturday -> Monday of that week is 2025/04/14
        # -> one week of production lead time -> 2025/04/07.
        first, second = CustomerAParser().parse(str(customer_a_pdf))
        assert first["CRD"] == "2025/04/07"
        assert second["CRD"] == "2025/04/21"  # Fri 2025/05/02 -> Mon 04/28 -> 04/21

    def test_crd_falls_back_to_tbd_without_a_delivery_date(self, tmp_path: Path):
        pdf = build_a_pdf(
            tmp_path / "no_date.pdf",
            [ItemA("C460-3373", "40", "1,234.56", "49,382.40", delivery="")],
        )
        (row,) = CustomerAParser().parse(str(pdf))
        assert row["CRD"] == "TBD"

    def test_po_number_falls_back_to_unknown(self, tmp_path: Path):
        pdf = build_a_pdf(
            tmp_path / "no_po.pdf",
            [ItemA("C460-3373", "40", "1,234.56", "49,382.40", "Apr 19, 2025")],
            po_number="",
        )
        (row,) = CustomerAParser().parse(str(pdf))
        assert row["Customer Reference"] == "UNKNOWN"

    def test_lines_without_pcs_are_not_line_items(self, tmp_path: Path):
        # Only the prose paragraphs -> nothing that looks like an item line.
        pdf = build_a_pdf(tmp_path / "empty.pdf", [])
        assert CustomerAParser().parse(str(pdf)) == []


class TestCustomerB:
    """Tabular layout: fields come from a header-mapped table."""

    def test_extracts_one_row_per_table_row(self, customer_b_pdf: Path):
        rows = CustomerBParser().parse(str(customer_b_pdf))
        assert len(rows) == 2

    def test_header_fields(self, customer_b_pdf: Path):
        for row in CustomerBParser().parse(str(customer_b_pdf)):
            assert row["Sold-to Party"] == "10002"
            assert row["Sold-to Abbreviation"] == "CUST-B"
            assert row["Customer Reference"] == "CB-64810"
            assert row["Customer Reference Date"] == "2025/04/19"

    def test_item_code_and_name_land_in_separate_columns(self, customer_b_pdf: Path):
        first, _ = CustomerBParser().parse(str(customer_b_pdf))
        assert first["Customer Material"] == "C948-2452"
        assert first["Module Material"] == "SKU-7919-E85"
        assert first["Order Quantity"] == "59"

    def test_usd_price_is_kept_as_is(self, customer_b_pdf: Path):
        first, _ = CustomerBParser().parse(str(customer_b_pdf))
        assert first["Unit Price"] == "450.0000"
        assert first["Unit Price Currency"] == "USD"

    def test_prices_quoted_in_us_cents_are_converted_to_dollars(self, customer_b_pdf: Path):
        # 12,300 USC is 123.00 USD -- getting this wrong inflates the order
        # value by 100x, so it is worth a test of its own.
        _, second = CustomerBParser().parse(str(customer_b_pdf))
        assert second["Unit Price"] == "123.0000"
        assert second["Unit Price Currency"] == "USD"

    def test_required_arrival_date_becomes_crd(self, customer_b_pdf: Path):
        first, second = CustomerBParser().parse(str(customer_b_pdf))
        assert first["CRD"] == "2025/06/02"
        assert second["CRD"] == "2025/07/14"

    def test_sales_document_item_numbers_in_tens(self, customer_b_pdf: Path):
        rows = CustomerBParser().parse(str(customer_b_pdf))
        assert [r["Sales Document Item"] for r in rows] == ["10", "20"]

    def test_rows_without_an_item_name_are_dropped(self, tmp_path: Path):
        pdf = build_b_pdf(
            tmp_path / "gap.pdf",
            [
                ["CB-1", "2025/04/19", "C948-2452", "SKU-7919-E85", "10", "450", "USD", "2025/06/02"],
                ["", "", "", "", "", "", "", ""],  # spacer row in the customer's template
            ],
        )
        assert len(CustomerBParser().parse(str(pdf))) == 1

    def test_table_without_the_required_headers_is_ignored(self, tmp_path: Path):
        pdf = build_b_pdf(
            tmp_path / "other_table.pdf",
            [["Freight", "Prepaid"], ["Incoterm", "FOB"]],
            columns=["Term", "Value"],
        )
        assert CustomerBParser().parse(str(pdf)) == []

    def test_dmy_dates_are_understood(self, tmp_path: Path):
        pdf = build_b_pdf(
            tmp_path / "dmy.pdf",
            [["CB-2", "19.04.2025", "C948-2452", "SKU-7919-E85", "10", "450", "USD", "02.06.2025"]],
        )
        (row,) = CustomerBParser().parse(str(pdf))
        assert row["Customer Reference Date"] == "2025/04/19"
        assert row["CRD"] == "2025/06/02"


class TestSampleGeneratorRoundTrip:
    """The demo in the README must keep working end to end."""

    def test_customer_a(self, tmp_path: Path, rng):
        pdf = tmp_path / "a.pdf"
        build_customer_a_pdf(pdf, rng, item_count=3)

        parser_cls, rows = Dispatcher().parse(str(pdf))
        assert parser_cls.customer_label == "Customer-A"
        assert len(rows) == 3
        for row in rows:
            assert row["Sold-to Party"] == "10001"
            assert row["Order Quantity"] != ""
            assert row["Customer Reference"]

    def test_customer_b(self, tmp_path: Path, rng):
        pdf = tmp_path / "b.pdf"
        build_customer_b_pdf(pdf, rng, item_count=4)

        parser_cls, rows = Dispatcher().parse(str(pdf))
        assert parser_cls.customer_label == "Customer-B"
        assert len(rows) == 4
        for row in rows:
            assert row["Sold-to Party"] == "10002"
            assert row["Order Quantity"] != ""
            assert row.get("Unit Price Currency") in {"USD", ""}

    @pytest.mark.parametrize("item_count", [1, 5])
    def test_item_count_is_respected(self, tmp_path: Path, rng, item_count: int):
        pdf = tmp_path / f"a{item_count}.pdf"
        build_customer_a_pdf(pdf, rng, item_count=item_count)
        _, rows = Dispatcher().parse(str(pdf))
        assert len(rows) == item_count


class TestParserInternals:
    """Branches that a well-formed PDF never reaches, but a real one might."""

    def test_unreadable_delivery_date_is_passed_through_verbatim(self, tmp_path: Path):
        # Better to hand the operator the raw string than to invent a date.
        pdf = build_a_pdf(
            tmp_path / "odd_month.pdf",
            [ItemA("C460-3373", "40", "1,234.56", "49,382.40", "Xyz 19, 2025")],
        )
        (row,) = CustomerAParser().parse(str(pdf))
        assert row["CRD"] == "Xyz 19, 2025"

    def test_an_empty_table_maps_to_no_columns(self):
        assert CustomerBParser._map_header([]) is None

    def test_a_header_missing_order_qty_maps_to_no_columns(self):
        assert CustomerBParser._map_header([["PO#", "Item Name"]]) is None

    def test_a_row_shorter_than_its_header_does_not_raise(self):
        # pdfplumber occasionally returns a ragged row on a merged cell.
        parser = CustomerBParser()
        base = parser._common_row(po_number="CB-1", po_date="2025/04/19")
        row = parser._row_from_table(["SKU-7919-E85"], {"item_name": 0, "qty": 5}, base)
        assert row is not None
        assert row["Order Quantity"] == "0"
