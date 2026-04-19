from __future__ import annotations

import random
from pathlib import Path

import pytest

from autopo.parsers import Dispatcher
from samples.generate_mock_pos import build_customer_a_pdf, build_customer_b_pdf


@pytest.fixture()
def rng():
    return random.Random(42)


def test_customer_a_roundtrip(tmp_path: Path, rng):
    pdf = tmp_path / "a.pdf"
    build_customer_a_pdf(pdf, rng, item_count=3)

    parser_cls, rows = Dispatcher().parse(str(pdf))
    assert parser_cls.customer_label == "Customer-A"
    assert len(rows) == 3
    for row in rows:
        assert row["Sold-to Party"] == "10001"
        assert row["Order Quantity"] != ""
        assert row["Customer Reference"]


def test_customer_b_roundtrip(tmp_path: Path, rng):
    pdf = tmp_path / "b.pdf"
    build_customer_b_pdf(pdf, rng, item_count=4)

    parser_cls, rows = Dispatcher().parse(str(pdf))
    assert parser_cls.customer_label == "Customer-B"
    assert len(rows) == 4
    for row in rows:
        assert row["Sold-to Party"] == "10002"
        assert row["Order Quantity"] != ""
        assert row.get("Unit Price Currency") in {"USD", ""}
