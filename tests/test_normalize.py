import pytest

from autopo.core.normalize import (
    clean_number,
    normalize_key,
    parse_date,
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
        # Excel and ERP exports turn part numbers into floats.
        assert normalize_key("12345.0") == "12345"

    def test_accepts_non_strings(self):
        assert normalize_key(12345.0) == "12345"

    def test_removes_nbsp(self):
        assert normalize_key("AB\xa0C") == "ABC"

    def test_strip_spaces_option(self):
        assert normalize_key("A B-C", strip_spaces=True) == "ABC"

    def test_strip_spaces_is_off_by_default(self):
        assert normalize_key("A B-C") == "A B-C"

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

    def test_two_digit_years_are_this_century(self):
        assert parse_date_dmy("1/4/25") == "2025/04/01"

    def test_mdy(self):
        assert parse_date_mdy("4/19/2025") == "2025/04/19"

    def test_textual(self):
        assert parse_date_textual("Apr 19, 2025") == "2025/04/19"
        assert parse_date_textual("19 APR 2025") == "2025/04/19"

    def test_textual_handles_german_month_names(self):
        # EU POs arrive with localised month abbreviations.
        assert parse_date_textual("19 DEZ 2025") == "2025/12/19"

    def test_textual_needs_both_a_day_and_a_year(self):
        assert parse_date_textual("MAY 2025") is None

    @pytest.mark.parametrize("bad", ["", None, "not-a-date"])
    def test_garbage(self, bad):
        assert parse_date_iso(bad or "") is None

    @pytest.mark.parametrize(
        "fn", [parse_date_iso, parse_date_dmy, parse_date_mdy, parse_date_textual]
    )
    def test_every_parser_rejects_an_out_of_range_date(self, fn):
        assert fn("2025/19/45") is None

    def test_day_month_ordering_is_rejected_rather_than_guessed_wrong(self):
        # "19" cannot be a month, so the D/M/Y reading of 4/19/2025 is invalid.
        assert parse_date_dmy("4/19/2025") is None


class TestParseDate:
    """The catch-all used when the layout does not pin down the format."""

    def test_prefers_iso(self):
        assert parse_date("2025-04-19") == "2025/04/19"

    def test_handles_textual(self):
        assert parse_date("Apr 19, 2025") == "2025/04/19"

    def test_handles_day_first(self):
        assert parse_date("19/04/2025") == "2025/04/19"

    def test_falls_back_to_month_first_when_day_first_is_impossible(self):
        # A US-style PO date must not come back as month 19.
        assert parse_date("4/19/2025") == "2025/04/19"

    def test_ambiguous_dates_follow_the_day_first_convention(self):
        # 04/05 could be either; the majority of our POs are EU/APAC.
        assert parse_date("04/05/2025") == "2025/05/04"

    @pytest.mark.parametrize("bad", ["", "n/a", "TBD", "not-a-date"])
    def test_unparseable_input_returns_none(self, bad):
        assert parse_date(bad) is None


class TestShiftToMonday:
    def test_snaps_to_prior_monday(self):
        # 2025-04-19 is a Saturday; the Monday of that week is 2025-04-14.
        assert shift_to_monday("2025/04/19") == "2025/04/14"

    def test_a_monday_stays_put(self):
        assert shift_to_monday("2025/04/14") == "2025/04/14"

    def test_week_offset(self):
        # One week earlier.
        assert shift_to_monday("2025/04/19", weeks_offset=-1) == "2025/04/07"

    def test_positive_week_offset(self):
        assert shift_to_monday("2025/04/19", weeks_offset=1) == "2025/04/21"

    def test_offset_can_cross_a_month_boundary(self):
        assert shift_to_monday("2025/05/02", weeks_offset=-1) == "2025/04/21"

    def test_rejects_a_date_it_cannot_read(self):
        with pytest.raises(ValueError):
            shift_to_monday("19/04/2025")


class TestCleanNumber:
    def test_us_style(self):
        assert clean_number("1,234.56") == "1234.56"

    def test_eu_style(self):
        assert clean_number("1.234,56") == "1234.56"

    def test_comma_as_a_decimal_separator(self):
        assert clean_number("1,5") == "1.5"

    def test_comma_as_a_thousands_separator(self):
        assert clean_number("1,500") == "1500"

    def test_strip_symbols(self):
        assert clean_number("USD 99.00") == "99.00"

    def test_keeps_a_negative_sign(self):
        assert clean_number("-1.234,56") == "-1234.56"

    def test_strips_trailing_units(self):
        assert clean_number("40 PCS") == "40"

    def test_empty(self):
        assert clean_number("") == "0"

    def test_none(self):
        assert clean_number(None) == "0"

    @pytest.mark.parametrize("text", ["1,234.56", "1.234,56", "1234.56"])
    def test_result_is_always_float_parseable(self, text):
        # Downstream code calls float() on this without guarding.
        assert float(clean_number(text)) == pytest.approx(1234.56)


class TestKnownLimitations:
    """Documented gaps, so a future fix has a test waiting for it."""

    @pytest.mark.xfail(
        reason="the three-number branch picks the smallest number as the day",
        strict=True,
    )
    def test_textual_date_with_a_trailing_week_number(self):
        assert parse_date_textual("19 APR 2025 W17") == "2025/04/19"
