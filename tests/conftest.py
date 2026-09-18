"""Shared fixtures.

The PDF builders live in :mod:`tests.factories`.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from tests.factories import ItemA, build_a_pdf, build_b_pdf


@pytest.fixture()
def rng() -> random.Random:
    """Seeded RNG so the sample generator produces the same PDFs every run."""
    return random.Random(42)


@pytest.fixture()
def customer_a_pdf(tmp_path: Path) -> Path:
    """Two line items with values the assertions can hard-code."""
    return build_a_pdf(
        tmp_path / "customer_a.pdf",
        [
            ItemA("C460-3373", "40", "1,234.56", "49,382.40", "Apr 19, 2025"),
            ItemA("C650-7790", "7", "99.00", "693.00", "May 02, 2025"),
        ],
    )


@pytest.fixture()
def customer_b_pdf(tmp_path: Path) -> Path:
    """One USD line and one quoted in US cents, to exercise the conversion."""
    return build_b_pdf(
        tmp_path / "customer_b.pdf",
        [
            ["CB-64810", "2025/04/19", "C948-2452", "SKU-7919-E85", "59", "450", "USD", "2025/06/02"],
            ["CB-64810", "2025/04/19", "C135-9971", "SKU-4997-B14", "33", "12,300", "USC", "2025/07/14"],
        ],
    )
