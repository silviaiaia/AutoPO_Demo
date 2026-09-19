"""The ingest pipeline shared by the CLI and the GUI.

Both front-ends used to carry their own copy of this loop. That is how the GUI
ended up with two hard-coded SKUs the CLI never had, and how it lost the
--sheet option along the way. They now differ only in how they report progress:
the CLI prints, the GUI posts to its log pane.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Union

from autopo.config import STANDARD_COLUMNS
from autopo.core.excel_writer import append_rows, existing_rows
from autopo.core.mapper import CustomerMapper, build_default_sku_lookup, enrich_rows
from autopo.core.normalize import normalize_key
from autopo.parsers import Dispatcher, ParserNotFound

DEFAULT_WORKBOOK = "out/open_order.xlsx"
DEFAULT_SHEET = "OpenOrder"


@dataclass(frozen=True)
class FileResult:
    """What became of one PDF."""

    path: Path
    customer_label: str = ""
    rows: int = 0
    matched: int = 0
    skipped: str = ""  # non-empty holds the reason the file was skipped
    duplicates: int = 0  # lines already present in the workbook

    @property
    def was_skipped(self) -> bool:
        return bool(self.skipped)


@dataclass(frozen=True)
class IngestSummary:
    results: List[FileResult] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        return sum(r.rows for r in self.results)

    @property
    def skipped(self) -> List[FileResult]:
        return [r for r in self.results if r.was_skipped]

    @property
    def duplicates(self) -> int:
        return sum(r.duplicates for r in self.results)


def line_key(row: dict) -> tuple:
    """Identity of one PO line: the customer's PO number and their line number.

    Not every customer numbers their lines -- Customer-B's POs carry no item
    number column at all -- so the customer's part number stands in when there
    is none, which keeps the lines of a single PO distinct from one another.
    """
    col = STANDARD_COLUMNS
    reference = normalize_key(row.get(col["customer_ref"], ""))
    item = normalize_key(row.get(col["customer_po_item"], ""))
    if not item:
        item = normalize_key(row.get(col["customer_material"], ""), strip_spaces=True)
    return reference, item


ProgressCallback = Callable[[FileResult], None]


def collect_pdfs(source: Union[str, Path]) -> List[Path]:
    """The PDFs to ingest: a directory's contents, or the single file given.

    Raises FileNotFoundError if the path does not exist, so each front-end can
    report that in its own idiom.
    """
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(source)
    if source.is_file():
        return [source]
    return sorted(p for p in source.iterdir() if p.suffix.lower() == ".pdf")


def ingest(
    pdfs: Sequence[Path],
    workbook: Union[str, Path] = DEFAULT_WORKBOOK,
    *,
    sheet: str = DEFAULT_SHEET,
    on_file: Optional[ProgressCallback] = None,
) -> IngestSummary:
    """Parse each PDF, resolve its SKUs and append it to the workbook.

    `on_file` is called once per PDF, as soon as that PDF is done, so a caller
    can report progress during a long run rather than only at the end.
    """
    dispatcher = Dispatcher()
    mapper = CustomerMapper()
    sku_lookup = build_default_sku_lookup()

    # Read once up front, then keep it current in memory, so that a PO repeated
    # inside this same batch is caught as well as one already on the sheet.
    seen = {line_key(r) for r in existing_rows(workbook, sheet_name=sheet)}

    results: List[FileResult] = []
    for pdf in pdfs:
        try:
            parser_cls, rows = dispatcher.parse(str(pdf))
        except ParserNotFound as exc:
            result = FileResult(path=pdf, skipped=str(exc))
        except Exception as exc:
            # Damaged, encrypted, or a .pdf that is not one. A customer sends
            # one of these every so often, and it must cost the operator that
            # file rather than the whole batch -- which, before this, it did:
            # a bad file early in the alphabet meant no workbook at all.
            result = FileResult(path=pdf, skipped=f"{type(exc).__name__}: {exc}")
        else:
            matched = enrich_rows(rows, sku_lookup, mapper)

            keys = [line_key(r) for r in rows]
            duplicates = sum(1 for key in keys if key in seen)
            seen.update(keys)

            append_rows(workbook, rows, sheet_name=sheet)
            result = FileResult(
                path=pdf,
                customer_label=parser_cls.customer_label,
                rows=len(rows),
                matched=matched,
                duplicates=duplicates,
            )

        results.append(result)
        if on_file is not None:
            on_file(result)

    return IngestSummary(results)
