from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List

import pdfplumber

from autopo.config import STANDARD_COLUMNS

PoRow = Dict[str, str]


class BaseParser(ABC):
    customer_label: str = ""
    customer_code: str = ""
    customer_abbr: str = ""
    fingerprints: tuple = ()
    _registry: List["BaseParser"] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "fingerprints", None):
            BaseParser._registry.append(cls)

    @classmethod
    def all(cls) -> List["BaseParser"]:
        return list(cls._registry)

    @classmethod
    def detect(cls, text: str) -> bool:
        upper = (text or "").upper()
        return any(fp.upper() in upper for fp in cls.fingerprints)

    def parse(self, pdf_path: str) -> List[PoRow]:
        with pdfplumber.open(pdf_path) as pdf:
            return self._extract(pdf)

    def _common_row(self, po_number: str, po_date: str) -> PoRow:
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

    @abstractmethod
    def _extract(self, pdf: pdfplumber.PDF) -> List[PoRow]:
        ...
