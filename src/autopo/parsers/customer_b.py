"""
Parser for *Customer-B* — a representative "table-layout" PO.

Where Customer-A lays out each line item as a run of words on a single text
line, Customer-B ships a real tabular PDF with clear column headers:

    PO#  |  PO Date  |  Item Code  |  Item Name  |  Qty  |  Unit Price  |  Currency  |  Required Arrival Date

That makes it a very different parsing problem: we rely on
``pdfplumber.extract_tables`` and map columns by header name rather than by
position, which makes the parser robust against template tweaks.

The currency column introduces a second quirk — the customer sometimes
quotes prices in US cents (``USC``) instead of dollars, so we divide by 100
when we see that flag.
"""

from __future__ import annotations

import re
from typing import List, Optional

import pdfplumber

from autopo.config import STANDARD_COLUMNS
from autopo.core.normalize import (
    clean_number,
    parse_date_dmy,
    parse_date_iso,
)
from autopo.parsers.base import BaseParser, PoRow


_HEADER_KEYS = {
    "PO DATE": "po_date",
    "PO#": "po",
    "PO #": "po",
    "ITEM CODE": "item_code",
    "ITEM NAME": "item_name",
    "ORDER QTY": "qty",
    "ORDER QUANTITY": "qty",
    "UNIT PRICE": "price",
    "CURRENCY": "currency",
    "REQUIRED ARRIVAL DATE": "crd",
}


class CustomerBParser(BaseParser):
    customer_label = "Customer-B"
    customer_code = "10002"
    customer_abbr = "CUST-B"
    fingerprints = ("Customer-B Corporation",)

    def _extract(self, pdf: pdfplumber.PDF) -> List[PoRow]:
        col = STANDARD_COLUMNS
        rows: List[PoRow] = []
        base = self._common_row(po_number="", po_date="")  # filled per-row

        for page in pdf.pages:
            for table in page.extract_tables() or []:
                col_map = self._map_header(table)
                if col_map is None:
                    continue
                # Every subsequent row is a line item.
                for raw in table[1:]:
                    row = self._row_from_table(raw, col_map, base)
                    if row:
                        row[col["sales_doc_item"]] = str((len(rows) + 1) * 10)
                        rows.append(row)

        return rows

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _map_header(table) -> Optional[dict]:
        """Translate the first row of the table into a column->index map."""
        if not table:
            return None
        header = [str(c or "").strip().upper() for c in table[0]]
        mapping = {}
        for idx, cell in enumerate(header):
            for key, field in _HEADER_KEYS.items():
                if key in cell:
                    mapping[field] = idx
                    break
        # We require the minimum fields needed to make a row useful.
        if not all(f in mapping for f in ("item_name", "qty")):
            return None
        return mapping

    def _row_from_table(self, raw_row, col_map, base) -> Optional[PoRow]:
        col = STANDARD_COLUMNS
        cells = [str(c or "").replace("\n", " ").strip() for c in raw_row]

        def get(field):
            idx = col_map.get(field)
            if idx is None or idx >= len(cells):
                return ""
            return cells[idx]

        item_name = get("item_name")
        if not item_name:
            return None

        row = dict(base)
        row[col["customer_ref"]] = get("po") or row[col["customer_ref"]]

        # PO date may be ISO or DMY depending on the branch; try both.
        po_date = get("po_date")
        row[col["customer_ref_date"]] = (
            parse_date_iso(po_date) or parse_date_dmy(po_date) or po_date
        )

        item_code = get("item_code")
        row[col["customer_material"]] = item_code or item_name
        row[col["module_material"]] = item_name
        row[col["order_qty"]] = clean_number(get("qty"))

        # Unit price + currency
        price = clean_number(get("price"))
        currency = get("currency").upper()
        if price:
            value = float(price or 0)
            if currency == "USC":      # quoted in US cents
                value = value / 100
                currency = "USD"
            row[col["original_unit_price"]] = f"{value:.4f}"
            row[col["unit_price"]] = f"{value:.4f}"
            row[col["currency"]] = currency or "USD"

        crd_raw = get("crd")
        crd = parse_date_iso(crd_raw) or parse_date_dmy(crd_raw)
        row[col["crd"]] = crd or crd_raw or "TBD"

        return row
