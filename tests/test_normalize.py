import pytest

from autopo.core.normalize import (
    clean_number,
    normalize_key,
    parse_date_dmy,
    parse_date_iso,
    parse_date_mdy,
    parse_date_textual,
    shift_to_monday,
)


class TestNormalizeKey:
    def test_trims_and_uppercases(self):
        assert normalize_key("  abc ") == "ABC"

    def test_drops_float_suffix(self):
        assert normalize_key("12345.0") == "12345"

    def test_removes_nbsp(self):
        assert normalize_key("AB\xa0C") == "ABC"

    def test_strip_spaces_option(self):
        assert normalize_key("A B-C", strip_spaces=True) == "ABC"

    def test_none(self):
        assert normalize_key(None) == ""


class TestDateParsing:
    def test_iso_variants(self):
        assert parse_date_iso("2025-04-19") == "2025/04/19"
        assert parse_date_iso("2025/4/9") == "2025/04/09"
        assert parse_date_iso("2025.04.19") == "2025/04/19"

    def test_dmy(self):
        assert parse_date_dmy("19.04.2025") == "2025/04/19"
        assert parse_date_dmy("1/4/25") == "2025/04/01"

    def test_mdy(self):
        assert parse_date_mdy("4/19/2025") == "2025/04/19"

    def test_textual(self):
        assert parse_date_textual("Apr 19, 2025") == "2025/04/19"
        assert parse_date_textual("19 APR 2025") == "2025/04/19"

    @pytest.mark.parametrize("bad", ["", None, "not-a-date"])
    def test_garbage(self, bad):
        assert parse_date_iso(bad or "") is None


class TestShiftToMonday:
    def test_snaps_to_prior_monday(self):
        # 2025-04-19 is a Saturday; the Monday of that week is 2025-04-14.
        assert shift_to_monday("2025/04/19") == "2025/04/14"

    def test_week_offset(self):
        # One week earlier.
        assert shift_to_monday("2025/04/19", weeks_offset=-1) == "2025/04/07"


class TestCleanNumber:
    def test_us_style(self):
        assert clean_number("1,234.56") == "1234.56"

    def test_eu_style(self):
        assert clean_number("1.234,56") == "1234.56"

    def test_strip_symbols(self):
        assert clean_number("USD 99.00") == "99.00"

    def test_empty(self):
        assert clean_number("") == "0"
