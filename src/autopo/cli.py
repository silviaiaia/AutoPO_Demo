from __future__ import annotations

import argparse
import sys
from pathlib import Path

from autopo.core.pipeline import (
    DEFAULT_SHEET,
    DEFAULT_WORKBOOK,
    FileResult,
    collect_pdfs,
    ingest,
)


def _report(result: FileResult) -> None:
    if result.was_skipped:
        print(f"[skip] {result.path.name}: {result.skipped}")
        return
    print(f"[{result.customer_label:10}] {result.path.name}: "
          f"{result.rows} line(s), {result.matched} SKU match(es)")
    if result.duplicates:
        print(f"[warn      ] {result.path.name}: {result.duplicates} line(s) "
              f"already in this workbook")


def cmd_ingest(args: argparse.Namespace) -> int:
    source = Path(args.source)
    try:
        pdfs = collect_pdfs(source)
    except FileNotFoundError:
        print(f"error: source path {source} does not exist", file=sys.stderr)
        return 2

    if not pdfs:
        print(f"no PDFs under {source}")
        return 1

    summary = ingest(pdfs, args.workbook, sheet=args.sheet, on_file=_report)

    notes = []
    if summary.skipped:
        notes.append(f"{len(summary.skipped)} file(s) skipped")
    if summary.duplicates:
        notes.append(f"{summary.duplicates} duplicate line(s)")
    tail = f" ({', '.join(notes)})" if notes else ""

    print(f"\nWrote {summary.total_rows} row(s) to {args.workbook}{tail}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="autopo")
    sub = p.add_subparsers(dest="cmd", required=True)

    ingest_cmd = sub.add_parser("ingest", help="parse PDFs and append to a workbook")
    ingest_cmd.add_argument("source", help="PDF file or directory of PDFs")
    ingest_cmd.add_argument(
        "--workbook",
        default=DEFAULT_WORKBOOK,
        help="workbook to append to; created if it does not exist "
             f"(default: {DEFAULT_WORKBOOK})",
    )
    ingest_cmd.add_argument(
        "--sheet",
        default=DEFAULT_SHEET,
        help=f"worksheet within the workbook (default: {DEFAULT_SHEET})",
    )
    ingest_cmd.set_defaults(func=cmd_ingest)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
