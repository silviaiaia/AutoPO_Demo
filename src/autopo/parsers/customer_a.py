"""
Parser for *Customer-A* — a representative "text-layout" PO.

Format quirks we have to cope with:

* PO number is printed as ``ORDER NO: 12345`` on the first page.
* Line items start with a 2-to-4-digit item number and contain the literal
  token ``PCS`` somewhere on the row.
* Prices use US decimal notation (1,234.56).
* Delivery date appears on a *separate* follow-up line prefixed with
  ``Delivery date:`` and written in textual form ("Apr 19, 2025"). The
  warehouse ships on Mondays, so the CRD is snapped to the Monday before.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import List

import pdfplumber

from autopo.config import STANDARD_COLUMNS
from autopo.core.normalize import (
    clean_number,
    parse_date_textual,
    shift_to_monday,
)
from autopo.parsers.base import BaseParser, PoRow


class CustomerAParser(BaseParser):
    customer_label = "Customer-A"
    customer_code = "10001"
    customer_abbr = "CUST-A"
    fingerprints = ("Customer-A Electronics",)

    _ITEM_LINE_RE = re.compile(r"^\s*(\d+)\s+\S+.*\bPCS\b", re.IGNORECASE)
    _PO_RE = re.compile(r"ORDER\s*NO[.:]*\s*(\w+)", re.IGNORECASE)
    _DELIVERY_RE = re.compile(
        r"Delivery\s*date[:\s]*([A-Za-z]{3}\s*\d{1,2}\s*,\s*\d{4})",
        re.IGNORECASE,
    )

    def _extract(self, pdf: pdfplumber.PDF) -> List[PoRow]:
        col = STANDARD_COLUMNS
        rows: List[PoRow] = []

        first_text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
        m = self._PO_RE.search(first_text)
        po_number = m.group(1) if m else "UNKNOWN"

        base = self._common_row(po_number, datetime.now().strftime("%Y/%m/%d"))

        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if not self._ITEM_LINE_RE.match(line):
                    continue

                row = dict(base)
                item_no = self._ITEM_LINE_RE.match(line).group(1)
                row[col["customer_po_item"]] = item_no

                tokens = [t for t in line.split() if t.upper() != "PCS"]
                # After stripping the noise tokens, the customer part number
                # is the second word and the unit price is the second-to-last
                # numeric token.
                row[col["customer_material"]] = tokens[1] if len(tokens) > 1 else ""

                qty_match = re.search(r"([\d.,]+)\s*PCS", line, re.IGNORECASE)
                row[col["order_qty"]] = clean_number(qty_match.group(1)) if qty_match else ""

                numbers = re.findall(r"\d[\d.,]*", line)
                if len(numbers) >= 2:
                    price = clean_number(numbers[-2])
                    row[col["original_unit_price"]] = price
                    row[col["unit_price"]] = price

                # Delivery date on a follow-up line (look ahead up to 10).
                row[col["crd"]] = self._find_crd(lines, i)
                row[col["sales_doc_item"]] = str((len(rows) + 1) * 10)
                rows.append(row)

        return rows

    def _find_crd(self, lines: List[str], start: int) -> str:
        for offset in range(0, 10):
            idx = start + offset
            if idx >= len(lines):
                break
            m = self._DELIVERY_RE.search(lines[idx])
            if not m:
                continue
            iso = parse_date_textual(m.group(1))
            if iso:
                return shift_to_monday(iso, weeks_offset=-1)
            return m.group(1)
        return "TBD"
