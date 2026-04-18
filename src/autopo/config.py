# Canonical columns and customer registry. Production pulls this from the
# ERP; the demo ships synthetic codes that mimic the shape.

from dataclasses import dataclass, field
from typing import Dict, List


# Every parser emits rows keyed by these values so the writer stays generic.
STANDARD_COLUMNS: Dict[str, str] = {
    "upload": "Upload",
    "sales_doc": "Sales Document",
    "sales_doc_item": "Sales Document Item",
    "soldto_abbr": "Sold-to Abbreviation",
    "shipto_abbr": "Ship-to Abbreviation",
    "customer_ref_date": "Customer Reference Date",
    "soldto": "Sold-to Party",
    "shipto": "Ship-to Party",
    "customer_ref": "Customer Reference",
    "customer_po_item": "Customer PO Item No",
    "material": "Material",
    "module_material": "Module Material",
    "customer_material": "Customer Material",
    "order_qty": "Order Quantity",
    "unit_price": "Unit Price",
    "original_unit_price": "Original Unit Price",
    "crd": "CRD",
    "etd": "ETD",
    "eta": "ETA",
    "remark": "Remark",
    "amount": "Amount",
    "currency": "Unit Price Currency",
}

DATE_COLUMNS = ["Customer Reference Date", "CRD", "ETD", "ETA"]


# A customer can have multiple ERP codes (per ship-to branch, legacy entity,
# etc). The mapper collapses them back to one canonical code.
@dataclass(frozen=True)
class Customer:
    code: str
    name: str
    region: str
    aliases: List[str] = field(default_factory=list)


CUSTOMERS: List[Customer] = [
    Customer("10001", "Customer-A",   "APAC", ["10001", "10901"]),
    Customer("10002", "Customer-B",   "APAC", ["10002"]),
    Customer("20001", "Customer-C",   "US",   ["20001", "20501"]),
    Customer("30001", "Customer-D",   "EU",   ["30001", "30201"]),
    Customer("30002", "Customer-E",   "EU",   ["30002"]),
    Customer("40001", "Customer-F",   "JP",   ["40001"]),
]


def build_alias_lookup() -> Dict[str, str]:
    """Flatten aliases -> canonical customer code."""
    table: Dict[str, str] = {}
    for cust in CUSTOMERS:
        for alias in cust.aliases or [cust.code]:
            table[alias] = cust.code
    return table


REGIONS = sorted({c.region for c in CUSTOMERS})
