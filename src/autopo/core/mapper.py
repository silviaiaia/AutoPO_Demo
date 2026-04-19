from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

from autopo.config import Customer, build_alias_lookup
from autopo.core.normalize import normalize_key


@dataclass(frozen=True)
class SkuEntry:
    material: str
    module_material: str
    customer_material: str


class CustomerMapper:
    def __init__(self):
        self._aliases = build_alias_lookup()

    def canonical(self, code: str) -> str:
        code = normalize_key(code)
        return self._aliases.get(code, code)


class SkuLookup:
    def __init__(self, entries: Iterable[Tuple[str, SkuEntry]] | None = None):
        self._db: Dict[Tuple[str, str], SkuEntry] = {}
        if entries:
            for cust_code, entry in entries:
                self.add(cust_code, entry)

    def add(self, customer_code: str, entry: SkuEntry) -> None:
        cust = normalize_key(customer_code)
        if entry.module_material:
            self._db[(cust, normalize_key(entry.module_material, strip_spaces=True))] = entry
        if entry.customer_material:
            self._db[(cust, normalize_key(entry.customer_material, strip_spaces=True))] = entry

    def lookup(self, customer_code: str, key: str) -> Optional[SkuEntry]:
        return self._db.get(
            (normalize_key(customer_code), normalize_key(key, strip_spaces=True))
        )

    def __len__(self) -> int:
        return len(self._db)


def enrich_rows(rows, sku_lookup: SkuLookup, mapper: CustomerMapper) -> int:
    matched = 0
    for row in rows:
        cust = mapper.canonical(row.get("Sold-to Party", ""))
        for key_field in ("Module Material", "Customer Material"):
            key = row.get(key_field, "")
            if not key:
                continue
            entry = sku_lookup.lookup(cust, key)
            if entry:
                row["Material"] = entry.material
                # If our module number was missing on the PO, backfill it.
                if not row.get("Module Material"):
                    row["Module Material"] = entry.module_material
                matched += 1
                break
    return matched
