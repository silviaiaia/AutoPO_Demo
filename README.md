# AutoPO

[![tests](https://github.com/silviaiaia/AutoPO_Demo/actions/workflows/tests.yml/badge.svg)](https://github.com/silviaiaia/AutoPO_Demo/actions/workflows/tests.yml)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/silviaiaia/AutoPO_Demo/actions/workflows/tests.yml)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Python pipeline that reads customer purchase order PDFs, extracts line items, reconciles them against an internal SKU table, and appends them to the operations team's shipment-tracking Excel workbook.

This system was originally built at a mid-sized electronics manufacturer to replace a manual copy-paste workflow that took ~90 minutes per day per region. The production version now handles 60+ customer PO formats across 5 regional workbooks and is used daily by 4 sales-operations teams in APAC, EU, US and JP.

This repository is a **sanitized public demo**. Customer names, part numbers, prices and ERP codes are all synthetic. Two representative parsers — _Customer-A_ and _Customer-B_ — stand in for the two archetypes of PO PDF encountered.

## Impact

| Metric                            | Before     | After  |
| :-------------------------------- | :--------- | :----- |
| PO entry time per region, per day | ~90 min    | ~3 min |
| Transcription errors per week     | 5–10       | ~0     |
| Customer formats supported        | 1 (manual) | 60+    |

## Quick start

**Requirements:** Python 3.10 or newer.

Check what you have:

```bash
python3 --version
```

If it's 3.10 or newer, use `python3` in the venv step below. If it's older
(macOS ships 3.9), install a newer one and use that binary instead —
`brew install python@3.12` gives you `python3.12`.

### macOS / Linux

```bash
git clone https://github.com/silviaiaia/AutoPO_Demo.git
cd AutoPO_Demo

python3 -m venv .venv      # or python3.12, python3.11, ... — see above
source .venv/bin/activate

pip install --upgrade pip
pip install -e .

python samples/generate_mock_pos.py --out samples/generated
autopo ingest samples/generated/ --workbook out/open_order.xlsx
```

### Windows (PowerShell)

```powershell
git clone https://github.com/silviaiaia/AutoPO_Demo.git
cd AutoPO_Demo

py -3 -m venv .venv
.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -e .

python samples\generate_mock_pos.py --out samples\generated
autopo ingest samples\generated\ --workbook out\open_order.xlsx
```

Expected output:

```
Generated 4 synthetic PO(s) in samples/generated/

[Customer-A] customer_a_po_1.pdf: 5 line(s), 5 SKU match(es)
[Customer-A] customer_a_po_2.pdf: 5 line(s), 5 SKU match(es)
[Customer-B] customer_b_po_1.pdf: 4 line(s), 4 SKU match(es)
[Customer-B] customer_b_po_2.pdf: 4 line(s), 4 SKU match(es)

Wrote 18 row(s) to out/open_order.xlsx
```

The result is written to `out/open_order.xlsx` — the directory is created if
it does not exist.

`autopo` is installed by `pip install -e .`; `python -m autopo.cli ingest ...`
is the same thing if you would rather not rely on the console script being on
your PATH. `autopo ingest --help` lists the options.

### Running it twice

A PO that is already in the workbook is reported, not blocked:

```
[Customer-A] customer_a_po_1.pdf: 5 line(s), 5 SKU match(es)
[warn      ] customer_a_po_1.pdf: 5 line(s) already in this workbook
...

Wrote 18 row(s) to out/open_order.xlsx (18 duplicate line(s))
```

The ERP import refuses a duplicate order at upload, so the rows still go in —
the warning only means the operator hears about it now rather than later.

### GUI

```bash
autopo-gui
```

> On macOS, the Tkinter GUI needs Tk installed alongside Python.
> With Homebrew: `brew install python-tk`

## Screenshots

### AutoPO GUI

<!-- To refresh this shot: run `autopo-gui`, set the source to
     samples/generated and the target to out/open_order.xlsx, press Ingest,
     then capture the window and overwrite docs/screenshots/gui.png. -->

<p align="center">
  <img src="docs/screenshots/gui.png" width="600" alt="GUI">
</p>

### Output Excel

![Output Excel](docs/screenshots/excel.png)

## Architecture

```
    PO PDFs ──▶ Dispatcher ──▶ Customer parser ──┐
                                                 ▼
                              Normalizer + Mapper (dates, SKUs, aliases)
                                                 │
                                                 ▼
                                          Excel writer
```

```
src/autopo/
├── config.py                # canonical columns + synthetic customer registry
├── cli.py                   # `python -m autopo.cli ingest ...`
├── gui.py                   # Tkinter front-end
├── core/
│   ├── pipeline.py          # the ingest run, shared by the CLI and the GUI
│   ├── normalize.py         # dates, numbers, key canonicalization
│   ├── mapper.py            # customer-alias collapsing + SKU lookup
│   └── excel_writer.py      # openpyxl writer for the Open Order workbook
└── parsers/
    ├── base.py              # BaseParser + auto-registry
    ├── dispatch.py          # first-page fingerprint → parser
    ├── customer_a.py        # free-text layout
    └── customer_b.py        # tabular layout
```

New customers are added by dropping another `BaseParser` subclass into
`parsers/` — the dispatcher, mapper and writer need no changes.

The Open Order workbook is the staging file for an ERP import, and that
importer rejects typed cells — so every value is written as **text**, including
quantities, prices and dates. Quantities therefore will not sum inside Excel.
That is the trade the import requires, and the writer's tests lock it in so a
well-meaning change to "fix" the types fails loudly rather than at upload.

A PO line is identified by the customer's PO number plus their line number,
falling back to their part number for customers whose POs carry no line
numbers. Re-ingesting a PO that is already in the workbook is **reported, not
blocked** — the ERP import refuses a duplicate order at upload, so the
gatekeeper already exists downstream; the warning only moves the news earlier.

The order date is taken from the PO itself, and only falls back to the run date
when the PDF carries no date or one nothing can parse.

The CLI and the GUI are thin shells over `core/pipeline.py`; they differ only
in how they report progress. A PDF the pipeline cannot fingerprint or cannot
open — damaged, encrypted, or simply not a PDF — is reported and skipped, so
one bad file in the drop folder never costs the operator the rest of the batch. Because Tk is not thread-safe, the GUI runs the
pipeline on a worker thread that never touches a widget — it posts messages to
a queue that the main thread drains.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

With coverage:

```bash
pytest --cov --cov-report=term-missing
```

198 tests, 100% statement coverage of everything except the Tkinter front-end
(which has no assertable behaviour without a display server). Every push runs
them on Python 3.10 through 3.13 — see
[`.github/workflows/tests.yml`](.github/workflows/tests.yml).

| Suite                    | What it pins down                                                          |
| :----------------------- | :------------------------------------------------------------------------- |
| `test_normalize.py`      | Date formats (ISO / D-M-Y / M-D-Y / textual, incl. German months), thousands-vs-decimal separators, week-start snapping |
| `test_parsers.py`        | Both PO layouts field by field — CRD lead time, US-cent prices, dropped spacer rows, unreadable dates |
| `test_mapper.py`         | Customer-alias collapsing and SKU matching across inconsistent part-number spellings |
| `test_excel_writer.py`   | Headers written once, appends accumulate, every cell stays text for the ERP import |
| `test_dispatch.py`       | Fingerprint routing, and that an unrecognised PDF is reported rather than guessed at |
| `test_pipeline.py`       | The ingest run itself — progress callbacks, damaged and unrecognised files, totals |
| `test_cli.py`            | The full `ingest` run end to end, plus its exit codes                      |

Parser tests build their own PO PDFs (`tests/factories.py`) with fixed
quantities, prices and dates, so assertions can name an exact CRD or unit
price rather than settling for "something was extracted".

## License

[MIT](LICENSE).
