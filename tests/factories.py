"""Builders for the PO PDFs the tests parse.

The sample generator in ``samples/`` randomises quantities, prices and dates,
which is what you want for eyeballing the demo but not for assertions. The
builders here lay out the same two PO formats with values the test supplies,
so a test can pin down an exact CRD or an exact unit price.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass(frozen=True)
class ItemA:
    """One free-text line item on a Customer-A PO."""

    customer_material: str
    qty: str
    price: str
    amount: str
    delivery: str  # e.g. "Apr 19, 2025"
    material: str = "ATP-1042-A17"


def build_a_pdf(
    path: Path,
    items: Sequence[ItemA],
    *,
    po_number: str = "242445",
    po_date: str = "",
    header: str = "Customer-A Electronics",
) -> Path:
    """Customer-A layout: free text, one paragraph per field."""
    styles = getSampleStyleSheet()
    mono = ParagraphStyle("item", parent=styles["Normal"], fontName="Courier", fontSize=10)
    doc = SimpleDocTemplate(str(path), pagesize=A4, title="Customer-A PO")

    story = [Paragraph(f"<b>{header}</b>", styles["Title"])]
    if po_number:
        story.append(Paragraph(f"ORDER NO: {po_number}", styles["Heading2"]))
    if po_date:
        story.append(Paragraph(f"Date: {po_date}", styles["Normal"]))
    story.append(Spacer(1, 12))
    for n, item in enumerate(items, 1):
        story.append(
            Paragraph(
                f"{n:02d} {item.customer_material} {item.qty} PCS {item.price} {item.amount}",
                mono,
            )
        )
        story.append(Paragraph(f"Manufacturer part: {item.material}", styles["Normal"]))
        story.append(Paragraph(f"Delivery date: {item.delivery}", styles["Normal"]))
        story.append(Spacer(1, 6))

    doc.build(story)
    return path


B_HEADER = [
    "PO#",
    "PO Date",
    "Item Code",
    "Item Name",
    "Order Qty",
    "Unit Price",
    "Currency",
    "Required Arrival Date",
]


def build_b_pdf(
    path: Path,
    rows: Sequence[Sequence[str]],
    *,
    header: str = "Customer-B Corporation",
    columns: Sequence[str] = B_HEADER,
) -> Path:
    """Customer-B layout: a bordered table that pdfplumber can lift whole."""
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, title="Customer-B PO")

    data: List[List[str]] = [list(columns)] + [list(r) for r in rows]
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    doc.build([Paragraph(f"<b>{header}</b>", styles["Title"]), Spacer(1, 12), table])
    return path


def build_unreadable_pdf(path: Path) -> Path:
    """A file with a .pdf name that no PDF library can open."""
    path.write_bytes(b"%PDF-1.4\nthis file was truncated in transit")
    return path


def build_plain_pdf(path: Path, text: str = "Just a memo, not a purchase order.") -> Path:
    """A PDF no parser fingerprint should match."""
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, title="Memo")
    doc.build([Paragraph(text, styles["Normal"])])
    return path
