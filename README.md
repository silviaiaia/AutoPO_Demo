# AutoPO — Purchase Order Ingestion Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status: Portfolio](https://img.shields.io/badge/status-portfolio%20demo-orange.svg)](#about-this-repository)

A Python pipeline that reads customer **purchase-order PDFs**, extracts the
line items (part number, quantity, price, delivery date…), reconciles them
against the company's internal SKU table, and appends them to the
operations team's **"Open Order" Excel workbook** — in one click.

> The production version of this tool currently handles **30+ customer
> formats** across **5 regional workbooks** at a mid-sized electronics
> manufacturer. It replaced a manual copy-paste workflow that took the sales
> operations team **~90 minutes per day** per region.

---

## About this repository

This is a **sanitized public demo** of a tool I designed and shipped at work.
All customer names, part numbers, prices and ERP codes have been replaced
with synthetic data. The real customer-specific PDF formats are represented
here by two fabricated customers, *Customer-A* and *Customer-B*, that
exhibit the two archetypal layouts encountered in production:

| Layout    | Example customer | Why it matters                                   |
| :-------- | :--------------- | :----------------------------------------------- |
| Free-text | *Customer-A*     | No tables; line items detected by regex anchors. |
| Tabular   | *Customer-B*     | Columns mapped by header name via `pdfplumber.extract_tables`. |

The full production system follows the same architecture but extends the
parser registry to every customer the company deals with.

---

## Demo in 30 seconds

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Generate synthetic purchase-order PDFs
python samples/generate_mock_pos.py --out samples/generated --per-layout 2

# 3. Run the pipeline against them
python -m autopo.cli ingest samples/generated/ --workbook out/open_order.xlsx

# 4. (Optional) Launch the GUI
python -m autopo.gui
```

You should see output like:

```
[Customer-A ] customer_a_po_1.pdf: 5 row(s), 2 SKU match(es)
[Customer-B ] customer_b_po_1.pdf: 4 row(s), 1 SKU match(es)
...
Wrote 18 row(s) to out/open_order.xlsx
```

Open `out/open_order.xlsx` and the parsed orders are there, one row per line
item, with dates correctly typed and currencies normalized.

---

## Impact (production deployment)

| Metric                               | Before   | After     |
| :----------------------------------- | :------- | :-------- |
| Manual PO entry time per region/day  | ~90 min  | ~3 min    |
| Transcription errors per week        | 5–10     | ~0        |
| Customer formats supported           | N/A (manual) | 30+   |
| Regions covered                      | 1 at a time | 5 concurrently |

The tool is now used daily by **4 sales-operations teams** across APAC, EU,
US and JP.

---

## Architecture

```
                    ┌──────────────────┐
                    │   PO PDFs (raw)  │
                    └────────┬─────────┘
                             │
                             ▼
                 ┌──────────────────────┐
                 │      Dispatcher      │   — first-page fingerprinting
                 └──────────┬───────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │ Customer-A │  │ Customer-B │  │    ...     │
     │   parser   │  │   parser   │  │            │
     └──────┬─────┘  └──────┬─────┘  └──────┬─────┘
            └───────┬───────┴────────┬──────┘
                    ▼                ▼
             ┌──────────────┐  ┌───────────┐
             │  Normalizer  │◄─┤  Mapper   │   — aliases → canonical code
             │(dates, nums) │  │ SkuLookup │   — part # → internal SKU
             └──────┬───────┘  └───────────┘
                    ▼
             ┌───────────────┐
             │ Excel writer  │   — openpyxl; writes "Open Order" workbook
             └───────────────┘
```

### Module layout

```
src/autopo/
├── config.py            # Canonical columns & synthetic customer registry
├── cli.py               # `python -m autopo.cli ingest ...`
├── gui.py               # Tkinter front-end
├── core/
│   ├── normalize.py     # dates, numbers, key normalization
│   ├── mapper.py        # customer-alias collapsing + SKU lookup
│   └── excel_writer.py  # openpyxl "Open Order" workbook writer
└── parsers/
    ├── base.py          # Abstract BaseParser + auto-registry
    ├── dispatch.py      # First-page fingerprint → parser
    ├── customer_a.py    # Representative free-text parser
    └── customer_b.py    # Representative tabular parser
```

### Design decisions worth calling out

1. **Auto-registering parser plugin system.** New customers are added by
   dropping a new subclass of `BaseParser` into `parsers/` — the dispatcher
   picks it up automatically. No central registry to edit.

2. **Canonical column schema.** Every parser emits rows keyed by the names
   in `STANDARD_COLUMNS`, so the downstream mapper and Excel writer are
   completely customer-agnostic. New customers do not require downstream
   changes.

3. **Customer alias collapsing.** The same customer often has multiple ERP
   codes (different ship-to branches, legacy entities). `CustomerMapper`
   collapses them back to a canonical code before the SKU lookup, so the
   ops team sees one consistent row per order regardless of which code the
   PO carries.

4. **Locale-aware date + number parsing.** European POs use `19.04.2025`
   and `1.234,56`; US POs use `04/19/2025` and `1,234.56`; Japanese POs use
   `2025/4/19`. The normalizer handles all of these with a family of
   parsers the customer parser explicitly selects, avoiding ambiguity.

5. **Production coupling isolated.** The production version talks to a
   live Excel session via `xlwings` (on Windows) so ops can watch rows
   appear in real time. This repo uses `openpyxl` against a file on disk
   so the demo runs anywhere. The dispatcher and parsers are identical —
   the only swap is the final writer.

---

## Adding a new customer

```python
# src/autopo/parsers/customer_c.py
from autopo.parsers.base import BaseParser

class CustomerCParser(BaseParser):
    customer_label = "Customer-C"
    customer_code  = "20001"
    customer_abbr  = "CUST-C"
    fingerprints   = ("Customer-C GmbH",)

    def _extract(self, pdf):
        rows = []
        # ...read pdf.pages, emit rows keyed by STANDARD_COLUMNS...
        return rows
```

Register it in `src/autopo/parsers/__init__.py` and it's live — the
dispatcher, mapper and Excel writer require no changes.

---

## Testing

```bash
pytest
```

The suite covers:

* `core/normalize.py` — every date format and numeric-locale combination
  encountered in production.
* An **end-to-end smoke test** that generates a synthetic PDF with
  `reportlab`, feeds it through the dispatcher, and checks that the parsed
  rows satisfy key invariants.

---

## Screenshots

`docs/screenshots/` has the GUI screenshot and a 20-row sample of the
resulting Excel workbook. (Placeholders in this demo — swap in your own
after running the pipeline.)

---

## What I would do next

If I were to keep investing in this as a product rather than an internal
tool, the first additions on my list would be:

* **ML fallback parser** — train a layout-aware model (e.g. LayoutLMv3) so
  that an unrecognised customer format degrades gracefully to a
  best-effort extraction instead of an outright skip.
* **Amount / currency validation** — cross-check `qty × unit_price == total`
  and flag drift against an FX source.
* **Audit trail** — emit a JSONL log of `(pdf_hash, parser, rows, matched,
  unmatched)` for every run, so ops can trace back any anomaly.
* **Web front-end** — replace Tkinter with a FastAPI + HTMX UI that any
  operator can hit over the intranet without a local install.

---

## License

[MIT](LICENSE). The code in this repository is original and contains no
proprietary data.
