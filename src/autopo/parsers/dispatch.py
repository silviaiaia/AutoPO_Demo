"""
Dispatcher: given a PDF path, decide which customer parser to invoke.

The strategy is simple: open the first page, lower-case its text, and ask
each registered parser whether it recognises its fingerprint. First match
wins. If no parser matches, we raise :class:`ParserNotFound` so the caller
can surface a useful error to the operator.
"""

from __future__ import annotations

from typing import Type

import pdfplumber

from autopo.parsers.base import BaseParser


class ParserNotFound(Exception):
    """Raised when no registered parser recognises the PDF's first page."""


class Dispatcher:
    """Singleton-style helper that owns the list of registered parsers."""

    def __init__(self, parsers=None):
        self._parsers = parsers or BaseParser.all()

    def find_parser(self, pdf_path: str) -> Type[BaseParser]:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                raise ParserNotFound(f"{pdf_path} has no pages")
            first = pdf.pages[0].extract_text() or ""

        for parser_cls in self._parsers:
            if parser_cls.detect(first):
                return parser_cls
        raise ParserNotFound(
            f"No parser fingerprint matched the first page of {pdf_path}"
        )

    def parse(self, pdf_path: str):
        parser_cls = self.find_parser(pdf_path)
        parser = parser_cls()
        return parser_cls, parser.parse(pdf_path)
