# Generate synthetic PO PDFs

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)



ADJECTIVES = ["Quantum", "Nimbus", "Apex", "Vertex", "Halcyon", "Orion"]
NOUNS = ["Systems", "Dynamics", "Analytics", "Robotics", "Networks"]


def synth_part_number(rng: random.Random, prefix: str = "ATP") -> str:
    return f"{prefix}-{rng.randint(1000, 9999)}-{rng.choice('ABCDE')}{rng.randint(10, 99)}"


def synth_customer_pn(rng: random.Random) -> str:
    return f"C{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"


# Customer-A

def build_customer_a_pdf(out_path: Path, rng: random.Random, *, item_count: int = 5):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out_path), pagesize=A4, title="Customer-A PO")
    story = []

    story.append(Paragraph("<b>Customer-A Electronics</b>", styles["Title"]))
    story.append(Paragraph("1 Mock Industrial Park, Nowhere", styles["Normal"]))
    story.append(Spacer(1, 12))

    po_number = rng.randint(200000, 299999)
    story.append(Paragraph(f"ORDER NO: {po_number}", styles["Heading2"]))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Item lines are free-text: "<item#> <part> <qty> PCS <price> <amount>"
    for n in range(1, item_count + 1):
        part = synth_part_number(rng)
        cust_pn = synth_customer_pn(rng)
        qty = rng.randint(10, 200)
        price = round(rng.uniform(25, 499), 2)
        amount = round(qty * price, 2)
        delivery = (datetime.now() + timedelta(days=rng.randint(21, 90))).strftime("%b %d, %Y")

        story.append(Paragraph(
            f"{n:02d} {cust_pn} {qty} PCS {price:,.2f} {amount:,.2f}",
            ParagraphStyle("item", parent=styles["Normal"], fontName="Courier", fontSize=10),
        ))
        story.append(Paragraph(f"Manufacturer part: {part}", styles["Normal"]))
        story.append(Paragraph(f"Delivery date: {delivery}", styles["Normal"]))
        story.append(Spacer(1, 6))

    doc.build(story)


# Customer-B (tabular layout)

def build_customer_b_pdf(out_path: Path, rng: random.Random, *, item_count: int = 4):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out_path), pagesize=A4, title="Customer-B PO")
    story = []

    story.append(Paragraph("<b>Customer-B Corporation</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    po_number = f"CB-{rng.randint(10000, 99999)}"
    header = [
        "PO#", "PO Date", "Item Code", "Item Name",
        "Order Qty", "Unit Price", "Currency", "Required Arrival Date",
    ]
    data: List[List[str]] = [header]

    po_date = datetime.now().strftime("%Y/%m/%d")
    for _ in range(item_count):
        cust_pn = synth_customer_pn(rng)
        part = synth_part_number(rng, prefix="SKU")
        qty = rng.randint(5, 120)
        use_cents = rng.random() < 0.3
        price = rng.randint(50, 500) * (100 if use_cents else 1)
        currency = "USC" if use_cents else "USD"
        eta = (datetime.now() + timedelta(days=rng.randint(14, 75))).strftime("%Y/%m/%d")
        data.append([po_number, po_date, cust_pn, part, str(qty), f"{price:,}", currency, eta])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("ALIGN",      (4, 1), (5, -1), "RIGHT"),
    ]))
    story.append(table)
    doc.build(story)


LAYOUTS = {
    "customer_a": build_customer_a_pdf,
    "customer_b": build_customer_b_pdf,
}


def main():
    ap = argparse.ArgumentParser(description="Generate synthetic PO PDFs.")
    ap.add_argument("--out", default="samples/generated", help="output directory")
    ap.add_argument("--layouts", nargs="+", default=list(LAYOUTS), choices=list(LAYOUTS))
    ap.add_argument("--per-layout", type=int, default=2,
                    help="how many PDFs to generate per layout (default 2)")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    written = []
    for layout in args.layouts:
        builder = LAYOUTS[layout]
        for i in range(1, args.per_layout + 1):
            path = out / f"{layout}_po_{i}.pdf"
            builder(path, rng)
            written.append(path)
            print(f"[+] wrote {path}")

    print(f"\nGenerated {len(written)} synthetic PO(s) in {out}/")


if __name__ == "__main__":
    main()
