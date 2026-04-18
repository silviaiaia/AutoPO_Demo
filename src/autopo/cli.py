# CLI entry point.
#   python -m autopo.cli ingest samples/generated/ --workbook out/open_order.xlsx

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from autopo.core.excel_writer import append_rows
from autopo.core.mapper import CustomerMapper, SkuEntry, SkuLookup, enrich_rows
from autopo.parsers import Dispatcher, ParserNotFound


def _demo_sku_lookup() -> SkuLookup:
    # Tiny fake SKU table so the demo shows non-zero match counts.
    entries = [
        ("10001", SkuEntry(material="INT-0001", module_material="ATP-1234-A10", customer_material="C123-4567")),
        ("10002", SkuEntry(material="INT-0002", module_material="SKU-5678-B20", customer_material="C234-5678")),
    ]
    lookup = SkuLookup()
    for code, entry in entries:
        lookup.add(code, entry)
    return lookup


def cmd_ingest(args: argparse.Namespace) -> int:
    source = Path(args.source)
    if not source.exists():
        print(f"error: source path {source} does not exist", file=sys.stderr)
        return 2

    pdfs = (
        [source] if source.is_file()
        else sorted(p for p in source.iterdir() if p.suffix.lower() == ".pdf")
    )
    if not pdfs:
        print(f"no PDFs under {source}")
        return 1

    dispatcher = Dispatcher()
    mapper = CustomerMapper()
    sku_lookup = _demo_sku_lookup()

    total = 0
    for pdf in pdfs:
        try:
            parser_cls, rows = dispatcher.parse(str(pdf))
        except ParserNotFound as exc:
            print(f"[skip] {pdf.name}: {exc}")
            continue

        matched = enrich_rows(rows, sku_lookup, mapper)
        print(f"[{parser_cls.customer_label:10}] {pdf.name}: "
              f"{len(rows)} line(s), {matched} SKU match(es)")

        append_rows(args.workbook, rows, sheet_name=args.sheet)
        total += len(rows)

    print(f"\nWrote {total} row(s) to {args.workbook}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="autopo")
    sub = p.add_subparsers(dest="cmd", required=True)

    ingest = sub.add_parser("ingest", help="parse PDFs and append to a workbook")
    ingest.add_argument("source", help="PDF file or directory of PDFs")
    ingest.add_argument("--workbook", default="out/open_order.xlsx")
    ingest.add_argument("--sheet", default="OpenOrder")
    ingest.set_defaults(func=cmd_ingest)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
