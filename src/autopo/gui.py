from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from autopo.core.excel_writer import append_rows
from autopo.core.mapper import CustomerMapper, SkuEntry, SkuLookup, enrich_rows
from autopo.parsers import Dispatcher, ParserNotFound


APP_TITLE = "AutoPO"


class AutoPoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("720x520")
        self.resizable(True, True)

        self.source_var = tk.StringVar()
        self.workbook_var = tk.StringVar(value=str(Path("out/open_order.xlsx").resolve()))

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        frm = ttk.Frame(self)
        frm.pack(fill="x", **pad)

        ttk.Label(frm, text="Source folder (PDFs):").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.source_var, width=60).grid(row=0, column=1, sticky="ew")
        ttk.Button(frm, text="Browse...", command=self._pick_source).grid(row=0, column=2, padx=4)

        ttk.Label(frm, text="Target workbook:").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.workbook_var, width=60).grid(row=1, column=1, sticky="ew")
        ttk.Button(frm, text="Save as...", command=self._pick_workbook).grid(row=1, column=2, padx=4)

        frm.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)
        self.run_btn = ttk.Button(btn_frame, text="Ingest", command=self._run)
        self.run_btn.pack(side="left")
        ttk.Button(btn_frame, text="Clear log", command=self._clear_log).pack(side="left", padx=8)

        self.log = tk.Text(self, height=20, wrap="word", font=("Courier", 10))
        self.log.pack(fill="both", expand=True, padx=8, pady=8)
        self.log.configure(state="disabled")

    def _pick_source(self) -> None:
        folder = filedialog.askdirectory(title="Select folder containing PO PDFs")
        if folder:
            self.source_var.set(folder)

    def _pick_workbook(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Select target workbook",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if path:
            self.workbook_var.set(path)

    def _log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _run(self) -> None:
        source = self.source_var.get().strip()
        workbook = self.workbook_var.get().strip()
        if not source or not Path(source).exists():
            messagebox.showerror(APP_TITLE, "Please pick a folder that exists.")
            return
        if not workbook:
            messagebox.showerror(APP_TITLE, "Please choose a destination workbook.")
            return

        self.run_btn.configure(state="disabled")
        thread = threading.Thread(target=self._run_worker, args=(source, workbook), daemon=True)
        thread.start()

    def _run_worker(self, source: str, workbook: str) -> None:
        try:
            dispatcher = Dispatcher()
            mapper = CustomerMapper()
            sku_lookup = SkuLookup()
            sku_lookup.add("10001", SkuEntry("INT-0001", "ATP-1234-A10", "C123-4567"))
            sku_lookup.add("10002", SkuEntry("INT-0002", "SKU-5678-B20", "C234-5678"))

            pdfs = sorted(p for p in Path(source).iterdir() if p.suffix.lower() == ".pdf")
            if not pdfs:
                self._log(f"No PDFs in {source}.")
                return

            total = 0
            for pdf in pdfs:
                try:
                    parser_cls, rows = dispatcher.parse(str(pdf))
                except ParserNotFound as exc:
                    self._log(f"[skip] {pdf.name}: {exc}")
                    continue
                matched = enrich_rows(rows, sku_lookup, mapper)
                append_rows(workbook, rows)
                total += len(rows)
                self._log(f"[{parser_cls.customer_label:10}] {pdf.name}: "
                          f"{len(rows)} row(s), {matched} matched")

            self._log(f"\nDone. Wrote {total} row(s) to {workbook}.")
        except Exception as exc:
            self._log(f"Error: {exc}")
        finally:
            self.run_btn.configure(state="normal")


def main() -> None:
    AutoPoApp().mainloop()


if __name__ == "__main__":
    main()
