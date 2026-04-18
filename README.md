# AutoPO

Python pipeline that reads customer purchase-order PDFs, extracts line items,
reconciles them against an internal SKU table, and appends them to the
operations team's shipment-tracking Excel workbook.

Built at a mid-sized electronics manufacturer to replace a manual copy-paste
workflow that took ~90 minutes per day per region. The production version now
handles 30+ customer PO formats across 5 regional workbooks and is used daily
by 4 sales-operations teams in APAC, EU, US and JP.

This repository is a **sanitized public demo**. Customer names, part numbers,
prices and ERP codes are all synthetic. Two representative parsers —
*Customer-A* (free-text layout) and *Customer-B* (tabular layout) — stand in
for the two archetypes of PO PDF encountered in production.

## Impact

| Metric                            | Before   | After  |
| :-------------------------------- | :------- | :----- |
| PO entry time per region, per day | ~90 min  | ~3 min |
| Transcription errors per week     | 5–10     | ~0     |
| Customer formats supported        | manual   | 30+    |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# generate synthetic PDFs, then ingest them
python samples/generate_mock_pos.py --out samples/generated
python -m autopo.cli ingest samples/generated/ --workbook out/open_order.xlsx
```

Or launch the GUI:

```bash
python -m autopo.gui
```

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

## Tests

```bash
pytest
```

## License

[MIT](LICENSE).
