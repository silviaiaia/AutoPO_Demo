from dataclasses import dataclass, field
from typing import Dict, List

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

SKU_TABLE: List[Dict[str, str]] = [
    # Customer-A
    {"customer": "10001", "material": "ATP-1042-A17", "module_material": "MOD-1042", "customer_material": "C460-3373"},
    {"customer": "10001", "material": "ATP-2318-B44", "module_material": "MOD-2318", "customer_material": "C650-7790"},
    {"customer": "10001", "material": "ATP-3771-C09", "module_material": "MOD-3771", "customer_material": "C270-9357"},
    {"customer": "10001", "material": "ATP-4506-D82", "module_material": "MOD-4506", "customer_material": "C566-1561"},
    {"customer": "10001", "material": "ATP-5920-E33", "module_material": "MOD-5920", "customer_material": "C803-7388"},
    {"customer": "10001", "material": "ATP-6187-A55", "module_material": "MOD-6187", "customer_material": "C296-9709"},
    # Customer-B
    {"customer": "10002", "material": "ATP-7301-B12", "module_material": "SKU-7919-E85", "customer_material": "C948-2452"},
    {"customer": "10002", "material": "ATP-8455-C67", "module_material": "SKU-4997-B14", "customer_material": "C135-9971"},
    {"customer": "10002", "material": "ATP-9012-D28", "module_material": "SKU-2426-A31", "customer_material": "C965-7244"},
    {"customer": "10002", "material": "ATP-1673-E71", "module_material": "SKU-3348-C35", "customer_material": "C879-6317"},
    {"customer": "10002", "material": "ATP-2894-A03", "module_material": "SKU-9846-D44", "customer_material": "C903-9621"},
    {"customer": "10002", "material": "ATP-3560-B96", "module_material": "SKU-9449-D61", "customer_material": "C223-5151"},
]


def build_alias_lookup() -> Dict[str, str]:
    """Flatten aliases -> canonical customer code."""
    table: Dict[str, str] = {}
    for cust in CUSTOMERS:
        for alias in cust.aliases or [cust.code]:
            table[alias] = cust.code
    return table


REGIONS = sorted({c.region for c in CUSTOMERS})
