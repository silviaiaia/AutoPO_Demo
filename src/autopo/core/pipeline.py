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

from autopo.core.excel_writer import append_rows
from autopo.core.mapper import CustomerMapper, build_default_sku_lookup, enrich_rows
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

    results: List[FileResult] = []
    for pdf in pdfs:
        try:
            parser_cls, rows = dispatcher.parse(str(pdf))
        except ParserNotFound as exc:
            result = FileResult(path=pdf, skipped=str(exc))
        else:
            matched = enrich_rows(rows, sku_lookup, mapper)
            append_rows(workbook, rows, sheet_name=sheet)
            result = FileResult(
                path=pdf,
                customer_label=parser_cls.customer_label,
                rows=len(rows),
                matched=matched,
            )

        results.append(result)
        if on_file is not None:
            on_file(result)

    return IngestSummary(results)
