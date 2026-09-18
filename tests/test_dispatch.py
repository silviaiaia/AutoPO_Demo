from __future__ import annotations

from pathlib import Path

import pytest

from autopo.parsers import (
    BaseParser,
    CustomerAParser,
    CustomerBParser,
    Dispatcher,
    ParserNotFound,
)
from tests.factories import build_plain_pdf


class TestRegistry:
    def test_subclasses_with_fingerprints_register_themselves(self):
        # Adding a customer means dropping in a file -- no registry to edit.
        assert {CustomerAParser, CustomerBParser} <= set(BaseParser.all())

    def test_all_returns_a_copy(self):
        BaseParser.all().clear()
        assert BaseParser.all(), "clearing the returned list must not empty the registry"


class TestDetect:
    def test_matches_its_fingerprint(self):
        assert CustomerAParser.detect("PURCHASE ORDER\nCustomer-A Electronics Ltd.")

    def test_is_case_insensitive(self):
        assert CustomerAParser.detect("customer-a electronics")

    def test_does_not_match_another_customer(self):
        assert not CustomerAParser.detect("Customer-B Corporation")

    @pytest.mark.parametrize("text", ["", None])
    def test_handles_empty_page_text(self, text):
        # A scanned page can extract to nothing at all.
        assert not CustomerAParser.detect(text)


class TestDispatcher:
    def test_routes_to_the_customer_a_parser(self, customer_a_pdf: Path):
        assert Dispatcher().find_parser(str(customer_a_pdf)) is CustomerAParser

    def test_routes_to_the_customer_b_parser(self, customer_b_pdf: Path):
        assert Dispatcher().find_parser(str(customer_b_pdf)) is CustomerBParser

    def test_parse_returns_the_parser_and_its_rows(self, customer_a_pdf: Path):
        parser_cls, rows = Dispatcher().parse(str(customer_a_pdf))
        assert parser_cls is CustomerAParser
        assert len(rows) == 2

    def test_unrecognised_pdf_raises(self, tmp_path: Path):
        pdf = build_plain_pdf(tmp_path / "memo.pdf")
        with pytest.raises(ParserNotFound, match="No parser fingerprint matched"):
            Dispatcher().find_parser(str(pdf))

    def test_only_the_first_page_is_fingerprinted(self, customer_a_pdf: Path):
        # Restricting the candidate list must not change the answer.
        dispatcher = Dispatcher(parsers=[CustomerAParser])
        assert dispatcher.find_parser(str(customer_a_pdf)) is CustomerAParser

    def test_a_restricted_dispatcher_ignores_parsers_it_was_not_given(
        self, customer_b_pdf: Path
    ):
        dispatcher = Dispatcher(parsers=[CustomerAParser])
        with pytest.raises(ParserNotFound):
            dispatcher.find_parser(str(customer_b_pdf))

    def test_pdf_without_pages_raises(self, monkeypatch):
        # A zero-page PDF has no first page to fingerprint.
        class _EmptyPdf:
            pages: list = []

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        monkeypatch.setattr(
            "autopo.parsers.dispatch.pdfplumber.open", lambda *a, **k: _EmptyPdf()
        )
        with pytest.raises(ParserNotFound, match="has no pages"):
            Dispatcher().find_parser("empty.pdf")
