# Value normalization shared by every parser. The "same" value arrives in
# half a dozen shapes depending on the customer and their ERP.

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional


def normalize_key(value, *, strip_spaces: bool = False) -> str:
    """Normalize a string so near-duplicate spellings compare equal."""
    if value is None:
        return ""
    s = str(value).upper().strip().replace("\xa0", "")
    if s.endswith(".0"):
        s = s[:-2]
    if strip_spaces:
        s = s.replace(" ", "").replace("-", "")
    return s


# Same customer sometimes sends "03/04/2025" meaning DMY, sometimes MDY — so
# each customer parser picks the right handler explicitly.

_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    # common German / Dutch spellings we encountered in production
    "MAI": 5, "OKT": 10, "DEZ": 12,
}

ISO = "%Y/%m/%d"


def _finalize(y: int, m: int, d: int) -> str:
    if y < 100:
        y += 2000
    return f"{y:04d}/{m:02d}/{d:02d}"


def parse_date_iso(text: str) -> Optional[str]:
    """2025-04-19, 2025/04/19, 2025.04.19 -> YYYY/MM/DD."""
    m = re.match(r"^\s*(\d{4})[-./](\d{1,2})[-./](\d{1,2})\s*$", text or "")
    if m:
        y, mo, d = map(int, m.groups())
        return _finalize(y, mo, d)
    return None


def parse_date_dmy(text: str) -> Optional[str]:
    """19.04.2025, 19/04/25 -> YYYY/MM/DD."""
    m = re.match(r"^\s*(\d{1,2})[-./\s](\d{1,2})[-./\s](\d{2,4})\s*$", text or "")
    if m:
        d, mo, y = map(int, m.groups())
        return _finalize(y, mo, d)
    return None


def parse_date_mdy(text: str) -> Optional[str]:
    """04/19/2025 -> YYYY/MM/DD."""
    m = re.match(r"^\s*(\d{1,2})[-./\s](\d{1,2})[-./\s](\d{2,4})\s*$", text or "")
    if m:
        mo, d, y = map(int, m.groups())
        return _finalize(y, mo, d)
    return None


def parse_date_textual(text: str) -> Optional[str]:
    """Apr 19, 2025 / 19 APR 2025 -> YYYY/MM/DD."""
    if not text:
        return None
    s = text.upper()
    for name, mo in _MONTHS.items():
        if name in s:
            nums = [int(n) for n in re.findall(r"\d+", s)]
            if len(nums) >= 2:
                # Two numbers: assume (day, year) with the month word in
                # between. The longer number is the year.
                if len(nums) == 2:
                    d, y = (nums[0], nums[1]) if nums[1] > 31 else (nums[1], nums[0])
                else:  # three numbers — pick the largest as year
                    y = max(nums)
                    rest = [n for n in nums if n != y]
                    d = min(rest)
                return _finalize(y, mo, d)
    return None


def parse_date(text: str) -> Optional[str]:
    """Try every strategy in order; return None if none stuck."""
    for fn in (parse_date_iso, parse_date_textual, parse_date_dmy):
        result = fn(text)
        if result:
            return result
    return None


def shift_to_monday(iso_date: str, weeks_offset: int = 0) -> str:
    """Snap to the Monday of that ISO week (warehouse ships weekly)."""
    dt = datetime.strptime(iso_date, ISO)
    monday = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    monday = monday.fromordinal(monday.toordinal() - monday.weekday())
    if weeks_offset:
        monday = monday.fromordinal(monday.toordinal() + weeks_offset * 7)
    return monday.strftime(ISO)


def clean_number(text: str) -> str:
    """Strip currency symbols; fix European vs US decimal separators."""
    if not text:
        return "0"
    s = re.sub(r"[^\d.,\-]", "", str(text))
    if "," in s and "." in s:
        # The last of the two is assumed to be the decimal separator.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # Ambiguous; if there are exactly two digits after the comma assume
        # decimal, otherwise assume thousands.
        if re.match(r"^-?\d+,\d{1,2}$", s):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    return s
