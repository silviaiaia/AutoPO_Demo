"""
Base class for customer-specific PO parsers.

Each customer issues POs in their own layout — different column orders,
different units, different date formats, sometimes text-based, sometimes
table-based. The base class captures what they all have in common; subclasses
supply the per-customer logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List

import pdfplumber

from autopo.config import STANDARD_COLUMNS

PoRow = Dict[str, str]


class BaseParser(ABC):
    """Abstract base for every customer parser."""

    #: A unique label shown in logs and the GUI.
    customer_label: str = ""

    #: Anonymized ERP code for this customer.
    customer_code: str = ""

    #: Short abbreviation used by sales ops.
    customer_abbr: str = ""

    #: Substrings on the first page that identify this customer. Matched
    #: case-insensitively; the first parser whose fingerprint matches wins.
    fingerprints: tuple = ()

    # Hook the dispatcher uses to auto-register subclasses.
    _registry: List["BaseParser"] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "fingerprints", None):
            BaseParser._registry.append(cls)

    # ------------------------------------------------------------------ API --

    @classmethod
    def all(cls) -> List["BaseParser"]:
        return list(cls._registry)

    @classmethod
    def detect(cls, text: str) -> bool:
        """Return True if the given first-page text belongs to this customer."""
        upper = (text or "").upper()
        return any(fp.upper() in upper for fp in cls.fingerprints)

    def parse(self, pdf_path: str) -> List[PoRow]:
        """Open the PDF and hand the document to ``_extract``."""
        with pdfplumber.open(pdf_path) as pdf:
            return self._extract(pdf)

    # --------------------------------------------------------------- common --

    def _common_row(self, po_number: str, po_date: str) -> PoRow:
        """Return the row fields every line item for this customer shares."""
        col = STANDARD_COLUMNS
        return {
            col["upload"]: "Y",
            col["soldto"]: self.customer_code,
            col["shipto"]: self.customer_code,
            col["soldto_abbr"]: self.customer_abbr,
            col["shipto_abbr"]: self.customer_abbr,
            col["customer_ref"]: po_number,
            col["customer_ref_date"]: po_date or datetime.now().strftime("%Y/%m/%d"),
            col["etd"]: "TBD",
        }

    # --------------------------------------------------------------- hooks --

    @abstractmethod
    def _extract(self, pdf: pdfplumber.PDF) -> List[PoRow]:
        """Pull out the line items from an already-open PDF."""
