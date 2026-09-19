from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from autopo.core.pipeline import DEFAULT_WORKBOOK, FileResult, collect_pdfs, ingest

APP_TITLE = "AutoPO"

# How often the main thread drains the worker's messages.
_POLL_MS = 100

# Posted by the worker when it has finished, however it finished.
_RUN_FINISHED = object()


class AutoPoApp(tk.Tk):
    """Tk front-end over autopo.core.pipeline.

    Tk is not thread-safe: only the thread that created a widget may touch it.
    The ingest run therefore happens on a worker thread that never calls a
    widget directly -- it puts messages on `self._events`, and `_drain_events`
    (which the main thread reschedules onto itself) is the single place where
    the log pane and the button are updated.
    """

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("720x520")
        self.resizable(True, True)

        self.source_var = tk.StringVar()
        self.workbook_var = tk.StringVar(value=str(Path(DEFAULT_WORKBOOK).resolve()))
        self._events: "queue.Queue[object]" = queue.Queue()

        self._build_ui()
        self.after(_POLL_MS, self._drain_events)

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

    # ----- main-thread handlers -------------------------------------------

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

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _drain_events(self) -> None:
        """Apply whatever the worker has posted. Main thread only."""
        try:
            while True:
                event = self._events.get_nowait()
                if event is _RUN_FINISHED:
                    self.run_btn.configure(state="normal")
                else:
                    self._append_log(str(event))
        except queue.Empty:
            pass
        self.after(_POLL_MS, self._drain_events)

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
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
        thread = threading.Thread(
            target=self._run_worker, args=(source, workbook), daemon=True
        )
        thread.start()

    # ----- worker thread ---------------------------------------------------

    def _post(self, message: str) -> None:
        """Queue a line for the main thread. Safe from any thread."""
        self._events.put(message)

    def _report(self, result: FileResult) -> None:
        if result.was_skipped:
            self._post(f"[skip] {result.path.name}: {result.skipped}")
        else:
            self._post(f"[{result.customer_label:10}] {result.path.name}: "
                       f"{result.rows} line(s), {result.matched} SKU match(es)")

    def _run_worker(self, source: str, workbook: str) -> None:
        """Runs off the main thread: no widget may be touched from here."""
        try:
            pdfs = collect_pdfs(source)
            if not pdfs:
                self._post(f"No PDFs in {source}.")
                return

            summary = ingest(pdfs, workbook, on_file=self._report)
            self._post(f"\nDone. Wrote {summary.total_rows} row(s) to {workbook}.")
        except Exception as exc:
            self._post(f"Error: {exc}")
        finally:
            self._events.put(_RUN_FINISHED)


def main() -> None:
    AutoPoApp().mainloop()


if __name__ == "__main__":
    main()
